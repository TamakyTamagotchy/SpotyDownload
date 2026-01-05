"""
Barra de navegación lateral moderna con iconos y animaciones.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QSize, 
                          pyqtSignal, QTimer)
from PyQt6.QtGui import QFont, QColor, QCursor, QPainter, QBrush, QPen


class NavItem(QPushButton):
    """Item individual de la barra de navegación."""
    
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._text = text
        self._selected = False
        
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(48)
        
        self.setup_ui()
        self.update_style()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        
        # Icono
        self.icon_label = QLabel(self._icon)
        self.icon_label.setFont(QFont("Segoe UI", 16))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedWidth(24)
        layout.addWidget(self.icon_label)
        
        # Texto
        self.text_label = QLabel(self._text)
        self.text_label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.text_label)
        
        layout.addStretch()
    
    def update_style(self):
        if self._selected:
            self.setStyleSheet("""
                NavItem {
                    background-color: rgba(29, 185, 84, 0.15);
                    border-left: 3px solid #1DB954;
                    border-radius: 0px 8px 8px 0px;
                }
            """)
            self.icon_label.setStyleSheet("color: #1DB954; background: transparent;")
            self.text_label.setStyleSheet("color: #1DB954; font-weight: bold; background: transparent;")
        else:
            self.setStyleSheet("""
                NavItem {
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                }
                NavItem:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
            """)
            self.icon_label.setStyleSheet("color: #888888; background: transparent;")
            self.text_label.setStyleSheet("color: #CCCCCC; background: transparent;")
    
    def setSelected(self, selected):
        self._selected = selected
        self.setChecked(selected)
        self.update_style()
    
    def isSelected(self):
        return self._selected


class SideNavigation(QWidget):
    """Barra de navegación lateral moderna."""
    
    page_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._current_index = 0
        
        self.setFixedWidth(220)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            SideNavigation {
                background-color: #181818;
                border-right: 1px solid #282828;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header con logo
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #181818;")
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        logo_icon = QLabel("🎵")
        logo_icon.setFont(QFont("Segoe UI", 24))
        logo_icon.setStyleSheet("background: transparent;")
        header_layout.addWidget(logo_icon)
        
        logo_text = QLabel("Spotify DL")
        logo_text.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        logo_text.setStyleSheet("color: #1DB954; background: transparent;")
        header_layout.addWidget(logo_text)
        
        header_layout.addStretch()
        
        main_layout.addWidget(header)
        
        # Separador
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #282828;")
        main_layout.addWidget(separator)
        
        # Container para items de navegación
        self.nav_container = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(8, 16, 8, 16)
        self.nav_layout.setSpacing(4)
        
        main_layout.addWidget(self.nav_container)
        main_layout.addStretch()
        
        # Footer con versión
        footer = QWidget()
        footer.setFixedHeight(40)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        
        version_label = QLabel("v2.0.0")
        version_label.setFont(QFont("Segoe UI", 9))
        version_label.setStyleSheet("color: #666666; background: transparent;")
        footer_layout.addWidget(version_label)
        footer_layout.addStretch()
        
        main_layout.addWidget(footer)
    
    def add_item(self, icon, text):
        """Agregar item de navegación."""
        item = NavItem(icon, text)
        index = len(self._items)  # Capturar el índice actual
        item.clicked.connect(lambda checked, idx=index: self._on_item_clicked(idx))
        
        self._items.append(item)
        self.nav_layout.addWidget(item)
        
        # Seleccionar el primero por defecto
        if len(self._items) == 1:
            item.setSelected(True)
        
        return item
    
    def add_separator(self, label=None):
        """Agregar separador con etiqueta opcional."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(0)
        
        if label:
            label_widget = QLabel(label.upper())
            label_widget.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            label_widget.setStyleSheet("color: #666666; background: transparent;")
            layout.addWidget(label_widget)
        
        self.nav_layout.addWidget(container)
    
    def _on_item_clicked(self, index):
        if index == self._current_index:
            return
        
        # Deseleccionar anterior
        if self._current_index < len(self._items):
            self._items[self._current_index].setSelected(False)
        
        # Seleccionar nuevo
        self._current_index = index
        self._items[index].setSelected(True)
        
        self.page_changed.emit(index)
    
    def set_current_index(self, index):
        """Cambiar página programáticamente."""
        if 0 <= index < len(self._items):
            self._on_item_clicked(index)
    
    def current_index(self):
        return self._current_index


class TopBar(QWidget):
    """Barra superior con título y acciones."""
    
    action_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedHeight(60)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            TopBar {
                background-color: #181818;
                border-bottom: 1px solid #282828;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        
        # Título de página
        self.title_label = QLabel("Inicio")
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Container para botones de acción
        self.actions_container = QWidget()
        self.actions_layout = QHBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        
        layout.addWidget(self.actions_container)
    
    def set_title(self, title):
        self.title_label.setText(title)
    
    def add_action(self, icon, action_id, tooltip=""):
        """Agregar botón de acción."""
        btn = QPushButton(icon)
        btn.setFixedSize(40, 40)
        btn.setFont(QFont("Segoe UI", 14))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        btn.clicked.connect(lambda: self.action_clicked.emit(action_id))
        
        self.actions_layout.addWidget(btn)
        return btn
    
    def clear_actions(self):
        while self.actions_layout.count() > 0:
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
