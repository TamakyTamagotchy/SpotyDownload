"""
Widgets para configuraciones rápidas del drawer.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QFileDialog, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
from config.settings_manager import SettingsManager


class QuickSettingItem(QFrame):
    """Item individual de configuración rápida."""
    
    def __init__(self, icon, title, subtitle=""):
        super().__init__()
        self.setup_ui(icon, title, subtitle)
    
    def setup_ui(self, icon, title, subtitle):
        self.setObjectName("quickSettingItem")
        self.setStyleSheet("""
            #quickSettingItem {
                background-color: #252525;
                border-radius: 8px;
                padding: 12px;
            }
            #quickSettingItem:hover {
                background-color: #2A2A2A;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Header con ícono y título
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 16))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Subtítulo
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("Segoe UI", 9))
            subtitle_label.setStyleSheet("color: #888888;")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        
        # Contenedor para widgets adicionales
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        layout.addLayout(self.content_layout)
    
    def add_widget(self, widget):
        """Agregar widget al contenido."""
        self.content_layout.addWidget(widget)


class ThemeSwitcher(QuickSettingItem):
    """Selector de tema claro/oscuro."""
    
    theme_changed = pyqtSignal(str)  # 'dark' o 'light'
    
    def __init__(self):
        super().__init__("🎨", "Tema", "Cambiar entre tema claro y oscuro")
        self.settings = SettingsManager()
        self.setup_controls()
    
    def setup_controls(self):
        combo = QComboBox()
        combo.addItems(["🌙 Oscuro", "☀️ Claro"])
        combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #1DB954;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                color: #FFFFFF;
                selection-background-color: #1DB954;
                border: 1px solid #3A3A3A;
            }
        """)
        
        # Establecer tema actual
        current_theme = self.settings.get("theme")
        combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        
        combo.currentIndexChanged.connect(self.on_theme_changed)
        self.add_widget(combo)
        self.combo = combo
    
    def on_theme_changed(self, index):
        theme = "dark" if index == 0 else "light"
        self.settings.set("theme", theme)
        self.theme_changed.emit(theme)


class SpotifyReconnect(QuickSettingItem):
    """Botón de reconexión de Spotify."""
    
    reconnect_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__("🎧", "Spotify", "Reconectar cuenta de Spotify")
        self.setup_controls()
    
    def setup_controls(self):
        btn = QPushButton("🔄 Reconectar Spotify")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
        """)
        btn.clicked.connect(self.reconnect_clicked.emit)
        self.add_widget(btn)


class DownloadLocationPicker(QuickSettingItem):
    """Selector de ubicación de descarga."""
    
    location_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__("📁", "Ubicación de descarga", "Carpeta donde se guardan las canciones")
        self.settings = SettingsManager()
        self.setup_controls()
    
    def setup_controls(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Label con ruta actual
        self.path_label = QLabel()
        self.path_label.setStyleSheet("""
            QLabel {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 8px;
                font-size: 10px;
            }
        """)
        self.path_label.setWordWrap(True)
        self.update_path_label()
        layout.addWidget(self.path_label, 1)
        
        # Botón para cambiar
        btn = QPushButton("📂")
        btn.setFixedSize(36, 36)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setToolTip("Cambiar ubicación")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
        """)
        btn.clicked.connect(self.select_folder)
        layout.addWidget(btn)
        
        self.add_widget(container)
    
    def update_path_label(self):
        path = self.settings.get("download_folder")
        # Mostrar solo las últimas partes de la ruta
        parts = path.split("\\")
        if len(parts) > 3:
            display = "...\\" + "\\".join(parts[-3:])
        else:
            display = path
        self.path_label.setText(display)
        self.path_label.setToolTip(path)
    
    def select_folder(self):
        current = self.settings.get("download_folder")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de descarga",
            current
        )
        if folder:
            self.settings.set("download_folder", folder)
            self.update_path_label()
            self.location_changed.emit(folder)


class QualitySelector(QuickSettingItem):
    """Selector de calidad de descarga."""
    
    quality_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__("🎵", "Calidad de audio", "Calidad por defecto para descargas")
        self.settings = SettingsManager()
        self.setup_controls()
    
    def setup_controls(self):
        combo = QComboBox()
        qualities = ["Mejor", "320 kbps", "256 kbps", "192 kbps", "128 kbps"]
        combo.addItems(qualities)
        combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #1DB954;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                color: #FFFFFF;
                selection-background-color: #1DB954;
                border: 1px solid #3A3A3A;
            }
        """)
        
        # Establecer calidad actual
        current_quality = self.settings.get("default_quality")
        try:
            index = qualities.index(current_quality)
            combo.setCurrentIndex(index)
        except ValueError:
            combo.setCurrentIndex(0)
        
        combo.currentTextChanged.connect(self.on_quality_changed)
        self.add_widget(combo)
    
    def on_quality_changed(self, quality):
        self.settings.set("default_quality", quality)
        self.quality_changed.emit(quality)


class QuickSettingsPanel(QWidget):
    """Panel completo de configuraciones rápidas."""
    
    spotify_reconnect = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Descripción
        desc = QLabel("Ajusta rápidamente las configuraciones más comunes")
        desc.setStyleSheet("color: #888888; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Spotify
        spotify_reconnect = SpotifyReconnect()
        spotify_reconnect.reconnect_clicked.connect(self.spotify_reconnect.emit)
        layout.addWidget(spotify_reconnect)
        
        # Ubicación de descarga
        download_location = DownloadLocationPicker()
        layout.addWidget(download_location)
        
        # Calidad
        quality = QualitySelector()
        layout.addWidget(quality)
        
        layout.addStretch()
