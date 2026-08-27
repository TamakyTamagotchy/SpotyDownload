#ui/history_page.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication, QTableWidget, 
                            QHeaderView, QTableWidgetItem, QHBoxLayout, QLineEdit, QPushButton, QMenu)
from PyQt6.QtCore import Qt, pyqtSlot
from downloader.utils import load_download_history, save_download_history
from downloader.spotify import get_spotify_item

from PyQt6.QtWidgets import QMenu  # Asegurar import para el menú

class CustomLineEdit(QLineEdit):
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        action_cut = menu.addAction("Cortar")
        action_copy = menu.addAction("Copiar")
        action_paste = menu.addAction("Pegar")
        action_select_all = menu.addAction("Seleccionar Todo")
        action = menu.exec_(event.globalPos())
        if action == action_cut:
            self.cut()
        elif action == action_copy:
            self.copy()
        elif action == action_paste:
            self.paste()
        elif action == action_select_all:
            self.selectAll()

class HistoryPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Añadir controles de filtrado con CustomLineEdit en lugar de QLineEdit
        filter_layout = QHBoxLayout()
        self.search_input = CustomLineEdit()  # Antes: QLineEdit()
        self.search_input.setPlaceholderText("Buscar en el historial...")
        self.search_input.textChanged.connect(self.filter_history)
        
        self.clear_button = QPushButton("Limpiar Historial")
        self.clear_button.clicked.connect(self.clear_history)
        
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.clear_button)
        
        layout.addLayout(filter_layout)
        
        # Configurar tabla
        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Título", "Artista", "Enlace"])
        header = self.history_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(QLabel("Historial de Descargas"))
        layout.addWidget(self.history_table)
        self.parent.stack.addWidget(self)

    def load_history(self):
        self.history_links = load_download_history()
        for link in self.history_links:
            title, artist = self.get_title_artist_from_link(link)
            self.add_to_history({"title": title, "artist": artist, "url": link}, from_load=True)

    def add_to_history(self, item, from_load=False):
        for row in range(self.history_table.rowCount()):
            url_item = self.history_table.item(row, 2)
            if url_item and url_item.text() == item['url']:
                return
        row_position = self.history_table.rowCount()
        self.history_table.insertRow(row_position)
        self.history_table.setItem(row_position, 0, QTableWidgetItem(item['title']))
        self.history_table.setItem(row_position, 1, QTableWidgetItem(item['artist']))
        self.history_table.setItem(row_position, 2, QTableWidgetItem(item['url']))

    @pyqtSlot(str)
    def filter_history(self, text):
        for row in range(self.history_table.rowCount()):
            should_show = False
            for col in range(self.history_table.columnCount()):
                item = self.history_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    should_show = True
                    break
            self.history_table.setRowHidden(row, not should_show)

    def show_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Eliminar")
        copy_link_action = menu.addAction("Copiar enlace")
        
        action = menu.exec_(self.history_table.mapToGlobal(position))
        
        if action == delete_action:
            self.delete_selected_items()
        elif action == copy_link_action:
            self.copy_selected_link()

    def delete_selected_items(self):
        selected_rows = set(item.row() for item in self.history_table.selectedItems())
        for row in sorted(selected_rows, reverse=True):
            self.history_table.removeRow(row)
            if row < len(self.history_links):
                self.history_links.pop(row)
        save_download_history(self.history_links)

    def copy_selected_link(self):
        selected_items = self.history_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            link_item = self.history_table.item(row, 2)
            if link_item:
                QApplication.clipboard().setText(link_item.text())

    def get_title_artist_from_link(self, link):
        try:
            spotify_id = (link)
            item = get_spotify_item(spotify_id)
            if item:
                tipo = item.get('__type')
                if tipo == 'track':
                    title = item.get('name', 'Desconocido')
                    artist = ', '.join([a['name'] for a in item.get('artists', [])]) or "Desconocido"
                elif tipo == 'album':
                    title = item.get('name', 'Álbum')
                    artist = ', '.join([a['name'] for a in item.get('artists', [])]) or "Desconocido"
                elif tipo == 'playlist':
                    title = item.get('name', 'Playlist')
                    owner = item.get('owner', {}).get('display_name', 'Desconocido')
                    artist = owner
                else:
                    title, artist = "Desconocido", "Desconocido"
                return title, artist
        except Exception:
            pass
        return "Desconocido", "Desconocido"
