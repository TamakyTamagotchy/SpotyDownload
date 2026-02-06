from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QListWidget, QListWidgetItem, QScrollArea, QFrame, 
                            QMessageBox, QProgressBar, QSplitter, QSizePolicy, QApplication)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QPixmap, QCursor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import logging
from core.download_manager import DownloadManager

class SpotifyLibraryPage(QWidget):
    """Página dedicada para mostrar playlists y canciones de Spotify"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.spotify_client = None
        self.current_tracks = []
        self.current_playlist_name = ""
        self.download_manager = DownloadManager()
        self._network_manager = QNetworkAccessManager(self)
        self._pending_covers = {}  # Para rastrear portadas pendientes
        
        self.initUI()
    
    def initUI(self):
        """Inicializar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título principal
        self.setup_header(layout)
        
        # Splitter principal para dividir playlists y canciones
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel izquierdo: Playlists
        self.setup_playlists_panel(splitter)
        
        # Panel derecho: Canciones
        self.setup_tracks_panel(splitter)
        
        # Configurar proporción del splitter
        splitter.setSizes([300, 500])
        splitter.setChildrenCollapsible(False)
        
        layout.addWidget(splitter)
        
        # Panel inferior: Controles
        self.setup_controls_panel(layout)
    
    def setup_header(self, parent_layout):
        """Configurar encabezado de la página"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(16)
        
        # Título
        title = QLabel("Biblioteca")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        
        # Estado de conexión
        self.connection_status = QLabel("Sin conexión")
        self.connection_status.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.connection_status.setStyleSheet("""
            QLabel {
                background-color: #E53935;
                color: white;
                padding: 6px 14px;
                border-radius: 12px;
            }
        """)
        
        # Botón de actualizar
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.refresh_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_button.clicked.connect(self.refresh_library)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                padding: 8px 20px;
                border-radius: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #666666;
            }
        """)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.connection_status)
        header_layout.addWidget(self.refresh_button)
        
        parent_layout.addLayout(header_layout)
    
    def setup_playlists_panel(self, parent_splitter):
        """Configurar panel de playlists"""
        playlists_widget = QFrame()
        playlists_widget.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border-radius: 12px;
            }
        """)
        playlists_layout = QVBoxLayout(playlists_widget)
        playlists_layout.setContentsMargins(16, 16, 16, 16)
        playlists_layout.setSpacing(12)
        
        # Título del panel
        playlists_title = QLabel("Playlists")
        playlists_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        playlists_title.setStyleSheet("color: #FFFFFF; background: transparent;")
        playlists_layout.addWidget(playlists_title)
        
        # Lista de playlists
        self.playlists_list = QListWidget()
        self.playlists_list.itemClicked.connect(self.on_playlist_selected)
        self.playlists_list.setStyleSheet("""
            QListWidget {
                border: none;
                border-radius: 8px;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 12px;
                border-radius: 8px;
                margin: 2px 0;
                color: #E0E0E0;
                background-color: #252525;
            }
            QListWidget::item:hover {
                background-color: #2A2A2A;
            }
            QListWidget::item:selected {
                background-color: #1DB954;
                color: white;
            }
        """)
        playlists_layout.addWidget(self.playlists_list)
        
        # Información de la playlist seleccionada
        self.playlist_info = QLabel("Selecciona una playlist")
        self.playlist_info.setWordWrap(True)
        self.playlist_info.setFont(QFont("Segoe UI", 11))
        self.playlist_info.setStyleSheet("""
            QLabel {
                background-color: #252525;
                padding: 14px;
                border-radius: 8px;
                color: #888888;
            }
        """)
        playlists_layout.addWidget(self.playlist_info)
        
        parent_splitter.addWidget(playlists_widget)
    
    def setup_tracks_panel(self, parent_splitter):
        """Configurar panel de canciones"""
        tracks_widget = QFrame()
        tracks_widget.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border-radius: 12px;
            }
        """)
        tracks_layout = QVBoxLayout(tracks_widget)
        tracks_layout.setContentsMargins(16, 16, 16, 16)
        tracks_layout.setSpacing(12)
        
        # Encabezado del panel de canciones
        tracks_header = QHBoxLayout()
        
        self.tracks_title = QLabel("Canciones")
        self.tracks_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.tracks_title.setStyleSheet("color: #FFFFFF; background: transparent;")
        
        self.tracks_count = QLabel("")
        self.tracks_count.setFont(QFont("Segoe UI", 11))
        self.tracks_count.setStyleSheet("color: #666666; background: transparent;")
        
        tracks_header.addWidget(self.tracks_title)
        tracks_header.addStretch()
        tracks_header.addWidget(self.tracks_count)
        
        tracks_layout.addLayout(tracks_header)
        
        # Barra de progreso para carga de canciones
        self.tracks_progress = QProgressBar()
        self.tracks_progress.setVisible(False)
        self.tracks_progress.setFixedHeight(4)
        self.tracks_progress.setTextVisible(False)
        self.tracks_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: #2A2A2A;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 2px;
            }
        """)
        tracks_layout.addWidget(self.tracks_progress)
        
        # Área de scroll para las canciones
        self.tracks_scroll = QScrollArea()
        self.tracks_scroll.setWidgetResizable(True)
        self.tracks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tracks_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #1A1A1A;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #3A3A3A;
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4A4A4A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        self.tracks_widget = QWidget()
        self.tracks_widget.setStyleSheet("background: transparent;")
        self.tracks_layout = QVBoxLayout(self.tracks_widget)
        self.tracks_layout.setSpacing(8)
        self.tracks_layout.setContentsMargins(0, 0, 8, 0)
        self.tracks_layout.addStretch()
        
        self.tracks_scroll.setWidget(self.tracks_widget)
        tracks_layout.addWidget(self.tracks_scroll)
        
        parent_splitter.addWidget(tracks_widget)
    
    def setup_controls_panel(self, parent_layout):
        """Configurar panel de controles - compacto"""
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(16, 8, 16, 8)
        controls_layout.setSpacing(12)
        
        # Info de playlist seleccionada
        self.download_info = QLabel("")
        self.download_info.setFont(QFont("Segoe UI", 10))
        self.download_info.setStyleSheet("color: #666666;")
        
        # Botón de descargar toda la playlist
        self.download_all_button = QPushButton("↓  Descargar Todo")
        self.download_all_button.setEnabled(False)
        self.download_all_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.download_all_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_all_button.clicked.connect(self.download_all_tracks)
        self.download_all_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                padding: 10px 24px;
                border-radius: 22px;
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
                padding-top: 12px;
                padding-bottom: 8px;
            }
            QPushButton:disabled {
                background-color: #252525;
                color: #555555;
                border: 1px solid #333333;
            }
        """)
        
        controls_layout.addWidget(self.download_info)
        controls_layout.addStretch()
        controls_layout.addWidget(self.download_all_button)
        
        parent_layout.addLayout(controls_layout)
    
    def set_spotify_client(self, spotify_client):
        """Establecer cliente de Spotify"""
        self.spotify_client = spotify_client
        if spotify_client:
            self.update_connection_status("Conectado", "green")
            self.refresh_button.setEnabled(True)
            self.load_playlists()
        else:
            self.update_connection_status("Sin conexión", "red")
            self.refresh_button.setEnabled(False)
            self.clear_library()
    
    def update_connection_status(self, text, color):
        """Actualizar estado de conexión"""
        colors = {
            "green": "#1DB954",
            "red": "#E53935", 
            "orange": "#FF9800"
        }
        
        self.connection_status.setText(text)
        self.connection_status.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.get(color, '#333')};
                color: white;
                padding: 8px 16px;
                border-radius: 16px;
                font-weight: 600;
            }}
        """)
    
    def load_playlists(self):
        """Cargar playlists del usuario"""
        if not self.spotify_client:
            return
        
        try:
            self.playlists_list.clear()
            self.update_connection_status("Cargando...", "orange")
            
            playlists = []
            
            # Cargar canciones guardadas primero
            try:
                liked_songs_count = self.spotify_client.current_user_saved_tracks(limit=1)['total']
                playlists.append({
                    'name': 'Canciones que te gustan',
                    'id': 'liked_songs',
                    'tracks': {'total': liked_songs_count},
                    'images': [{'url': ''}],
                    'owner': {'display_name': 'Tu biblioteca'},
                    'description': f'{liked_songs_count} canciones guardadas'
                })
            except Exception as e:
                logging.warning(f"No se pudieron cargar canciones guardadas: {e}")
            
            # Cargar playlists del usuario
            results = self.spotify_client.current_user_playlists(limit=50)
            playlists.extend(results['items'])
            
            # Obtener playlists adicionales si hay más
            while results['next']:
                results = self.spotify_client.next(results)
                playlists.extend(results['items'])
            
            # Agregar playlists a la lista
            for playlist in playlists:
                name = playlist['name']
                track_count = playlist['tracks']['total']
                owner = playlist['owner']['display_name']
                
                item_text = f"{name}\n{track_count} canciones"
                if owner != "Tu biblioteca":
                    item_text += f" · {owner}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, playlist)
                
                # Tooltip con descripción
                if playlist['id'] == 'liked_songs':
                    item.setToolTip("Tus canciones guardadas en Spotify")
                else:
                    description = playlist.get('description', '')
                    if description:
                        item.setToolTip(description)
                
                self.playlists_list.addItem(item)
            
            self.update_connection_status(f"{len(playlists)} playlists", "green")
            
        except Exception as e:
            logging.error(f"Error cargando playlists: {e}")
            self.update_connection_status("Error", "red")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las playlists:\n{e}")
    
    def on_playlist_selected(self, item):
        """Manejar selección de playlist"""
        playlist_data = item.data(Qt.ItemDataRole.UserRole)
        self.current_playlist_name = playlist_data['name']
        
        # Actualizar información de la playlist
        track_count = playlist_data['tracks']['total']
        owner = playlist_data['owner']['display_name']
        description = playlist_data.get('description', 'Sin descripción')
        
        info_text = f"""
        <b style="color: #FFFFFF; font-size: 13px;">{playlist_data['name']}</b><br>
        <span style="color: #1DB954;">{track_count} canciones</span><br>
        <span style="color: #666666;">{owner}</span>
        """
        self.playlist_info.setText(info_text)
        
        # Actualizar título del panel de canciones
        self.tracks_title.setText(playlist_data['name'])
        self.tracks_count.setText("")
        
        # Limpiar canciones anteriores
        self.clear_tracks()
        
        # Cargar canciones de la playlist
        self.load_playlist_tracks(playlist_data['id'])
    
    def load_playlist_tracks(self, playlist_id):
        """Cargar canciones de una playlist"""
        try:
            self.tracks_progress.setVisible(True)
            self.tracks_progress.setValue(0)
            self.tracks_progress.setFormat("Cargando canciones...")
            
            tracks = []
            
            if playlist_id == 'liked_songs':
                # Cargar canciones guardadas
                results = self.spotify_client.current_user_saved_tracks(limit=50)
                for item in results['items']:
                    if item['track']:
                        tracks.append(item['track'])
                
                while results['next']:
                    progress = int((len(tracks) / (len(tracks) + 50)) * 100)
                    self.tracks_progress.setValue(progress)
                    self.tracks_progress.setFormat(f"Cargando... {len(tracks)} canciones")
                    QApplication.processEvents()
                    
                    results = self.spotify_client.next(results)
                    for item in results['items']:
                        if item['track']:
                            tracks.append(item['track'])
            else:
                # Cargar playlist normal
                results = self.spotify_client.playlist_tracks(playlist_id, limit=50)
                for item in results['items']:
                    if item['track']:
                        tracks.append(item['track'])
                
                while results['next']:
                    progress = int((len(tracks) / (len(tracks) + 50)) * 100)
                    self.tracks_progress.setValue(progress)
                    self.tracks_progress.setFormat(f"Cargando... {len(tracks)} canciones")
                    QApplication.processEvents()
                    
                    results = self.spotify_client.next(results)
                    for item in results['items']:
                        if item['track']:
                            tracks.append(item['track'])
            
            # Mostrar canciones
            self.display_tracks(tracks)
            
            self.tracks_progress.setVisible(False)
            self.tracks_count.setText(f"{len(tracks)} canciones")
            self.download_all_button.setEnabled(len(tracks) > 0)
            
        except Exception as e:
            logging.error(f"Error cargando canciones: {e}")
            self.tracks_progress.setVisible(False)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las canciones:\n{e}")
    
    def display_tracks(self, tracks):
        """Mostrar canciones en el panel"""
        self.current_tracks = tracks
        
        # Limpiar tracks anteriores
        self.clear_tracks()
        
        for i, track in enumerate(tracks):
            track_widget = self.create_track_widget(track, i + 1)
            self.tracks_layout.insertWidget(self.tracks_layout.count() - 1, track_widget)
        
        # Scroll al inicio
        QTimer.singleShot(100, lambda: self.tracks_scroll.verticalScrollBar().setValue(0))
    
    def create_track_widget(self, track, track_number):
        """Crear widget para mostrar una canción con portada"""
        frame = QFrame()
        frame.setObjectName("trackFrame")
        frame.setFixedHeight(50)  # Altura fija para todos los items
        frame.setStyleSheet("""
            #trackFrame {
                background-color: #252525;
                border: none;
                border-radius: 8px;
            }
            #trackFrame:hover {
                background-color: #2A2A2A;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)  # Márgenes uniformes
        layout.setSpacing(12)
        
        # Número de track
        track_num_label = QLabel(f"{track_number}")
        track_num_label.setFont(QFont("Segoe UI", 9))
        track_num_label.setStyleSheet("color: #555555; background: transparent;")
        track_num_label.setFixedWidth(25)
        track_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Portada del álbum - más pequeña
        cover_label = QLabel()
        cover_label.setFixedSize(36, 36)
        cover_label.setStyleSheet("""
            background-color: #3A3A3A;
            border-radius: 4px;
        """)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Cargar portada desde URL
        cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        if cover_url:
            self._load_cover(cover_url, cover_label)
        
        # Información de la canción - solo título y artista en una línea
        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent;")
        info_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        info_widget.setMaximumWidth(9999)  # Permitir expansión pero limitada
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Título - con elipsis si es muy largo
        title = track['name']
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        title_label.setWordWrap(False)
        title_label.setTextFormat(Qt.TextFormat.PlainText)
        # Habilitar elipsis para cortar texto largo
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        
        # Artista + duración - con elipsis si es muy largo
        artists = ', '.join([artist['name'] for artist in track['artists']])
        duration_ms = track.get('duration_ms', 0)
        duration_min = duration_ms // 60000
        duration_sec = (duration_ms % 60000) // 1000
        artist_label = QLabel(f"{artists} • {duration_min}:{duration_sec:02d}")
        artist_label.setFont(QFont("Segoe UI", 9))
        artist_label.setStyleSheet("color: #888888; background: transparent;")
        artist_label.setTextFormat(Qt.TextFormat.PlainText)
        # Habilitar elipsis para cortar texto largo
        artist_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        artist_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(artist_label)
        
        # Contenedor para el botón con ancho fijo para garantizar posición
        button_container = QWidget()
        button_container.setFixedWidth(50)  # Más ancho para dar espacio
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(4, 0, 4, 0)  # Márgenes para evitar cortes
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Botón de descarga profesional con ícono SVG-style
        download_button = QPushButton("↓")
        download_button.setFixedSize(38, 38)
        download_button.setMinimumSize(38, 38)
        download_button.setMaximumSize(38, 38)
        download_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        download_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #B3B3B3;
                border-radius: 19px;
                border: 2px solid #535353;
                font-size: 20px;
                font-family: 'Segoe UI Symbol', sans-serif;
                padding-bottom: 2px; /* Ajuste visual vertical */
            }
            QPushButton:hover {
                background-color: transparent;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid #B3B3B3;
                color: #B3B3B3;
                padding-top: 0px; 
            }
            QPushButton:disabled {
                border: 2px solid #333333;
                color: #333333;
            }
        """)
        download_button.setToolTip("Descargar esta canción")
        download_button.clicked.connect(lambda checked, t=track, f=frame: self.download_single_track(t, f))
        
        button_layout.addWidget(download_button)
        
        # Layout principal - todos los elementos con tamaños controlados
        layout.addWidget(track_num_label, 0)
        layout.addWidget(cover_label, 0)
        layout.addWidget(info_widget, 1)  # Solo info_widget se expande
        layout.addWidget(button_container, 0)  # Botón siempre en posición fija
        
        return frame
    
    def _load_cover(self, url, label):
        """Cargar portada de álbum de forma asíncrona"""
        request = QNetworkRequest(QUrl(url))
        reply = self._network_manager.get(request)
        self._pending_covers[reply] = label
        reply.finished.connect(lambda: self._on_cover_loaded(reply))
    
    def _on_cover_loaded(self, reply):
        """Callback cuando la portada se carga"""
        label = self._pending_covers.pop(reply, None)
        try:
            # Verificar que el label aún existe y es válido
            if label and reply.error() == QNetworkReply.NetworkError.NoError:
                # Intentar acceder al label para verificar que no fue eliminado
                try:
                    label.isVisible()  # Test si el objeto C++ aún existe
                except RuntimeError:
                    reply.deleteLater()
                    return
                    
                data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    scaled = pixmap.scaled(
                        36, 36,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    if scaled.width() > 36 or scaled.height() > 36:
                        x = (scaled.width() - 36) // 2
                        y = (scaled.height() - 36) // 2
                        scaled = scaled.copy(x, y, 36, 36)
                    label.setPixmap(scaled)
        except RuntimeError:
            pass  # El widget fue eliminado, ignorar
        finally:
            reply.deleteLater()
    
    def download_single_track(self, track, track_widget):
        """Descargar una canción individual"""
        try:
            # Preparar datos de la canción
            song_data = {
                'song': track['name'],
                'artists': [artist['name'] for artist in track['artists']],
                'album': track['album']['name'],
                'preview_url': track.get('preview_url'),
                'cover_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'release_date': track['album'].get('release_date', ''),
                'duration_ms': track.get('duration_ms', 0),
                'id': track['id'],
                'title': f"{track['name']} - {track['artists'][0]['name']}"
            }
            
            # Usar el sistema de descarga centralizado
            self.download_manager.add_download('spotify_track', song_data)
            
            # Actualizar botón
            download_button = track_widget.findChild(QPushButton)
            if download_button:
                download_button.setText("✓")
                download_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2A2A2A;
                        color: #1DB954;
                        border-radius: 19px;
                        border: 2px solid #1DB954;
                        font-size: 18px;
                        font-weight: bold;
                        padding: 0px;
                    }
                """)
                download_button.setToolTip("En cola de descarga")
                download_button.setEnabled(False)
                
            # Notificar al usuario (opcional, para no ser intrusivo)
            # QMessageBox.information(self, "Cola", "Canción añadida a la cola de descargas")
                
        except Exception as e:
            logging.error(f"Error iniciando descarga: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo iniciar la descarga:\n{e}")
    
    def download_all_tracks(self):
        """Descargar todas las canciones de la playlist actual"""
        if not self.current_tracks:
            QMessageBox.warning(self, "Error", "No hay canciones para descargar.")
            return
        
        # Confirmar descarga
        reply = QMessageBox.question(
            self,
            "Confirmar Descarga",
            f"¿Añadir las {len(self.current_tracks)} canciones de '{self.current_playlist_name}' a la cola?\n\n"
            "Se descargarán en segundo plano.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Preparar lista de canciones
            songs = []
            for track in self.current_tracks:
                songs.append({
                    'song': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'preview_url': track.get('preview_url'),
                    'cover_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'release_date': track['album'].get('release_date', ''),
                    'duration_ms': track.get('duration_ms', 0),
                    'id': track['id']
                })
            
            data = {
                'tracks': songs,
                'title': f"Playlist: {self.current_playlist_name}"
            }
            
            # Usar el sistema de descarga centralizado
            self.download_manager.add_download('spotify_playlist', data)
            
            QMessageBox.information(self, "Cola", "Playlist añadida a la cola de descargas.")
            
        except Exception as e:
            logging.error(f"Error iniciando descarga masiva: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo iniciar la descarga:\n{e}")
    
    def clear_tracks(self):
        """Limpiar lista de canciones"""
        # Eliminar todos los widgets de tracks excepto el stretch
        for i in reversed(range(self.tracks_layout.count() - 1)):
            child = self.tracks_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        self.current_tracks = []
        self.download_all_button.setEnabled(False)
    
    def clear_library(self):
        """Limpiar toda la biblioteca"""
        self.playlists_list.clear()
        self.clear_tracks()
        self.playlist_info.setText("Conecta con Spotify para ver tus playlists")
        self.tracks_title.setText("Canciones")
        self.tracks_count.setText("")
    
    def refresh_library(self):
        """Actualizar biblioteca"""
        if self.spotify_client:
            self.load_playlists()
        else:
            QMessageBox.warning(self, "Error", "No estás conectado a Spotify.")
