from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor, QColor
from .animations import AnimationMixin
from config.settings_manager import SettingsManager

class QueueItemWidget(QFrame, AnimationMixin):
    """Widget moderno para items en la cola de descargas."""
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self._is_completed = False
        self._is_error = False
        self._original_geometry = None
        
        # Colores fijos (Tema Oscuro)
        self.colors = {
            'bg': '#2A2A2A',
            'bg_hover': '#333333',
            'border': '#404040',
            'text_primary': '#FFFFFF',
            'text_secondary': '#B3B3B3',
            'accent': '#1DB954',
            'progress_bg': '#404040',
            'icon_bg': '#1DB954'
        }
        
        self.setObjectName("queueItem")
        self.setup_style()
        self.init_ui()
        self.connect_signals()

    def setup_style(self):
        """Configurar estilos del widget con CSS profesional."""
        c = self.colors
        
        # Sombra suave
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet(f"""
            #queueItem {{
                background-color: {c['bg']};
                border-radius: 12px;
                border: 1px solid {c['border']};
            }}
            #queueItem:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['accent']};
            }}
        """)

    def init_ui(self):
        """Inicializar la interfaz."""
        c = self.colors
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Icono con fondo
        icon_container = QFrame()
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background-color: {c['icon_bg']};
                border-radius: 12px;
            }}
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("🎵")
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; color: white;")
        icon_layout.addWidget(icon_label)
        
        layout.addWidget(icon_container)
        
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
        self.progress_bar.setFixedSize(140, 6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['progress_bg']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {c['accent']};
                border-radius: 3px;
            }}
        """)
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
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['accent']};
                border: none;
                border-radius: 3px;
                opacity: 0.5;
            }}
            QProgressBar::chunk {{
                background-color: {c['accent']};
                border-radius: 3px;
            }}
        """)

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
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['progress_bg']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: #E53935;
                border-radius: 3px;
            }}
        """)

    def cancel_task(self):
        """Cancelar la tarea."""
        worker = self.task.get('worker')
        if worker and hasattr(worker, 'cancel'):
            worker.cancel()
        
        self.status_label.setText("⏹ Cancelado")
        self.status_label.setStyleSheet("color: #FF9800; background: transparent;")
        self.cancel_btn.setEnabled(False)

