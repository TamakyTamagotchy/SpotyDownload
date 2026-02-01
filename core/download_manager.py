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
                
                # Conectar señales principales
                worker.finished.connect(lambda: self.on_task_finished(task))
                
                # Manejar diferencia en señal de error
                if hasattr(worker, 'error'):
                    worker.error.connect(lambda err: self.on_task_error(task, err))
                elif hasattr(worker, 'error_occurred'):
                    worker.error_occurred.connect(lambda err: self.on_task_error(task, err))
                
                # Conectar señales para la barra de progreso global
                self._connect_progress_signals(worker, task)
                
                # Iniciar worker
                if is_qthread:
                    worker.start()
                else:
                    # Crear thread para QObject worker
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
        """Conectar señales del worker a la barra de progreso global."""
        title = task.get('title', 'Descarga')
        cover_url = task.get('data', {}).get('cover_url')
        
        # Señales de progreso
        if hasattr(worker, 'progress'):
            worker.progress.connect(lambda p: progress_manager.update(p, f"Descargando: {title}"))
        if hasattr(worker, 'progress_updated'):
            worker.progress_updated.connect(lambda p: progress_manager.update(p, f"Descargando: {title}"))
        
        # Señales de estado
        if hasattr(worker, 'download_started'):
            worker.download_started.connect(lambda name: progress_manager.show(name, cover_url))
        if hasattr(worker, 'status_changed'):
            worker.status_changed.connect(lambda status: self._update_status(status))
        
        # Señales de conversión y metadatos
        if hasattr(worker, 'converting'):
            worker.converting.connect(lambda: progress_manager.converting())
        if hasattr(worker, 'applying_metadata'):
            worker.applying_metadata.connect(lambda: progress_manager.metadata())
        
        # Mostrar la barra al inicio con portada
        progress_manager.show(title, cover_url)
    
    def _update_status(self, status):
        """Actualizar solo el estado sin cambiar el progreso."""
        bar = progress_manager.get_progress_bar()
        if bar:
            bar.status_label.setText(status)
