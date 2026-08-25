"""Utilidades livianas para parsear referencias de Spotify."""

import re
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests


_SHORT_SPOTIFY_HOSTS = {"spotify.link", "spotify.app.link"}


def _is_short_spotify_link(value: str) -> bool:
    """Determina si la URL es un enlace corto de compartido de Spotify."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() in _SHORT_SPOTIFY_HOSTS
    except Exception:
        return False


@lru_cache(maxsize=64)
def _resolve_short_spotify_link(url: str) -> str:
    """Resuelve un enlace corto de Spotify siguiendo redirecciones."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=8)
        if response.url:
            return response.url
    except requests.RequestException:
        pass

    try:
        response = requests.get(url, allow_redirects=True, timeout=8, stream=True)
        final_url = response.url or url
        response.close()
        return final_url
    except requests.RequestException:
        return url


def parse_spotify_reference(id_or_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parsea una referencia de Spotify y devuelve (tipo, id).

    Tipos posibles: track, playlist, album, unknown.
    """
    if not isinstance(id_or_url, str):
        return None, None

    value = id_or_url.strip()
    if not value:
        return None, None

    if _is_short_spotify_link(value):
        value = _resolve_short_spotify_link(value)

    patterns = [
        r"(?:https?://)?(?:open\.)?spotify\.com/(?:intl-[a-zA-Z-]+/)?(playlist|track|album)/([a-zA-Z0-9]{22})",
        r"spotify:(playlist|track|album):([a-zA-Z0-9]{22})",
        r"(playlist|track|album)/([a-zA-Z0-9]{22})",
    ]

    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1), match.group(2)

    # ID base62 sin tipo explícito: debe resolverse por fallback en API.
    if re.fullmatch(r"[a-zA-Z0-9]{22}", value):
        return "unknown", value

    return None, None


def extract_id(link: str) -> str:
    """
    Extrae ID de Spotify preservando tipo cuando está presente.

    Ejemplos:
    - URL track -> track/<id>
    - URL playlist -> playlist/<id>
    - URI spotify -> <tipo>/<id>
    - ID puro -> <id>
    """
    if not isinstance(link, str):
        return link

    spotify_type, spotify_id = parse_spotify_reference(link)
    if not spotify_id:
        return link

    if spotify_type and spotify_type != "unknown":
        return f"{spotify_type}/{spotify_id}"

    return spotify_id
