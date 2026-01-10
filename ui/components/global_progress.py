"""
Barra de progreso global para descargas.
Aparece en la parte inferior de la ventana principal.
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QCursor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl
from .animations import AnimationMixin, GeometryAnimator


class GlobalProgressBar(QFrame, AnimationMixin):
    """Barra de progreso global que muestra el estado de descargas."""
    
    cancel_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_visible = False
        self._current_task = None
        self._slide_anim = None
        self._geometry_anim = None
        self._network_manager = QNetworkAccessManager(self)
        self._network_manager.finished.connect(self._on_cover_loaded)
        self._default_icon = "⬇️"
        self._has_cover = False
        self._use_geometry_anim = True  # Usar animaciones con QRect
        
        self.setObjectName("globalProgress")
        self.setup_style()
        self.setup_ui()
        self.hide()
    
    def setup_style(self):
        self.setStyleSheet("""
            #globalProgress {
                background-color: #252525;
                border-top: 1px solid #1DB954;
            }
        """)
        self.setFixedHeight(70)
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(16)
        
        # Contenedor para icono/portada
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(46, 46)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A3A;
                border-radius: 6px;
                font-size: 18px;
            }
        """)
        self.cover_label.setText("⬇️")
        layout.addWidget(self.cover_label)
        
        # Info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        # Título
        self.title_label = QLabel("Descargando...")
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(self.title_label)
        
        # Subtítulo con estado
        self.status_label = QLabel("Preparando descarga...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_container, 1)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3A3A3A;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Porcentaje
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.percent_label.setStyleSheet("color: #1DB954;")
        self.percent_label.setFixedWidth(50)
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.percent_label)
        
        # Botón cancelar
        cancel_btn = QPushButton("✕")
        cancel_btn.setFixedSize(32, 32)
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666666;
                font-size: 16px;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #3A3A3A;
                color: #E53935;
            }
        """)
        cancel_btn.clicked.connect(self.cancel_clicked.emit)
        layout.addWidget(cancel_btn)
    
    def show_progress(self, title="Descargando...", cover_url=None, animate=True):
        """Mostrar la barra de progreso con animación usando GeometryAnimator."""
        if self._is_visible:
            # Si ya está visible, solo actualizar título y portada
            self.title_label.setText(title)
            if cover_url:
                self.set_cover(cover_url)
            return
            
        self._is_visible = True
        self._has_cover = False
        self.title_label.setText(title)
        self.status_label.setText("Preparando descarga...")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.cover_label.setText("⬇️")
        self.cover_label.setPixmap(QPixmap())  # Limpiar pixmap anterior
        
        # Cargar portada si se proporciona
        if cover_url:
            self.set_cover(cover_url)
        
        parent = self.parent()
        if parent:
            bar_height = 70
            start_rect = QRect(0, parent.height(), parent.width(), bar_height)
            end_rect = QRect(0, parent.height() - bar_height, parent.width(), bar_height)
            
            self.setGeometry(start_rect)
            self.show()
            self.raise_()
            
            if animate and self._use_geometry_anim:
                # Usar GeometryAnimator para animación con QRect
                self._geometry_anim = GeometryAnimator.slide_and_resize(self, end_rect, 300)
                self._geometry_anim.start()
            elif animate:
                # Animación de deslizamiento clásica
                self._slide_anim = QPropertyAnimation(self, b"pos")
                self._slide_anim.setDuration(300)
                self._slide_anim.setStartValue(QPoint(0, parent.height()))
                self._slide_anim.setEndValue(QPoint(0, parent.height() - bar_height))
                self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._slide_anim.start()
            else:
                self.setGeometry(end_rect)
    
    def hide_progress(self, animate=True):
        """Ocultar la barra de progreso con animación usando GeometryAnimator."""
        if not self._is_visible:
            return
            
        self._is_visible = False
        parent = self.parent()
        
        if parent and animate:
            bar_height = 70
            end_rect = QRect(0, parent.height(), parent.width(), bar_height)
            
            if self._use_geometry_anim:
                # Usar GeometryAnimator para animación con QRect
                self._geometry_anim = GeometryAnimator.slide_and_resize(self, end_rect, 250)
                self._geometry_anim.finished.connect(self.hide)
                self._geometry_anim.start()
            else:
                self._slide_anim = QPropertyAnimation(self, b"pos")
                self._slide_anim.setDuration(250)
                self._slide_anim.setStartValue(self.pos())
                self._slide_anim.setEndValue(QPoint(0, parent.height()))
                self._slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
                self._slide_anim.finished.connect(self.hide)
                self._slide_anim.start()
        else:
            self.hide()
    
    def update_progress(self, percent, status=None):
        """Actualizar el progreso."""
        self.progress_bar.setValue(int(percent))
        self.percent_label.setText(f"{int(percent)}%")
        
        if status:
            self.status_label.setText(status)
        elif percent < 100:
            self.status_label.setText(f"Descargando... {int(percent)}%")
        else:
            self.status_label.setText("Completado")
    
    def set_cover(self, cover_url):
        """Cargar y mostrar la portada desde URL."""
        if cover_url:
            request = QNetworkRequest(QUrl(cover_url))
            self._network_manager.get(request)
    
    def _on_cover_loaded(self, reply: QNetworkReply):
        """Callback cuando la portada se carga."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Escalar y mostrar
                scaled = pixmap.scaled(
                    46, 46,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Recortar al centro si es necesario
                if scaled.width() > 46 or scaled.height() > 46:
                    x = (scaled.width() - 46) // 2
                    y = (scaled.height() - 46) // 2
                    scaled = scaled.copy(x, y, 46, 46)
                
                self.cover_label.setPixmap(scaled)
                self.cover_label.setText("")  # Quitar emoji
                self._has_cover = True
        reply.deleteLater()
    
    def _set_icon(self, emoji):
        """Establecer icono emoji solo si no hay portada."""
        if not self._has_cover:
            self.cover_label.setText(emoji)
            self.cover_label.setPixmap(QPixmap())
    
    def set_converting(self):
        """Mostrar estado de conversión."""
        self._set_icon("🔄")
        self.status_label.setText("Convirtiendo a MP3...")
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
    
    def set_metadata(self):
        """Mostrar estado de metadatos."""
        self._set_icon("📝")
        self.status_label.setText("Aplicando metadatos y portada...")
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
    
    def set_completed(self, title=""):
        """Mostrar estado completado."""
        self._set_icon("✅")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.status_label.setText(f"¡{title} descargado!" if title else "¡Descarga completada!")
        self.title_label.setText("Completado")
    
    def set_error(self, message="Error en la descarga"):
        """Mostrar estado de error."""
        self._set_icon("❌")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.percent_label.setText("--")
        self.status_label.setText(message)
        self.title_label.setText("Error")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3A3A3A;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #E53935;
                border-radius: 4px;
            }
        """)
    
    def reset_style(self):
        """Resetear estilos a normal."""
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3A3A3A;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 4px;
            }
        """)


class GlobalProgressManager:
    """Singleton para manejar la barra de progreso global."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._progress_bar = None
            cls._instance._parent = None
        return cls._instance
    
    def set_parent(self, parent):
        """Establecer el parent y crear la barra de progreso."""
        self._parent = parent
        self._progress_bar = GlobalProgressBar(parent)
    
    def get_progress_bar(self):
        """Obtener la barra de progreso."""
        return self._progress_bar
    
    def show(self, title="Descargando...", cover_url=None):
        """Mostrar la barra de progreso."""
        if self._progress_bar:
            self._progress_bar.reset_style()
            self._progress_bar.show_progress(title, cover_url)
    
    def hide(self, delay=0):
        """Ocultar la barra de progreso."""
        if self._progress_bar:
            if delay > 0:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(delay, self._progress_bar.hide_progress)
            else:
                self._progress_bar.hide_progress()
    
    def update(self, percent, status=None):
        """Actualizar progreso."""
        if self._progress_bar:
            self._progress_bar.update_progress(percent, status)
    
    def converting(self):
        """Modo conversión."""
        if self._progress_bar:
            self._progress_bar.set_converting()
    
    def metadata(self):
        """Modo metadatos."""
        if self._progress_bar:
            self._progress_bar.set_metadata()
    
    def completed(self, title=""):
        """Completado."""
        if self._progress_bar:
            self._progress_bar.set_completed(title)
    
    def error(self, message="Error"):
        """Error."""
        if self._progress_bar:
            self._progress_bar.set_error(message)


# Singleton global
progress_manager = GlobalProgressManager()
