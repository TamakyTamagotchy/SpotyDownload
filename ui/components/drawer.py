"""
Drawer/Panel deslizable para contenido secundario.
Sin efectos de opacidad para evitar errores de QPainter.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve, 
                          QPoint, pyqtSignal)
from PyQt6.QtGui import QFont, QCursor


class Drawer(QFrame):
    """Panel lateral deslizable."""
    
    opened = pyqtSignal()
    closed = pyqtSignal()
    
    LEFT = "left"
    RIGHT = "right"
    
    def __init__(self, parent, position=RIGHT, width=350):
        super().__init__(parent)
        self._position = position
        self._drawer_width = width
        self._is_open = False
        
        self.setup_style()
        self.setup_ui()
        self.setup_overlay()
        self.hide()
    
    def setup_style(self):
        self.setObjectName("drawer")
        self.setStyleSheet("""
            #drawer {
                background-color: #1E1E1E;
                border-left: 1px solid #2A2A2A;
            }
        """)
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-bottom: 1px solid #2A2A2A;
            }
        """)
        header.setFixedHeight(60)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 8, 0)
        
        self.title_label = QLabel("Panel")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(36, 36)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                font-size: 24px;
                border: none;
                border-radius: 18px;
            }
            QPushButton:hover {
                background: #3A3A3A;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.close_drawer)
        header_layout.addWidget(close_btn)
        
        self.main_layout.addWidget(header)
        
        # Content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #1E1E1E;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #4A4A4A;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5A5A5A;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        self.content_layout.addStretch()
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
    
    def setup_overlay(self):
        """Crear overlay semi-transparente para el fondo."""
        self.overlay = QWidget(self.parent())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.hide()
        self.overlay.mousePressEvent = lambda e: self.close_drawer()
    
    def set_title(self, title):
        self.title_label.setText(title)
    
    def add_widget(self, widget):
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
    
    def clear_content(self):
        """Limpiar contenido del drawer."""
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def open_drawer(self):
        if self._is_open:
            return
        
        self._is_open = True
        parent = self.parent()
        
        if self._position == self.RIGHT:
            start_x = parent.width()
            end_x = parent.width() - self._drawer_width
        else:
            start_x = -self._drawer_width
            end_x = 0
        
        self.setGeometry(start_x, 0, self._drawer_width, parent.height())
        
        # Mostrar overlay
        self.overlay.setGeometry(0, 0, parent.width(), parent.height())
        self.overlay.show()
        self.overlay.raise_()
        
        # Mostrar drawer
        self.show()
        self.raise_()
        
        # Animación de deslizamiento
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setStartValue(QPoint(start_x, 0))
        self.slide_anim.setEndValue(QPoint(end_x, 0))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.finished.connect(self.opened.emit)
        self.slide_anim.start()
    
    def close_drawer(self):
        if not self._is_open:
            return
        
        self._is_open = False
        parent = self.parent()
        
        if self._position == self.RIGHT:
            end_x = parent.width()
        else:
            end_x = -self._drawer_width
        
        # Animación de deslizamiento
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(250)
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(QPoint(end_x, 0))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_anim.finished.connect(self._on_close_finished)
        self.slide_anim.start()
    
    def _on_close_finished(self):
        self.hide()
        self.overlay.hide()
        self.closed.emit()
    
    def toggle(self):
        if self._is_open:
            self.close_drawer()
        else:
            self.open_drawer()
    
    def is_open(self):
        return self._is_open


class BottomSheet(QFrame):
    """Panel inferior deslizable."""
    
    opened = pyqtSignal()
    closed = pyqtSignal()
    
    def __init__(self, parent, height=400):
        super().__init__(parent)
        self._sheet_height = height
        self._is_open = False
        
        self.setup_style()
        self.setup_ui()
        self.setup_overlay()
        self.hide()
    
    def setup_style(self):
        self.setObjectName("bottomSheet")
        self.setStyleSheet("""
            #bottomSheet {
                background-color: #1E1E1E;
                border-top: 1px solid #2A2A2A;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Handle bar
        handle_container = QWidget()
        handle_container.setFixedHeight(24)
        handle_layout = QHBoxLayout(handle_container)
        handle_layout.setContentsMargins(0, 8, 0, 0)
        handle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        handle = QFrame()
        handle.setFixedSize(40, 4)
        handle.setStyleSheet("""
            QFrame {
                background-color: #4A4A4A;
                border-radius: 2px;
            }
        """)
        handle_layout.addWidget(handle)
        
        self.main_layout.addWidget(handle_container)
        
        # Content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 8, 16, 16)
        self.content_layout.setSpacing(12)
        self.content_layout.addStretch()
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
    
    def setup_overlay(self):
        """Crear overlay semi-transparente."""
        self.overlay = QWidget(self.parent())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.hide()
        self.overlay.mousePressEvent = lambda e: self.close_sheet()
    
    def add_widget(self, widget):
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
    
    def clear_content(self):
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def open_sheet(self):
        if self._is_open:
            return
        
        self._is_open = True
        parent = self.parent()
        
        start_y = parent.height()
        end_y = parent.height() - self._sheet_height
        
        self.setGeometry(0, start_y, parent.width(), self._sheet_height)
        
        self.overlay.setGeometry(0, 0, parent.width(), parent.height())
        self.overlay.show()
        self.overlay.raise_()
        
        self.show()
        self.raise_()
        
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setStartValue(QPoint(0, start_y))
        self.slide_anim.setEndValue(QPoint(0, end_y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.finished.connect(self.opened.emit)
        self.slide_anim.start()
    
    def close_sheet(self):
        if not self._is_open:
            return
        
        self._is_open = False
        parent = self.parent()
        end_y = parent.height()
        
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(250)
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(QPoint(0, end_y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_anim.finished.connect(self._on_close_finished)
        self.slide_anim.start()
    
    def _on_close_finished(self):
        self.hide()
        self.overlay.hide()
        self.closed.emit()
    
    def toggle(self):
        if self._is_open:
            self.close_sheet()
        else:
            self.open_sheet()
