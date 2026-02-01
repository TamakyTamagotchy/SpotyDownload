import os, logging, re, time, requests, eyed3, yt_dlp
from PIL import Image
from io import BytesIO
from .search import search_song
from config.settings_manager import SettingsManager

HISTORY_FILE = "download_history.txt"

def _get_js_runtime_options():
    """
    Configura el runtime de JavaScript para yt-dlp.
    
    YouTube requiere un JS runtime (deno) para resolver challenges.
    Esta función usa exclusivamente el ejecutable deno.exe en la ruta por defecto
    del proyecto (Deno/deno.exe), que viene incluido con el programa.
    
    La detección se cachea para mejorar el rendimiento.
    
    También habilita remote_components para descargar el script de
    resolución de challenges desde GitHub (requerido por yt-dlp).
    
    FORMATO CORRECTO de js_runtimes para API Python:
    js_runtimes = {'deno': {'path': '/ruta/a/deno'}}
    """
    # Intentar obtener de cache primero
    cached_path = getattr(_get_js_runtime_options, '_cached_deno_path', None)
    if cached_path and os.path.exists(cached_path) and cached_path.endswith('.exe'):
        logging.debug(f"Deno encontrado en cache: {cached_path}")
        return {
            'js_runtimes': {'deno': {'path': cached_path}},
            'remote_components': ['ejs:github'],
        }
    
    # Obtener el directorio base del proyecto (donde está src/ o similar)
    current_file = os.path.abspath(__file__)
    downloader_dir = os.path.dirname(current_file)  # downloader
    project_dir = os.path.dirname(downloader_dir)  # proyecto raíz
    
    # Ruta por defecto obligatoria
    project_deno_path = os.path.join(project_dir, 'Deno', 'deno.exe')
    
    if os.path.exists(project_deno_path) and project_deno_path.endswith('.exe'):
        # Cachear la ruta para futuras ejecuciones
        _get_js_runtime_options._cached_deno_path = project_deno_path
        logging.info(f"Deno encontrado y cacheado en ruta por defecto: {project_deno_path}")
        return {
            'js_runtimes': {'deno': {'path': project_deno_path}},
            'remote_components': ['ejs:github'],
        }
    
    logging.warning("Deno no encontrado en la ruta por defecto, YouTube puede tener formatos limitados")
    return {}

def _get_youtube_extractor_args(last_resort_mode=False):
    """
    Configura argumentos avanzados del extractor de YouTube.
    Incluye PO Token, player clients, y configuraciones para evitar throttling.
    """
    args = {}
    
    if last_resort_mode:
        # Modo último recurso: usar client menos restringido
        args['player_client'] = ['web_safari', 'web', 'android']
        args['player_skip'] = ['webpage', 'configs']
    else:
        # Configuración estándar con múltiples clients
        args['player_client'] = ['tv', 'web_safari', 'web', 'android']
        args['player_skip'] = ['webpage', 'configs']
    
    # Configuración de PO Token (Proof of Origin Token) (nuevo)
    po_token = _get_po_token_config()
    if po_token:
        args['po_token'] = po_token
    
    # Visitor Data para mejorar la extracción (nuevo)
    # Por ahora no implementado
    
    # Tiempo de espera entre extracción y descarga para asegurar disponibilidad (nuevo)
    args['playback_wait'] = ['6']  # 6 segundos (recomendado por yt-dlp)
    
    # Configuraciones adicionales de formato
    args['formats'] = ['dashy', 'incomplete']  # Incluir formatos DASH e incompletos
    
    return args

def _get_po_token_config():
    """
    Obtiene el PO Token (Proof of Origin Token) para YouTube.
    Lee desde config/youtube_po_token.txt si existe.
    
    Formato: CLIENT.CONTEXT+PO_TOKEN
    Ejemplo: "web.gvs+XXX,web.player=XXX,web_safari.gvs+YYY"
    """
    try:
        # Buscar en el directorio del proyecto
        current_file = os.path.abspath(__file__)
        downloader_dir = os.path.dirname(current_file)
        project_dir = os.path.dirname(downloader_dir)
        config_dir = os.path.join(project_dir, 'config')
        po_token_file = os.path.join(config_dir, 'youtube_po_token.txt')
        
        if os.path.exists(po_token_file):
            with open(po_token_file, 'r', encoding='utf-8') as f:
                po_token = f.read().strip()
                if po_token:
                    logging.info("PO Token cargado desde archivo de configuración")
                    return po_token
    except Exception as e:
        logging.debug(f"Error cargando PO Token: {e}")
    
    return None

"""def _get_impersonation_target():
    """
"""    Obtiene el objetivo de impersonación para bypass de protecciones TLS.
    Requiere curl_cffi instalado.
    
    Returns:
        str: Target de impersonación (ej: 'chrome', 'safari', 'chrome-110')
    """
"""    try:
        # Verificar si curl_cffi está disponible sin forzar import estático
        __import__('curl_cffi')
        
        # Retornar el target más compatible
        # Opciones: chrome, chrome-110, chrome-99, edge, safari
        return 'chrome-110'  # Versión específica de Chrome
    except ImportError:
        logging.debug("curl_cffi no disponible para impersonación")
        return None
"""
def extract_id(link):
    pattern = re.compile(r'(?:playlist|track)/(\w+)')
    match = pattern.search(link)
    if match:
        return match.group(1)
    else:
        return link

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
    import unicodedata  # Solo importar aquí si se usa

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

def update_mp3_metadata(filename, title, artist, album, cover_image_url, release_date):
    """
    Actualiza los metadatos de un archivo MP3.
    """
    try:
        if not os.path.exists(filename):
            logging.error(f'Archivo no encontrado: {filename}')
            return False
        audio = eyed3.load(filename)
        if audio is None:
            logging.error(f'No se pudo cargar el archivo de audio: {filename}')
            return False
        if audio.tag is None:
            audio.initTag()
        audio.tag.title = title or "Titulo Desconocido"
        audio.tag.artist = artist or "Artista Desconocido"
        audio.tag.album = album or "Album Desconocido"
        try:
            if release_date:
                year_match = re.search(r'\d{4}', release_date)
                if year_match:
                    audio.tag.year = int(year_match.group())
        except (ValueError, TypeError) as date_error:
            logging.warning(f'Fecha de lanzamiento no válida: {release_date}. Error: {date_error}')
        if cover_image_url:
            try:
                response = requests.get(cover_image_url, timeout=10)
                response.raise_for_status()
                image_content = response.content
                # Detectar el MIME real de la imagen
                try:
                    img = Image.open(BytesIO(image_content))
                    img.verify()  # Solo verifica, no carga en memoria
                    mime = Image.MIME.get(img.format, "image/jpeg")
                except Exception as pil_error:
                    logging.warning(f'La imagen de portada no es válida: {pil_error}')
                    mime = "image/jpeg"
                audio.tag.images.set(3, image_content, mime, u"Cover")
            except Exception as img_error:
                logging.error(f'Error al procesar la imagen de portada: {img_error}')
        audio.tag.save(version=(2,3,0))
        return True
    except Exception as e:
        logging.error(f'Error integral en la actualización de metadatos: {e}')
        return False

def update_mp3_metadata_hybrid(filename, title, artist, album, cover_image_url, release_date, genre=None):
    """
    Función híbrida que combina lo mejor de ID3v2.4 e ID3v2.3:
    - Metadatos de texto: ID3v2.4 (mejor codificación UTF-8)
    - Portada: ID3v2.3 (mejor compatibilidad)
    """
    try:
        if not os.path.exists(filename):
            logging.error(f'Archivo no encontrado: {filename}')
            return False
        
        # PASO 1: Guardar metadatos de texto con ID3v2.4 (mejor UTF-8)
        audio = eyed3.load(filename)
        if audio is None:
            logging.error(f'No se pudo cargar el archivo de audio: {filename}')
            return False
        
        if audio.tag is None:
            audio.initTag()
        
        # Metadatos básicos con codificación UTF-8 mejorada
        audio.tag.title = title or "Titulo Desconocido"
        audio.tag.artist = artist or "Artista Desconocido"
        audio.tag.album = album or "Album Desconocido"
        
        # Año mejorado
        if release_date:
            year_match = re.search(r'\b(19|20)\d{2}\b', str(release_date))
            if year_match:
                year = int(year_match.group())
                audio.tag.recording_date = year
                logging.info(f'Año establecido: {year}')
        
        # Género
        if genre and isinstance(genre, str) and genre.strip():
            audio.tag.genre = genre.strip()
            logging.info(f'Género establecido: {genre.strip()}')
        
        # Guardar metadatos de texto con ID3v2.4 (SIN portada todavía)
        audio.tag.save(version=(2,4,0))
        logging.info(f'Metadatos de texto guardados con ID3v2.4')
        
        # PASO 2: Agregar portada con ID3v2.3 (mejor compatibilidad)
        if cover_image_url:
            try:
                # Recargar el archivo para trabajar con la portada
                audio = eyed3.load(filename)
                if audio.tag is None:
                    audio.initTag()
                
                logging.info(f'Descargando portada desde: {cover_image_url}')
                response = requests.get(cover_image_url, timeout=10)
                response.raise_for_status()
                image_content = response.content
                logging.info(f'Portada descargada, tamaño: {len(image_content)} bytes')
                
                # Detectar formato de imagen con PIL
                mime = "image/jpeg"  # Default fallback
                try:
                    img = Image.open(BytesIO(image_content))
                    if img.format:
                        format_to_mime = {
                            'JPEG': 'image/jpeg',
                            'PNG': 'image/png',
                            'GIF': 'image/gif',
                            'BMP': 'image/bmp',
                            'WEBP': 'image/webp'
                        }
                        mime = format_to_mime.get(img.format, 'image/jpeg')
                        logging.info(f'Formato detectado: {img.format}, MIME: {mime}')
                    img.verify()
                except Exception as pil_error:
                    logging.warning(f'Error PIL, usando JPEG como fallback: {pil_error}')
                
                # Limpiar imágenes existentes antes de agregar la nueva
                audio.tag.images.remove(description="Cover")
                
                # Aplicar la portada con ID3v2.3
                audio.tag.images.set(3, image_content, mime, u"Cover")
                logging.info(f'Portada aplicada con MIME: {mime}')
                
                # Guardar SOLO la portada con ID3v2.3
                audio.tag.save(version=(2,3,0))
                logging.info(f'Portada guardada con ID3v2.3 para máxima compatibilidad')
                
            except Exception as img_error:
                logging.error(f'Error procesando portada: {img_error}')
                return False
        
        logging.info(f'Metadatos híbridos aplicados exitosamente: {title} - {artist}')
        return True
    
    except Exception as e:
        logging.error(f'Error en metadatos híbridos: {e}')
        return False

def search_music_services(title, artist, album=None):
    """
    Buscar canción usando el algoritmo simple
    
    Args:
        title: Título de la canción
        artist: Artista o lista de artistas
        album: Álbum (opcional)
    """
    url = search_song(title, artist, album)
    return url

def download_song(url, filename, q, pause_event, cancel_event, max_retries=3, output_format="mp3"):
    """
    Descarga una canción de YouTube Music o similar y la convierte al formato especificado.
    
    Args:
        url: URL del video/audio
        filename: Ruta del archivo de salida (sin extensión o con extensión)
        q: Cola para reportar progreso
        pause_event: Evento para pausar
        cancel_event: Evento para cancelar
        max_retries: Intentos máximos
        output_format: Formato de salida ('mp3' o 'flac')
    """
    import glob
    import subprocess
    import os
    
    base, _ = os.path.splitext(filename)
    outtmpl = base + '.%(ext)s'
    ffmpeg_path = SettingsManager().get_ffmpeg_path()
    
    # Determinar extensión y archivo de salida según formato
    if output_format.lower() == 'flac':
        output_file = base + '.flac'
    else:
        output_file = base + '.mp3'
    
    download_dir = os.path.dirname(base)
    base_name = os.path.basename(base)

    # Obtener opciones de JS runtime (Deno)
    js_runtime_opts = _get_js_runtime_options()
    
    # Descargar siempre el mejor audio disponible
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'progress_hooks': [lambda d: q.put(d)],
        'ffmpeg_location': ffmpeg_path,
        'restrictfilenames': False,  # Permitir caracteres especiales
        'retries': 10,  # Aumentar reintentos
        'fragment_retries': 10,
        'extractor_retries': 3,
        'file_access_retries': 3,
        'socket_timeout': 30,
        'concurrent_fragment_downloads': 3,
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_requests': 0.5,
        'retry_sleep_functions': {
            'http': lambda n: min(2 ** n, 60),
            'fragment': lambda n: min(2 ** n, 30),
            'extractor': lambda n: min(3 * n, 20),
        },
    }
    
    # Agregar opciones de JS runtime si están disponibles
    js_runtime_opts = _get_js_runtime_options()
    if js_runtime_opts:
        ydl_opts.update(js_runtime_opts)
    
    # Agregar extractor args específicos para YouTube
    if 'youtube' in url.lower() or 'youtu.be' in url.lower():
        youtube_extractor_args = _get_youtube_extractor_args()
        if youtube_extractor_args:
            ydl_opts['extractor_args'] = {'youtube': youtube_extractor_args}
    
    # Intentar configurar impersonación si está disponible (comentado por compatibilidad)
    # impersonate_target = _get_impersonation_target()
    # if impersonate_target:
    #     ydl_opts['impersonate'] = impersonate_target
    #     logging.info(f"Impersonación configurada: {impersonate_target}")

    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                while not cancel_event.is_set():
                    if pause_event.is_set():
                        pause_event.wait()
                    else:
                        result = ydl.download([url])
                        
                        # Buscar el archivo descargado (puede ser webm, m4a, etc.)
                        downloaded_file = None
                        
                        # Primero buscar con el nombre exacto
                        for ext in [".webm", ".m4a", ".opus", ".mp4", ".flac", ".wav", ".aac", ".mp3"]:
                            candidate = base + ext
                            if os.path.exists(candidate):
                                downloaded_file = candidate
                                logging.info(f"Archivo encontrado: {candidate}")
                                break
                        
                        # Si no se encuentra, buscar archivos similares en el directorio
                        if not downloaded_file:
                            # Buscar archivos recién creados en el directorio de descarga
                            import time
                            search_pattern = os.path.join(download_dir, "*.*")
                            all_files = glob.glob(search_pattern)
                            
                            # Filtrar solo archivos de audio recientes (últimos 30 segundos)
                            audio_extensions = ('.webm', '.m4a', '.opus', '.mp4', '.flac', '.wav', '.aac', '.mp3')
                            recent_time = time.time() - 30
                            
                            recent_audio_files = [
                                f for f in all_files 
                                if f.lower().endswith(audio_extensions) 
                                and os.path.getmtime(f) > recent_time
                            ]
                            
                            if recent_audio_files:
                                # Usar el archivo más reciente
                                downloaded_file = max(recent_audio_files, key=os.path.getmtime)
                                logging.info(f"Archivo encontrado por fecha: {downloaded_file}")
                        
                        # También buscar con glob el patrón base
                        if not downloaded_file:
                            files = glob.glob(base + ".*")
                            audio_files = [f for f in files if f.lower().endswith(audio_extensions)]
                            if audio_files:
                                downloaded_file = max(audio_files, key=os.path.getctime)
                                logging.info(f"Archivo encontrado con glob: {downloaded_file}")
                        
                        if not downloaded_file:
                            logging.error(f"No se encontró el archivo descargado. Base esperada: {base}")
                            raise Exception("El archivo descargado no se encontró")
                        
                        # Convertir al formato de salida especificado
                        if not downloaded_file.endswith(f'.{output_format.lower()}'):
                            # Determinar la ruta de ffmpeg
                            ffmpeg_exe = None
                            
                            # Opción 1: Ruta configurada
                            if ffmpeg_path:
                                candidate = os.path.join(ffmpeg_path, 'ffmpeg.exe')
                                if os.path.exists(candidate):
                                    ffmpeg_exe = candidate
                                else:
                                    candidate = os.path.join(ffmpeg_path, 'ffmpeg')
                                    if os.path.exists(candidate):
                                        ffmpeg_exe = candidate
                            
                            # Opción 2: Buscar en PATH del sistema
                            if not ffmpeg_exe:
                                import shutil
                                ffmpeg_exe = shutil.which('ffmpeg')
                            
                            # Opción 3: Buscar en ubicaciones comunes
                            if not ffmpeg_exe:
                                common_paths = [
                                    r"D:\Escritorio\Carpetas con cosas\Programas\ffmpeg-7.1-full_build\bin\ffmpeg.exe",
                                    r"C:\ffmpeg\bin\ffmpeg.exe",
                                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                                ]
                                for path in common_paths:
                                    if os.path.exists(path):
                                        ffmpeg_exe = path
                                        break
                            
                            if not ffmpeg_exe:
                                logging.error("FFmpeg no encontrado. Por favor configura la ruta en Configuración.")
                                raise Exception("FFmpeg no encontrado")
                            
                            logging.info(f"Usando FFmpeg: {ffmpeg_exe}")
                            
                            # Construir comando según formato de salida
                            if output_format.lower() == 'flac':
                                cmd = [
                                    ffmpeg_exe,
                                    '-y',
                                    '-i', downloaded_file,
                                    '-codec:a', 'flac',
                                    '-compression_level', '8',  # Máxima compresión sin pérdida
                                    output_file
                                ]
                                logging.info(f"Convirtiendo a FLAC: {downloaded_file} -> {output_file}")
                            else:
                                cmd = [
                                    ffmpeg_exe,
                                    '-y',
                                    '-i', downloaded_file,
                                    '-codec:a', 'libmp3lame',
                                    '-b:a', '320k',
                                    output_file
                                ]
                                logging.info(f"Convirtiendo a MP3: {downloaded_file} -> {output_file}")
                            
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            
                            if result.returncode != 0:
                                logging.error(f"Error de FFmpeg: {result.stderr}")
                                raise Exception(f"Error convirtiendo a {output_format.upper()}: {result.stderr}")
                            
                            # Verificar que se creó el archivo
                            if os.path.exists(output_file):
                                logging.info(f"{output_format.upper()} creado exitosamente: {output_file}")
                                # Eliminar archivo original después de convertir
                                try:
                                    os.remove(downloaded_file)
                                    logging.info(f"Archivo original eliminado: {downloaded_file}")
                                except Exception as e:
                                    logging.warning(f"No se pudo eliminar archivo original: {e}")
                            else:
                                raise Exception(f"El archivo {output_format.upper()} no se creó")
                        elif downloaded_file != output_file:
                            # Ya está en el formato correcto, solo renombrar si es necesario
                            os.rename(downloaded_file, output_file)
                        
                        return
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e)
            logging.error(f'Intento {attempt + 1} fallido. Error: {e}')
            if 'ffmpeg no encontrado' in error_str or 'ffprobe no encontrado' in error_str:
                q.put({'error': 'No se pudo descargar la canción: ffmpeg o ffprobe no encontrado. Verifica la ruta.'})
                break
            if attempt == max_retries - 1:
                q.put({'error': f'No se pudo descargar la canción después de {max_retries} intentos: {e}'})
        except requests.exceptions.RequestException as e:
            logging.error(f'Error de red durante la descarga: {e}')
            q.put({'error': 'error_de_red'})
            return
        except Exception as e:
            logging.error(f'Error inesperado durante la descarga: {e}')
            q.put({'error': str(e)})
            return
    if cancel_event.is_set():
        partial_file = filename[:-4] + '.part'
        if os.path.exists(partial_file):
            os.remove(partial_file)

def save_download_history(history_links):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            for link in history_links:
                f.write(link.strip() + '\n')
    except Exception as e:
        logging.error(f'No se pudo guardar el historial de descargas: {e}')

def load_download_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
                return links
        except Exception as e:
            logging.error(f'No se pudo cargar el historial de descargas: {e}')
            return []
    return []

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def are_files_equal(file1, file2):
    """
    Compara dos archivos MP3 por título, artista y álbum.
    """
    try:
        audio1 = eyed3.load(file1)
        audio2 = eyed3.load(file2)
        if not audio1 or not audio1.tag or not audio2 or not audio2.tag:
            return False
        return (audio1.tag.title == audio2.tag.title and
                audio1.tag.artist == audio2.tag.artist and
                audio1.tag.album == audio2.tag.album)
    except Exception as e:
        logging.error(f'Error al comparar archivos MP3: {e}')
        return False
