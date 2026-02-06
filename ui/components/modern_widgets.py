"""
Componentes de UI reutilizables con estilo moderno.
Cards, botones, inputs, etc.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QFrame,
                            QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QFont, QIcon, QCursor
from .animations import AnimationMixin, GeometryAnimator


class Card(QFrame, AnimationMixin):
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
                background-color: rgba(22, 24, 29, 0.95);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            #card:hover {
                border: 1px solid rgba(29, 185, 84, 0.5);
                background-color: rgba(22, 24, 29, 1);
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
            self.pulse_effect()  # Feedback visual al hacer clic
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def show_animated(self, target_rect: QRect = None, duration=300):
        """
        Mostrar la card con animación de expansión desde el centro.
        Usa GeometryAnimator para crear efecto de aparición suave.
        """
        if target_rect is None:
            target_rect = self.geometry()
        
        self._show_anim = GeometryAnimator.expand_from_center(self, target_rect, duration)
        self.show()
        self._show_anim.start()
        return self._show_anim
    
    def hide_animated(self, duration=250):
        """
        Ocultar la card con animación de colapso hacia el centro.
        Usa GeometryAnimator para crear efecto de desaparición.
        """
        self._hide_anim = GeometryAnimator.collapse_to_center(
            self, duration, on_finished=self.hide
        )
        self._hide_anim.start()
        return self._hide_anim
    
    def morph_to_rect(self, target_rect: QRect, duration=350):
        """
        Transformar la geometría de la card suavemente.
        Útil para redimensionar o reposicionar dinámicamente.
        """
        self._morph_anim = GeometryAnimator.morph_to(self, target_rect, duration)
        self._morph_anim.start()
        return self._morph_anim


class ModernButton(QPushButton, AnimationMixin):
    """Botón moderno con variantes de estilo."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"
    GHOST = "ghost"

    _STYLES = {
        "primary": """
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #1ED760, stop: 1 #1DB954);
                color: #000000;
                border: none;
                border-radius: 10px;
                padding: 12px 28px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #1FDF64, stop: 1 #1ED760);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #169c46, stop: 1 #148A3D);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.08);
                color: #6B6B6B;
            }
        """,
        "secondary": """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 12px 28px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """,
        "danger": """
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #F15E6C, stop: 1 #E8384F);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px 28px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #F47380, stop: 1 #F15E6C);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #E8384F, stop: 1 #D6293A);
            }
        """,
        "ghost": """
            QPushButton {
                background-color: transparent;
                color: #1DB954;
                border: 2px solid #1DB954;
                border-radius: 10px;
                padding: 12px 28px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(29, 185, 84, 0.15);
                border-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: rgba(29, 185, 84, 0.25);
            }
        """
    }

    def __init__(self, text, variant=PRIMARY, icon=None, parent=None, animated=True):
        super().__init__(text, parent)
        self._variant = variant
        self._animated = animated

        self.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(40)

        if icon:
            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(18, 18))

        self.apply_style()

        # Conectar animación al click si está habilitada
        if animated:
            self.clicked.connect(self._on_click_animation)

    def _on_click_animation(self):
        """Efecto de pulso al hacer clic."""
        self.pulse_effect(scale=1.05, duration=150)

    def slide_to(self, target_rect: QRect, duration=300):
        """
        Deslizar el botón hacia una nueva posición/tamaño.
        Usa GeometryAnimator para animación fluida.
        """
        self._slide_anim = GeometryAnimator.slide_and_resize(self, target_rect, duration)
        self._slide_anim.start()
        return self._slide_anim

    def apply_style(self):
        self.setStyleSheet(self._STYLES.get(self._variant, self._STYLES["primary"]))


class ModernInput(QLineEdit, AnimationMixin):
    """Input moderno con placeholder animado y validación visual."""

    _BASE_STYLE = """
        QLineEdit {
            background-color: rgba(255, 255, 255, 0.05);
            color: #FFFFFF;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 12px 18px;
            selection-background-color: #1DB954;
            font-size: 13px;
        }
        QLineEdit:focus {
            border-color: #1DB954;
            background-color: rgba(255, 255, 255, 0.08);
        }
        QLineEdit:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background-color: rgba(255, 255, 255, 0.07);
        }
        QLineEdit::placeholder {
            color: #6B6B6B;
        }
    """

    _ERROR_STYLE = """
        QLineEdit {
            background-color: rgba(229, 57, 53, 0.05);
            color: #FFFFFF;
            border: 2px solid #E53935;
            border-radius: 10px;
            padding: 12px 18px;
            selection-background-color: #E53935;
            font-size: 13px;
        }
        QLineEdit:focus {
            border-color: #F15E6C;
            background-color: rgba(229, 57, 53, 0.08);
        }
        QLineEdit:hover {
            border-color: #F15E6C;
            background-color: rgba(229, 57, 53, 0.07);
        }
        QLineEdit::placeholder {
            color: #6B6B6B;
        }
    """

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self._original_geometry = None

        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Segoe UI", 11))
        self.setMinimumHeight(44)
        self.setStyleSheet(self._BASE_STYLE)

    def set_error(self, has_error=True, animate=True):
        """Mostrar estado de error visual con animación opcional."""
        if has_error:
            self.setStyleSheet(self._ERROR_STYLE)
            if animate:
                self.shake_effect(intensity=5, duration=300)
        else:
            self.setStyleSheet(self._BASE_STYLE)


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
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                  stop: 0 #1DB954, stop: 1 #1ED760);
                border-radius: 4px;
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
    
    def set_completed(self, animate=True):
        """Marcar como completado con animación de pulso opcional."""
        self.progress_bar.setValue(100)
        self.status_label.setText("✓ Completado")
        self.status_label.setStyleSheet("color: #1DB954; background: transparent;")
        if animate:
            self.pulse_effect(scale=1.03, duration=250)
    
    def show_at_rect(self, rect: QRect, duration=350):
        """
        Mostrar el ProgressCard expandiéndose hacia un rect específico.
        Útil para mostrar progreso en una ubicación determinada.
        """
        self._appear_anim = GeometryAnimator.expand_from_center(self, rect, duration)
        self.show()
        self._appear_anim.start()
        return self._appear_anim
    
    def dismiss_animated(self, duration=200):
        """
        Ocultar el ProgressCard con animación de colapso.
        Útil para descartar notificaciones de progreso.
        """
        self._dismiss_anim = GeometryAnimator.collapse_to_center(
            self, duration, on_finished=self.hide
        )
        self._dismiss_anim.start()
        return self._dismiss_anim
    
    def set_error(self, message, animate=True):
        """Mostrar estado de error con animación de sacudida opcional."""
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
        if animate:
            self.shake_effect(intensity=8, duration=400)


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
