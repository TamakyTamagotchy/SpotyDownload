from ytmusicapi import YTMusic
import logging
from fuzzywuzzy import fuzz

class YouTubeMusicSearcher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YouTubeMusicSearcher, cls).__new__(cls)
            cls._instance.ytmusic = YTMusic()
        return cls._instance

    def search_track(self, title, artist, album=None, duration=None):
        """
        Busca una canción en YouTube Music y devuelve el mejor resultado (Video ID).
        Prioriza coincidencias de título, artista y duración.
        """
        try:
            # Normalizar artista a string si es una lista
            if isinstance(artist, list):
                artist_str = ", ".join(artist)
            else:
                artist_str = artist
            
            query = f"{title} {artist_str}"
            logging.info(f"Buscando en YT Music: {query}")
            
            # Buscar en la categoría de canciones para filtrar videos de usuarios
            results = self.ytmusic.search(query, filter="songs")
            
            if not results:
                # Fallback: búsqueda general si no hay resultados en canciones
                results = self.ytmusic.search(query)

            if not results:
                return None

            best_match = None
            highest_score = 0

            for result in results:
                # Calcular puntaje de similitud
                score = 0
                
                # 1. Similitud de título (40%)
                res_title = result.get('title', '')
                title_score = fuzz.partial_ratio(title.lower(), res_title.lower())
                score += title_score * 0.4

                # 2. Similitud de artista (40%)
                res_artists = " ".join([a['name'] for a in result.get('artists', [])])
                artist_score = fuzz.partial_ratio(artist_str.lower(), res_artists.lower())
                score += artist_score * 0.4

                # 3. Similitud de álbum (10%) - si está disponible
                if album and 'album' in result:
                    res_album = result['album'].get('name', '')
                    album_score = fuzz.partial_ratio(album.lower(), res_album.lower())
                    score += album_score * 0.1
                
                # 4. Duración (10%) - si está disponible (no implementado aquí por simplicidad, pero recomendado)
                
                # Penalizar versiones en vivo, remix, karaoke si no se pidieron
                lower_title = res_title.lower()
                if any(x in lower_title for x in ['live', 'vivo', 'concert', 'karaoke', 'instrumental']) and \
                   not any(x in title.lower() for x in ['live', 'vivo', 'concert', 'karaoke', 'instrumental']):
                    score -= 20

                if score > highest_score:
                    highest_score = score
                    best_match = result

            if best_match and highest_score > 60: # Umbral mínimo de confianza
                video_id = best_match['videoId']
                logging.info(f"Mejor coincidencia: {best_match['title']} ({highest_score}%) - ID: {video_id}")
                return f"https://music.youtube.com/watch?v={video_id}"
            
            logging.warning(f"No se encontró coincidencia confiable para: {title} - {artist_str}")
            return None

        except Exception as e:
            logging.error(f"Error en búsqueda avanzada YT Music: {e}")
            return None

def search_youtube_music(title, artist, album=None):
    """
    Wrapper compatible con la implementación anterior
    """
    # Normalizar artista a string si es una lista
    if isinstance(artist, list):
        artist_str = ", ".join(artist)
    else:
        artist_str = artist
    
    searcher = YouTubeMusicSearcher()
    result = searcher.search_track(title, artist_str, album)
    
    if result:
        return result
    
    # Fallback al método antiguo si falla la API o no encuentra nada
    logging.info("Usando fallback a búsqueda simple de yt-dlp")
    query = f'{title} {artist_str}'
    return f"ytsearch1:{query}"
