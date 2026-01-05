from PyQt6.QtWidgets import QApplication
from ui.main_window import ModernApp
import sys
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('spotify_downloader.log'),
            logging.StreamHandler()
        ]
    )

if __name__ == "__main__":
    setup_logging()
    app = QApplication(sys.argv)
    try:
        window = ModernApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)
