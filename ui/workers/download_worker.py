from PyQt6.QtCore import pyqtSignal, QObject, QThread
import os, queue, threading, logging
from downloader.utils import sanitize_filename, search_music_services, download_song, save_download_history, load_download_history, update_mp3_metadata_hybrid
from downloader.spotify import get_spotify_item

class DownloadWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    track_info = pyqtSignal(dict)
    ask_replace = pyqtSignal(str, str)
    song_not_found = pyqtSignal(str)
    # Nuevas señales para progreso global
    status_changed = pyqtSignal(str)  # Estado actual
    converting = pyqtSignal()  # Cuando empieza conversión
    applying_metadata = pyqtSignal()  # Cuando aplica metadatos
    download_started = pyqtSignal(str)  # Nombre de la canción

    def __init__(self, spotify_id, download_folder, quality):
        super().__init__()
        self.spotify_id = spotify_id
        self.download_folder = download_folder
        self.quality = quality
        self.q = queue.Queue()
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.replace_response = None

    def run(self):
        try:
            item = get_spotify_item(self.spotify_id)
            if not item:
                self.error.emit("No se pudo obtener información del ítem de Spotify")
                return

            tipo = item.get('__type')
            if tipo == 'playlist':
                tracks = item['tracks']['items']
                track_list = [td['track'] if 'track' in td else td for td in tracks]
                album_context = None
            elif tipo == 'album':
                tracks = item['tracks']['items']
                track_list = tracks
                album_context = item  # Guardar el álbum para metadatos
            elif tipo == 'track':
                track_list = [item]
                album_context = None
            else:
                self.error.emit("Tipo de ítem de Spotify no soportado")
                return

            history_links = load_download_history()
            for idx, track in enumerate(track_list):
                if self.cancel_event.is_set():
                    break
                self.process_track(track, len(track_list), idx, album_context)
                spotify_url = track.get('external_urls', {}).get('spotify')
                if spotify_url and spotify_url not in history_links:
                    history_links.append(spotify_url)
            save_download_history(history_links)

            if not self.cancel_event.is_set():
                self.finished.emit()

        except Exception as e:
            logging.error(f'Error en la descarga: {e}')
            self.error.emit(str(e))

    def process_track(self, track, total_tracks, track_index, album_context=None):
        song_metadata = None  # Definir antes del try
        try:
            # Si el track no tiene 'album', usar el contexto del álbum
            if 'album' in track and track['album']:
                album_name = track['album']['name']
                cover_url = track['album']['images'][0]['url']
                release_date = track['album']['release_date']
            elif album_context:
                album_name = album_context.get('name', 'Álbum')
                images = album_context.get('images', [])
                cover_url = images[0]['url'] if images else ''
                release_date = album_context.get('release_date', '')
            else:
                album_name = ''
                cover_url = ''
                release_date = ''

            # Extraer género desde Spotify (del artista o álbum)
            genre = self.extract_genre(track, album_context)

            song_metadata = {
                'song': track['name'],
                'artists': ', '.join([artist['name'] for artist in track['artists']]),
                'album': album_name,
                'cover_url': cover_url,
                'release_date': release_date,
                'genre': genre
            }
            
            # Emitir señal de inicio de descarga
            self.download_started.emit(song_metadata['song'])
            self.status_changed.emit(f"Buscando: {song_metadata['song']}")
            
            # Determinar formato de salida según calidad
            output_format = 'flac' if 'FLAC' in self.quality else 'mp3'
            file_ext = '.flac' if output_format == 'flac' else '.mp3'
            
            filename = os.path.join(
                self.download_folder, 
                f'{sanitize_filename(song_metadata["song"])}{file_ext}'
            )
            if os.path.exists(filename):
                if not self.handle_existing_file(song_metadata['song'], filename):
                    self.progress.emit(int((track_index + 1) / total_tracks * 100))
                    return
            
            self.status_changed.emit(f"Descargando: {song_metadata['song']}")
            url = self.find_download_url(song_metadata)
            if not url:
                self.song_not_found.emit(f'"{song_metadata["song"]}" - {song_metadata["artists"]}')
                self.progress.emit(int((track_index + 1) / total_tracks * 100))
                return
            self.download_and_process_song(
                url, filename, song_metadata, track_index, total_tracks, output_format
            )
            # Guardar solo el enlace en el historial
            history_links = load_download_history()
            if url not in history_links:
                history_links.append(url)
                save_download_history(history_links)
        except Exception as e:
            logging.error(f'Error procesando la pista: {e}')
            song = song_metadata["song"] if song_metadata and "song" in song_metadata else "Desconocido"
            self.song_not_found.emit(f'"{song}"')
            self.progress.emit(int((track_index + 1) / total_tracks * 100))

    def handle_existing_file(self, song, filename):
        self.ask_replace.emit(song, filename)
        while self.replace_response is None:
            QThread.msleep(100)
        
        replace_response = self.replace_response
        self.replace_response = None
        
        if replace_response:
            os.remove(filename)
        return replace_response

    def find_download_url(self, song_metadata):
        url = search_music_services(
            song_metadata['song'], 
            song_metadata['artists'], 
            song_metadata['album']
        )
        return url

    def download_and_process_song(self, url, filename, song_metadata, track_index, total_tracks, output_format='mp3'):
        try:
            download_song(
                url, filename, self.q, 
                self.pause_event, self.cancel_event,
                output_format=output_format
            )
            
            # Emitir señal de conversión
            self.converting.emit()
            self.status_changed.emit(f"Convirtiendo: {song_metadata['song']}")
            
            # Determinar la extensión según el formato
            base, _ = os.path.splitext(filename)
            output_file = base + ('.flac' if output_format == 'flac' else '.mp3')
            
            # Esperar a que el archivo exista
            import time
            max_wait = 5  # segundos
            waited = 0
            while not os.path.exists(output_file) and waited < max_wait:
                time.sleep(0.2)
                waited += 0.2
            
            if os.path.exists(output_file):
                # Solo aplicar metadatos si es MP3 (FLAC usa metadatos diferentes)
                if output_format == 'mp3':
                    # Emitir señal de metadatos
                    self.applying_metadata.emit()
                    self.status_changed.emit(f"Aplicando metadatos: {song_metadata['song']}")
                    
                    result = update_mp3_metadata_hybrid(
                        output_file, 
                        song_metadata['song'], 
                        song_metadata['artists'], 
                        song_metadata['album'], 
                        song_metadata['cover_url'], 
                        song_metadata['release_date'],
                        song_metadata['genre']
                    )
                    if not result:
                        logging.error(f'No se pudieron actualizar los metadatos para: {output_file}')
                else:
                    # Para FLAC, aplicar metadatos con mutagen
                    self.applying_metadata.emit()
                    self.status_changed.emit(f"Aplicando metadatos FLAC: {song_metadata['song']}")
                    self._apply_flac_metadata(output_file, song_metadata)
            else:
                logging.error(f'Archivo no encontrado tras la conversión: {output_file}')
            
            self.track_info.emit({
                "spotify_id": self.spotify_id,
                "title": song_metadata['song'],
                "artist": song_metadata['artists'],
                "album": song_metadata['album'],
                "cover_url": song_metadata['cover_url'],
                "file_path": output_file,
                "url": url,
                "release_date": song_metadata['release_date'],
                "quality": self.quality
            })
        except Exception as e:
            logging.error(f'Error al descargar "{song_metadata["song"]}": {e}')
            self.error.emit(f'Error al descargar "{song_metadata["song"]}": {str(e)}')
        self.progress.emit(int((track_index + 1) / total_tracks * 100))
    
    def _apply_flac_metadata(self, filepath, song_metadata):
        """Aplicar metadatos a archivo FLAC usando mutagen"""
        try:
            from mutagen.flac import FLAC, Picture
            import requests
            
            audio = FLAC(filepath)
            
            # Metadatos básicos
            audio['TITLE'] = song_metadata['song']
            audio['ARTIST'] = song_metadata['artists']
            audio['ALBUM'] = song_metadata['album']
            audio['GENRE'] = song_metadata.get('genre', '')
            
            # Año
            if song_metadata.get('release_date'):
                year = song_metadata['release_date'][:4]
                audio['DATE'] = year
            
            # Portada
            if song_metadata.get('cover_url'):
                try:
                    response = requests.get(song_metadata['cover_url'], timeout=10)
                    if response.status_code == 200:
                        picture = Picture()
                        picture.type = 3  # Front cover
                        picture.mime = 'image/jpeg'
                        picture.desc = 'Cover'
                        picture.data = response.content
                        audio.add_picture(picture)
                except Exception as e:
                    logging.warning(f'No se pudo añadir portada FLAC: {e}')
            
            audio.save()
            logging.info(f'Metadatos FLAC aplicados: {filepath}')
        except ImportError:
            logging.warning('mutagen no disponible para metadatos FLAC')
        except Exception as e:
            logging.error(f'Error aplicando metadatos FLAC: {e}')
        except Exception as e:
            logging.error(f'Error al descargar "{song_metadata["song"]}": {e}')
            self.error.emit(f'Error al descargar "{song_metadata["song"]}": {str(e)}')
        self.progress.emit(int((track_index + 1) / total_tracks * 100))

    def set_replace_response(self, response):
        self.replace_response = response

    def extract_genre(self, track, album_context=None):
        """
        Extrae el género musical directamente desde Spotify
        """
        try:
            # Intentar obtener géneros del álbum primero
            if 'album' in track and track['album'] and 'genres' in track['album']:
                genres = track['album'].get('genres', [])
                if genres:
                    logging.info(f'Género encontrado en álbum: {genres[0]}')
                    return genres[0]
            
            # Si hay contexto de álbum, intentar desde ahí
            if album_context and 'genres' in album_context:
                genres = album_context.get('genres', [])
                if genres:
                    logging.info(f'Género encontrado en contexto de álbum: {genres[0]}')
                    return genres[0]
            
            # Intentar obtener géneros del artista principal
            if 'artists' in track and track['artists']:
                from downloader.spotify import sp
                try:
                    artist_id = track['artists'][0]['id']
                    artist_info = sp.artist(artist_id)
                    if 'genres' in artist_info and artist_info['genres']:
                        genre = artist_info['genres'][0]
                        logging.info(f'Género encontrado del artista {track["artists"][0]["name"]}: {genre}')
                        return genre
                except Exception as e:
                    logging.warning(f'No se pudo obtener género del artista: {e}')
            
            # Si hay múltiples artistas, intentar con el segundo artista
            if 'artists' in track and len(track['artists']) > 1:
                from downloader.spotify import sp
                try:
                    artist_id = track['artists'][1]['id']
                    artist_info = sp.artist(artist_id)
                    if 'genres' in artist_info and artist_info['genres']:
                        genre = artist_info['genres'][0]
                        logging.info(f'Género encontrado del segundo artista {track["artists"][1]["name"]}: {genre}')
                        return genre
                except Exception as e:
                    logging.warning(f'No se pudo obtener género del segundo artista: {e}')
            
            logging.info('No se encontró género específico en Spotify')
            return None
            
        except Exception as e:
            logging.warning(f'Error al extraer género: {e}')
            return None
