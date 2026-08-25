"""
Módulo de integración con Spotify API usando spotipy.

Este módulo proporciona funcionalidades para obtener información de tracks,
álbumes y playlists desde Spotify usando la API oficial.

Requiere credenciales válidas en spotify_credentials.json:
    - client_id: ID de la aplicación de Spotify
    - client_secret: Secret de la aplicación
    - genius_api_token: Token de Genius API (opcional)
"""

import spotipy, os, logging, json
from typing import Optional, Dict, Any, Union
from functools import lru_cache
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
from .spotify_id import parse_spotify_reference

# Configuración de logging
logger = logging.getLogger(__name__)

# Obtener la ruta del directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(script_dir, 'spotify_credentials.json')


class SpotifyClientManager:
    """
    Gestor singleton para el cliente de Spotify con manejo mejorado de credenciales
    y reconexión automática.
    """
    _instance: Optional['SpotifyClientManager'] = None
    _client: Optional[spotipy.Spotify] = None
    
    def __new__(cls) -> 'SpotifyClientManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Inicializa el cliente de Spotify."""
        self._credentials: Dict[str, str] = {}
        self._load_credentials()
        self._create_client()
    
    def _load_credentials(self) -> None:
        """Carga las credenciales desde el archivo JSON."""
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                self._credentials = json.load(f)
                
            required_keys = ['client_id', 'client_secret']
            for key in required_keys:
                if key not in self._credentials or not self._credentials[key]:
                    raise ValueError(f"Credencial requerida faltante: {key}")
                    
            logger.info("Credenciales de Spotify cargadas correctamente")
            
        except FileNotFoundError:
            logger.error(f"Archivo de credenciales no encontrado: {credentials_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear credenciales JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            raise
    
    def _create_client(self) -> None:
        """Crea el cliente de Spotify con las credenciales cargadas."""
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=self._credentials['client_id'],
                client_secret=self._credentials['client_secret']
            )
            
            # Configurar cliente con timeouts y reintentos
            self._client = spotipy.Spotify(
                auth_manager=auth_manager,
                requests_timeout=10,
                retries=3,
                status_retries=3,
                backoff_factor=0.3
            )
            
            logger.info("Cliente de Spotify inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error al crear cliente de Spotify: {e}")
            raise
    
    @property
    def client(self) -> spotipy.Spotify:
        """Retorna el cliente de Spotify, reconectando si es necesario."""
        if self._client is None:
            self._create_client()
        return self._client
    
    @property
    def genius_token(self) -> Optional[str]:
        """Retorna el token de Genius API si está disponible."""
        return self._credentials.get('genius_api_token')
    
    def reconnect(self) -> None:
        """Fuerza una reconexión del cliente."""
        logger.info("Reconectando cliente de Spotify...")
        self._client = None
        self._create_client()


# Instancia global del gestor (lazy initialization)
_client_manager: Optional[SpotifyClientManager] = None


def get_spotify_client() -> spotipy.Spotify:
    """Obtiene el cliente de Spotify singleton."""
    global _client_manager
    if _client_manager is None:
        _client_manager = SpotifyClientManager()
    return _client_manager.client


# Compatibilidad con código existente
try:
    sp = get_spotify_client()
    GENIUS_API_TOKEN = _client_manager.genius_token if _client_manager else None
except Exception as e:
    logger.warning(f"No se pudo inicializar cliente de Spotify al importar: {e}")
    sp = None
    GENIUS_API_TOKEN = None


@lru_cache(maxsize=128)
def _parse_spotify_url(id_or_url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parsea una URL o ID de Spotify y retorna el tipo y el ID.
    
    Args:
        id_or_url: URL de Spotify o ID directo
        
    Returns:
        Tupla (tipo, id) donde tipo puede ser 'playlist', 'album' o 'track'
    """
    return parse_spotify_reference(id_or_url)


def _fetch_playlist_with_all_tracks(client: spotipy.Spotify, playlist_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene una playlist y pagina todas sus canciones."""
    obj = client.playlist(playlist_id)
    if obj and 'tracks' in obj:
        tracks = obj['tracks']
        while tracks.get('next'):
            more_tracks = client.next(tracks)
            tracks['items'].extend(more_tracks['items'])
            tracks['next'] = more_tracks.get('next')
    return obj


def _fetch_object_by_type(client: spotipy.Spotify, tipo: str, real_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un objeto de Spotify según tipo."""
    if tipo == "playlist":
        return _fetch_playlist_with_all_tracks(client, real_id)
    if tipo == "album":
        return client.album(real_id)
    if tipo == "track":
        return client.track(real_id)
    return None


def get_spotify_item(id_or_url: Union[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Obtiene un objeto de Spotify (playlist, album o track) según el tipo de ID o URL.
    
    Args:
        id_or_url: URL de Spotify, URI o ID directo
        
    Returns:
        Diccionario con la información del ítem y '__type' indicando el tipo,
        o None si no se encuentra
    """
    client = get_spotify_client()
    if client is None:
        logger.error("Cliente de Spotify no disponible")
        return None
    
    try:
        tipo = None
        real_id = None
        
        if isinstance(id_or_url, str):
            tipo, real_id = _parse_spotify_url(id_or_url)
            
            if not tipo or not real_id:
                logger.error(f"No se pudo parsear la URL/ID de Spotify: {id_or_url}")
                return None
        else:
            logger.error(f"Tipo de entrada no válido: {type(id_or_url)}")
            return None

        obj = None
        resolved_type = tipo

        # Un ID base62 de 22 caracteres no contiene tipo. Intentar resolverlo.
        if tipo == "unknown":
            for candidate_type in ("track", "playlist", "album"):
                try:
                    candidate_obj = _fetch_object_by_type(client, candidate_type, real_id)
                    if candidate_obj is not None:
                        obj = candidate_obj
                        resolved_type = candidate_type
                        logger.info(f"ID {real_id} resuelto como {candidate_type}")
                        break
                except SpotifyException as candidate_error:
                    if candidate_error.http_status == 404:
                        continue
                    raise
        else:
            obj = _fetch_object_by_type(client, tipo, real_id)

        if resolved_type not in ("playlist", "album", "track"):
            logger.error(f"Tipo de Spotify no soportado: {resolved_type}")
            return None

        if obj is not None:
            obj['__type'] = resolved_type
            return obj
        else:
            logger.error(f"No se pudo obtener el objeto de Spotify para: {id_or_url}")
            return None
            
    except SpotifyException as e:
        if e.http_status == 404:
            logger.error(f"Ítem de Spotify no encontrado: {id_or_url}")
        elif e.http_status == 401:
            logger.error("Error de autenticación con Spotify. Verificar credenciales.")
        elif e.http_status == 429:
            logger.warning("Rate limit de Spotify alcanzado. Esperando...")
        else:
            logger.error(f"Error de Spotify API ({e.http_status}): {e.msg}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al obtener ítem de Spotify: {e}")
        return None

