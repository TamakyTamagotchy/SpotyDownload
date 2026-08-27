"""
Clases base compartidas por los workers de descarga.

Objetivo: eliminar la lógica que antes estaba copiada casi idéntica en
SpotifyDownloadWorker, SpotifyPlaylistDownloadWorker y DownloadWorker
(resolución de archivos existentes, nombres únicos, aplicación de
metadatos), y darle a DownloadManager una interfaz uniforme de señales
para no depender de hasattr(...) por todos lados (polimorfismo real).
"""
import logging
import os
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from config.settings_manager import SettingsManager


class FileExistsResolverMixin:
    """
    Lógica compartida para decidir qué hacer con un archivo que ya existe
    (preguntar / sobrescribir / omitir / renombrar).

    Requiere que la clase que la use tenga `self.settings` (SettingsManager),
    `self.cancel_requested` (bool) y la señal `self.ask_replace = pyqtSignal(str, str)`.
    """

    def _init_file_exists_state(self):
        self.replace_response = None
        self._file_exists_event = threading.Event()
        self._batch_action = None

    def resolve_existing_file(self, song_title: str, filename: str):
        """Devuelve el filename final a usar, o None si se debe omitir la descarga."""
        action = self.settings.get_file_exists_action()

        if action == 'skip':
            logging.info(f"Archivo ya existe (omitiendo): {filename}")
            return None
        if action == 'rename':
            new_name = self._get_unique_filename(filename)
            logging.info(f"Archivo renombrado a: {new_name}")
            return new_name
        if action == 'ask':
            return self._handle_ask(song_title, filename)

        # 'overwrite' o cualquier valor desconocido -> sobrescribir
        self._remove_file(filename)
        return filename

    def _handle_ask(self, song_title: str, filename: str):
        if self._batch_action is not None:
            return self._apply_action(self._batch_action, filename)

        self._file_exists_event.clear()
        self.replace_response = None
        self.ask_replace.emit(song_title, filename)

        while not self._file_exists_event.is_set():
            if getattr(self, 'cancel_requested', False):
                return None
            self._file_exists_event.wait(timeout=0.5)

        if self.replace_response is None:
            return None

        action = self.replace_response.get('action', 'skip')
        if self.replace_response.get('apply_to_all', False):
            self._batch_action = action

        return self._apply_action(action, filename)

    def _apply_action(self, action: str, filename: str):
        if action == 'overwrite':
            self._remove_file(filename)
            return filename
        if action == 'skip':
            logging.info(f"[_apply_action] Omitiendo: {filename}")
            return None
        if action == 'rename':
            new_name = self._get_unique_filename(filename)
            logging.info(f"[_apply_action] Renombrando a: {new_name}")
            return new_name
        return filename

    @staticmethod
    def _remove_file(filename: str):
        logging.info(f"Sobrescribiendo: {filename}")
        try:
            os.remove(filename)
        except Exception as e:
            logging.error(f"Error eliminando archivo: {e}")

    @staticmethod
    def _get_unique_filename(filename: str) -> str:
        if not os.path.exists(filename):
            return filename
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = f"{base} ({counter}){ext}"
        while os.path.exists(new_filename):
            counter += 1
            new_filename = f"{base} ({counter}){ext}"
        return new_filename

    def set_file_exists_response(self, response_dict: dict):
        """Llamado desde el hilo principal con la respuesta del diálogo."""
        self.replace_response = response_dict
        self._file_exists_event.set()


class BaseDownloadWorker(QThread, FileExistsResolverMixin):
    """
    Base común para todos los workers de descarga.

    Garantiza un conjunto único de señales (error_occurred, progress_updated,
    status_changed, converting, applying_metadata, ask_replace, finished),
    así DownloadManager puede conectarse de forma polimórfica sin usar
    hasattr(...) para adivinar qué señales tiene cada worker.

    Patrón Template Method: `run()` NO se sobreescribe; las subclases solo
    implementan `_download_one()` y, si lo necesitan, los hooks marcados
    abajo para especializar su comportamiento.
    """
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    converting = pyqtSignal()
    applying_metadata = pyqtSignal()
    ask_replace = pyqtSignal(str, str)

    def __init__(self, download_folder: str, quality: str):
        super().__init__()
        self.download_folder = download_folder
        self.quality = quality
        self.settings = SettingsManager()
        self.cancel_requested = False
        # Compartidos entre canciones (antes se creaban nuevos por canción,
        # lo que hacía que cancelar no interrumpiera la descarga en curso).
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self._init_file_exists_state()

    def cancel(self):
        """Cancela la descarga, incluida la que esté en curso ahora mismo."""
        self.cancel_requested = True
        self.cancel_event.set()

    def _build_output_filename(self, title: str) -> str:
        from downloader.utils import sanitize_filename
        file_ext = self.settings.get_file_extension()
        return os.path.join(self.download_folder, f"{sanitize_filename(title)}{file_ext}")

    def _apply_metadata(self, filename: str, song: dict):
        """Aplica metadatos (MP3 o FLAC según extensión) reusando la
        implementación híbrida ya existente en utils.py."""
        from downloader.utils import update_mp3_metadata_hybrid
        update_mp3_metadata_hybrid(
            filename,
            song.get('song', ''),
            song.get('artists', ''),
            song.get('album', ''),
            song.get('cover_url', ''),
            song.get('release_date', ''),
            song.get('genre', ''),
        )

    # ---- Hooks para que cada subclase especialice el comportamiento ----

    def _get_songs(self):
        """Lista de canciones (dicts) a descargar. Por defecto `self.songs`
        (ya resuelta en __init__); DownloadWorker la sobreescribe para
        resolverla desde Spotify en tiempo de ejecución."""
        return self.songs

    def _download_one(self, song: dict, current: int, total: int):
        """Descarga y aplica metadatos a una sola canción. OBLIGATORIO."""
        raise NotImplementedError

    def _on_song_error(self, song: dict, error: Exception):
        """Comportamiento por defecto ante un fallo de una canción: registrar
        y emitir error_occurred, pero seguir con las siguientes."""
        logging.error(f"Error descargando '{song.get('song', '?')}': {error}")
        self.error_occurred.emit(str(error))

    def _report_progress(self, index: int, total: int):
        """Hook opcional; no-op por defecto (para workers que ya reportan
        progreso granular en tiempo real dentro de _download_one)."""
        pass

    def _on_all_finished(self, completed: int, total: int):
        """Hook opcional al terminar todo el proceso."""
        pass

    # ---- Template method: no se sobreescribe en subclases ----

    def run(self):
        try:
            os.makedirs(self.download_folder, exist_ok=True)
            songs = self._get_songs()
            if songs is None:
                return  # la subclase ya emitió el error correspondiente

            total = len(songs)
            completed = 0

            for i, song in enumerate(songs):
                if self.cancel_requested:
                    break
                try:
                    self._download_one(song, i + 1, total)
                    completed += 1
                except Exception as e:
                    self._on_song_error(song, e)
                self._report_progress(i, total)

            if not self.cancel_requested:
                self._on_all_finished(completed, total)
                self.finished.emit()

        except Exception as e:
            logging.error(f"Error crítico en {self.__class__.__name__}: {e}")
            self.error_occurred.emit(str(e))