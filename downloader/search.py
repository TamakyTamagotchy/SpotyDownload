import logging
from .youtube import search_youtube_music

def search_song(title, artist, album=None):
    """
    Función de búsqueda que delega en el módulo youtube mejorado
    """
    try:
        logging.info(f'Iniciando búsqueda para: {title} - {artist}')
        return search_youtube_music(title, artist, album)
        
    except Exception as e:
        logging.error(f'Error en búsqueda: {e}')
        return None
