from PyQt6.QtCore import QObject, pyqtSignal, QThread
from ui.workers.download_worker import DownloadWorker
from ui.workers.spotify_worker import SpotifyDownloadWorker, SpotifyPlaylistDownloadWorker
from config.settings_manager import SettingsManager
from ui.components.global_progress import progress_manager
from ui.components.toast import toast
import logging

class Singleton(type(QObject)):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class DownloadManager(QObject, metaclass=Singleton):
    
    # Señales
    task_added = pyqtSignal(object)  # Emite el objeto tarea
    task_started = pyqtSignal(str)   # ID de la tarea
    task_finished = pyqtSignal(str)  # ID de la tarea
    queue_updated = pyqtSignal()     # Señal general de actualización

    def __init__(self):
        super().__init__()
        self.queue = []
        self.active_downloads = []
        self.max_concurrent = 2 # Podría venir de settings
        self.settings = SettingsManager()
        self._initialized = True

    # def _init_manager(self): ... removed

    def add_download(self, type, data):
        """
        Agrega una descarga a la cola.
        type: 'youtube', 'spotify_track', 'spotify_playlist'
        data: diccionario con info necesaria (url, id, etc)
        """
        task_id = f"{type}_{len(self.queue) + len(self.active_downloads)}_{id(data)}"
        
        task = {
            'id': task_id,
            'type': type,
            'data': data,
            'status': 'pending', # pending, downloading, completed, error
            'worker': None,
            'thread': None, # Para workers que necesitan QThread
            'progress': 0,
            'title': data.get('title', 'Desconocido')
        }
        
        self.queue.append(task)
        self.task_added.emit(task)
        self.process_queue()
        return task

    def process_queue(self):
        # Limpiar descargas terminadas de la lista activa
        self.active_downloads = [t for t in self.active_downloads if t['status'] == 'downloading']
        
        # Iniciar nuevas descargas si hay espacio
        while len(self.active_downloads) < self.max_concurrent and self.queue:
            task = self.queue.pop(0)
            self.start_task(task)

    def start_task(self, task):
        try:
            download_folder = self.settings.get("download_folder")
            quality = self.settings.get("default_quality")

            worker_config = {
                'spotify_url': {'class': DownloadWorker, 'is_qthread': False, 'data_func': lambda d: d['id']},
                'spotify_track': {'class': SpotifyDownloadWorker, 'is_qthread': True, 'data_func': lambda d: [d]},
                'spotify_playlist': {'class': SpotifyPlaylistDownloadWorker, 'is_qthread': True, 'data_func': lambda d: d['tracks']}
            }

            worker = None
            is_qthread = False

            if task['type'] in worker_config:
                config = worker_config[task['type']]
                worker = config['class'](config['data_func'](task['data']), download_folder, quality)
                is_qthread = config['is_qthread']

            if worker:
                task['worker'] = worker
                task['status'] = 'downloading'
                self.active_downloads.append(task)

                worker.finished.connect(lambda: self.on_task_finished(task))
                worker.error_occurred.connect(lambda err: self.on_task_error(task, err))

                self._connect_progress_signals(worker, task)

                if is_qthread:
                    worker.start()
                else:
                    thread = QThread()
                    worker.moveToThread(thread)
                    thread.started.connect(worker.run)
                    worker.finished.connect(thread.quit)
                    worker.finished.connect(worker.deleteLater)
                    thread.finished.connect(thread.deleteLater)
                    task['thread'] = thread
                    thread.start()

                self.task_started.emit(task['id'])

        except Exception as e:
            logging.error(f"Error iniciando tarea {task['id']}: {e}")
            task['status'] = 'error'
            self.on_task_error(task, str(e))

    def on_task_finished(self, task):
        task['status'] = 'completed'
        self.task_finished.emit(task['id'])
        # Mostrar completado en barra de progreso
        progress_manager.completed(task.get('title', 'Descarga'))
        # Ocultar después de 3 segundos
        progress_manager.hide(3000)
        # Mostrar toast de éxito
        title = task.get('title', 'Canción')
        toast.success(f"{title} descargado correctamente")
        self.process_queue()

    def on_task_error(self, task, error_msg):
        logging.error(f"Task {task['id']} failed: {error_msg}")
        task['status'] = 'error'
        task['error'] = error_msg
        # Mostrar error en barra de progreso
        progress_manager.error(error_msg)
        # Ocultar después de 5 segundos
        progress_manager.hide(5000)
        # Mostrar toast de error
        toast.error(f"Error: {error_msg[:50]}...")
        self.process_queue()

    def _connect_progress_signals(self, worker, task):
        """Conectar señales del worker a la barra de progreso global.

        progress_updated, status_changed, converting, applying_metadata y
        ask_replace están garantizados por BaseDownloadWorker. Solo
        download_started/track_completed/track_info son extras opcionales
        de algunas subclases.
        """
        title = task.get('title', 'Descarga')
        cover_url = task.get('data', {}).get('cover_url')

        worker.progress_updated.connect(lambda p: progress_manager.update(p, f"Descargando: {title}"))
        worker.status_changed.connect(self._update_status)
        worker.converting.connect(progress_manager.converting)
        worker.applying_metadata.connect(progress_manager.metadata)
        worker.ask_replace.connect(
            lambda song, filename, w=worker: self._on_file_exists(w, song, filename)
        )

        if hasattr(worker, 'download_started'):
            try:
                worker.download_started.connect(lambda name, url='': progress_manager.show(name, url or cover_url))
            except TypeError:
                worker.download_started.connect(lambda name: progress_manager.show(name, cover_url))

        if hasattr(worker, 'track_completed'):
            worker.track_completed.connect(lambda info, t=task: t.__setitem__('file_path', info.get('file_path')))
        if hasattr(worker, 'track_info'):
            worker.track_info.connect(lambda info, t=task: t.__setitem__('file_path', info.get('file_path')))

        progress_manager.show(title, cover_url)

    def _update_status(self, status):
        """Actualizar solo el estado sin cambiar el progreso."""
        bar = progress_manager.get_progress_bar()
        if bar:
            bar.status_label.setText(status)

    def _on_file_exists(self, worker, song_title, filename):
        """Mostrar diálogo en el hilo principal cuando un archivo ya existe."""
        from ui.components.file_exists_dialog import FileExistsDialog

        dialog = FileExistsDialog(filename, song_title)
        dialog.exec()

        response = {
            'action': dialog.action,
            'apply_to_all': dialog.apply_to_all
        }

        try:
            worker.set_file_exists_response(response)
        except RuntimeError:
            logging.warning("Worker eliminado antes de enviar respuesta del diálogo")
