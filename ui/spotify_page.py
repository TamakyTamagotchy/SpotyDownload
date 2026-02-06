from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QMessageBox, QLineEdit, QGroupBox, QInputDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from spotipy.oauth2 import SpotifyOAuth
import os, logging, webbrowser, json, time, spotipy

# Constantes
CONFIG_FILE = "config/spotify_settings.json"
CACHE_FILE = ".spotify_cache"

class SpotifyAuthError(Exception):
    """Excepción personalizada para errores de autenticación de Spotify"""
    pass

class SpotifyPage(QWidget):

    # Estilo compartido para inputs de credenciales
    _INPUT_STYLE = """
        QLineEdit {
            padding: 12px 16px;
            border-radius: 10px;
            background-color: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            color: #FFFFFF;
            font-size: 13px;
        }
        QLineEdit:focus {
            border-color: #1DB954;
            background-color: rgba(255, 255, 255, 0.08);
        }
    """

    # Plantilla para estilos de estado de conexión
    _STATUS_TEMPLATE = """
        QLabel {{
            padding: 14px 20px;
            border-radius: 10px;
            background-color: rgba({rgb}, 0.15);
            color: {color};
            font-weight: 600;
            border: 1px solid rgba({rgb}, 0.3);
        }}
    """

    _STATUS_COLORS = {
        "green":  {"rgb": "29, 185, 84",  "color": "#1ED760"},
        "red":    {"rgb": "241, 94, 108", "color": "#F15E6C"},
        "orange": {"rgb": "255, 167, 38", "color": "#FFA726"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.spotify_client = None
        self.sp_oauth = None
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.check_session_validity)

        self.initUI()
        self.load_config()
        # Auto-conectar después de un pequeño delay para que la UI esté lista
        QTimer.singleShot(500, self.auto_connect_if_cached)
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Título principal con diseño moderno
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        title = QLabel("🎧 Integración con Spotify")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #1ED760;
                margin: 20px;
            }
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("Conecta tu cuenta de Spotify para acceder a tu biblioteca")
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #B3B3B3; margin-bottom: 10px;")
        title_layout.addWidget(subtitle)

        layout.addWidget(title_container)
        
        # Sección de configuración (solo esta sección)
        self.setup_config_section(layout)
        
        # Mensaje informativo después de conectar - diseño mejorado
        self.info_message = QLabel("")
        self.info_message.setVisible(False)
        self.info_message.setFont(QFont("Segoe UI", 12))
        self.info_message.setWordWrap(True)
        self.info_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_message.setStyleSheet("""
            QLabel {
                background-color: rgba(29, 185, 84, 0.12);
                padding: 24px;
                border-radius: 12px;
                border: 1px solid rgba(29, 185, 84, 0.3);
                color: #FFFFFF;
            }
        """)
        layout.addWidget(self.info_message)
        
        # Espaciador para centrar el contenido
        layout.addStretch()
    
    def setup_config_section(self, parent_layout):
        """Configurar sección de autenticación con diseño moderno."""
        config_group = QGroupBox("🔐 Configuración de Spotify")
        config_group.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        config_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(22, 24, 29, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                margin-top: 16px;
                padding: 24px;
                color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 8px 16px;
                color: #FFFFFF;
                background-color: transparent;
            }
        """)
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(20)
        
        # Instrucciones mejoradas
        instructions = QLabel("""
        <b>🎵 Configuración rápida de Spotify:</b><br>
        1. Ve a <a href="https://developer.spotify.com/dashboard">Spotify Developer Dashboard</a><br>
        2. Crea una nueva aplicación (Create an App)<br>
        3. Copia el Client ID y Client Secret<br>
        4. ⚠️ <b>IMPORTANTE:</b> En 'Settings' → 'Redirect URIs' agrega:<br>
        &nbsp;&nbsp;&nbsp;<code>http://127.0.0.1:8080/callback</code><br>
        5. Guarda los cambios y conecta
        """)
        instructions.setTextFormat(Qt.TextFormat.RichText)
        instructions.setOpenExternalLinks(True)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                background-color: rgba(29, 185, 84, 0.08);
                padding: 20px;
                border-radius: 12px;
                border: 1px solid rgba(29, 185, 84, 0.2);
                color: #FFFFFF;
            }
            QLabel a {
                color: #1ED760;
                text-decoration: none;
                font-weight: 600;
            }
            QLabel a:hover {
                text-decoration: underline;
            }
        """)
        config_layout.addWidget(instructions)
        
        # Campos de entrada mejorados
        input_label_style = "color: #FFFFFF; font-weight: 600; margin-top: 8px;"

        client_id_label = QLabel("Client ID:")
        client_id_label.setStyleSheet(input_label_style)
        config_layout.addWidget(client_id_label)

        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Ingresa tu Client ID de Spotify")
        self.client_id_input.setMinimumHeight(44)
        self.client_id_input.setStyleSheet(self._INPUT_STYLE)
        config_layout.addWidget(self.client_id_input)

        client_secret_label = QLabel("Client Secret:")
        client_secret_label.setStyleSheet(input_label_style)
        config_layout.addWidget(client_secret_label)

        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Ingresa tu Client Secret de Spotify")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setMinimumHeight(44)
        self.client_secret_input.setStyleSheet(self._INPUT_STYLE)
        config_layout.addWidget(self.client_secret_input)
        
        # Botones de control con diseño moderno
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.connect_button = QPushButton("🔗 Conectar con Spotify")
        self.connect_button.setMinimumHeight(48)
        self.connect_button.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.connect_button.clicked.connect(self.connect_to_spotify)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #1ED760, stop: 1 #1DB954);
                color: #000000;
                padding: 14px 28px;
                border-radius: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #1FDF64, stop: 1 #1ED760);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #169c46, stop: 1 #148A3D);
            }
        """)

        self.disconnect_button = QPushButton("🔌 Desconectar")
        self.disconnect_button.setMinimumHeight(48)
        self.disconnect_button.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.disconnect_button.clicked.connect(self.disconnect_spotify)
        self.disconnect_button.setVisible(False)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                padding: 14px 28px;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)

        self.help_button = QPushButton("❓ Ayuda")
        self.help_button.setMinimumHeight(48)
        self.help_button.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.help_button.clicked.connect(self.show_help)
        self.help_button.setFixedWidth(100)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1DB954;
                padding: 14px 20px;
                border-radius: 10px;
                border: 2px solid #1DB954;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(29, 185, 84, 0.15);
                border-color: #1ED760;
            }
        """)
        
        buttons_layout.addWidget(self.connect_button)
        buttons_layout.addWidget(self.disconnect_button)
        buttons_layout.addWidget(self.help_button)
        
        # Status de conexión mejorado
        self.connection_status = QLabel("🔴 No conectado")
        self.connection_status.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status.setMinimumHeight(52)
        self.connection_status.setStyleSheet("""
            QLabel {
                padding: 14px 20px;
                border-radius: 10px;
                background-color: rgba(241, 94, 108, 0.15);
                color: #F15E6C;
                font-weight: 600;
                border: 1px solid rgba(241, 94, 108, 0.3);
            }
        """)
        
        config_layout.addLayout(buttons_layout)
        config_layout.addWidget(self.connection_status)
        
        parent_layout.addWidget(config_group)
    
    def auto_connect_if_cached(self):
        """Intentar conectar automáticamente si hay credenciales y token en cache"""
        try:
            # Verificar que hay credenciales guardadas
            if not self.client_id_input.text() or not self.client_secret_input.text():
                logging.info("No hay credenciales guardadas, omitiendo auto-conexión")
                return
                
            # Verificar que existe el cache
            if not os.path.exists(CACHE_FILE):
                logging.info("No hay cache de Spotify, omitiendo auto-conexión")
                return
            
            logging.info("Intentando conexión automática a Spotify...")
            self.update_connection_status("🟡 Conectando automáticamente...", "orange")
            
            # Crear autenticación
            if not self.create_spotify_auth():
                logging.warning("No se pudo crear autenticación para auto-conexión")
                self.update_connection_status("🔴 No conectado", "red")
                return
            
            # Obtener token del cache
            token_info = self.sp_oauth.get_cached_token()
            if not token_info:
                logging.info("Token de cache no válido o expirado")
                self.update_connection_status("🔴 No conectado", "red")
                return
            
            # Crear cliente de Spotify
            sp = spotipy.Spotify(auth_manager=self.sp_oauth)
            
            # Verificar que el token funciona
            user = sp.current_user()
            username = user.get('display_name', user.get('id', 'Usuario'))
            logging.info(f"✅ Reconexión automática exitosa como: {username}")
            
            self.on_auth_success(sp)
            
        except Exception as e:
            logging.info(f"No se pudo reconectar automáticamente: {e}")
            self.update_connection_status("🔴 No conectado", "red")
    
    def create_spotify_auth(self):
        """Crear objeto de autenticación de Spotify"""
        if not self.client_id_input.text() or not self.client_secret_input.text():
            return False
            
        try:
            scope = "playlist-read-private playlist-read-collaborative user-library-read user-read-private"
            
            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id_input.text().strip(),
                client_secret=self.client_secret_input.text().strip(),
                redirect_uri="http://127.0.0.1:8080/callback",
                scope=scope,
                cache_path=CACHE_FILE,
                open_browser=False
            )
            return True
            
        except Exception as e:
            logging.error(f"Error creando autenticación: {e}")
            return False
    
    def connect_to_spotify(self):
        """Conectar con la API de Spotify"""
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        
        if not all([client_id, client_secret]):
            QMessageBox.warning(self, "Error", "Por favor completa Client ID y Client Secret.")
            return
        
        # Guardar configuración
        self.save_config()
        
        self.update_connection_status("🟡 Iniciando autenticación...", "orange")
        self.connect_button.setEnabled(False)
        
        try:
            if not self.create_spotify_auth():
                raise SpotifyAuthError("No se pudo crear el objeto de autenticación")
            
            # Verificar si ya hay token válido
            token_info = self.sp_oauth.get_cached_token()
            if token_info:
                sp = spotipy.Spotify(auth_manager=self.sp_oauth)
                user = sp.current_user()
                logging.info("Usando token existente")
                self.on_auth_success(sp)
                return
            
            # Generar URL de autorización
            auth_url = self.sp_oauth.get_authorize_url()
            
            # Mostrar instrucciones
            self.show_auth_instructions()
            
            # Abrir navegador
            webbrowser.open(auth_url)
            logging.info(f"Abriendo navegador con URL: {auth_url}")
            
            # Pedir URL de respuesta
            response_url = self.get_authorization_code()
            if not response_url:
                self.on_auth_error("Conexión cancelada por el usuario")
                return
            
            # Procesar código de autorización
            self.process_authorization_code(response_url)
                
        except Exception as e:
            logging.error(f"Error en autenticación: {e}")
            self.on_auth_error(str(e))
    
    def show_auth_instructions(self):
        """Mostrar instrucciones de autenticación"""
        msg = QMessageBox(self)
        msg.setWindowTitle("🔐 Autenticación de Spotify")
        msg.setText(
            "🔐 INSTRUCCIONES DE AUTENTICACIÓN:\n\n"
            "1. Se abrirá tu navegador con Spotify\n"
            "2. Inicia sesión en Spotify si no lo has hecho\n"
            "3. Haz clic en 'AUTHORIZE' o 'AUTORIZAR'\n"
            "4. Serás redirigido a una página que mostrará un ERROR - ¡ESTO ES NORMAL!\n"
            "5. En esa página de error, COPIA LA URL COMPLETA de la barra de direcciones\n"
            "6. La URL debe contener 'code=' seguido de un código largo\n"
            "7. Pega esa URL completa en el siguiente campo\n\n"
            "⚠️ IMPORTANTE: Debes haber agregado 'http://127.0.0.1:8080/callback' \n"
            "en los Redirect URIs de tu aplicación de Spotify Developer Dashboard"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Cancel:
            raise SpotifyAuthError("Autenticación cancelada por el usuario")
    
    def get_authorization_code(self):
        """Obtener código de autorización del usuario"""
        response_url, ok = QInputDialog.getText(
            self,
            "📋 Pegar URL de Respuesta",
            "Pega aquí la URL COMPLETA de la página de error que se abrió:\n"
            "(Debe contener 'code=' seguido de un código)\n\n"
            "Ejemplo: http://127.0.0.1:8080/callback?code=AQC1234567890..."
        )
        
        if not ok or not response_url:
            return None
            
        return response_url.strip()
    
    def process_authorization_code(self, response_url):
        """Procesar código de autorización"""
        if "code=" not in response_url:
            help_msg = (
                "❌ La URL no contiene un código de autorización válido.\n\n"
                "La URL debe verse similar a:\n"
                "http://127.0.0.1:8080/callback?code=AQC1234567890...\n\n"
                "Verifica que:\n"
                "• Copiaste la URL COMPLETA de la página de error\n"
                "• La URL contiene 'code=' seguido de un código largo\n"
                "• Agregaste 'http://127.0.0.1:8080/callback' en Redirect URIs de tu app Spotify"
            )
            raise SpotifyAuthError(help_msg)
        
        try:
            code = response_url.split("code=")[1].split("&")[0]
            logging.info(f"Código extraído: {code[:10]}...")
            
            # Obtener token usando el código
            token_info = self.sp_oauth.get_access_token(code)
            
            if not token_info:
                raise SpotifyAuthError("No se pudo obtener token de acceso")
            
            # Crear cliente de Spotify
            sp = spotipy.Spotify(auth_manager=self.sp_oauth)
            
            # Verificar que funciona
            user = sp.current_user()
            logging.info(f"Autenticación exitosa para: {user.get('display_name', 'Usuario')}")
            
            self.on_auth_success(sp)
            
        except Exception as e:
            raise SpotifyAuthError(f"Error procesando el código de autorización: {e}")
    
    def on_auth_success(self, spotify_client):
        """Manejar autenticación exitosa"""
        self.spotify_client = spotify_client
        
        try:
            user = self.spotify_client.current_user()
            username = user.get('display_name', user.get('id', 'Usuario'))
            
            self.update_connection_status(f"🟢 Conectado como: {username}", "green")
            self.connect_button.setText("🔄 Reconectar")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setVisible(True)
            
            # Mostrar mensaje informativo
            self.info_message.setText(
                f"✅ ¡Conectado exitosamente como {username}!\n\n"
                "🎵 Ve a la pestaña '📚 Biblioteca' para explorar tus playlists y canciones.\n"
                "⬇️ Desde allí podrás descargar canciones individuales o playlists completas."
            )
            self.info_message.setVisible(True)
            
            # Iniciar timer para verificar sesión
            self.session_timer.start(300000)  # Verificar cada 5 minutos
            
            # Notificar al parent sobre la conexión exitosa
            if hasattr(self.parent, 'on_spotify_connected'):
                self.parent.on_spotify_connected(spotify_client)
            
        except Exception as e:
            self.on_auth_error(f"Error obteniendo información del usuario: {e}")
    
    def on_auth_error(self, error_message):
        """Manejar error de autenticación"""
        logging.error(f"Error de autenticación: {error_message}")
        
        self.update_connection_status("🔴 Error de conexión", "red")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setVisible(False)
        
        # Ocultar mensaje informativo
        self.info_message.setVisible(False)
        
        # Detener timer de sesión
        self.session_timer.stop()
        
        # Mostrar error al usuario
        QMessageBox.critical(
            self,
            "❌ Error de Autenticación", 
            f"No se pudo conectar con Spotify:\n\n{error_message}\n\n"
            f"Verifica que:\n"
            f"• El Client ID y Client Secret sean correctos\n"
            f"• Hayas agregado 'http://127.0.0.1:8080/callback' en Redirect URIs\n"
            f"• Tu aplicación de Spotify esté configurada correctamente"
        )
    
    def disconnect_spotify(self):
        """Desconectar de Spotify"""
        try:
            # Limpiar cache
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
            
            # Limpiar variables
            self.spotify_client = None
            self.sp_oauth = None
            
            # Detener timer
            self.session_timer.stop()
            
            # Actualizar UI
            self.update_connection_status("🔴 Desconectado", "red")
            self.connect_button.setText("🔗 Conectar con Spotify")
            self.disconnect_button.setVisible(False)
            self.info_message.setVisible(False)
            
            # Notificar al parent sobre la desconexión
            if hasattr(self.parent, 'on_spotify_disconnected'):
                self.parent.on_spotify_disconnected()
            
            logging.info("Desconectado de Spotify exitosamente")
            
        except Exception as e:
            logging.error(f"Error al desconectar: {e}")
    
    def check_session_validity(self):
        """Verificar validez de la sesión"""
        if not self.spotify_client:
            return
            
        try:
            # Intentar hacer una consulta simple
            self.spotify_client.current_user()
            
        except Exception as e:
            logging.warning(f"Sesión de Spotify expirada: {e}")
            self.update_connection_status("🟡 Sesión expirada, reconectando...", "orange")
            
            # Intentar renovar token
            try:
                if self.sp_oauth:
                    token_info = self.sp_oauth.get_cached_token()
                    if token_info:
                        self.spotify_client = spotipy.Spotify(auth_manager=self.sp_oauth)
                        user = self.spotify_client.current_user()
                        username = user.get('display_name', user.get('id', 'Usuario'))
                        self.update_connection_status(f"🟢 Reconectado como: {username}", "green")
                        return
                        
            except Exception:
                pass
            
            # Si no se pudo renovar, desconectar
            self.disconnect_spotify()
    
    def update_connection_status(self, text, color):
        """Actualizar status de conexión con diseño moderno."""
        self.connection_status.setText(text)
        colors = self._STATUS_COLORS.get(color, self._STATUS_COLORS["red"])
        self.connection_status.setStyleSheet(
            self._STATUS_TEMPLATE.format(**colors)
        )
    
    def show_help(self):
        """Mostrar ayuda para configurar Spotify"""
        help_text = """
        <h3>🎵 Configuración de Spotify Developer</h3>
        
        <p><b>1. Crear aplicación en Spotify:</b></p>
        <ul>
            <li>Ve a <a href="https://developer.spotify.com/dashboard">Spotify Developer Dashboard</a></li>
            <li>Haz clic en "Create an App"</li>
            <li>Llena el nombre y descripción</li>
            <li>Acepta los términos y condiciones</li>
        </ul>
        
        <p><b>2. Configurar Redirect URI:</b></p>
        <ul>
            <li>En tu aplicación, haz clic en "Settings"</li>
            <li>En "Redirect URIs" agrega: <code>http://127.0.0.1:8080/callback</code></li>
            <li>Haz clic en "Add" y luego "Save"</li>
        </ul>
        
        <p><b>3. Obtener credenciales:</b></p>
        <ul>
            <li>Copia el "Client ID"</li>
            <li>Haz clic en "Show client secret" y copia el "Client Secret"</li>
            <li>Pega ambos en los campos correspondientes</li>
        </ul>
        
        <p><b>4. Conectar:</b></p>
        <ul>
            <li>Haz clic en "Conectar con Spotify"</li>
            <li>Sigue las instrucciones en pantalla</li>
            <li>Tu sesión se mantendrá activa automáticamente</li>
        </ul>
        
        <p><b>💡 Nota:</b> Tu aplicación debe estar en modo "Development" para funcionar.</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("❓ Ayuda - Configuración de Spotify")
        msg.setText(help_text)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setFixedSize(500, 400)
        msg.exec()
    
    def save_config(self):
        """Guardar configuración de Spotify"""
        try:
            # Crear directorio si no existe
            os.makedirs("config", exist_ok=True)
            
            config = {
                "spotify": {
                    "client_id": self.client_id_input.text().strip(),
                    "client_secret": self.client_secret_input.text().strip()
                },
                "last_updated": time.time()
            }
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
            logging.info("Configuración guardada exitosamente")
                
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
    
    def load_config(self):
        """Cargar configuración guardada"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                spotify_config = config.get("spotify", {})
                if spotify_config:
                    self.client_id_input.setText(spotify_config.get('client_id', ''))
                    self.client_secret_input.setText(spotify_config.get('client_secret', ''))
                    
                logging.info("Configuración cargada exitosamente")
                    
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
