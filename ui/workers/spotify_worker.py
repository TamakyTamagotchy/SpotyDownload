from PyQt6.QtCore import QThread, pyqtSignal
import logging, os, queue, threading
from downloader.utils import search_music_services, download_song, sanitize_filename
from downloader.metadata import update_mp3_metadata
from config.settings_manager import SettingsManager

class SpotifyDownloadWorker(QThread):
    """Worker para descargar canciones individuales desde Spotify"""
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    track_completed = pyqtSignal(dict)
    status_changed = pyqtSignal(str)  # Nueva seÃ±al para cambios de estado
    converting = pyqtSignal()  # Nueva seÃ±al para conversiÃ³n
    applying_metadata = pyqtSignal()  # Nueva seÃ±al para metadatos

    def __init__(self, songs, download_folder, quality, track_widget=None):
        super().__init__()
        self.songs = songs
        self.download_folder = download_folder
        self.quality = quality
        self.settings = SettingsManager()
        self.track_widget = track_widget
        self.cancel_requested = False

    def run(self):
        try:
            for i, song in enumerate(self.songs):
                if self.cancel_requested:
                    break
                    
                self.download_single_song(song, i + 1, len(self.songs))
                
            if not self.cancel_requested:
                self.finished.emit()
                
        except Exception as e:
            logging.error(f"Error en SpotifyDownloadWorker: {e}")
            self.error_occurred.emit(str(e))

    def download_single_song(self, song, current, total):
        """Descargar una canciÃ³n individual"""
        try:
            # Preparar datos
            title = song['song']
            artists = song['artists']
            album = song.get('album', '')
            
            self.status_changed.emit(f"Buscando: {title}")
            
            # Buscar URL de descarga
            url = search_music_services(title, artists, album)
            if not url:
                raise Exception(f"No se encontrÃ³ la canciÃ³n: {title} - {artists}")
            
            # Obtener formato desde configuraciÃ³n
            output_format = self.settings.get_audio_format()
            file_ext = self.settings.get_file_extension()
            
            logging.info(f"[SpotifyDownloadWorker] Formato: {output_format}, extensiÃ³n: {file_ext}")
            
            # Crear nombre de archivo (solo tÃ­tulo, sin artistas)
            filename = os.path.join(
                self.download_folder,
                f"{sanitize_filename(title)}{file_ext}"
            )
            
            # Verificar si el archivo ya existe
            if os.path.exists(filename):
                file_action = self.settings.get_file_exists_action()
                
                if file_action == 'skip':
                    logging.info(f"Archivo ya existe (omitiendo): {filename}")
                    self.track_completed.emit({
                        'song': title,
                        'artists': artists,
                        'file_path': filename,
                        'id': song.get('id', '')
                    })
                    return
                elif file_action == 'rename':
                    filename = self._get_unique_filename(filename)
                    logging.info(f"Archivo renombrado a: {filename}")
                elif file_action == 'overwrite':
                    logging.info(f"Sobrescribiendo: {filename}")
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logging.error(f"Error eliminando archivo: {e}")
                # Si es 'ask', por simplicidad en canciones individuales, sobrescribimos
                else:
                    logging.info(f"Sobrescribiendo (default): {filename}")
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logging.error(f"Error eliminando archivo: {e}")
            
            self.status_changed.emit(f"Descargando: {title}")
            
            # Descargar canciÃ³n
            q = queue.Queue()
            pause_event = threading.Event()
            cancel_event = threading.Event()
            
            # FunciÃ³n de callback para progreso
            def progress_callback(d):
                if d['status'] == 'downloading':
                    try:
                        percent = d.get('_percent_str', '0%').replace('%', '')
                        progress = int(float(percent))
                        self.progress_updated.emit(progress)
                    except:
                        pass
            
            # Descargar usando la funciÃ³n existente
            download_song(url, filename, q, pause_event, cancel_event, output_format=output_format)
            
            # Emitir seÃ±al de conversiÃ³n
            self.converting.emit()
            self.status_changed.emit(f"Convirtiendo: {title}")
            
            # Actualizar metadatos
            if os.path.exists(filename):
                self.applying_metadata.emit()
                self.status_changed.emit(f"Aplicando metadatos: {title}")
                
                if output_format == 'mp3':
                    update_mp3_metadata(
                        filename,
                        title,
                        artists,
                        album,
                        song.get('cover_url', ''),
                        song.get('release_date', ''),
                        song.get('genre', '')
                    )
                else:
                    # Metadatos FLAC
                    self._apply_flac_metadata(filename, song)
                
                # Emitir seÃ±al de completado
                self.track_completed.emit({
                    'song': title,
                    'artists': artists,
                    'album': album,
                    'file_path': filename,
                    'id': song.get('id', '')
                })
                
                logging.info(f"CanciÃ³n descargada exitosamente: {filename}")
            else:
                raise Exception("El archivo no se creÃ³ correctamente")
                
        except Exception as e:
            logging.error(f"Error descargando canciÃ³n: {e}")
            self.error_occurred.emit(str(e))
    
    def _apply_flac_metadata(self, filepath, song):
        """Aplicar metadatos a archivo FLAC"""
        try:
            from mutagen.flac import FLAC, Picture
            import requests
            
            audio = FLAC(filepath)
            audio['TITLE'] = song['song']
            audio['ARTIST'] = song['artists']
            audio['ALBUM'] = song.get('album', '')
            audio['GENRE'] = song.get('genre') or ''
            
            if song.get('release_date'):
                audio['DATE'] = song['release_date'][:4]
            
            if song.get('cover_url'):
                try:
                    response = requests.get(song['cover_url'], timeout=10)
                    if response.status_code == 200:
                        picture = Picture()
                        picture.type = 3
                        picture.mime = 'image/jpeg'
                        picture.desc = 'Cover'
                        picture.data = response.content
                        audio.add_picture(picture)
                except:
                    pass
            
            audio.save()
        except Exception as e:
            logging.warning(f'Error metadatos FLAC: {e}')

    def cancel(self):
        """Cancelar descarga"""
        self.cancel_requested = True
    
    def _get_unique_filename(self, filename):
        """Genera un nombre de archivo único agregando (1), (2), etc."""
        if not os.path.exists(filename):
            return filename
        
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = f"{base} ({counter}){ext}"
        
        while os.path.exists(new_filename):
            counter += 1
            new_filename = f"{base} ({counter}){ext}"
        
        return new_filename

class SpotifyPlaylistDownloadWorker(QThread):
    """Worker para descargar playlists completas desde Spotify"""
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    track_info = pyqtSignal(dict)
    ask_replace = pyqtSignal(str, str)
    song_not_found = pyqtSignal(str)

    def __init__(self, songs, download_folder, quality, parent=None):
        super().__init__()
        self.songs = songs
        self.download_folder = download_folder
        self.quality = quality
        self.settings = SettingsManager()
        self.parent = parent
        self.cancel_requested = False
        self.replace_response = None

    def run(self):
        try:
            total_songs = len(self.songs)
            completed = 0
            
            # Crear carpeta si no existe
            os.makedirs(self.download_folder, exist_ok=True)
            
            for i, song in enumerate(self.songs):
                if self.cancel_requested:
                    break
                
                # Emitir informaciÃ³n de la canciÃ³n actual
                self.track_info.emit(song)
                
                try:
                    self.download_single_song(song, i + 1, total_songs)
                    completed += 1
                except Exception as e:
                    logging.error(f"Error descargando {song['song']}: {e}")
                    self.song_not_found.emit(f"{song['song']} - {song['artists']}")
                
                # Actualizar progreso
                progress = int((i + 1) / total_songs * 100)
                self.progress_updated.emit(progress)
            
            if not self.cancel_requested:
                logging.info(f"Descarga de playlist completada: {completed}/{total_songs} canciones")
                self.finished.emit()
                
        except Exception as e:
            logging.error(f"Error en SpotifyPlaylistDownloadWorker: {e}")
            self.error_occurred.emit(str(e))

    def download_single_song(self, song, current, total):
        """Descargar una canciÃ³n individual de la playlist"""
        try:
            title = song['song']
            artists = song['artists']
            album = song.get('album', '')
            
            # Buscar URL de descarga
            url = search_music_services(title, artists, album)
            if not url:
                raise Exception(f"No se encontrÃ³: {title}")
            
            # Obtener formato desde configuraciÃ³n
            output_format = self.settings.get_audio_format()
            file_ext = self.settings.get_file_extension()
            
            logging.info(f"[SpotifyPlaylistDownloadWorker] Formato: {output_format}, extensiÃ³n: {file_ext}")
            
            # Crear nombre de archivo (solo tÃ­tulo, sin artistas)
            filename = os.path.join(
                self.download_folder,
                f"{sanitize_filename(title)}{file_ext}"
            )
            
            # Verificar si el archivo ya existe
            if os.path.exists(filename):
                file_action = self.settings.get_file_exists_action()
                logging.info(f"[SpotifyPlaylistDownloadWorker] Archivo existe, acción: {file_action}")
                
                if file_action == 'skip':
                    logging.info(f"Archivo ya existe (omitiendo): {filename}")
                    return  # Saltar esta canción
                elif file_action == 'rename':
                    filename = self._get_unique_filename(filename)
                    logging.info(f"Archivo renombrado a: {filename}")
                elif file_action == 'overwrite':
                    logging.info(f"Sobrescribiendo: {filename}")
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logging.error(f"Error eliminando archivo: {e}")
                elif file_action == 'ask':
                    # NOTA: El diálogo de preguntar no está implementado
                    # Por ahora, usar sobrescribir como fallback
                    logging.warning(f"[SpotifyPlaylistDownloadWorker] 'ask' no implementado, sobrescribiendo")
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logging.error(f"Error eliminando archivo: {e}")
                else:
                    # Valor desconocido, sobrescribir
                    logging.warning(f"Acción desconocida '{file_action}', sobrescribiendo")
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logging.error(f"Error eliminando archivo: {e}")
            
            # Descargar canciÃ³n
            q = queue.Queue()
            pause_event = threading.Event()
            cancel_event = threading.Event()
            
            if self.cancel_requested:
                cancel_event.set()
            
            # Descargar usando la funciÃ³n existente
            download_song(url, filename, q, pause_event, cancel_event, output_format=output_format)
            
            # Actualizar metadatos si la descarga fue exitosa
            if os.path.exists(filename) and not self.cancel_requested:
                if output_format == 'mp3':
                    update_mp3_metadata(
                        filename,
                        title,
                        artists,
                        album,
                        song.get('cover_url', ''),
                        song.get('release_date', ''),
                        song.get('genre', '')
                    )
                else:
                    self._apply_flac_metadata(filename, song)
                
                logging.info(f"Descargada: {title} ({current}/{total})")
            elif self.cancel_requested:
                # Eliminar archivo parcial si se cancelÃ³
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except:
                        pass
                        
        except Exception as e:
            raise Exception(f"Error descargando {title}: {e}")

    def set_replace_response(self, response):
        """Establecer respuesta para reemplazar archivo"""
        self.replace_response = response

    def cancel(self):
        """Cancelar descarga"""
        self.cancel_requested = True
    
    def _get_unique_filename(self, filename):
        """Genera un nombre de archivo único agregando (1), (2), etc."""
        if not os.path.exists(filename):
            return filename
        
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = f"{base} ({counter}){ext}"
        
        while os.path.exists(new_filename):
            counter += 1
            new_filename = f"{base} ({counter}){ext}"
        
        return new_filename
    
    def _apply_flac_metadata(self, filepath, song):
        """Aplicar metadatos a archivo FLAC"""
        try:
            from mutagen.flac import FLAC, Picture
            import requests
            
            audio = FLAC(filepath)
            audio['TITLE'] = song['song']
            audio['ARTIST'] = song['artists']
            audio['ALBUM'] = song.get('album', '')
            audio['GENRE'] = song.get('genre') or ''
            
            if song.get('release_date'):
                audio['DATE'] = song['release_date'][:4]
            
            if song.get('cover_url'):
                try:
                    response = requests.get(song['cover_url'], timeout=10)
                    if response.status_code == 200:
                        picture = Picture()
                        picture.type = 3
                        picture.mime = 'image/jpeg'
                        picture.desc = 'Cover'
                        picture.data = response.content
                        audio.add_picture(picture)
                except:
                    pass
            
            audio.save()
        except Exception as e:
            logging.warning(f'Error metadatos FLAC: {e}')
