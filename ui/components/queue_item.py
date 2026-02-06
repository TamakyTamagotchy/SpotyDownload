from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QCursor, QColor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from .animations import AnimationMixin
from config.settings_manager import SettingsManager


class SpotifyInfoLoader(QThread):
    """Thread para cargar información de Spotify sin bloquear la UI."""
    info_loaded = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, spotify_id):
        super().__init__()
        self.spotify_id = spotify_id
    
    def run(self):
        try:
            from downloader.spotify import get_spotify_item
            item = get_spotify_item(self.spotify_id)
            if item:
                # Extraer información relevante
                info = {
                    'title': item.get('name', 'Sin título'),
                    'artists': ', '.join([a['name'] for a in item.get('artists', [])]),
                    'cover_url': ''
                }
                
                # Obtener portada
                if 'album' in item and item['album'] and 'images' in item['album']:
                    images = item['album']['images']
                    if images:
                        info['cover_url'] = images[0]['url']
                elif 'images' in item and item['images']:
                    info['cover_url'] = item['images'][0]['url']
                
                self.info_loaded.emit(info)
            else:
                self.error.emit("No se pudo obtener información de Spotify")
        except Exception as e:
            self.error.emit(str(e))

class QueueItemWidget(QFrame, AnimationMixin):
    """Widget moderno para items en la cola de descargas."""

    # Estilos de barra de progreso reutilizables
    _PROGRESS_STYLE_DEFAULT = """
        QProgressBar {{
            background-color: {bg};
            border: none;
            border-radius: 4px;
        }}
        QProgressBar::chunk {{
            background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                              stop: 0 #1DB954, stop: 0.5 #1ED760, stop: 1 #1FDF64);
            border-radius: 4px;
        }}
    """

    _PROGRESS_STYLE_SOLID = """
        QProgressBar {{
            background-color: {bg};
            border: none;
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {chunk};
            border-radius: 3px;
        }}
    """

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self._is_completed = False
        self._is_error = False
        self._original_geometry = None
        self._info_loader = None
        self._network_manager = None
        
        # Colores fijos (Tema Oscuro Mejorado)
        self.colors = {
            'bg': 'rgba(22, 24, 29, 0.95)',
            'bg_hover': 'rgba(29, 185, 84, 0.08)',
            'border': 'rgba(255, 255, 255, 0.08)',
            'border_hover': 'rgba(29, 185, 84, 0.3)',
            'text_primary': '#FFFFFF',
            'text_secondary': '#B3B3B3',
            'accent': '#1DB954',
            'progress_bg': 'rgba(255, 255, 255, 0.05)',
            'icon_bg': '#1DB954',
            'shadow': 'rgba(0, 0, 0, 0.3)'
        }
        
        self.setObjectName("queueItem")
        self.setup_style()
        self.init_ui()
        self.connect_signals()
        
        # Si es una descarga de Spotify URL, cargar la información
        if task.get('type') == 'spotify_url' and task.get('title') == 'Cargando...':
            self._load_spotify_info()

    def setup_style(self):
        """Configurar estilos del widget con CSS profesional."""
        c = self.colors

        # Sombra más suave y elegante
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(f"""
            #queueItem {{
                background-color: {c['bg']};
                border-radius: 16px;
                border: 1px solid {c['border']};
            }}
            #queueItem:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['border_hover']};
            }}
        """)

    def init_ui(self):
        """Inicializar la interfaz."""
        c = self.colors
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Icono/Portada con fondo moderno
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(56, 56)
        self.icon_container.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #1ED760, stop: 1 #1DB954);
                border-radius: 14px;
            }}
        """)
        
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        self.icon_label = QLabel("🎵")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 24))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; color: white;")
        icon_layout.addWidget(self.icon_label)

        # Label para la portada (inicialmente oculto)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 14px;")
        self.cover_label.setVisible(False)
        
        layout.addWidget(self.icon_container)
        layout.addWidget(self.cover_label)
        
        # Info principal
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 2, 0, 2)
        
        self.title_label = QLabel(self.task.get('title', 'Sin título'))
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {c['text_primary']}; background: transparent;")
        self.title_label.setWordWrap(False) # Evitar multiline para consistencia
        
        # Elipsis para títulos largos
        font_metrics = self.title_label.fontMetrics()
        elided_text = font_metrics.elidedText(self.title_label.text(), Qt.TextElideMode.ElideRight, 300)
        self.title_label.setText(elided_text)
        
        info_layout.addWidget(self.title_label)
        
        self.status_layout = QHBoxLayout()
        self.status_layout.setSpacing(8)
        
        self.status_label = QLabel("En cola...")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        
        self.status_layout.addWidget(self.status_label)
        info_layout.addLayout(self.status_layout)
        
        layout.addLayout(info_layout, 1)
        
        # Barra de progreso
        progress_container = QVBoxLayout()
        progress_container.setSpacing(6)
        progress_container.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(150, 8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            self._PROGRESS_STYLE_DEFAULT.format(bg=c['progress_bg'])
        )
        progress_container.addWidget(self.progress_bar)
        
        self.progress_text = QLabel("0%")
        self.progress_text.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.progress_text.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_container.addWidget(self.progress_text)
        
        layout.addLayout(progress_container)
        
        # Botón cancelar
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setToolTip("Cancelar descarga")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: 1px solid transparent;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(229, 57, 53, 0.1);
                color: #E53935;
                border: 1px solid rgba(229, 57, 53, 0.3);
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_task)
        layout.addWidget(self.cancel_btn)

    def connect_signals(self):
        """Conectar señales del worker."""
        worker = self.task.get('worker')
        if worker:
            if hasattr(worker, 'progress'):
                worker.progress.connect(self.update_progress)
            elif hasattr(worker, 'progress_updated'):
                worker.progress_updated.connect(self.update_progress)
                
            if hasattr(worker, 'finished'):
                worker.finished.connect(self.on_finished)
            
            if hasattr(worker, 'error'):
                worker.error.connect(self.on_error)
            elif hasattr(worker, 'error_occurred'):
                worker.error_occurred.connect(self.on_error)

    def update_progress(self, val):
        """Actualizar progreso."""
        c = self.colors
        self.progress_bar.setValue(val)
        self.progress_text.setText(f"{val}%")
        self.status_label.setText("Descargando...")
        self.status_label.setStyleSheet(f"color: {c['accent']}; background: transparent; font-weight: bold;")

    def on_finished(self):
        """Callback al completar."""
        c = self.colors
        self._is_completed = True
        self.progress_bar.setValue(100)
        self.progress_text.setText("100%")
        
        # Icono de check
        self.status_label.setText("✓ Completado")
        self.status_label.setStyleSheet(f"color: {c['accent']}; background: transparent; font-weight: bold;")
        
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        
        # Animación de pulso
        self.pulse_effect(scale=1.02, duration=300)
        
        # Feedback visual final
        self.progress_bar.setStyleSheet(
            self._PROGRESS_STYLE_SOLID.format(bg=c['accent'], chunk=c['accent'])
        )

    def on_error(self, err):
        """Callback en error."""
        c = self.colors
        self._is_error = True
        self.status_label.setText(f"✕ Error: {err[:30]}...")
        self.status_label.setToolTip(str(err))
        self.status_label.setStyleSheet("color: #E53935; background: transparent; font-weight: bold;")
        
        self.progress_text.setText("Falló")
        self.progress_text.setStyleSheet("color: #E53935; background: transparent;")
        
        # Animación de sacudida
        self.shake_effect(intensity=6, duration=350)
        
        self.progress_bar.setStyleSheet(
            self._PROGRESS_STYLE_SOLID.format(bg=c['progress_bg'], chunk='#E53935')
        )

    def cancel_task(self):
        """Cancelar la tarea."""
        worker = self.task.get('worker')
        if worker and hasattr(worker, 'cancel'):
            worker.cancel()
        
        self.status_label.setText("⏹ Cancelado")
        self.status_label.setStyleSheet("color: #FF9800; background: transparent;")
        self.cancel_btn.setEnabled(False)

    def _load_spotify_info(self):
        """Cargar información de Spotify en un thread separado."""
        spotify_id = self.task.get('data', {}).get('id')
        if not spotify_id:
            return
        
        self._info_loader = SpotifyInfoLoader(spotify_id)
        self._info_loader.info_loaded.connect(self._on_spotify_info_loaded)
        self._info_loader.error.connect(self._on_spotify_info_error)
        self._info_loader.start()
    
    def _on_spotify_info_loaded(self, info):
        """Callback cuando se carga la información de Spotify."""
        # Actualizar título
        title = info.get('title', 'Sin título')
        artists = info.get('artists', '')
        
        display_title = f"{title}" if not artists else f"{title}"
        
        # Actualizar el label con elipsis
        font_metrics = self.title_label.fontMetrics()
        elided_text = font_metrics.elidedText(display_title, Qt.TextElideMode.ElideRight, 300)
        self.title_label.setText(elided_text)
        self.title_label.setToolTip(f"{title} - {artists}")
        
        # Actualizar estado
        self.status_label.setText(f"{artists}" if artists else "En cola...")
        
        # Actualizar la tarea con el título real
        self.task['title'] = title
        self.task['data']['title'] = title
        self.task['data']['artists'] = artists
        self.task['data']['cover_url'] = info.get('cover_url', '')
        
        # Cargar portada
        cover_url = info.get('cover_url')
        if cover_url:
            self._load_cover_image(cover_url)
    
    def _on_spotify_info_error(self, error):
        """Callback cuando hay error cargando información de Spotify."""
        self.title_label.setText("Error cargando info")
        self.status_label.setText(error[:30] + "..." if len(error) > 30 else error)
    
    def _load_cover_image(self, url):
        """Cargar la imagen de portada desde una URL."""
        from PyQt6.QtCore import QUrl
        
        if not self._network_manager:
            self._network_manager = QNetworkAccessManager(self)
            self._network_manager.finished.connect(self._on_cover_loaded)
        
        request = QNetworkRequest(QUrl(url))
        self._network_manager.get(request)
    
    def _on_cover_loaded(self, reply):
        """Callback cuando se carga la imagen de portada."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Escalar y mostrar la imagen con mejor calidad
                scaled_pixmap = pixmap.scaled(
                    56, 56,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled_pixmap)
                
                # Ocultar el ícono y mostrar la portada
                self.icon_container.setVisible(False)
                self.cover_label.setVisible(True)
        
        reply.deleteLater()

