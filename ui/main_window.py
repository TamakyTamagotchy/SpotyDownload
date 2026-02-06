from PyQt6.QtWidgets import (QMainWindow, QMessageBox, QWidget,
                             QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel,
                            QTableWidget, QHeaderView, QTableWidgetItem,
                            QApplication)
from PyQt6.QtGui import QFont
import logging, os
from downloader.utils import extract_id, load_download_history, save_download_history
from downloader.spotify import get_spotify_item
from ui.spotify_page import SpotifyPage
from ui.spotify_library_page import SpotifyLibraryPage
from ui.config_page import ConfigPage
from ui.download_page import DownloadPage
from ui.components.navigation import SideNavigation, TopBar
from ui.components.toast import toast
from ui.components.drawer import Drawer
from ui.components.global_progress import progress_manager
from ui.components.quick_settings import QuickSettingsPanel


class ModernApp(QMainWindow):
    """Ventana principal con diseño moderno y transiciones suaves."""
    
    PAGE_TITLES = {
        0: "Descargas",
        1: "Spotify",
        2: "Biblioteca",
        3: "Historial",
        4: "Configuración"
    }
    
    def __init__(self):
        super().__init__()
        self.spotify_client = None
        self._current_page = 0
        self._page_animation = None
        
        self.init_ui()
        self.create_pages()
        self.setup_connections()
        self.load_stylesheet("dark_theme.qss")
        self.load_history()
        self.center_on_screen()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        self.setWindowTitle("MusicBlast")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 800)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Navegación lateral
        self.side_nav = SideNavigation()
        self.side_nav.add_item("📥", "Descargas")
        self.side_nav.add_item("🎧", "Spotify")
        self.side_nav.add_item("📚", "Biblioteca")
        self.side_nav.add_separator("Más")
        self.side_nav.add_item("📋", "Historial")
        self.side_nav.add_item("⚙️", "Configuración")
        
        main_layout.addWidget(self.side_nav)
        
        # Contenedor derecho (topbar + contenido)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Barra superior
        self.top_bar = TopBar()
        self.top_bar.set_title("Descargas")
        self.top_bar.add_action("🔔", "notifications", "Notificaciones")
        self.top_bar.add_action("⚙️", "settings", "Configuración rápida")
        right_layout.addWidget(self.top_bar)
        
        # Stack de páginas con fondo moderno
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0A0E12;")
        right_layout.addWidget(self.stack)
        
        main_layout.addWidget(right_container)
        
        # Drawer para configuración rápida
        self.settings_drawer = Drawer(central, Drawer.RIGHT, 380)
        self.settings_drawer.set_title("⚙️ Configuración Rápida")
        
        # Agregar panel de configuraciones rápidas al drawer
        self.quick_settings_panel = QuickSettingsPanel()
        self.quick_settings_panel.spotify_reconnect.connect(self.on_quick_spotify_reconnect)
        self.settings_drawer.add_widget(self.quick_settings_panel)
        
        # Configurar el ToastManager para que los toasts aparezcan en la ventana
        toast.set_parent(central)
        
        # Configurar la barra de progreso global
        progress_manager.set_parent(central)
    
    def create_pages(self):
        """Crear todas las páginas."""
        # Página de descargas
        self.download_page = DownloadPage(self)
        
        # Página de Spotify
        self.spotify_page = SpotifyPage(self)
        self.stack.addWidget(self.spotify_page)
        
        # Página de biblioteca
        self.library_page = SpotifyLibraryPage(self)
        self.stack.addWidget(self.library_page)
        
        # Página de historial
        self.history_page = self.create_history_page()
        self.stack.addWidget(self.history_page)
        
        # Página de configuración
        self.config_page = ConfigPage(self)
        self.stack.addWidget(self.config_page)
    
    def create_history_page(self):
        """Crear página de historial."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header_label = QLabel("Historial de Descargas")
        header_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header_label)
        
        subtitle = QLabel("Todas tus descargas anteriores")
        subtitle.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(subtitle)
        
        # Tabla
        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Título", "Artista", "Enlace"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.cellDoubleClicked.connect(self.open_file)
        self.history_table.setFont(QFont("Segoe UI", 11))
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1A;
                alternate-background-color: #1E1E1E;
                gridline-color: #2A2A2A;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.history_table)
        
        return page
    
    def setup_connections(self):
        """Configurar conexiones de señales."""
        self.side_nav.page_changed.connect(self.on_page_changed)
        self.top_bar.action_clicked.connect(self.on_topbar_action)
    
    def on_page_changed(self, index):
        """Manejar cambio de página con animación."""
        # Verificar acceso a biblioteca
        if index == 2 and not self.spotify_client:
            toast.warning("Conecta tu cuenta de Spotify primero")
            self.side_nav.set_current_index(1)
            return
        
        # Recargar historial
        if index == 3:
            self.load_history()
        
        # Actualizar título
        self.top_bar.set_title(self.PAGE_TITLES.get(index, ""))
        
        # Animación de transición
        self.animate_page_change(index)
    
    def animate_page_change(self, new_index):
        """Cambiar página sin animación para evitar errores QPainter."""
        self.stack.setCurrentIndex(new_index)
    
    def on_topbar_action(self, action_id):
        """Manejar acciones de la barra superior."""
        if action_id == "settings":
            self.settings_drawer.toggle()
        elif action_id == "notifications":
            toast.info("No hay notificaciones nuevas")
    
    def load_stylesheet(self, filename):
        """Cargar archivo de estilos QSS."""
        try:
            style_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'styles')
            stylesheet_path = os.path.join(style_dir, filename)
            
            if not os.path.exists(stylesheet_path):
                logging.error(f"Archivo de estilo no encontrado: {stylesheet_path}")
                return
            
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
                logging.info(f'Archivo QSS cargado: {filename}')
            
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
            
        except Exception as e:
            logging.error(f"Error al cargar estilos: {e}")
    
    def load_history(self):
        """Cargar historial de descargas."""
        self.history_links = load_download_history()
        self.history_table.setRowCount(0)
        
        for link in self.history_links:
            title, artist = self.get_title_artist_from_link(link)
            self.add_to_history({"title": title, "artist": artist, "url": link}, from_load=True)
    
    def add_to_history(self, item, from_load=False):
        """Agregar item al historial."""
        # Verificar duplicados
        for row in range(self.history_table.rowCount()):
            if self.history_table.item(row, 2).text() == item['url']:
                return
        
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(item['title']))
        self.history_table.setItem(row, 1, QTableWidgetItem(item['artist']))
        self.history_table.setItem(row, 2, QTableWidgetItem(item['url']))
        
        if not from_load:
            self.history_links.append(item['url'])
            save_download_history(self.history_links)
    
    def get_title_artist_from_link(self, link):
        """Obtener título y artista de un enlace."""
        if "open.spotify.com" in link:
            try:
                spotify_id = extract_id(link)
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
                        artist = item.get('owner', {}).get('display_name', 'Desconocido')
                    else:
                        return "Desconocido", "Desconocido"
                    return title, artist
            except Exception:
                pass
        elif "music.youtube.com" in link:
            return "YouTube Music", "YouTube Music"
        return "Desconocido", "Desconocido"
    
    def open_file(self, row, column):
        """Abrir archivo desde historial."""
        link = self.history_table.item(row, 2).text()
        QMessageBox.information(self, "Enlace", f"Enlace de descarga: {link}")
    
    def on_spotify_connected(self, spotify_client):
        """Callback cuando Spotify se conecta."""
        self.spotify_client = spotify_client
        
        if hasattr(self, 'library_page'):
            self.library_page.set_spotify_client(spotify_client)
        
        toast.success("¡Conectado a Spotify!")
        logging.info("Spotify conectado en ventana principal")
    
    def on_spotify_disconnected(self):
        """Callback cuando Spotify se desconecta."""
        self.spotify_client = None
        
        if hasattr(self, 'library_page'):
            self.library_page.clear_library()
        
        if self.stack.currentIndex() == 2:
            self.side_nav.set_current_index(1)
        
        toast.info("Desconectado de Spotify")
        logging.info("Spotify desconectado")
    
    def center_on_screen(self):
        """Centrar la ventana en la pantalla."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            window_geometry.moveCenter(screen_geometry.center())
            self.move(window_geometry.topLeft())

    def on_quick_spotify_reconnect(self):
        """Manejar reconexión de Spotify desde configuraciones rápidas."""
        # Cambiar a la página de Spotify y cerrar el drawer
        self.side_nav.set_current_index(1)
        self.settings_drawer.close_drawer()
        toast.info("Ve a la página de Spotify para reconectar")
