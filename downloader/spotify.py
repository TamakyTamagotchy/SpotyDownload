import spotipy, os, re, logging, json
from spotipy.oauth2 import SpotifyClientCredentials

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

def get_spotify_item(id_or_url):
    """
    Obtiene un objeto de Spotify (playlist, album o track) según el tipo de ID o URL.
    """
    try:
        tipo = None
        real_id = None
        if isinstance(id_or_url, str):
            match = re.search(r"(playlist|track|album)/([a-zA-Z0-9]+)", id_or_url)
            if match:
                tipo, real_id = match.group(1), match.group(2)
            else:
                tipo = "track" if len(id_or_url) == 22 else None
                real_id = id_or_url
        else:
            tipo = None
            real_id = id_or_url

        obj = None
        if tipo == "playlist":
            obj = sp.playlist(real_id)
        elif tipo == "album":
            obj = sp.album(real_id)
        elif tipo == "track":
            obj = sp.track(real_id)
        else:
            logging.error(f'No se pudo determinar el tipo de Spotify ID: {id_or_url}')
            return None

        if obj is not None:
            obj['__type'] = tipo
            return obj
        else:
            logging.error(f'No se pudo obtener el objeto de Spotify para: {id_or_url}')
            return None
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 404:
            logging.error(f'Ítem no encontrado: {e}')
        else:
            logging.error(f'No se pudo obtener el ítem de Spotify: {e}')
        return None
    except Exception as e:
        logging.error(f'Error inesperado al obtener el ítem de Spotify: {e}')
        return None
