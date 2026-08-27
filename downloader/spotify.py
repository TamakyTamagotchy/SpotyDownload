"""
Módulo de obtención de información de Spotify SIN la API oficial.
Usa spotify_public.py (scraping vía spotifyscraper, sin credenciales).
"""
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def get_spotify_item(id_or_url: Union[str, Any]) -> Optional[Dict[str, Any]]:
    from .spotify_public import get_spotify_item_public  # import diferido: evita ciclos

    if not isinstance(id_or_url, str):
        logger.error(f"Tipo de entrada no válido: {type(id_or_url)}")
        return None
    return get_spotify_item_public(id_or_url)