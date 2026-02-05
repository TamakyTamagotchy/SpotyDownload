import json, os, shutil, logging
class SettingsManager:
    _instance = None
    
    # Formatos de audio soportados
    AUDIO_FORMATS = {
        'mp3': {
            'name': 'MP3',
            'extension': '.mp3',
            'description': 'Formato comprimido con pérdida, amplia compatibilidad',
            'qualities': ['320', '256', '192', '128'],  # kbps
        },
        'flac': {
            'name': 'FLAC',
            'extension': '.flac',
            'description': 'Formato sin pérdida, mayor tamaño pero calidad perfecta',
            'qualities': ['N/A'],  # FLAC no usa bitrate
        }
    }
    
    # Opciones de comportamiento al encontrar archivos existentes
    FILE_EXISTS_OPTIONS = {
        'ask': 'Preguntar',          # Mostrar diálogo
        'overwrite': 'Sobrescribir', # Siempre sobrescribir
        'skip': 'Omitir',            # Siempre omitir
        'rename': 'Renombrar'        # Agregar número al nombre
    }
    
    DEFAULT_SETTINGS = {
        "ffmpeg_path": "",
        "download_folder": os.path.join(os.path.expanduser("~"), "Downloads", "SpotifyMusic"),
        "default_quality": "Mejor",
        "audio_format": "mp3",  # 'mp3' o 'flac'
        "mp3_bitrate": "320",   # kbps para MP3
        "flac_compression": "8",  # 0-8, mayor = más compresión
        "file_exists_action": "overwrite",  # 'ask', 'overwrite', 'skip', 'rename'
        "theme": "dark",
        "max_retries": 3
    }
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings.json')

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
        
        # Auto-detect FFmpeg if not set
        if not self.settings["ffmpeg_path"]:
            print("Detecting ffmpeg")
            self.settings["ffmpeg_path"] = self._detect_ffmpeg()
            print(f"FFmpeg detected: {self.settings['ffmpeg_path']}")

    def _detect_ffmpeg(self):
        """Try to find ffmpeg in system path or common locations"""
        # Check system PATH
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return os.path.dirname(ffmpeg)
        
        # Obtener directorio base del proyecto
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(os.path.dirname(project_dir))
        
        # Check common windows locations
        common_paths = [
            # Rutas relativas al proyecto
            os.path.join(project_dir, "Ffmpeg", "bin"),
            os.path.join(project_dir, "ffmpeg", "bin"),
            # Rutas en carpeta padre (Programas)
            os.path.join(parent_dir, "ffmpeg-7.1-full_build", "bin"),
            os.path.join(parent_dir, "ffmpeg", "bin"),
            # Rutas estándar de Windows
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            os.path.join(os.getcwd(), "ffmpeg", "bin"),
            # Buscar en Downloads también
            os.path.join(os.path.expanduser("~"), "Downloads", "ffmpeg", "bin"),
        ]
        
        for path in common_paths:
            ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                print(f"FFmpeg encontrado en: {path}")
                return path
        
        # Buscar recursivamente en el directorio padre
        for root, dirs, files in os.walk(parent_dir):
            if "ffmpeg.exe" in files:
                print(f"FFmpeg encontrado en: {root}")
                return root
            # Limitar profundidad de búsqueda
            if root.count(os.sep) - parent_dir.count(os.sep) > 3:
                break
                
        return ""

    def get(self, key):
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self._save_settings()

    def _save_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def get_ffmpeg_path(self):
        return self.settings.get("ffmpeg_path", "")
    
    def get_audio_format(self):
        """Obtiene el formato de audio configurado ('mp3' o 'flac')"""
        return self.settings.get("audio_format", "mp3")
    
    def get_mp3_bitrate(self):
        """Obtiene el bitrate para MP3 en kbps"""
        return self.settings.get("mp3_bitrate", "320")
    
    def get_flac_compression(self):
        """Obtiene el nivel de compresión FLAC (0-8)"""
        return self.settings.get("flac_compression", "8")
    
    def get_file_extension(self):
        """Obtiene la extensión de archivo según el formato configurado"""
        fmt = self.get_audio_format()
        return self.AUDIO_FORMATS.get(fmt, {}).get('extension', '.mp3')
    
    def get_format_info(self, format_key=None):
        """Obtiene información del formato de audio"""
        if format_key is None:
            format_key = self.get_audio_format()
        return self.AUDIO_FORMATS.get(format_key, self.AUDIO_FORMATS['mp3'])
    
    def get_file_exists_action(self):
        """Obtiene la acción a realizar cuando existe un archivo"""
        return self.settings.get("file_exists_action", "overwrite")
    
    def should_ask_replace(self):
        """Retorna True si debe preguntar antes de sobrescribir"""
        return self.get_file_exists_action() == 'ask'
    
    def should_overwrite(self):
        """Retorna True si debe sobrescribir automáticamente"""
        return self.get_file_exists_action() == 'overwrite'
    
    def should_skip_existing(self):
        """Retorna True si debe omitir archivos existentes"""
        return self.get_file_exists_action() == 'skip'
    
    def should_rename(self):
        """Retorna True si debe renombrar el archivo nuevo"""
        return self.get_file_exists_action() == 'rename'
