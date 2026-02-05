from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox,
                             QFileDialog, QGroupBox, QScrollArea, QMessageBox,
                             QRadioButton, QButtonGroup, QFrame)
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

        # --- Sección de Formato de Audio ---
        format_group = QGroupBox("Formato de Audio")
        format_layout = QVBoxLayout(format_group)
        
        # Radio buttons para formato
        format_radio_layout = QHBoxLayout()
        self.format_group = QButtonGroup(self)
        
        self.mp3_radio = QRadioButton("MP3 (Comprimido)")
        self.mp3_radio.setToolTip("Formato comprimido con pérdida. Archivos más pequeños, amplia compatibilidad.")
        self.mp3_radio.toggled.connect(self.on_format_changed)
        
        self.flac_radio = QRadioButton("FLAC (Sin pérdida)")
        self.flac_radio.setToolTip("Formato sin pérdida. Calidad perfecta, archivos más grandes.")
        self.flac_radio.toggled.connect(self.on_format_changed)
        
        self.format_group.addButton(self.mp3_radio, 0)
        self.format_group.addButton(self.flac_radio, 1)
        
        format_radio_layout.addWidget(self.mp3_radio)
        format_radio_layout.addWidget(self.flac_radio)
        format_radio_layout.addStretch()
        format_layout.addLayout(format_radio_layout)
        
        # Frame para opciones de MP3
        self.mp3_options_frame = QFrame()
        mp3_options_layout = QVBoxLayout(self.mp3_options_frame)
        mp3_options_layout.setContentsMargins(10, 5, 10, 5)
        
        # Bitrate para MP3
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("Calidad MP3:"))
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["320 kbps (Mejor)", "256 kbps (Alta)", "192 kbps (Buena)", "128 kbps (Normal)"])
        self.bitrate_combo.setToolTip("Mayor bitrate = mejor calidad pero archivos más grandes")
        bitrate_layout.addWidget(self.bitrate_combo)
        bitrate_layout.addStretch()
        mp3_options_layout.addLayout(bitrate_layout)
        
        format_layout.addWidget(self.mp3_options_frame)
        
        # Frame para opciones de FLAC
        self.flac_options_frame = QFrame()
        flac_options_layout = QVBoxLayout(self.flac_options_frame)
        flac_options_layout.setContentsMargins(10, 5, 10, 5)
        
        # Compresión FLAC
        compression_layout = QHBoxLayout()
        compression_layout.addWidget(QLabel("Compresión FLAC:"))
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["8 (Máxima)", "5 (Balanceada)", "0 (Rápida)"])
        self.compression_combo.setToolTip("Mayor compresión = archivos más pequeños pero más tiempo de conversión")
        compression_layout.addWidget(self.compression_combo)
        compression_layout.addStretch()
        flac_options_layout.addLayout(compression_layout)
        
        # Nota sobre FLAC
        flac_note = QLabel("ℹ️ FLAC mantiene calidad perfecta sin importar la compresión.")
        flac_note.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
        flac_options_layout.addWidget(flac_note)
        
        format_layout.addWidget(self.flac_options_frame)
        
        content_layout.addWidget(format_group)

        # Calidad por defecto (ahora es más un preset)
        quality_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Mejor", "Buena", "Baja"])
        self.quality_combo.setToolTip("Calidad de búsqueda de audio en YouTube Music")
        
        quality_layout.addWidget(QLabel("Calidad de búsqueda:"))
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        download_layout.addLayout(quality_layout)
        
        content_layout.addWidget(download_group)

        # --- Sección de Archivos Existentes ---
        exists_group = QGroupBox("📁 Archivos Existentes")
        exists_layout = QVBoxLayout(exists_group)
        
        exists_desc = QLabel("¿Qué hacer cuando el archivo ya existe en la carpeta de destino?")
        exists_desc.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 10px;")
        exists_layout.addWidget(exists_desc)
        
        # Opciones
        self.exists_group = QButtonGroup(self)
        
        self.exists_overwrite = QRadioButton("Sobrescribir (reemplazar el archivo existente)")
        self.exists_overwrite.setToolTip("Siempre reemplaza el archivo existente con la nueva descarga")
        self.exists_group.addButton(self.exists_overwrite, 0)
        exists_layout.addWidget(self.exists_overwrite)
        
        self.exists_skip = QRadioButton("Omitir (no descargar)")
        self.exists_skip.setToolTip("Salta la descarga si el archivo ya existe")
        self.exists_group.addButton(self.exists_skip, 1)
        exists_layout.addWidget(self.exists_skip)
        
        self.exists_rename = QRadioButton("Renombrar (agregar número al nombre)")
        self.exists_rename.setToolTip("Agrega (1), (2), etc. al nombre del nuevo archivo")
        self.exists_group.addButton(self.exists_rename, 2)
        exists_layout.addWidget(self.exists_rename)
        
        content_layout.addWidget(exists_group)

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
        
        # Cargar formato de audio
        audio_format = self.settings_manager.get_audio_format()
        if audio_format == 'flac':
            self.flac_radio.setChecked(True)
        else:
            self.mp3_radio.setChecked(True)
        
        # Cargar bitrate MP3
        mp3_bitrate = self.settings_manager.get_mp3_bitrate()
        bitrate_map = {'320': 0, '256': 1, '192': 2, '128': 3}
        self.bitrate_combo.setCurrentIndex(bitrate_map.get(mp3_bitrate, 0))
        
        # Cargar compresión FLAC
        flac_compression = self.settings_manager.get_flac_compression()
        compression_map = {'8': 0, '5': 1, '0': 2}
        self.compression_combo.setCurrentIndex(compression_map.get(flac_compression, 0))
        
        # Actualizar visibilidad de opciones
        self.on_format_changed()
        
        # Cargar acción para archivos existentes
        file_action = self.settings_manager.get_file_exists_action()
        action_map = {'overwrite': self.exists_overwrite, 'skip': self.exists_skip, 
                      'rename': self.exists_rename}
        if file_action in action_map:
            action_map[file_action].setChecked(True)
        else:
            self.exists_overwrite.setChecked(True)  # Default
        
        # Calidad de búsqueda
        quality = self.settings_manager.get("default_quality")
        index = self.quality_combo.findText(quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
    
    def on_format_changed(self):
        """Mostrar/ocultar opciones según el formato seleccionado"""
        is_mp3 = self.mp3_radio.isChecked()
        self.mp3_options_frame.setVisible(is_mp3)
        self.flac_options_frame.setVisible(not is_mp3)

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
            
            # Guardar formato de audio
            audio_format = 'flac' if self.flac_radio.isChecked() else 'mp3'
            self.settings_manager.set("audio_format", audio_format)
            
            # Guardar bitrate MP3
            bitrate_text = self.bitrate_combo.currentText()
            bitrate = bitrate_text.split()[0]  # Extraer "320" de "320 kbps (Mejor)"
            self.settings_manager.set("mp3_bitrate", bitrate)
            
            # Guardar compresión FLAC
            compression_text = self.compression_combo.currentText()
            compression = compression_text.split()[0]  # Extraer "8" de "8 (Máxima)"
            self.settings_manager.set("flac_compression", compression)
            
            # Guardar acción para archivos existentes
            if self.exists_overwrite.isChecked():
                self.settings_manager.set("file_exists_action", "overwrite")
            elif self.exists_skip.isChecked():
                self.settings_manager.set("file_exists_action", "skip")
            elif self.exists_rename.isChecked():
                self.settings_manager.set("file_exists_action", "rename")
            
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")
