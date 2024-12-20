import os
import json
import subprocess
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from ytmusicapi import YTMusic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import pyqtSignal, QObject, QThread, Qt
import threading
import logging
import queue
import re
from PIL import Image
from io import BytesIO
import unicodedata
import requests
import eyed3
import qdarkstyle
from fuzzywuzzy import fuzz
import lyricsgenius

# Configuración de logging
logging.basicConfig(filename='Logger_Spotify.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Obtener la ruta del directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(script_dir, 'spotify_credentials.json')

# Cargar credenciales de Spotify desde archivo JSON
try:
    with open(credentials_path) as f:
        credentials = json.load(f)
        SPOTIFY_CLIENT_ID = credentials['client_id']
        SPOTIFY_CLIENT_SECRET = credentials['client_secret']
        GENIUS_API_TOKEN = credentials['genius_api_token'] # https://genius.com/api-clients
except Exception as e:
    logging.error(f'Error al cargar las credenciales: {e}')
    raise

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

ytmusic = YTMusic()
genius = lyricsgenius.Genius(GENIUS_API_TOKEN)

HISTORY_FILE = "download_history.json"

# Funciones de utilidad
def get_spotify_item(id):
    """
    Obtiene un ítem de Spotify, ya sea una playlist o una canción.
    """
    try:
        playlist = sp.playlist(id)
        return playlist  # Devuelve el objeto de la playlist si existe
    except Exception as e:
        logging.error(f'No se pudo obtener la playlist de Spotify: {e}')
        try:
            track = sp.track(id)
            return track  # Devuelve el objeto de la canción si existe
        except Exception as e:
            logging.error(f'No se pudo obtener la canción de Spotify: {e}')
            return None

def search_youtube_music(title, artist, album=None):
    try:
        query = f'{title} {artist}'
        if album:
            query += f' {album}'
        
        # Intentar búsqueda en YouTube Music primero
        results = ytmusic.search(query, filter='songs')
        best_match = None
        highest_ratio = 0
        
        for result in results:
            video_title = result['title']
            video_artist = ', '.join([a['name'] for a in result['artists']])
            video_album = result.get('album', {}).get('name', '')
            
            title_ratio = fuzz.ratio(title.lower(), video_title.lower())
            artist_ratio = fuzz.ratio(artist.lower(), video_artist.lower())
            album_ratio = fuzz.ratio(album.lower(), video_album.lower()) if album else 100
            
            total_ratio = (title_ratio * 0.5) + (artist_ratio * 0.3) + (album_ratio * 0.2)
            
            if total_ratio > highest_ratio:
                highest_ratio = total_ratio
                best_match = result
        
        # Si encontró en YouTube Music, retornar enlace
        if best_match and highest_ratio > 70:
            return f"https://music.youtube.com/watch?v={best_match['videoId']}"
        
        # Si no encuentra en YouTube Music, buscar en YouTube directamente
        logging.warning(f'No se encontraron resultados confiables en YouTube Music. Intentando búsqueda en YouTube.')
        return None
        
    except Exception as e:
        logging.error(f'Error al buscar la canción: {e}')
        return None

def download_song(url, filename, q, quality, pause_event, cancel_event, max_retries=3):
    if quality == "Mejor":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename[:-4] + '.%(ext)s',
            'progress_hooks': [lambda d: q.put(d)],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
        }
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename[:-4] + '.%(ext)s',
            'progress_hooks': [lambda d: q.put(d)],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320' if quality == "Buena" else '128',
            }],
        }

    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                while not cancel_event.is_set():
                    if pause_event.is_set():
                        pause_event.wait()
                    else:
                        ydl.download([url])
                        if quality == "Mejor":
                            wav_file = filename[:-4] + '.wav'
                            mp3_file = filename[:-4] + '.mp3' 
                            # Convertir WAV a MP3 de alta calidad usando FFmpeg
                            ffmpeg_command = [
                                'ffmpeg', '-i', wav_file,
                                '-acodec', 'libmp3lame',
                                '-b:a', '320k',  # Bitrate de 320kbps
                                '-ar', '48000',  # Frecuencia de muestreo de 48kHz
                                mp3_file
                            ]
                            subprocess.run(ffmpeg_command, check=True)
                            os.remove(wav_file)  # Eliminar el archivo WAV temporal
                        return
        except yt_dlp.utils.DownloadError as e:
            logging.error(f'Intento {attempt + 1} fallido. Error: {e}')
            if attempt == max_retries - 1:
                q.put({'error': f'No se pudo descargar la canción después de {max_retries} intentos: {e}'})
        except requests.exceptions.RequestException as e:
            logging.error(f'Error de red durante la descarga: {e}')
            q.put({'error': 'error_de_red'})
            return
        except subprocess.CalledProcessError as e:
            logging.error(f'Error al convertir el audio: {e}')
            q.put({'error': f'Error al convertir el audio: {e}'})
            return
        except Exception as e:
            logging.error(f'Error inesperado durante la descarga: {e}')
            q.put({'error': str(e)})
            return
    
    if cancel_event.is_set():
        partial_file = filename[:-4] + '.part'
        if os.path.exists(partial_file):
            os.remove(partial_file)
            
def sanitize_filename(title, artist=None, album=None, fallback_method=True):
    """
    Sanitize filenames with improved robustness and handling of special characters.
    
    Args:
        title (str): Primary title for the filename
        artist (str, optional): Artist for filename
        album (str, optional): Album for filename
        fallback_method (bool): Use fallback naming if sanitization fails
    
    Returns:
        str: Sanitized and safe filename
    """
    def clean_base_name(name):
        """Advanced filename cleaning"""
        if not name:
            return ""
        
        # Normalize Unicode characters and remove diacritics
        name = unicodedata.normalize('NFKD', str(name))
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Remove or replace problematic characters
        name = re.sub(r'[<>:"/\\|?*¿#\']', '', name)
        
        # Replace multiple spaces and trim
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    try:
        # Primary filename construction
        parts = [clean_base_name(title)]
        
        # Add artist if available
        if artist:
            parts.append(clean_base_name(artist))
        
        # Add album in parentheses if available
        if album:
            parts.append(f"({clean_base_name(album)})")
        
        # Join parts
        filename = ' '.join(parts)
        
        # Truncate to safe length
        filename = filename[:255]
        
        # Fallback for empty filename
        if not filename and fallback_method:
            filename = f"Track_{int(time.time())}"
        
        return filename.strip()
    
    except Exception as e:
        logging.error(f'Error in filename sanitization: {e}')
        return f"Track_{int(time.time())}"

def save_lyrics_to_file(lyrics, filename):
    """
    Save lyrics to a text file.
    
    Args:
        lyrics (str): Lyrics of the song
        filename (str): Path to save the lyrics file
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(lyrics)
    except Exception as e:
        logging.error(f'Error saving lyrics to file: {e}')

def update_mp3_metadata(filename, title, artist, album, cover_image_url, release_date, lyrics=None):
    """
    Update MP3 metadata with robust error handling and flexibility.
    
    Args:
        filename (str): Path to the MP3 file
        title (str): Track title
        artist (str): Track artist(s)
        album (str): Album name
        cover_image_url (str): URL of cover image
        release_date (str): Release date
        lyrics (str, optional): Lyrics of the song
    
    Returns:
        bool: True if metadata update successful, False otherwise
    """
    try:
        # Ensure the file exists and is a valid MP3
        if not os.path.exists(filename):
            logging.error(f'File not found: {filename}')
            return False
        
        # Load the audio file with error handling
        audio = eyed3.load(filename)
        if audio is None:
            logging.error(f'Could not load audio file: {filename}')
            return False
        
        # Initialize tag if not exists
        if audio.tag is None:
            audio.initTag()
        
        # Set basic metadata with None checks
        audio.tag.title = title or "Titulo Desconocido"
        audio.tag.artist = artist or "Artista Desconocido"
        audio.tag.album = album or "Album Desconocido"
        
        # Handle release date and year
        try:
            if release_date:
                # Extract year, handling potential formatting variations
                year_match = re.search(r'\d{4}', release_date)
                if year_match:
                    audio.tag.year = int(year_match.group())
                audio.tag.release_date = release_date
        except (ValueError, TypeError) as date_error:
            logging.warning(f'Invalid release date: {release_date}. Error: {date_error}')
        
        # Handle cover image with more robust error checking
        if cover_image_url:
            try:
                response = requests.get(cover_image_url, timeout=10)
                response.raise_for_status()
                
                # Check image type and size
                image_content = response.content
                image = Image.open(BytesIO(image_content))
                
                # Set image if valid
                audio.tag.images.set(3, image_content, "image/jpeg", u"Cover")
            except Exception as img_error:
                logging.error(f'Cover image processing error: {img_error}')
        
        # Set lyrics if available
        if lyrics:
            audio.tag.lyrics.set(lyrics)
        
        # Save with specific ID3v2.3 version for maximum compatibility
        audio.tag.save(version=(2,3,0))
        
        return True
    
    except Exception as e:
        logging.error(f'Comprehensive metadata update error: {e}')
        return False

def extract_id(link):
    pattern = re.compile(r'(?:playlist|track)/(\w+)')
    match = pattern.search(link)
    if match:
        return match.group(1)
    else:
        return link

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def are_files_equal(file1, file2):
    try:
        audio1 = eyed3.load(file1)
        audio2 = eyed3.load(file2)
        return (audio1.tag.title == audio2.tag.title and
                audio1.tag.artist == audio2.tag.artist and
                audio1.tag.album == audio2.tag.album and
                audio1.tag.release_date == audio2.tag.release_date)
    except Exception as e:
        logging.error(f'Error al comparar archivos MP3: {e}')
        return False

def save_download_history(history):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        logging.error(f'No se pudo guardar el historial de descargas: {e}')

def load_download_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f'No se pudo cargar el historial de descargas: {e}')
            return []
    return []

def get_lyrics(title, artist):
    try:
        song = genius.search_song(title, artist)
        if song:
            return song.lyrics
    except Exception as e:
        logging.error(f'Error al obtener la letra de la canción: {e}')
    return None

class DownloadWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    track_info = pyqtSignal(dict)
    ask_replace = pyqtSignal(str, str)
    song_not_found = pyqtSignal(str)

    def __init__(self, spotify_id, download_folder, quality):
        super().__init__()
        self.spotify_id = spotify_id
        self.download_folder = download_folder
        self.quality = quality
        self.q = queue.Queue()
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.replace_response = None

    def run(self):
        try:
            item = get_spotify_item(self.spotify_id)
            if not item:
                self.error.emit("No se pudo obtener información del ítem de Spotify")
                return
            
            tracks = (item['tracks']['items'] if item.get('type') == 'playlist' 
                    else [item] if item.get('type') == 'track' else [])
            
            total_tracks = len(tracks)
            for idx, track_data in enumerate(tracks):
                if self.cancel_event.is_set():
                    break
                
                track = track_data['track'] if 'track' in track_data else track_data
                self.process_track(track, total_tracks, idx)
            
            if not self.cancel_event.is_set():
                self.finished.emit()
        
        except Exception as e:
            logging.error(f'Error en la descarga: {e}')
            self.error.emit(str(e))

    def process_track(self, track, total_tracks, track_index):
        try:
            # Extraer metadatos de la pista de manera más concisa
            song_metadata = {
                'song': track['name'],
                'artists': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'cover_url': track['album']['images'][0]['url'],
                'release_date': track['album']['release_date']
            }
            
            # Crear nombre de archivo sanitizado
            filename = os.path.join(
                self.download_folder, 
                f'{sanitize_filename(song_metadata["song"])}.mp3'
            )

            # Manejar archivos existentes
            if os.path.exists(filename):
                if not self.handle_existing_file(song_metadata['song'], filename):
                    self.progress.emit(int((track_index + 1) / total_tracks * 100))
                    return

            # Buscar URL de descarga
            url = self.find_download_url(song_metadata)
            
            # Manejar caso de canción no encontrada
            if not url:
                self.song_not_found.emit(f'"{song_metadata["song"]}" - {song_metadata["artists"]}')
                self.progress.emit(int((track_index + 1) / total_tracks * 100))
                return

            # Descargar y procesar la canción
            self.download_and_process_song(
                url, filename, song_metadata, track_index, total_tracks
            )

        except Exception as e:
            logging.error(f'Error procesando la pista: {e}')
            self.song_not_found.emit(f'"{song_metadata.get("song", "Desconocido")}"')
            self.progress.emit(int((track_index + 1) / total_tracks * 100))

    def handle_existing_file(self, song, filename):
        self.ask_replace.emit(song, filename)
        while self.replace_response is None:
            QThread.msleep(100)
        
        replace_response = self.replace_response
        self.replace_response = None
        
        if replace_response:
            os.remove(filename)
        return replace_response

    def find_download_url(self, song_metadata):
        # Intentar encontrar la canción en YouTube Music
        url = search_youtube_music(
            song_metadata['song'], 
            song_metadata['artists'], 
            song_metadata['album']
        )
        
        # Si no se encuentra en YouTube Music, buscar en YouTube
        if not url:
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'max_downloads': 1,
                    'default_search': 'ytsearch1:',
                    'quiet': True
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(
                        f"{song_metadata['song']} {song_metadata['artists']}", 
                        download=False
                    )
                    
                    if info and 'entries' in info and info['entries']:
                        for entry in info['entries']:
                            video_title = entry['title']
                            video_artist = entry['uploader']
                            
                            title_ratio = fuzz.ratio(song_metadata['song'].lower(), video_title.lower())
                            artist_ratio = fuzz.ratio(song_metadata['artists'].lower(), video_artist.lower())
                            
                            if title_ratio > 70 and artist_ratio > 70:
                                return entry['webpage_url']
            except Exception as e:
                logging.error(f'Error al buscar en YouTube: {e}')
        
        return url

    def download_and_process_song(self, url, filename, song_metadata, track_index, total_tracks):
        try:
            # Descargar la canción
            download_song(
                url, filename, self.q, self.quality, 
                self.pause_event, self.cancel_event
            )

            # Obtener letras de la canción
            lyrics = get_lyrics(song_metadata['song'], song_metadata['artists'])

            # Guardar letras en un archivo de texto separado
            if lyrics:
                lyrics_filename = os.path.join(
                    self.download_folder, 
                    f'{sanitize_filename(song_metadata["song"])}_letra.txt'
                )
                save_lyrics_to_file(lyrics, lyrics_filename)

            # Actualizar metadatos
            if update_mp3_metadata(
                filename, 
                song_metadata['song'], 
                song_metadata['artists'], 
                song_metadata['album'], 
                song_metadata['cover_url'], 
                song_metadata['release_date'],
                lyrics  # Añadir letras a los metadatos
            ):
                # Emitir información de la pista
                self.track_info.emit({
                    "spotify_id": self.spotify_id,
                    "title": song_metadata['song'],
                    "artist": song_metadata['artists'],
                    "album": song_metadata['album'],
                    "cover_url": song_metadata['cover_url'],
                    "file_path": filename,
                    "url": url,
                    "release_date": song_metadata['release_date'],
                    "quality": self.quality
                })
            else:
                self.error.emit(f'Error al actualizar los metadatos de "{song_metadata["song"]}"')
        
        except Exception as e:
            logging.error(f'Error al descargar "{song_metadata["song"]}": {e}')
            self.error.emit(f'Error al descargar "{song_metadata["song"]}": {str(e)}')

        # Actualizar progreso
        self.progress.emit(int((track_index + 1) / total_tracks * 100))

    def set_replace_response(self, response):
        self.replace_response = response
        
class ModernApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_history()

    def initUI(self):
        self.setWindowTitle("Spotify Downloader")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        # Crear un widget central y un diseño principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Crear un widget de pestañas para la navegación
        self.nav_list = QListWidget()
        self.nav_list.addItems(["Descargar", "Historial"])
        self.nav_list.setFixedWidth(200)
        self.nav_list.currentRowChanged.connect(self.display_page)

        # Crear un widget apilado para las diferentes páginas
        self.stack = QStackedWidget()
        self.create_download_page()
        self.create_history_page()

        # Añadir widgets al diseño principal
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.stack)

    def create_download_page(self):
        download_page = QWidget()
        layout = QVBoxLayout(download_page)

        self.label = QLabel("Ingresa el link de la playlist o de la canción")
        self.label.setFont(QFont("Roboto", 12))
        self.textinput = QLineEdit()
        self.textinput.setPlaceholderText("Ingresa el link de la playlist o de la canción")
        self.textinput.setFont(QFont("Roboto", 10))

        self.quality_selector = QComboBox()
        self.quality_selector.addItems(["Mejor", "Buena", "Baja"])

        self.download_lyrics_checkbox = QCheckBox("Descargar letras")
        self.download_lyrics_checkbox.setChecked(True)

        self.button = QPushButton("Descargar")
        self.button.setIcon(QIcon.fromTheme("document-save"))
        self.button.setToolTip("Iniciar la descarga de la canción")
        self.button.clicked.connect(self.download_songs)

        self.pause_resume_button = QPushButton("Pausar")
        self.pause_resume_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_resume_button.setToolTip("Pausar/Reanudar la descarga")
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.pause_resume_button.setEnabled(False)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setIcon(QIcon.fromTheme("process-stop"))
        self.cancel_button.setToolTip("Cancelar la descarga")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)

        self.theme_switch = QCheckBox("Modo Oscuro")
        self.theme_switch.setChecked(True)
        self.theme_switch.stateChanged.connect(self.change_theme)

        self.status = QLabel("")
        self.progress = QProgressBar()
        self.progress.setMaximum(100)

        self.cover = QLabel()
        self.info = QLabel()

        layout.addWidget(self.label)
        layout.addWidget(self.textinput)
        layout.addWidget(self.quality_selector)
        layout.addWidget(self.download_lyrics_checkbox)
        layout.addWidget(self.button)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.pause_resume_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        layout.addWidget(self.theme_switch)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.cover)
        layout.addWidget(self.info)
        layout.addStretch()

        self.stack.addWidget(download_page)

    def create_history_page(self):
        history_page = QWidget()
        layout = QVBoxLayout(history_page)

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(["Título", "Artista", "Álbum", "Fecha", "Archivo", "Existe"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.cellDoubleClicked.connect(self.open_file)
        self.history_table.setFont(QFont("Roboto", 10))

        layout.addWidget(QLabel("Historial de Descargas"))
        layout.addWidget(self.history_table)

        self.stack.addWidget(history_page)

    def display_page(self, index):
        self.stack.setCurrentIndex(index)

    def change_theme(self, state):
        """Cambia el tema de la aplicación entre claro y oscuro"""
        if state == Qt.Checked:
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            self.setStyleSheet("")

    def download_songs(self):
        spotify_link = self.textinput.text()
        self.textinput.setEnabled(False)
        self.button.setEnabled(False)
        self.quality_selector.setEnabled(False)
        self.progress.setValue(0)

        spotify_id = extract_id(spotify_link)
        quality = self.quality_selector.currentText()
        download_lyrics = self.download_lyrics_checkbox.isChecked()

        self.download_folder = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta de descarga")
        if not self.download_folder:
            QMessageBox.warning(self, "Advertencia", "No se seleccionó una carpeta de descarga.")
            self.textinput.setEnabled(True)
            self.button.setEnabled(True)
            self.quality_selector.setEnabled(True)
            return
        
        self.worker = DownloadWorker(spotify_id, self.download_folder, quality)
        self.worker.download_lyrics = download_lyrics  # Añadir opción de descargar letras
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.track_info.connect(self.add_to_history)
        self.worker.ask_replace.connect(self.ask_replace_file)
        self.worker.song_not_found.connect(self.handle_song_not_found)  # Conectar nueva señal

        self.thread.started.connect(self.worker.run)
        self.thread.start()

        self.pause_resume_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def ask_replace_file(self, song, existing_file):
        reply = QMessageBox.question(self, 'Archivo existente',
                                    f'La canción "{song}" ya existe como "{existing_file}". ¿Desea reemplazarla?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        self.worker.set_replace_response(reply == QMessageBox.Yes)

    def handle_song_not_found(self, song_info):
        QMessageBox.warning(self, "Canción no encontrada", f"No se pudo encontrar la canción {song_info} en YouTube Music.")

        
    def toggle_pause_resume(self):
        if not hasattr(self, 'worker'):
            return

        if self.pause_resume_button.text() == "Pausar":
            self.worker.pause_event.set()
            self.pause_resume_button.setText("Reanudar")
            self.status.setText("Descarga pausada")
        else:
            self.worker.pause_event.clear()
            self.pause_resume_button.setText("Pausar")
            self.status.setText("Descarga reanudada")

    def cancel_download(self):
        if hasattr(self, 'worker'):
            self.worker.cancel_event.set()
            self.thread.quit()
            self.thread.wait()
            self.status.setText("Descarga cancelada")
            self.textinput.setEnabled(True)
            self.button.setEnabled(True)
            self.quality_selector.setEnabled(True)
            self.pause_resume_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.progress.setValue(0)

    def update_progress(self, value):
        self.progress.setValue(value)

    def download_finished(self):
        self.status.setText("Descarga completada")
        self.textinput.setEnabled(True)
        self.button.setEnabled(True)
        self.quality_selector.setEnabled(True)
        self.pause_resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.thread.quit()
        self.thread.wait()
        QMessageBox.information(self, 'Información', 'Descarga completada.')

    def handle_error(self, error_message):
        self.status.setText(f"Error: {error_message}")
        self.textinput.setEnabled(True)
        self.button.setEnabled(True)
        self.quality_selector.setEnabled(True)
        self.pause_resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress.setValue(0)
        self.thread.quit()
        self.thread.wait()
        QMessageBox.warning(self, 'Error', error_message)

    def load_history(self):
        self.history = load_download_history()
        for item in self.history:
            # Verificar si el archivo aún existe
            item['exists'] = os.path.exists(item['file_path'])
            self.add_to_history(item, from_load=True)

    def add_to_history(self, item, from_load=False):
        # Verificar si el ítem ya existe en el historial
        for existing_item in self.history:
            if (existing_item['spotify_id'] == item['spotify_id'] and
                existing_item['title'] == item['title'] and
                existing_item['artist'] == item['artist'] and
                existing_item['album'] == item['album'] and
                existing_item['url'] == item['url']):
                return  # No añadir duplicados exactos

        row_position = self.history_table.rowCount()
        self.history_table.insertRow(row_position)
        self.history_table.setItem(row_position, 0, QTableWidgetItem(item['title']))
        self.history_table.setItem(row_position, 1, QTableWidgetItem(item['artist']))
        self.history_table.setItem(row_position, 2, QTableWidgetItem(item['album']))
        self.history_table.setItem(row_position, 3, QTableWidgetItem(item['release_date']))
        self.history_table.setItem(row_position, 4, QTableWidgetItem(item['file_path']))
        self.history_table.setItem(row_position, 5, QTableWidgetItem("Sí" if item.get('exists', True) else "No"))

        if not from_load:
            self.history.append(item)
            save_download_history(self.history)

    def open_file(self, row, column):
        file_path = self.history_table.item(row, 4).text()
        if os.path.exists(file_path):
            os.startfile(file_path)
        else:
            QMessageBox.warning(self, "Advertencia", f"El archivo {file_path} no existe.")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = ModernApp()
    window.show()
    sys.exit(app.exec_())
