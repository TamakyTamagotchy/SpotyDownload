from ytmusicapi import YTMusic
import logging
# Usar rapidfuzz en lugar de fuzzywuzzy (10x más rápido y sin dependencia de python-Levenshtein)
try:
    from rapidfuzz import fuzz
except ImportError:
    # Fallback a fuzzywuzzy si rapidfuzz no está disponible
    from fuzzywuzzy import fuzz
    logging.warning("rapidfuzz no instalado, usando fuzzywuzzy como fallback (más lento)")

class YouTubeMusicSearcher:
    """
    Singleton para buscar canciones en YouTube Music con algoritmo de coincidencia mejorado.
    
    Utiliza ytmusicapi para búsquedas y rapidfuzz para comparación de strings.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YouTubeMusicSearcher, cls).__new__(cls)
            cls._instance.ytmusic = YTMusic()
            cls._instance._search_cache = {}  # Cache de búsquedas recientes
        return cls._instance

    def search_track(self, title: str, artist: str, album: str = None, duration: int = None) -> str | None:
        """
        Busca una canción en YouTube Music y devuelve el mejor resultado (Video ID).
        Prioriza coincidencias de título, artista y duración.
        
        Args:
            title: Título de la canción
            artist: Artista o lista de artistas
            album: Álbum (opcional)
            duration: Duración en segundos (opcional, para mejor matching)
            
        Returns:
            URL de YouTube Music o None si no se encuentra coincidencia confiable
        """
        try:
            # Normalizar artista a string si es una lista
            if isinstance(artist, list):
                artist_str = ", ".join(artist)
            else:
                artist_str = artist
            
            # Crear clave de cache
            cache_key = f"{title}|{artist_str}|{album or ''}"
            if cache_key in self._search_cache:
                logging.debug(f"Cache hit para: {cache_key}")
                return self._search_cache[cache_key]
            
            query = f"{title} {artist_str}"
            logging.info(f"Buscando en YT Music: {query}")
            
            # Buscar en la categoría de canciones para filtrar videos de usuarios
            results = self.ytmusic.search(query, filter="songs", limit=15)
            
            if not results:
                # Fallback: búsqueda general si no hay resultados en canciones
                results = self.ytmusic.search(query, limit=10)

            if not results:
                return None

            best_match = None
            highest_score = 0

            for result in results:
                # Calcular puntaje de similitud
                score = 0
                
                # 1. Similitud de título (40%) - usando token_sort_ratio para mejor matching
                res_title = result.get('title', '')
                title_score = fuzz.token_sort_ratio(title.lower(), res_title.lower())
                score += title_score * 0.4

                # 2. Similitud de artista (40%)
                res_artists = " ".join([a['name'] for a in result.get('artists', [])])
                artist_score = fuzz.token_sort_ratio(artist_str.lower(), res_artists.lower())
                score += artist_score * 0.4

                # 3. Similitud de álbum (10%) - si está disponible
                if album and 'album' in result and result['album']:
                    res_album = result['album'].get('name', '')
                    album_score = fuzz.token_sort_ratio(album.lower(), res_album.lower())
                    score += album_score * 0.1
                
                # 4. Duración (10%) - si está disponible
                if duration and 'duration_seconds' in result:
                    res_duration = result.get('duration_seconds', 0)
                    if res_duration > 0:
                        # Tolerancia de 5 segundos
                        duration_diff = abs(duration - res_duration)
                        if duration_diff <= 5:
                            score += 10
                        elif duration_diff <= 15:
                            score += 5
                
                # Penalizar versiones en vivo, remix, karaoke si no se pidieron
                lower_title = res_title.lower()
                original_lower = title.lower()
                penalize_keywords = ['live', 'vivo', 'concert', 'karaoke', 'instrumental', 'cover', 'acoustic', 'remix']
                
                for keyword in penalize_keywords:
                    if keyword in lower_title and keyword not in original_lower:
                        score -= 15
                        break

                if score > highest_score:
                    highest_score = score
                    best_match = result

            if best_match and highest_score > 55:  # Umbral mínimo de confianza
                video_id = best_match['videoId']
                result_url = f"https://music.youtube.com/watch?v={video_id}"
                logging.info(f"Mejor coincidencia: {best_match['title']} ({highest_score:.1f}%) - ID: {video_id}")
                
                # Guardar en cache
                self._search_cache[cache_key] = result_url
                return result_url
            
            logging.warning(f"No se encontró coincidencia confiable para: {title} - {artist_str}")
            return None

        except Exception as e:
            logging.error(f"Error en búsqueda avanzada YT Music: {e}")
            return None
    
    def clear_cache(self):
        """Limpia el cache de búsquedas."""
        self._search_cache.clear()
        logging.info("Cache de búsquedas limpiado")

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
