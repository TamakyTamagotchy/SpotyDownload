"""
MusicBlast - Aplicación moderna para descargar música desde Spotify.

Este módulo inicializa la aplicación PyQt6 con configuraciones optimizadas
para rendimiento y experiencia de usuario.
"""

import sys, logging
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    # Forzar UTF-8 en Windows
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont, QPalette, QColor


def setup_logging() -> None:
    """
    Configura el sistema de logging con rotación de archivos.
    """
    log_dir = Path(__file__).parent
    log_file = log_dir / 'spotify_downloader.log'
    
    # Configuración de formato mejorada
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar handlers
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]
    
    # Agregar file handler con manejo de errores
    try:
        file_handler = logging.FileHandler(
            log_file, 
            encoding='utf-8',
            mode='a'
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    except (IOError, PermissionError) as e:
        print(f"Advertencia: No se pudo crear archivo de log: {e}")
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    # Reducir verbosidad de algunas bibliotecas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('spotipy').setLevel(logging.WARNING)


def configure_qt_application(app: QApplication) -> None:
    """
    Configura opciones avanzadas de la aplicación Qt.
    
    Args:
        app: Instancia de QApplication
    """
    # Configurar atributos de la aplicación
    app.setApplicationName("MusicBlast")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MusicBlast")
    
    # Habilitar High DPI scaling (PyQt6 lo hace por defecto, pero aseguramos)
    # En PyQt6, el high DPI está habilitado por defecto
    
    # Configurar estilo de fuente por defecto
    default_font = QFont("Segoe UI", 10)
    default_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(default_font)
    
    # Deshabilitar efectos que pueden causar lag en algunas configuraciones
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, True)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, True)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, True)


def main() -> int:
    """
    Punto de entrada principal de la aplicación.
    
    Returns:
        Código de salida de la aplicación
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Iniciando MusicBlast...")
    
    try:
        # Crear aplicación Qt
        app = QApplication(sys.argv)
        configure_qt_application(app)
        
        # Importar después de crear QApplication para evitar warnings
        from ui.main_window import ModernApp
        
        # Crear y mostrar ventana principal
        window = ModernApp()
        window.show()
        
        logger.info("Aplicación iniciada correctamente")
        return app.exec()
        
    except ImportError as e:
        logger.critical(f"Error de importación: {e}")
        logger.critical("Asegúrate de que todas las dependencias estén instaladas")
        return 1
    except Exception as e:
        logger.critical(f"Error crítico al iniciar: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
