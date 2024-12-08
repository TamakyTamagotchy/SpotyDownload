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
import unicodedata
import requests
import eyed3
import qdarkstyle
from fuzzywuzzy import fuzz

# Configuración de logging
logging.basicConfig(filename='Logger_Spotify.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Credenciales de Spotify
SPOTIFY_CLIENT_ID = '7156ac6acc584ebd8ccd4c58402534e6'
SPOTIFY_CLIENT_SECRET = '11a8d2a6efed405280769f33ae6425ee'

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

ytmusic = YTMusic()

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
            video_artist = result['artists'][0]['name']
            video_album = result.get('album', {}).get('name', '')
            
            title_ratio = fuzz.ratio(title.lower(), video_title.lower())
            artist_ratio = fuzz.ratio(artist.lower(), video_artist.lower())
            album_ratio = fuzz.ratio(album.lower(), video_album.lower()) if album else 100
            
            total_ratio = (title_ratio * 0.5) + (artist_ratio * 0.3) + (album_ratio * 0.2)
            
            if total_ratio > highest_ratio:
                highest_ratio = total_ratio
                best_match = result
        
        # Si no encuentra en YouTube Music, buscar en YouTube directamente
        if best_match is None or highest_ratio <= 70:
            logging.warning(f'No se encontraron resultados confiables en YouTube Music. Intentando búsqueda en YouTube.')
            
            # Configurar opciones para búsqueda en YouTube
            ydl_opts = {
                'format': 'bestaudio/best',
                'max_downloads': 1,
                'default_search': 'ytsearch1:',
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                
                if info and 'entries' in info and info['entries']:
                    first_result = info['entries'][0]
                    return first_result['webpage_url']
                else:
                    logging.warning(f'No se encontraron resultados en YouTube para: {query}')
                    return None
        
        # Si encontró en YouTube Music, retornar enlace
        if best_match and highest_ratio > 70:
            return f"https://music.youtube.com/watch?v={best_match['videoId']}"
        
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
            q.put({'error': 'network_error'})
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
    Sanitiza nombres de archivos con estrategias múltiples de limpieza.
    
    Args:
        title (str): Título principal para el nombre del archivo
        artist (str, opcional): Artista para nombre de archivo
        album (str, opcional): Álbum para nombre de archivo
        fallback_method (bool): Usar método tradicional si la sanitización falla
    
    Returns:
        str: Nombre de archivo sanitizado y seguro
    """
    def clean_base_name(name):
        """Limpieza base para nombres"""
        # Eliminar caracteres especiales problemáticos
        name = re.sub(r'[<>:"/\\|?*¿#\']', '', name)
        
        # Normalizar caracteres Unicode
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Reemplazar espacios múltiples
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    # Estrategia 1: Usar título completo con artista
    if artist:
        filename = f"{clean_base_name(title)} - {clean_base_name(artist)}"
    else:
        filename = clean_base_name(title)
    # Estrategia 2: Agregar álbum si está disponible
    if album:
        filename = f"{filename} ({clean_base_name(album)})"
    # Truncar a 255 caracteres
    filename = filename[:255]
    # Fallback si el nombre está vacío
    if not filename and fallback_method:
        filename = f"Track_{int(time.time())}"
    return filename.strip()

def update_mp3_metadata(filename, title, artist, album, cover_image_url, release_date):
    try:
        # Sanitizar el título para nombre de archivo
        safe_filename = sanitize_filename(title)
        
        # Construir ruta de archivo segura
        safe_filepath = os.path.join(
            os.path.dirname(filename), 
            f"{safe_filename}.mp3"
        )
        
        # Renombrar archivo si es necesario
        if safe_filepath != filename:
            os.rename(filename, safe_filepath)
            filename = safe_filepath
        audio = eyed3.load(filename)
        if audio.tag is None:
            audio.initTag()     
        # Usar títulos originales para metadatos
        audio.tag.title = title
        audio.tag.artist = artist
        audio.tag.album = album        
        # Extraer el año de la fecha de lanzamiento
        year = release_date.split('-')[0] if release_date else None
        if year:
            try:
                audio.tag.year = int(year)
            except ValueError:
                logging.warning(f"No se pudo convertir el año: {year}")
        audio.tag.release_date = release_date
        # Manejar imagen de portada con más robustez
        try:
            response = requests.get(cover_image_url)
            if response.status_code == 200:
                audio.tag.images.set(3, response.content, "image/jpeg", u"cover")
        except Exception as img_error:
            logging.error(f'Error al procesar imagen de portada: {img_error}')
        audio.tag.save(version=(2,3,0))
        return True
    except Exception as e:
        logging.error(f'Error al actualizar los metadatos del MP3: {e}')
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
                self.handle_existing_file(song_metadata['song'], filename)
                if not self.replace_response:
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
        
        # Reset replace response for next iteration
        replace_response = self.replace_response
        self.replace_response = None
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
                    
                    url = (info['entries'][0]['webpage_url'] 
                        if info and 'entries' in info and info['entries'] 
                        else None)
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

            # Actualizar metadatos
            if update_mp3_metadata(
                filename, 
                song_metadata['song'], 
                song_metadata['artists'], 
                song_metadata['album'], 
                song_metadata['cover_url'], 
                song_metadata['release_date']
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

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Título", "Artista", "Álbum", "Fecha", "Archivo"])
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

        self.download_folder = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta de descarga")
        if not self.download_folder:
            QMessageBox.warning(self, "Advertencia", "No se seleccionó una carpeta de descarga.")
            self.textinput.setEnabled(True)
            self.button.setEnabled(True)
            self.quality_selector.setEnabled(True)
            return
        
        self.worker = DownloadWorker(spotify_id, self.download_folder, quality)
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
            self.add_to_history(item, from_load=True)

    def add_to_history(self, item, from_load=False):
        row_position = self.history_table.rowCount()
        self.history_table.insertRow(row_position)
        self.history_table.setItem(row_position, 0, QTableWidgetItem(item['title']))
        self.history_table.setItem(row_position, 1, QTableWidgetItem(item['artist']))
        self.history_table.setItem(row_position, 2, QTableWidgetItem(item['album']))
        self.history_table.setItem(row_position, 3, QTableWidgetItem(item['release_date']))
        self.history_table.setItem(row_position, 4, QTableWidgetItem(item['file_path']))
        
        if not from_load:
            self.history.append(item)
            save_download_history(self.history)

    def open_file(self, row, column):
        file_path = self.history_table.item(row, 4).text()
        if os.path.exists(file_path):
            os.startfile(file_path)
        else:
            reply = QMessageBox.question(self, 'Archivo no encontrado', 'El archivo no existe. ¿Desea eliminarlo del historial?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.history.pop(row)
                save_download_history(self.history)
                self.history_table.removeRow(row)
                
if __name__ == "__main__":
    app = QApplication([])
    window = ModernApp()
    window.show()
    app.exec_()