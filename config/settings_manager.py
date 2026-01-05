import json
import os
import logging
import shutil

class SettingsManager:
    _instance = None
    DEFAULT_SETTINGS = {
        "ffmpeg_path": "",
        "download_folder": os.path.join(os.path.expanduser("~"), "Downloads", "SpotifyMusic"),
        "default_quality": "Mejor",
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
