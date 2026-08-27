from PyQt6.QtCore import pyqtSignal, QThread
import os, queue, threading, logging
from downloader.utils import (
    sanitize_filename, search_music_services, download_song, 
    save_download_history, load_download_history, update_mp3_metadata_hybrid
)
from downloader.spotify import get_spotify_item
from config.settings_manager import SettingsManager

class DownloadWorker(QThread):
    """Worker unificado y robusto para procesar tracks, álbumes y playlists de Spotify."""
    progress_updated = pyqtSignal(int)      # antes: progress
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)        # antes: error
    track_info = pyqtSignal(dict)
    ask_replace = pyqtSignal(str, str)
    song_not_found = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    converting = pyqtSignal()
    applying_metadata = pyqtSignal()
    download_started = pyqtSignal(str, str)

    def __init__(self, spotify_id_or_songs, download_folder, quality, is_direct_list=False):
        super().__init__()
        self.input_data = spotify_id_or_songs
        self.download_folder = download_folder
        self.quality = quality
        self.is_direct_list = is_direct_list
        self.settings = SettingsManager()
        self.q = queue.Queue()
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.replace_response = None
        self._file_exists_event = threading.Event()
        self._batch_action = None
        self._ask_renamed_filename = None

    def run(self):
        try:
            os.makedirs(self.download_folder, exist_ok=True)
            track_list = []

            if self.is_direct_list:
                track_list = self.input_data
                album_context = None
            else:
                item = get_spotify_item(self.input_data)
                if not item:
                    self.error.emit("No se pudo obtener información del ítem de Spotify")
                    return

                tipo = item.get('__type')
                if tipo == 'playlist':
                    tracks = item.get('tracks', {}).get('items', [])
                    track_list = [td['track'] if 'track' in td else td for td in tracks]
                    album_context = None
                elif tipo == 'album':
                    track_list = item.get('tracks', {}).get('items', [])
                    album_context = item
                elif tipo == 'track':
                    track_list = [item]
                    album_context = None
                else:
                    self.error.emit("Tipo de ítem de Spotify no soportado")
                    return

            total_tracks = len(track_list)
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
            logging.error(f'Error crítico en DownloadWorker: {e}')
            self.error.emit(str(e))

    def process_track(self, track, total_tracks, track_index, album_context=None):
        try:
            if 'album' in track and track['album']:
                album_name = track['album'].get('name', '')
                images = track['album'].get('images', [])
                cover_url = images[0]['url'] if images else ''
                release_date = track['album'].get('release_date', '')
            elif album_context:
                album_name = album_context.get('name', 'Álbum')
                images = album_context.get('images', [])
                cover_url = images[0]['url'] if images else ''
                release_date = album_context.get('release_date', '')
            else:
                album_name = ''
                cover_url = ''
                release_date = ''

            genre = self.extract_genre(track, album_context)
            song_name = track.get('name', 'Desconocido')
            artists_list = track.get('artists', [])
            artists_str = ', '.join([a.get('name', '') for a in artists_list])

            song_metadata = {
                'song': song_name,
                'artists': artists_str,
                'album': album_name,
                'cover_url': cover_url,
                'release_date': release_date,
                'genre': genre
            }

            self.download_started.emit(song_name, cover_url or '')
            self.status_changed.emit(f"Buscando en YT Music: {song_name}")

            output_format = self.settings.get_audio_format()
            file_ext = self.settings.get_file_extension()

            filename = os.path.join(
                self.download_folder, 
                f'{sanitize_filename(song_name)}{file_ext}'
            )

            if os.path.exists(filename):
                if not self.handle_existing_file(song_name, filename):
                    return

            url = search_music_services(song_name, artists_str, album_name)
            if not url:
                self.song_not_found.emit(f'"{song_name}" - {artists_str}')
                return

            self.status_changed.emit(f"Descargando: {song_name}")
            download_song(
                url, filename, self.q, 
                self.pause_event, self.cancel_event,
                output_format=output_format
            )

            self.converting.emit()
            self.status_changed.emit(f"Convirtiendo: {song_name}")

            base, _ = os.path.splitext(filename)
            output_file = base + ('.flac' if output_format == 'flac' else '.mp3')

            max_wait = 5
            waited = 0
            import time
            while not os.path.exists(output_file) and waited < max_wait:
                time.sleep(0.2)
                waited += 0.2

            if os.path.exists(output_file):
                self.applying_metadata.emit()
                self.status_changed.emit(f"Aplicando metadatos: {song_name}")
                update_mp3_metadata_hybrid(
                    output_file, song_name, artists_str, 
                    album_name, cover_url, release_date, genre
                )

            self.track_info.emit({
                "spotify_id": track.get('id', ''),
                "title": song_name,
                "artist": artists_str,
                "album": album_name,
                "cover_url": cover_url,
                "file_path": output_file,
                "url": url,
                "release_date": release_date,
                "quality": self.quality
            })

            history_links = load_download_history()
            if url not in history_links:
                history_links.append(url)
                save_download_history(history_links)

        except Exception as e:
            logging.error(f'Error procesando la pista: {e}')
            raise e

    def handle_existing_file(self, song, filename):
        file_action = self.settings.get_file_exists_action()
        if file_action == 'overwrite':
            try:
                os.remove(filename)
            except Exception as e:
                logging.error(f"Error eliminando archivo: {e}")
            return True
        elif file_action == 'skip':
            return False
        elif file_action == 'rename':
            return True
        elif file_action == 'ask':
            if self._batch_action is not None:
                return self._apply_action(self._batch_action, filename)

            self._file_exists_event.clear()
            self.replace_response = None
            self.ask_replace.emit(song, filename)

            while not self._file_exists_event.is_set():
                if self.cancel_event.is_set():
                    return False
                self._file_exists_event.wait(timeout=0.5)

            if self.replace_response is None:
                return False

            action = self.replace_response.get('action', 'skip')
            if self.replace_response.get('apply_to_all', False):
                self._batch_action = action

            return self._apply_action(action, filename)
        return True

    def get_unique_filename(self, filename):
        if not os.path.exists(filename):
            return filename
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = f"{base} ({counter}){ext}"
        while os.path.exists(new_filename):
            counter += 1
            new_filename = f"{base} ({counter}){ext}"
        return new_filename

    def _apply_action(self, action, filename):
        if action == 'overwrite':
            try:
                os.remove(filename)
            except Exception as e:
                logging.error(f"Error eliminando archivo: {e}")
            return True
        elif action == 'skip':
            return False
        elif action == 'rename':
            self._ask_renamed_filename = self.get_unique_filename(filename)
            return True
        return True

    def set_file_exists_response(self, response_dict):
        self.replace_response = response_dict
        self._file_exists_event.set()

    def cancel(self):
        self.cancel_event.set()

    def extract_genre(self, track, album_context=None):
        try:
            if 'album' in track and track['album'] and 'genres' in track['album']:
                genres = track['album'].get('genres', [])
                if genres:
                    return genres[0]
            if album_context and 'genres' in album_context:
                genres = album_context.get('genres', [])
                if genres:
                    return genres[0]
            return None
        except Exception:
            return None