from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox,
                             QFileDialog, QGroupBox, QScrollArea, QMessageBox)
from PyQt6.QtGui import QFont
from config.settings_manager import SettingsManager

class ConfigPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.settings_manager = SettingsManager()
        self.initUI()
        self.load_current_settings()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Título
        title = QLabel("⚙️ Configuración")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1DB954; margin-bottom: 10px;")
        main_layout.addWidget(title)

        # Área de scroll para configuraciones
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # --- Sección de Descargas ---
        download_group = QGroupBox("📥 Descargas")
        download_layout = QVBoxLayout(download_group)
        
        # Ruta de descarga
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText("Ruta de descarga...")
        
        browse_btn = QPushButton("Explorar")
        browse_btn.clicked.connect(self.browse_download_folder)
        
        path_layout.addWidget(QLabel("Carpeta de descarga:"))
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)
        download_layout.addLayout(path_layout)

        # Calidad por defecto
        quality_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["FLAC (Sin pérdida)", "Mejor", "Buena", "Baja"])
        
        quality_layout.addWidget(QLabel("Calidad por defecto:"))
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        download_layout.addLayout(quality_layout)
        
        content_layout.addWidget(download_group)

        # --- Sección de Sistema ---
        system_group = QGroupBox("🔧 Sistema")
        system_layout = QVBoxLayout(system_group)

        # Ruta FFmpeg
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_input = QLineEdit()
        self.ffmpeg_input.setPlaceholderText("Ruta a la carpeta bin de FFmpeg...")
        
        ffmpeg_browse_btn = QPushButton("Buscar")
        ffmpeg_browse_btn.clicked.connect(self.browse_ffmpeg_folder)
        
        ffmpeg_layout.addWidget(QLabel("Ruta FFmpeg:"))
        ffmpeg_layout.addWidget(self.ffmpeg_input)
        ffmpeg_layout.addWidget(ffmpeg_browse_btn)
        system_layout.addLayout(ffmpeg_layout)
        
        # Nota sobre FFmpeg
        ffmpeg_note = QLabel("Nota: FFmpeg es necesario para la conversión a MP3 y metadatos.")
        ffmpeg_note.setStyleSheet("color: #888; font-size: 11px;")
        system_layout.addWidget(ffmpeg_note)

        content_layout.addWidget(system_group)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Botón Guardar
        save_btn = QPushButton("💾 Guardar Configuración")
        save_btn.setFixedSize(200, 40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                font-weight: bold;
                border-radius: 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def load_current_settings(self):
        """Cargar valores actuales desde SettingsManager"""
        self.path_input.setText(self.settings_manager.get("download_folder"))
        self.ffmpeg_input.setText(self.settings_manager.get("ffmpeg_path"))
        
        quality = self.settings_manager.get("default_quality")
        index = self.quality_combo.findText(quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)

    def browse_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de descarga")
        if folder:
            self.path_input.setText(folder)

    def browse_ffmpeg_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta bin de FFmpeg")
        if folder:
            self.ffmpeg_input.setText(folder)

    def save_settings(self):
        try:
            self.settings_manager.set("download_folder", self.path_input.text())
            self.settings_manager.set("ffmpeg_path", self.ffmpeg_input.text())
            self.settings_manager.set("default_quality", self.quality_combo.currentText())
            
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")
