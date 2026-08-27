"""
Módulo de gestión de metadatos de audio.

Utiliza mutagen para soporte multiplataforma de metadatos (MP3, FLAC, etc.)
con fallback a eyed3 para compatibilidad legacy.

Características:
    - Soporte para MP3 (ID3v2.3/2.4) y FLAC
    - Detección automática de formato de imagen para portadas
    - Manejo robusto de codificación UTF-8
    - Cache de imágenes descargadas
"""

import os, re, logging, requests
from io import BytesIO
from typing import Optional, List, Union
from functools import lru_cache
from PIL import Image, UnidentifiedImageError

# Intentar usar mutagen primero (más moderno y versátil)
try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, APIC, ID3NoHeaderError
    from mutagen.flac import FLAC, Picture
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logging.warning("mutagen no disponible, usando eyed3 como fallback")

# Fallback a eyed3
try:
    import eyed3
    EYED3_AVAILABLE = True
except ImportError:
    EYED3_AVAILABLE = False
    if not MUTAGEN_AVAILABLE:
        logging.error("Ni mutagen ni eyed3 están disponibles para metadatos")

# Configuración de logging
logger = logging.getLogger(__name__)

# Mapeo de formatos de imagen a MIME types
FORMAT_TO_MIME = {
    'JPEG': 'image/jpeg',
    'JPG': 'image/jpeg',
    'PNG': 'image/png',
    'GIF': 'image/gif',
    'BMP': 'image/bmp',
    'WEBP': 'image/webp',
}

# Cache de sesión HTTP para reutilizar conexiones
_http_session: Optional[requests.Session] = None


def _get_http_session() -> requests.Session:
    """Obtiene una sesión HTTP reutilizable."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({
            'User-Agent': 'MusicBlast/1.0'
        })
    return _http_session


@lru_cache(maxsize=64)
def _download_cover_image(url: str) -> Optional[tuple[bytes, str]]:
    """
    Descarga y valida una imagen de portada con cache.
    
    Args:
        url: URL de la imagen
        
    Returns:
        Tupla (contenido_bytes, mime_type) o None si falla
    """
    try:
        session = _get_http_session()
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        image_content = response.content
        if len(image_content) < 100:
            logger.warning(f"Imagen demasiado pequeña: {len(image_content)} bytes")
            return None
        
        # Detectar formato usando Pillow
        mime = "image/jpeg"  # Default
        try:
            with Image.open(BytesIO(image_content)) as img:
                img.verify()  # Verificar integridad
                mime = FORMAT_TO_MIME.get(img.format, 'image/jpeg')
                logger.debug(f"Formato detectado: {img.format}, MIME: {mime}")
        except (UnidentifiedImageError, Exception) as e:
            logger.warning(f"No se pudo verificar imagen, usando JPEG: {e}")
        
        return image_content, mime
        
    except requests.RequestException as e:
        logger.error(f"Error descargando portada desde {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado procesando portada: {e}")
        return None


def _normalize_artist(artist: Union[str, List[str], None]) -> str:
    """Normaliza el campo de artista a string."""
    if artist is None:
        return "Artista Desconocido"
    if isinstance(artist, list):
        return ", ".join(filter(None, artist))
    return str(artist).strip() or "Artista Desconocido"


def _extract_year(release_date: Optional[str]) -> Optional[int]:
    """Extrae el año de una fecha de lanzamiento."""
    if not release_date:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', str(release_date))
    return int(match.group()) if match else None


def update_mp3_metadata_mutagen(
    filename: str,
    title: str,
    artist: Union[str, List[str]],
    album: str,
    cover_image_url: Optional[str],
    release_date: Optional[str],
    genre: Optional[str]
) -> bool:
    """
    Actualiza metadatos MP3 usando mutagen (recomendado).
    
    Args:
        filename: Ruta del archivo MP3
        title: Título de la canción
        artist: Artista o lista de artistas
        album: Nombre del álbum
        cover_image_url: URL de la imagen de portada
        release_date: Fecha de lanzamiento (se extrae el año)
        genre: Género musical
        
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    if not MUTAGEN_AVAILABLE:
        logger.warning("mutagen no disponible")
        return False
    
    try:
        if not os.path.exists(filename):
            logger.error(f"Archivo no encontrado: {filename}")
            return False
        
        # Cargar o crear tags ID3
        try:
            audio = ID3(filename)
        except ID3NoHeaderError:
            audio = ID3()
        
        artist_str = _normalize_artist(artist)
        
        # Metadatos de texto con codificación UTF-8 (encoding=3)
        audio.delall('TIT2')
        audio.add(TIT2(encoding=3, text=title or "Titulo Desconocido"))
        
        audio.delall('TPE1')
        audio.add(TPE1(encoding=3, text=artist_str))
        
        audio.delall('TALB')
        audio.add(TALB(encoding=3, text=album or "Album Desconocido"))
        
        # Artista del álbum (para múltiples artistas)
        if ', ' in artist_str:
            artists_list = [a.strip() for a in artist_str.split(', ')]
            audio.delall('TPE2')
            audio.add(TPE2(encoding=3, text=artist_str))
            # Actualizar artista principal al primero
            audio.delall('TPE1')
            audio.add(TPE1(encoding=3, text=artists_list[0]))
        
        # Año
        year = _extract_year(release_date)
        if year:
            audio.delall('TDRC')
            audio.add(TDRC(encoding=3, text=str(year)))
            logger.info(f"Año establecido: {year}")
        
        # Género
        if genre and isinstance(genre, str) and genre.strip():
            audio.delall('TCON')
            audio.add(TCON(encoding=3, text=genre.strip()))
            logger.info(f"Género establecido: {genre.strip()}")
        
        # Portada
        if cover_image_url:
            cover_data = _download_cover_image(cover_image_url)
            if cover_data:
                image_content, mime = cover_data
                # Eliminar portadas existentes
                audio.delall('APIC')
                # Agregar nueva portada (tipo 3 = front cover)
                audio.add(APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # Front cover
                    desc='Cover',
                    data=image_content
                ))
                logger.info(f"Portada aplicada ({len(image_content)} bytes, {mime})")
        
        # Guardar con ID3v2.3 para máxima compatibilidad
        audio.save(filename, v2_version=3)
        logger.info(f"Metadatos guardados: {title} - {artist_str}")
        return True
        
    except Exception as e:
        logger.error(f"Error actualizando metadatos con mutagen: {e}")
        return False


def update_flac_metadata(
    filename: str,
    title: str,
    artist: Union[str, List[str]],
    album: str,
    cover_image_url: Optional[str],
    release_date: Optional[str],
    genre: Optional[str]
) -> bool:
    """
    Actualiza metadatos FLAC usando mutagen.
    
    Args:
        filename: Ruta del archivo FLAC
        title: Título de la canción
        artist: Artista o lista de artistas
        album: Nombre del álbum
        cover_image_url: URL de la imagen de portada
        release_date: Fecha de lanzamiento
        genre: Género musical
        
    Returns:
        True si se actualizó correctamente
    """
    if not MUTAGEN_AVAILABLE:
        logger.warning("mutagen no disponible para FLAC")
        return False
    
    try:
        if not os.path.exists(filename):
            logger.error(f"Archivo FLAC no encontrado: {filename}")
            return False
        
        audio = FLAC(filename)
        artist_str = _normalize_artist(artist)
        
        # Metadatos Vorbis Comment
        audio['title'] = title or "Titulo Desconocido"
        audio['artist'] = artist_str
        audio['album'] = album or "Album Desconocido"
        
        if ', ' in artist_str:
            audio['albumartist'] = artist_str
        
        year = _extract_year(release_date)
        if year:
            audio['date'] = str(year)
        
        if genre and genre.strip():
            audio['genre'] = genre.strip()
        
        # Portada para FLAC
        if cover_image_url:
            cover_data = _download_cover_image(cover_image_url)
            if cover_data:
                image_content, mime = cover_data
                picture = Picture()
                picture.type = 3  # Front cover
                picture.mime = mime
                picture.desc = 'Cover'
                picture.data = image_content
                
                # Obtener dimensiones
                try:
                    with Image.open(BytesIO(image_content)) as img:
                        picture.width, picture.height = img.size
                        picture.depth = 24  # Asumir 24-bit
                except Exception:
                    pass
                
                audio.clear_pictures()
                audio.add_picture(picture)
                logger.info(f"Portada FLAC aplicada ({len(image_content)} bytes)")
        
        audio.save()
        logger.info(f"Metadatos FLAC guardados: {title} - {artist_str}")
        return True
        
    except Exception as e:
        logger.error(f"Error actualizando metadatos FLAC: {e}")
        return False


def update_mp3_metadata(
    filename: str,
    title: str,
    artist: Union[str, List[str]],
    album: str,
    cover_image_url: Optional[str],
    release_date: Optional[str],
    genre: Optional[str] = None
) -> bool:
    """
    Función principal para actualizar metadatos MP3.
    Usa mutagen si está disponible, sino eyed3 como fallback.
    
    Args:
        filename: Ruta del archivo MP3
        title: Título de la canción
        artist: Artista o lista de artistas
        album: Nombre del álbum
        cover_image_url: URL de la imagen de portada
        release_date: Fecha de lanzamiento
        genre: Género musical (opcional)
        
    Returns:
        True si se actualizó correctamente
    """
    # Intentar con mutagen primero
    if MUTAGEN_AVAILABLE:
        result = update_mp3_metadata_mutagen(
            filename, title, artist, album, cover_image_url, release_date, genre
        )
        if result:
            return True
        logger.warning("Fallback a eyed3 después de error con mutagen")
    
    # Fallback a eyed3
    if EYED3_AVAILABLE:
        return _update_mp3_metadata_eyed3(
            filename, title, artist, album, cover_image_url, release_date, genre
        )
    
    logger.error("No hay biblioteca disponible para actualizar metadatos")
    return False


def _update_mp3_metadata_eyed3(
    filename: str,
    title: str,
    artist: Union[str, List[str]],
    album: str,
    cover_image_url: Optional[str],
    release_date: Optional[str],
    genre: Optional[str]
) -> bool:
    """Implementación legacy usando eyed3."""
    try:
        if not os.path.exists(filename):
            logger.error(f'Archivo no encontrado: {filename}')
            return False
        
        audio = eyed3.load(filename)
        if audio is None:
            logger.error(f'No se pudo cargar el archivo: {filename}')
            return False
        
        if audio.tag is None:
            audio.initTag()
        
        artist_str = _normalize_artist(artist)
        
        audio.tag.title = title or "Titulo Desconocido"
        audio.tag.artist = artist_str
        audio.tag.album = album or "Album Desconocido"
        
        if ', ' in artist_str:
            artists_list = [a.strip() for a in artist_str.split(', ')]
            audio.tag.artist = artists_list[0]
            audio.tag.album_artist = artist_str
        
        year = _extract_year(release_date)
        if year:
            audio.tag.recording_date = year
        
        if genre and genre.strip():
            audio.tag.genre = genre.strip()
        
        if cover_image_url:
            cover_data = _download_cover_image(cover_image_url)
            if cover_data:
                image_content, mime = cover_data
                audio.tag.images.set(3, image_content, mime, "Cover")
        
        audio.tag.save(version=(2, 3, 0))
        return True
        
    except Exception as e:
        logger.error(f'Error con eyed3: {e}')
        return False

