"""
Componentes de UI reutilizables con estilo moderno.
Cards, botones, inputs, etc.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QFrame,
                             QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor


class Card(QFrame):
    """Card contenedor con sombra y bordes redondeados."""
    
    clicked = pyqtSignal()
    
    def __init__(self, title="", subtitle="", parent=None, clickable=False):
        super().__init__(parent)
        self._clickable = clickable
        self._title = title
        self._subtitle = subtitle
        
        self.setup_style()
        self.setup_ui()
        
        if clickable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def setup_style(self):
        self.setObjectName("card")
        self.setStyleSheet("""
            #card {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A3A;
            }
            #card:hover {
                border: 1px solid #1DB954;
                background-color: #2F2F2F;
            }
        """)
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(8)
        
        if self._title:
            title_label = QLabel(self._title)
            title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
            self.main_layout.addWidget(title_label)
        
        if self._subtitle:
            subtitle_label = QLabel(self._subtitle)
            subtitle_label.setFont(QFont("Segoe UI", 11))
            subtitle_label.setStyleSheet("color: #888888; background: transparent;")
            subtitle_label.setWordWrap(True)
            self.main_layout.addWidget(subtitle_label)
    
    def add_widget(self, widget):
        self.main_layout.addWidget(widget)
    
    def add_layout(self, layout):
        self.main_layout.addLayout(layout)
    
    def mousePressEvent(self, event):
        if self._clickable:
            self.clicked.emit()
        super().mousePressEvent(event)


class ModernButton(QPushButton):
    """Botón moderno con variantes de estilo."""
    
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"
    GHOST = "ghost"
    
    def __init__(self, text, variant=PRIMARY, icon=None, parent=None):
        super().__init__(text, parent)
        self._variant = variant
        
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(40)
        
        if icon:
            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(18, 18))
        
        self.apply_style()
    
    def apply_style(self):
        styles = {
            "primary": """
                QPushButton {
                    background-color: #1DB954;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background-color: #1ED760;
                }
                QPushButton:pressed {
                    background-color: #169c46;
                }
                QPushButton:disabled {
                    background-color: #404040;
                    color: #808080;
                }
            """,
            "secondary": """
                QPushButton {
                    background-color: #3A3A3A;
                    color: #E0E0E0;
                    border: 1px solid #4A4A4A;
                    border-radius: 8px;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background-color: #4A4A4A;
                    border-color: #5A5A5A;
                }
                QPushButton:pressed {
                    background-color: #2A2A2A;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #E53935;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background-color: #EF5350;
                }
                QPushButton:pressed {
                    background-color: #C62828;
                }
            """,
            "ghost": """
                QPushButton {
                    background-color: transparent;
                    color: #1DB954;
                    border: 1px solid #1DB954;
                    border-radius: 8px;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background-color: rgba(29, 185, 84, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(29, 185, 84, 0.2);
                }
            """
        }
        self.setStyleSheet(styles.get(self._variant, styles["primary"]))


class ModernInput(QLineEdit):
    """Input moderno con placeholder animado y validación visual."""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        
        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Segoe UI", 11))
        self.setMinimumHeight(44)
        
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 2px solid #3A3A3A;
                border-radius: 8px;
                padding: 10px 16px;
                selection-background-color: #1DB954;
            }
            QLineEdit:focus {
                border-color: #1DB954;
                background-color: #2F2F2F;
            }
            QLineEdit:hover {
                border-color: #4A4A4A;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
    
    def set_error(self, has_error=True):
        """Mostrar estado de error visual."""
        if has_error:
            self.setStyleSheet(self.styleSheet().replace("#3A3A3A", "#E53935").replace("#1DB954", "#E53935"))
        else:
            self.setStyleSheet(self.styleSheet().replace("#E53935", "#3A3A3A"))


class IconButton(QPushButton):
    """Botón circular con icono."""
    
    def __init__(self, icon_text, size=40, parent=None):
        super().__init__(icon_text, parent)
        
        self.setFixedSize(size, size)
        self.setFont(QFont("Segoe UI", 14))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #3A3A3A;
                color: #E0E0E0;
                border: none;
                border-radius: {size // 2}px;
            }}
            QPushButton:hover {{
                background-color: #1DB954;
                color: white;
            }}
            QPushButton:pressed {{
                background-color: #169c46;
            }}
        """)


class SectionHeader(QWidget):
    """Encabezado de sección con título y acción opcional."""
    
    action_clicked = pyqtSignal()
    
    def __init__(self, title, action_text=None, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        
        # Título
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Botón de acción
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setFont(QFont("Segoe UI", 10))
            action_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            action_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #1DB954;
                    border: none;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    text-decoration: underline;
                }
            """)
            action_btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(action_btn)


class ProgressCard(Card):
    """Card con barra de progreso integrada."""
    
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(title, subtitle, parent)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
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
        
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #888888; background: transparent;")
        
        self.add_widget(self.progress_bar)
        self.add_widget(self.status_label)
    
    def set_progress(self, value, status_text=""):
        self.progress_bar.setValue(value)
        if status_text:
            self.status_label.setText(status_text)
    
    def set_completed(self):
        self.progress_bar.setValue(100)
        self.status_label.setText("✓ Completado")
        self.status_label.setStyleSheet("color: #1DB954; background: transparent;")
    
    def set_error(self, message):
        self.status_label.setText(f"✕ {message}")
        self.status_label.setStyleSheet("color: #E53935; background: transparent;")
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


class Divider(QFrame):
    """Línea divisoria horizontal."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: #3A3A3A;")


class Badge(QLabel):
    """Etiqueta/badge pequeña."""
    
    def __init__(self, text, color="#1DB954", parent=None):
        super().__init__(text, parent)
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 4px 10px;
            }}
        """)
