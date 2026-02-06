"""
Diálogo para preguntar al usuario qué hacer cuando un archivo ya existe.
Se muestra desde el hilo principal cuando un worker detecta un archivo duplicado.
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QCheckBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor


class FileExistsDialog(QDialog):
    """Diálogo modal que pregunta al usuario qué hacer con un archivo existente."""

    OVERWRITE = 'overwrite'
    SKIP = 'skip'
    RENAME = 'rename'

    def __init__(self, filename, song_title, parent=None):
        super().__init__(parent)
        self.action = self.SKIP
        self.apply_to_all = False

        self.setWindowTitle("Archivo existente")
        self.setFixedWidth(440)
        self.setModal(True)
        self.setStyleSheet(self._dialog_style())
        self._build_ui(filename, song_title)

    def _build_ui(self, filename, song_title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        # Icono
        icon = QLabel("\u26a0\ufe0f")
        icon.setFont(QFont("Segoe UI Emoji", 28))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background: transparent; margin-bottom: 4px;")
        layout.addWidget(icon)

        # Título
        title = QLabel("El archivo ya existe")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; background: transparent; margin-bottom: 8px;")
        layout.addWidget(title)

        # Subtítulo con nombre de canción
        subtitle = QLabel(f'"{song_title}" ya existe en la carpeta de destino')
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #B3B3B3; background: transparent; margin-bottom: 4px;")
        layout.addWidget(subtitle)

        # Ruta del archivo (truncada)
        display_path = self._truncate_path(filename, 55)
        path_label = QLabel(display_path)
        path_label.setFont(QFont("Segoe UI", 9))
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path_label.setToolTip(filename)
        path_label.setStyleSheet("color: #6B6B6B; background: transparent; font-style: italic; margin-bottom: 16px;")
        layout.addWidget(path_label)

        # Línea separadora
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); margin-bottom: 20px;")
        layout.addWidget(separator)

        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        btn_overwrite = QPushButton("Reemplazar")
        btn_overwrite.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        btn_overwrite.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_overwrite.setMinimumHeight(42)
        btn_overwrite.setStyleSheet(self._danger_btn_style())
        btn_overwrite.clicked.connect(self._on_overwrite)
        buttons_layout.addWidget(btn_overwrite)

        btn_skip = QPushButton("Omitir")
        btn_skip.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        btn_skip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_skip.setMinimumHeight(42)
        btn_skip.setStyleSheet(self._secondary_btn_style())
        btn_skip.clicked.connect(self._on_skip)
        buttons_layout.addWidget(btn_skip)

        btn_rename = QPushButton("Renombrar")
        btn_rename.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        btn_rename.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_rename.setMinimumHeight(42)
        btn_rename.setStyleSheet(self._secondary_btn_style())
        btn_rename.clicked.connect(self._on_rename)
        buttons_layout.addWidget(btn_rename)

        layout.addLayout(buttons_layout)

        # Checkbox "Aplicar a todos"
        self.apply_all_checkbox = QCheckBox("Aplicar a todos los archivos restantes")
        self.apply_all_checkbox.setFont(QFont("Segoe UI", 10))
        self.apply_all_checkbox.setStyleSheet("""
            QCheckBox {
                color: #B3B3B3;
                background: transparent;
                spacing: 8px;
                margin-top: 18px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.15);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:checked {
                background-color: #1DB954;
                border-color: #1DB954;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(255, 255, 255, 0.3);
            }
        """)
        layout.addWidget(self.apply_all_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_overwrite(self):
        self.action = self.OVERWRITE
        self.apply_to_all = self.apply_all_checkbox.isChecked()
        self.accept()

    def _on_skip(self):
        self.action = self.SKIP
        self.apply_to_all = self.apply_all_checkbox.isChecked()
        self.accept()

    def _on_rename(self):
        self.action = self.RENAME
        self.apply_to_all = self.apply_all_checkbox.isChecked()
        self.accept()

    @staticmethod
    def _truncate_path(filepath, max_len):
        if len(filepath) <= max_len:
            return filepath
        name = os.path.basename(filepath)
        parent = os.path.dirname(filepath)
        available = max_len - len(name) - 4  # 4 for "/..."
        if available > 0:
            return parent[:available] + "\\..." + "\\" + name
        return "..." + name[-(max_len - 3):]

    @staticmethod
    def _dialog_style():
        return """
            QDialog {
                background-color: #16181D;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
        """

    @staticmethod
    def _danger_btn_style():
        return """
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #F15E6C, stop: 1 #E8384F);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
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
        """

    @staticmethod
    def _secondary_btn_style():
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """
