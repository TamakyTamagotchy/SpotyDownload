from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
from .animations import AnimationMixin


class QueueItemWidget(QFrame, AnimationMixin):
    """Widget moderno para items en la cola de descargas."""
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self._is_completed = False
        self._is_error = False
        self._original_geometry = None
        
        self.setObjectName("queueItem")
        self.setup_style()
        self.init_ui()
        self.connect_signals()

    def setup_style(self):
        """Configurar estilos del widget."""
        self.setStyleSheet("""
            #queueItem {
                background-color: #2A2A2A;
                border-radius: 10px;
                border: 1px solid #3A3A3A;
            }
            #queueItem:hover {
                background-color: #2F2F2F;
                border-color: #4A4A4A;
            }
        """)

    def init_ui(self):
        """Inicializar la interfaz."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # Icono con fondo
        icon_container = QFrame()
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet("""
            QFrame {
                background-color: #1DB954;
                border-radius: 8px;
            }
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("🎵")
        icon_label.setFont(QFont("Segoe UI", 18))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_layout.addWidget(icon_label)
        
        layout.addWidget(icon_container)
        
        # Info principal
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_label = QLabel(self.task.get('title', 'Sin título'))
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)
        
        self.status_label = QLabel("En cola...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #888888; background: transparent;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, 1)
        
        # Barra de progreso
        progress_container = QVBoxLayout()
        progress_container.setSpacing(4)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(120, 6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3A3A3A;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 3px;
            }
        """)
        progress_container.addWidget(self.progress_bar)
        
        self.progress_text = QLabel("0%")
        self.progress_text.setFont(QFont("Segoe UI", 9))
        self.progress_text.setStyleSheet("color: #666666; background: transparent;")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_container.addWidget(self.progress_text)
        
        layout.addLayout(progress_container)
        
        # Botón cancelar
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(32, 32)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E53935;
                color: white;
            }
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
        self.progress_bar.setValue(val)
        self.progress_text.setText(f"{val}%")
        self.status_label.setText("Descargando...")
        self.status_label.setStyleSheet("color: #1DB954; background: transparent;")

    def on_finished(self):
        """Callback al completar."""
        self._is_completed = True
        self.progress_bar.setValue(100)
        self.progress_text.setText("100%")
        self.status_label.setText("✓ Completado")
        self.status_label.setStyleSheet("color: #1DB954; background: transparent; font-weight: bold;")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        
        # Animación de pulso para feedback visual de completado
        self.pulse_effect(scale=1.02, duration=300)
        
        # Cambiar estilo del progress bar
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1DB954;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 3px;
            }
        """)

    def on_error(self, err):
        """Callback en error."""
        self._is_error = True
        self.status_label.setText(f"✕ Error: {err[:40]}...")
        self.status_label.setStyleSheet("color: #E53935; background: transparent;")
        self.progress_text.setText("Error")
        self.progress_text.setStyleSheet("color: #E53935; background: transparent;")
        
        # Animación de sacudida para indicar error
        self.shake_effect(intensity=6, duration=350)
        
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3A3A3A;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #E53935;
                border-radius: 3px;
            }
        """)

    def cancel_task(self):
        """Cancelar la tarea."""
        worker = self.task.get('worker')
        if worker and hasattr(worker, 'cancel'):
            worker.cancel()
        
        self.status_label.setText("⏹ Cancelado")
        self.status_label.setStyleSheet("color: #FB8C00; background: transparent;")
        self.cancel_btn.setEnabled(False)
