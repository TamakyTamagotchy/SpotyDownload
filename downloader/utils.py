import os, logging, re, time, requests, eyed3, yt_dlp
from PIL import Image
from io import BytesIO
from .search import search_song
from config.settings_manager import SettingsManager

HISTORY_FILE = "download_history.txt"

# ============================================================================
# CONSTANTES DE YT-DLP (importadas de Axolutly)
# ============================================================================
YT_DLP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.6422.112 Safari/537.36"
)
MP3_FORMAT = "mp3"
BESTAUDIO_FORMAT = "bestaudio"
BEST_FORMAT = "best"
DEFAULT_AUDIO_QUALITY = "320"  # 320kbps para mejor calidad en música

# ============================================================================
# FUNCIONES DE CONFIGURACIÓN DE YT-DLP (mejoradas desde Axolutly)
# ============================================================================

def _validate_deno_executable(path: str) -> bool:
    """
    Valida que el ejecutable de Deno existe y es funcional.
    """
    if not path or not os.path.exists(path):
        return False
    
    if not path.lower().endswith('.exe'):
        return False
    
    try:
        file_size = os.path.getsize(path)
        if file_size < 1024 * 1024:  # Menor a 1MB probablemente corrupto
            logging.warning(f"Deno ejecutable parece corrupto (tamaño: {file_size} bytes)")
            return False
    except OSError as e:
        logging.debug(f"Error validando Deno: {e}")
        return False
    
    return True


def _build_js_runtime_config(deno_path: str) -> dict:
    """
    Construye la configuración del JS runtime con opciones optimizadas.
    
    yt-dlp 2026.01.29+ soporta:
    - deno (recomendado): Mejor seguridad, requiere permisos explícitos
    - node: Alternativa común
    - quickjs: Ligero pero menos compatible
    - bun: Nueva opción, rápido pero experimental
    
    Opciones de Deno:
    - --no-check: Omite verificación de tipos (más rápido)
    - --quiet: Reduce output
    - --allow-net: Permite conexiones de red
    - --allow-read: Permite lectura de archivos
    - --no-lock: No usar lockfile (evita problemas de cache)
    """
    config = {
        'js_runtimes': {
            'deno': {
                'path': deno_path,
                'args': [
                    '--no-check',
                    '--quiet',
                    '--allow-net',
                    '--allow-read',
                    '--no-lock',
                ],
            }
        },
        # Componentes remotos para descargar el script de challenges (yt-dlp-ejs)
        'remote_components': ['ejs:github'],
    }
    
    return config


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
    js_runtimes = {'deno': {'path': '/ruta/a/deno', 'args': [...]}}
    """
    # Intentar obtener de cache primero
    cached_path = getattr(_get_js_runtime_options, '_cached_deno_path', None)
    if cached_path and _validate_deno_executable(cached_path):
        logging.debug(f"Deno encontrado en cache: {cached_path}")
        return _build_js_runtime_config(cached_path)
    
    # Obtener el directorio base del proyecto
    current_file = os.path.abspath(__file__)
    downloader_dir = os.path.dirname(current_file)
    project_dir = os.path.dirname(downloader_dir)
    
    # Ruta por defecto obligatoria
    project_deno_path = os.path.join(project_dir, 'Deno', 'deno.exe')
    
    if _validate_deno_executable(project_deno_path):
        # Cachear la ruta para futuras ejecuciones
        _get_js_runtime_options._cached_deno_path = project_deno_path
        logging.info(f"Deno encontrado y cacheado en ruta por defecto: {project_deno_path}")
        return _build_js_runtime_config(project_deno_path)
    
    logging.warning("Deno no encontrado en la ruta por defecto, YouTube puede tener formatos limitados")
    return {}


def _get_youtube_extractor_args(last_resort_mode=False):
    """
    Configura argumentos avanzados del extractor de YouTube.
    Incluye PO Token, player clients, y configuraciones para evitar throttling.
    
    yt-dlp 2026.02+ player_clients disponibles:
    - web, web_safari, web_embedded, web_music, web_creator
    - mweb (mobile web)
    - ios, android, android_vr
    - tv, tv_downgraded, tv_simply
    
    CAMBIO IMPORTANTE (2026.02):
    - YouTube ahora usa 'tv' player JS variant por defecto
    - 'tv' ofrece mejor calidad y menos throttling
    - Mantiene compatibilidad con versiones anteriores
    
    Default sin JS runtime: android_vr
    Default con JS runtime (deno): tv, android_vr, web_safari
    Para videos con restricción de edad: web_embedded
    """
    args = {}
    
    if last_resort_mode:
        # Modo último recurso: clientes mínimos pero funcionales
        args['player_client'] = ['android_vr', 'web']
        args['player_skip'] = ['configs']
        logging.info("Modo último recurso activado: usando player_client=['android_vr', 'web']")
    else:
        # Configuración óptima para yt-dlp 2026.02+ con Deno
        # PRIORIDAD ACTUALIZADA (2026.02):
        # tv: Player por defecto de yt-dlp 2026.02+, mejor calidad/estabilidad
        # android_vr: No requiere JS, buena compatibilidad (fallback)
        # web_embedded: Para videos con restricción de edad
        # web_safari: Buena calidad, formatos iOS-like
        # web: Completo pero requiere JS challenges
        # tv_downgraded: Fallback legacy
        args['player_client'] = [
            'tv',              # Prioridad 1 (yt-dlp 2026.02+)
            'android_vr',      # Fallback para versiones anteriores
            'web_embedded',    # Restricción de edad
            'web_safari',      # Calidad iOS
            'web',             # Completo con JS
            'tv_downgraded'    # Legacy fallback
        ]
        args['player_skip'] = ['webpage']
    
    # Configuración de PO Token (Proof of Origin Token)
    po_token = _get_po_token_config()
    if po_token:
        args['po_token'] = [po_token]
        # fetch_pot: auto (default), always, never
        args['fetch_pot'] = 'auto'
        logging.info("PO Token configurado para YouTube")
    else:
        # Sin PO token manual, dejar que yt-dlp intente obtenerlo
        args['fetch_pot'] = 'auto'
    
    # Tiempo de espera entre extracción y descarga (segundos)
    args['playback_wait'] = 6
    
    # Configuraciones adicionales de formato
    args['formats'] = 'dashy,incomplete'  # Incluir formatos DASH e incompletos
    
    # Configuraciones de comentarios (deshabilitados para música)
    args['comment_sort'] = 'top'
    args['max_comments'] = [0]
    
    return args


def _get_po_token_config():
    """
    Obtiene el PO Token (Proof of Origin Token) para YouTube.
    Lee desde config/youtube_po_token.txt si existe.
    
    Formato: CLIENT.CONTEXT+PO_TOKEN
    Ejemplo: "web.gvs+XXX,web.player=XXX,web_safari.gvs+YYY"
    """
    try:
        current_file = os.path.abspath(__file__)
        downloader_dir = os.path.dirname(current_file)
        project_dir = os.path.dirname(downloader_dir)
        config_dir = os.path.join(project_dir, 'config')
        po_token_file = os.path.join(config_dir, 'youtube_po_token.txt')
        
        if os.path.exists(po_token_file):
            with open(po_token_file, 'r', encoding='utf-8') as f:
                token = f.read().strip()
                if token:
                    logging.info("PO Token cargado desde archivo de configuración")
                    return token
    except Exception as e:
        logging.debug(f"No se pudo leer PO Token: {e}")
    
    return None


def _get_impersonation_target():
    """
    Obtiene el objetivo de impersonación para bypass de protecciones TLS.
    Requiere curl_cffi instalado.
    
    Returns:
        str | None: Target de impersonación (ej: 'chrome', 'safari', 'chrome-110')
    """
    try:
        # Verificar si curl_cffi está disponible sin forzar import estático
        __import__('curl_cffi')
        
        # Retornar el target más compatible
        # Opciones: chrome, chrome-110, chrome-99, edge, safari
        return 'chrome'  # Chrome es generalmente el más compatible
    except ImportError:
        logging.debug("curl_cffi no disponible para impersonación")
        return None


def _get_common_retry_options(profile: str = 'default') -> dict:
    """
    Obtiene opciones comunes de reintentos según el perfil de plataforma.
    
    Perfiles:
    - 'aggressive': Más reintentos, backoff más fuerte (para sitios difíciles)
    - 'moderate': Balance entre velocidad y estabilidad (YouTube Music)
    - 'light': Menos restricciones
    - 'default': Configuración base
    """
    profiles = {
        'aggressive': {
            'retries': 15,
            'fragment_retries': 15,
            'extractor_retries': 5,
            'file_access_retries': 3,
            'socket_timeout': 30,
            'concurrent_fragment_downloads': 1,
            'sleep_interval': 2,
            'max_sleep_interval': 8,
            'sleep_requests': 1,
            'retry_sleep_functions': {
                'http': lambda n: min(3 ** n, 120),
                'fragment': lambda n: min(3 ** n, 60),
                'extractor': lambda n: min(5 * n, 30),
            },
        },
        'moderate': {
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'file_access_retries': 3,
            'socket_timeout': 30,
            'concurrent_fragment_downloads': 2,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_requests': 0.5,
            'retry_sleep_functions': {
                'http': lambda n: min(2 ** n, 60),
                'fragment': lambda n: min(2 ** n, 30),
                'extractor': lambda n: min(3 * n, 15),
            },
        },
        'light': {
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'file_access_retries': 3,
            'concurrent_fragment_downloads': 2,
            'sleep_interval': 1,
            'max_sleep_interval': 3,
            'sleep_requests': 0.5,
        },
    }
    return profiles.get(profile, profiles['moderate'])


def _get_audio_postprocessors(bitrate: str = None) -> list:
    """
    Obtiene los postprocesadores para audio MP3.
    
    Args:
        bitrate: Bitrate en kbps (ej: "320", "256", "192", "128")
                 Si es None, usa el valor de configuración o DEFAULT_AUDIO_QUALITY
    """
    if bitrate is None:
        settings = SettingsManager()
        bitrate = settings.get_mp3_bitrate()
    
    return [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': MP3_FORMAT,
        'preferredquality': bitrate,
    }]


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
    Función híbrida mejorada para actualizar metadatos de audio.
    
    Utiliza el nuevo módulo metadata.py que soporta:
    - mutagen para mejor compatibilidad y rendimiento
    - Soporte para MP3 y FLAC
    - Cache de imágenes descargadas
    - Mejor manejo de codificación UTF-8
    
    Args:
        filename: Ruta del archivo de audio
        title: Título de la canción
        artist: Artista o lista de artistas
        album: Nombre del álbum
        cover_image_url: URL de la imagen de portada
        release_date: Fecha de lanzamiento
        genre: Género musical (opcional)
        
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    from .metadata import update_mp3_metadata, update_flac_metadata
    
    try:
        if not os.path.exists(filename):
            logging.error(f'Archivo no encontrado: {filename}')
            return False
        
        # Detectar formato por extensión
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.flac':
            return update_flac_metadata(
                filename, title, artist, album, 
                cover_image_url, release_date, genre
            )
        else:
            # MP3 u otros formatos compatibles con ID3
            return update_mp3_metadata(
                filename, title, artist, album,
                cover_image_url, release_date, genre
            )
            
    except Exception as e:
        logging.error(f'Error en update_mp3_metadata_hybrid: {e}')
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
    
    Implementación mejorada basada en Axolutly con:
    - Configuración optimizada de yt-dlp 2026.02+
    - Soporte para player clients actualizados (tv, android_vr, etc.)
    - Mejor manejo de reintentos y errores
    - Impersonación opcional con curl_cffi
    - Postprocesadores FFmpeg mejorados
    
    Args:
        url: URL del video/audio
        filename: Ruta del archivo de salida (sin extensión o con extensión)
        q: Cola para reportar progreso
        pause_event: Evento para pausar
        cancel_event: Evento para cancelar
        max_retries: Intentos máximos
        output_format: Formato de salida ('mp3' o 'flac')
    """
    
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
    
    # Log del formato solicitado
    logging.info(f"[download_song] Formato solicitado: {output_format}, archivo de salida: {output_file}")

    # =========================================================================
    # CONFIGURACIÓN BASE MEJORADA (Axolutly style)
    # =========================================================================
    ydl_opts = {
        # Opciones básicas
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': False,
        
        # Formato de audio
        'format': f'{BESTAUDIO_FORMAT}[ext=m4a]/{BESTAUDIO_FORMAT}[ext=webm]/{BESTAUDIO_FORMAT}/{BEST_FORMAT}',
        'outtmpl': outtmpl,
        'progress_hooks': [lambda d: q.put(d)],
        'restrictfilenames': False,  # Permitir caracteres especiales
        
        # Headers HTTP mejorados
        'http_headers': {
            'User-Agent': YT_DLP_USER_AGENT,
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.9',
        },
        
        # Postprocesadores para audio - solo MP3 usa conversión automática de yt-dlp
        'postprocessors': _get_audio_postprocessors() if output_format.lower() == 'mp3' else [],
        
        # Postprocessor args para FFmpeg (mejorado)
        'postprocessor_args': {
            'ffmpeg': ['-threads', '0'],
        },
    }
    
    # Log de postprocesadores configurados
    logging.info(f"[download_song] Postprocesadores: {ydl_opts['postprocessors']}")
    
    # =========================================================================
    # CONFIGURACIÓN DE REINTENTOS (perfil moderado para música)
    # =========================================================================
    retry_opts = _get_common_retry_options('moderate')
    ydl_opts.update(retry_opts)
    
    # =========================================================================
    # CONFIGURACIÓN DE FFMPEG
    # =========================================================================
    if ffmpeg_path and os.path.isdir(ffmpeg_path):
        ydl_opts['ffmpeg_location'] = ffmpeg_path
    
    # =========================================================================
    # CONFIGURACIÓN DE JS RUNTIME (Deno)
    # =========================================================================
    js_runtime_opts = _get_js_runtime_options()
    if js_runtime_opts:
        ydl_opts.update(js_runtime_opts)
    
    # =========================================================================
    # CONFIGURACIÓN ESPECÍFICA DE YOUTUBE
    # =========================================================================
    is_youtube = 'youtube' in url.lower() or 'youtu.be' in url.lower() or 'music.youtube' in url.lower()
    
    if is_youtube:
        youtube_extractor_args = _get_youtube_extractor_args()
        if youtube_extractor_args:
            ydl_opts['extractor_args'] = {'youtube': youtube_extractor_args}
    
    # =========================================================================
    # IMPERSONACIÓN (opcional, requiere curl_cffi)
    # =========================================================================
    impersonate_target = _get_impersonation_target()
    if impersonate_target:
        ydl_opts['impersonate'] = impersonate_target
        logging.info(f"Impersonación configurada: {impersonate_target}")
    
    # =========================================================================
    # BUCLE DE DESCARGA CON REINTENTOS
    # =========================================================================
    last_resort_tried = False
    
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                while not cancel_event.is_set():
                    if pause_event.is_set():
                        pause_event.wait()
                    else:
                        result = ydl.download([url])
                        
                        # Buscar el archivo descargado (puede ser webm, m4a, etc.)
                        downloaded_file = _find_downloaded_file(base, download_dir)
                        
                        if not downloaded_file:
                            logging.error(f"No se encontró el archivo descargado. Base esperada: {base}")
                            raise Exception("El archivo descargado no se encontró")
                        
                        logging.info(f"[download_song] Archivo descargado encontrado: {downloaded_file}")
                        logging.info(f"[download_song] Formato de salida esperado: {output_format}, archivo objetivo: {output_file}")
                        
                        # Convertir al formato de salida especificado si es necesario
                        if not downloaded_file.endswith(f'.{output_format.lower()}'):
                            logging.info(f"[download_song] Convirtiendo {downloaded_file} -> {output_file}")
                            _convert_audio_file(downloaded_file, output_file, output_format, ffmpeg_path)
                        elif downloaded_file != output_file:
                            # Ya está en el formato correcto, solo renombrar si es necesario
                            logging.info(f"[download_song] Renombrando {downloaded_file} -> {output_file}")
                            os.rename(downloaded_file, output_file)
                        else:
                            logging.info(f"[download_song] Archivo ya está en formato correcto: {downloaded_file}")
                        
                        return
                        
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            logging.error(f'Intento {attempt + 1}/{max_retries} fallido. Error: {e}')
            
            # Errores fatales que no se pueden recuperar
            if 'ffmpeg' in error_str or 'ffprobe' in error_str:
                q.put({'error': 'No se pudo descargar: ffmpeg o ffprobe no encontrado. Verifica la ruta.'})
                break
            
            # Intentar modo último recurso para errores 403 o similar
            if not last_resort_tried and ('403' in error_str or 'forbidden' in error_str or 'sign in' in error_str):
                logging.warning("Activando modo último recurso debido a error de acceso")
                last_resort_tried = True
                youtube_extractor_args = _get_youtube_extractor_args(last_resort_mode=True)
                if youtube_extractor_args:
                    ydl_opts['extractor_args'] = {'youtube': youtube_extractor_args}
                continue  # Reintentar con nueva configuración
            
            if attempt == max_retries - 1:
                q.put({'error': f'No se pudo descargar después de {max_retries} intentos: {e}'})
                
        except requests.exceptions.RequestException as e:
            logging.error(f'Error de red durante la descarga: {e}')
            q.put({'error': 'error_de_red'})
            return
            
        except Exception as e:
            logging.error(f'Error inesperado durante la descarga: {e}')
            q.put({'error': str(e)})
            return
    
    # Limpiar archivos parciales si se canceló
    if cancel_event.is_set():
        partial_file = filename[:-4] + '.part'
        if os.path.exists(partial_file):
            os.remove(partial_file)


def _find_downloaded_file(base: str, download_dir: str) -> str:
    """
    Busca el archivo descargado en diferentes ubicaciones y formatos.
    
    Args:
        base: Ruta base del archivo (sin extensión)
        download_dir: Directorio de descargas
        
    Returns:
        Ruta del archivo encontrado o None
    """
    import glob
    
    audio_extensions = ('.webm', '.m4a', '.opus', '.mp4', '.flac', '.wav', '.aac', '.mp3')
    
    # 1. Buscar con el nombre exacto
    for ext in audio_extensions:
        candidate = base + ext
        if os.path.exists(candidate):
            logging.info(f"Archivo encontrado: {candidate}")
            return candidate
    
    # 2. Buscar archivos recién creados en el directorio
    search_pattern = os.path.join(download_dir, "*.*")
    all_files = glob.glob(search_pattern)
    
    recent_time = time.time() - 30  # Últimos 30 segundos
    recent_audio_files = [
        f for f in all_files 
        if f.lower().endswith(audio_extensions) 
        and os.path.getmtime(f) > recent_time
    ]
    
    if recent_audio_files:
        downloaded_file = max(recent_audio_files, key=os.path.getmtime)
        logging.info(f"Archivo encontrado por fecha: {downloaded_file}")
        return downloaded_file
    
    # 3. Buscar con glob el patrón base
    files = glob.glob(base + ".*")
    audio_files = [f for f in files if f.lower().endswith(audio_extensions)]
    if audio_files:
        downloaded_file = max(audio_files, key=os.path.getctime)
        logging.info(f"Archivo encontrado con glob: {downloaded_file}")
        return downloaded_file
    
    return None


def _convert_audio_file(input_file: str, output_file: str, output_format: str, ffmpeg_path: str) -> None:
    """
    Convierte un archivo de audio al formato especificado usando FFmpeg.
    
    Args:
        input_file: Ruta del archivo de entrada
        output_file: Ruta del archivo de salida
        output_format: Formato de salida ('mp3' o 'flac')
        ffmpeg_path: Ruta base de FFmpeg
    """
    import subprocess
    import shutil
    
    # Obtener configuración de calidad
    settings = SettingsManager()
    mp3_bitrate = settings.get_mp3_bitrate()
    flac_compression = settings.get_flac_compression()
    
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
            '-i', input_file,
            '-codec:a', 'flac',
            '-compression_level', flac_compression,  # Usar compresión configurada
            output_file
        ]
        logging.info(f"Convirtiendo a FLAC (compresión {flac_compression}): {input_file} -> {output_file}")
    else:
        cmd = [
            ffmpeg_exe,
            '-y',
            '-i', input_file,
            '-codec:a', 'libmp3lame',
            '-b:a', f'{mp3_bitrate}k',  # Usar bitrate configurado
            '-threads', '0',
            output_file
        ]
        logging.info(f"Convirtiendo a MP3 ({mp3_bitrate}kbps): {input_file} -> {output_file}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"Error de FFmpeg: {result.stderr}")
        raise Exception(f"Error convirtiendo a {output_format.upper()}: {result.stderr}")
    
    # Verificar que se creó el archivo
    if os.path.exists(output_file):
        logging.info(f"{output_format.upper()} creado exitosamente: {output_file}")
        # Eliminar archivo original después de convertir
        try:
            os.remove(input_file)
            logging.info(f"Archivo original eliminado: {input_file}")
        except Exception as e:
            logging.warning(f"No se pudo eliminar archivo original: {e}")
    else:
        raise Exception(f"El archivo {output_format.upper()} no se creó")


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
