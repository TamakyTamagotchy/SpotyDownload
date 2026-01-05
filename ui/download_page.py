from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QListWidget, QListWidgetItem, QScrollArea,
                             QFrame, QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSize
import logging
from downloader.utils import extract_id
from core.download_manager import DownloadManager
from ui.components.queue_item import QueueItemWidget
from ui.components.modern_widgets import Card, ModernButton, ModernInput, SectionHeader
from ui.components.toast import toast


class DownloadPage(QWidget):
    """Página de descargas con diseño moderno."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.download_manager = DownloadManager()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Configurar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # === Header Section ===
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        title = QLabel("Descargar Música")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Pega un enlace de Spotify para comenzar la descarga")
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet("color: #888888;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # === Input Card ===
        input_card = Card()
        input_card.setMinimumHeight(120)
        input_card.setMaximumHeight(160)
        
        input_inner = QVBoxLayout()
        input_inner.setSpacing(12)
        input_inner.setContentsMargins(0, 0, 0, 0)
        
        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        
        self.url_input = ModernInput("https://open.spotify.com/track/...")
        self.url_input.setMinimumHeight(44)
        self.url_input.returnPressed.connect(self.add_to_queue)
        input_row.addWidget(self.url_input)
        
        self.add_btn = ModernButton("Agregar", ModernButton.PRIMARY)
        self.add_btn.setFixedWidth(120)
        self.add_btn.setMinimumHeight(44)
        self.add_btn.clicked.connect(self.add_to_queue)
        input_row.addWidget(self.add_btn)
        
        input_inner.addLayout(input_row)
        
        # Quick actions
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        
        hint = QLabel("💡 Soporta: tracks, álbumes y playlists de Spotify")
        hint.setFont(QFont("Segoe UI", 11))
        hint.setStyleSheet("color: #666666;")
        quick_row.addWidget(hint)
        quick_row.addStretch()
        
        input_inner.addLayout(quick_row)
        
        input_card.add_layout(input_inner)
        layout.addWidget(input_card)
        
        # === Queue Section ===
        queue_header = SectionHeader("Cola de Descargas", "Limpiar todo")
        queue_header.action_clicked.connect(self.clear_queue)
        layout.addWidget(queue_header)
        
        # Queue container
        queue_container = QFrame()
        queue_container.setObjectName("queueContainer")
        queue_container.setStyleSheet("""
            #queueContainer {
                background-color: #1A1A1A;
                border: 1px solid #2A2A2A;
                border-radius: 12px;
            }
        """)
        
        queue_layout = QVBoxLayout(queue_container)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        
        # Lista de cola
        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 8px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 4px 0;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        self.queue_list.setMinimumHeight(300)
        queue_layout.addWidget(self.queue_list)
        
        # Empty state
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("📥")
        empty_icon.setFont(QFont("Segoe UI", 48))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("color: #3A3A3A;")
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No hay descargas en cola")
        empty_text.setFont(QFont("Segoe UI", 14))
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet("color: #666666;")
        empty_layout.addWidget(empty_text)
        
        empty_hint = QLabel("Pega un enlace de Spotify arriba para comenzar")
        empty_hint.setFont(QFont("Segoe UI", 12))
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setStyleSheet("color: #4A4A4A;")
        empty_layout.addWidget(empty_hint)
        
        queue_layout.addWidget(self.empty_state)
        
        layout.addWidget(queue_container)
        layout.addStretch()
        
        # Agregar al stack del parent
        self.parent.stack.addWidget(self)
        
        # Actualizar estado inicial
        self.update_empty_state()

    def connect_signals(self):
        """Conectar señales del download manager."""
        self.download_manager.task_added.connect(self.on_task_added)
        self.download_manager.task_started.connect(self.on_task_started)

    def update_empty_state(self):
        """Actualizar visibilidad del estado vacío."""
        has_items = self.queue_list.count() > 0
        self.empty_state.setVisible(not has_items)
        self.queue_list.setVisible(has_items)

    def add_to_queue(self):
        """Agregar URL a la cola de descargas."""
        link = self.url_input.text().strip()
        if not link:
            toast.warning("Ingresa un enlace de Spotify")
            return

        try:
            spotify_id = extract_id(link)
            
            data = {
                'id': spotify_id,
                'url': link,
                'title': f"Cargando..."
            }
            
            self.download_manager.add_download('spotify_url', data)
            self.url_input.clear()
            toast.success("Agregado a la cola")
            
        except Exception as e:
            toast.error(f"Enlace inválido: {e}")
            self.url_input.set_error(True)

    def on_task_added(self, task):
        """Callback cuando se agrega una tarea."""
        item = QListWidgetItem(self.queue_list)
        item.setSizeHint(QSize(0, 80))
        
        widget = QueueItemWidget(task)
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, widget)
        
        self.update_empty_state()

    def on_task_started(self, task_id):
        """Callback cuando inicia una tarea."""
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            widget = self.queue_list.itemWidget(item)
            if widget and widget.task['id'] == task_id:
                widget.connect_signals()
                widget.status_label.setText("Iniciando descarga...")
                break

    def clear_queue(self):
        """Limpiar toda la cola."""
        self.queue_list.clear()
        self.update_empty_state()
        toast.info("Cola limpiada")

