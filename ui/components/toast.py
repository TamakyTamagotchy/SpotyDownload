"""
Sistema de notificaciones Toast/Popup para la interfaz.
Notificaciones elegantes con animaciones de deslizamiento.
Aparecen dentro de la ventana de la aplicación.
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QPushButton, 
                             QApplication, QFrame)
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                          QPoint, pyqtSignal)
from PyQt6.QtGui import QFont


class Toast(QFrame):
    """Notificación tipo toast que aparece dentro de la ventana padre."""
    
    closed = pyqtSignal()
    
    # Tipos de toast
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    
    STYLES = {
        "success": {
            "bg": "#1DB954",
            "border": "#169c46",
            "icon": "✓",
            "text": "#ffffff"
        },
        "error": {
            "bg": "#E53935",
            "border": "#c62828",
            "icon": "✕",
            "text": "#ffffff"
        },
        "warning": {
            "bg": "#FB8C00",
            "border": "#ef6c00",
            "icon": "⚠",
            "text": "#ffffff"
        },
        "info": {
            "bg": "#2196F3",
            "border": "#1976D2",
            "icon": "ℹ",
            "text": "#ffffff"
        }
    }
    
    def __init__(self, message, toast_type=INFO, duration=3000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.toast_type = toast_type
        self._message = message
        self._parent_window = parent
        self._slide_anim = None
        self._hide_anim = None
        
        self.setObjectName("Toast")
        self.setup_ui()
        
    def setup_ui(self):
        style = self.STYLES.get(self.toast_type, self.STYLES["info"])
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Container con estilo
        self.setStyleSheet(f"""
            QFrame#Toast {{
                background-color: {style['bg']};
                border-radius: 8px;
                border: 2px solid {style['border']};
            }}
        """)
        
        # Icono
        icon_label = QLabel(style['icon'])
        icon_label.setFont(QFont("Segoe UI", 14))
        icon_label.setStyleSheet(f"color: {style['text']}; background: transparent;")
        layout.addWidget(icon_label)
        
        # Mensaje
        msg_label = QLabel(self._message)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setStyleSheet(f"color: {style['text']}; background: transparent;")
        msg_label.setWordWrap(True)
        msg_label.setMaximumWidth(350)
        layout.addWidget(msg_label)
        
        # Botón cerrar
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {style['text']};
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
        """)
        close_btn.clicked.connect(self.hide_toast)
        layout.addWidget(close_btn)
        
        self.adjustSize()
        
    def show_toast(self, y_position=20):
        """Mostrar el toast en la posición especificada dentro del padre."""
        if not self._parent_window:
            return
            
        # Calcular posición relativa al padre
        parent_width = self._parent_window.width()
        self.adjustSize()
        
        x_final = parent_width - self.width() - 20
        x_start = parent_width + 10  # Empezar fuera de la pantalla
        y = y_position
        
        # Posicionar fuera de la pantalla inicialmente
        self.move(x_start, y)
        self.show()
        self.raise_()
        
        # Animación de entrada (solo slide, sin opacidad)
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(300)
        self._slide_anim.setStartValue(QPoint(x_start, y))
        self._slide_anim.setEndValue(QPoint(x_final, y))
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()
        
        # Timer para auto-cerrar
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.hide_toast)
    
    def hide_toast(self):
        """Ocultar el toast con animación."""
        if not self._parent_window or not self.isVisible():
            return
            
        parent_width = self._parent_window.width()
        x_end = parent_width + 10
        
        # Animación de salida
        self._hide_anim = QPropertyAnimation(self, b"pos")
        self._hide_anim.setDuration(250)
        self._hide_anim.setStartValue(self.pos())
        self._hide_anim.setEndValue(QPoint(x_end, self.pos().y()))
        self._hide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._hide_anim.finished.connect(self._on_hide_finished)
        self._hide_anim.start()
    
    def _on_hide_finished(self):
        self.closed.emit()
        self.hide()
        self.deleteLater()


class ToastManager:
    """Gestor de múltiples toasts con posicionamiento automático dentro de la ventana."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._toasts = []
            cls._instance._parent_window = None
        return cls._instance
    
    def set_parent(self, parent_window):
        """Establecer la ventana padre donde aparecerán los toasts."""
        self._parent_window = parent_window
    
    def show(self, message, toast_type=Toast.INFO, duration=3000, parent=None):
        """Mostrar un nuevo toast."""
        # Usar el parent proporcionado o el configurado globalmente
        actual_parent = parent or self._parent_window
        
        if not actual_parent:
            # Intentar obtener la ventana activa
            actual_parent = QApplication.activeWindow()
        
        if not actual_parent:
            return None
            
        toast = Toast(message, toast_type, duration, actual_parent)
        toast.closed.connect(lambda: self._remove_toast(toast))
        self._toasts.append(toast)
        self._update_positions()
        return toast
    
    def success(self, message, duration=3000, parent=None):
        return self.show(message, Toast.SUCCESS, duration, parent)
    
    def error(self, message, duration=4000, parent=None):
        return self.show(message, Toast.ERROR, duration, parent)
    
    def warning(self, message, duration=3500, parent=None):
        return self.show(message, Toast.WARNING, duration, parent)
    
    def info(self, message, duration=3000, parent=None):
        return self.show(message, Toast.INFO, duration, parent)
    
    def _remove_toast(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._update_positions()
    
    def _update_positions(self):
        """Actualizar posiciones de todos los toasts activos."""
        y_offset = 20  # Margen desde arriba de la ventana
        
        for toast in self._toasts:
            if toast._parent_window:
                parent_width = toast._parent_window.width()
                toast.adjustSize()
                x = parent_width - toast.width() - 20
                
                if toast.isVisible():
                    # Animar hacia la nueva posición
                    anim = QPropertyAnimation(toast, b"pos")
                    anim.setDuration(200)
                    anim.setStartValue(toast.pos())
                    anim.setEndValue(QPoint(x, y_offset))
                    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    anim.start()
                    toast._pos_anim = anim
                else:
                    # Mostrar en la posición correcta
                    toast.show_toast(y_offset)
                
                y_offset += toast.height() + 10


# Singleton global
toast = ToastManager()
