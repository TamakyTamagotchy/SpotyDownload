"""
Obtiene metadatos públicos de Spotify (track / album / playlist) sin usar
la API oficial: sin client_id, sin client_secret, sin archivo de credenciales.

Usa la librería 'spotifyscraper' (pip install spotifyscraper), que replica
las llamadas internas que hace el propio reproductor web de Spotify y se
mantiene activamente (pruebas diarias contra Spotify en vivo), por lo que
es mucho más resistente a cambios que un scraper casero del HTML.
"""
import logging
from typing import Any, Dict, List, Optional

from spotify_scraper import SpotifyClient, SpotifyScraperError

from .spotify_id import parse_spotify_reference

logger = logging.getLogger(__name__)


def _artist_list(artists) -> List[Dict[str, str]]:
    return [{"name": a.get("name", "")} for a in (artists or [])]


def _images(images) -> List[Dict[str, Any]]:
    return [{"url": img.get("url")} for img in (images or []) if img.get("url")]


def _track_to_legacy(track: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte el dict de spotifyscraper.Track a la forma que ya
    consume el resto de la app (compatible con lo que devolvía spotipy)."""
    album = track.get("album")
    album_legacy = None
    if album:
        album_legacy = {
            "name": album.get("name", ""),
            "images": _images(album.get("images")),
            "release_date": (track.get("release_date") or "")[:10],
        }
    return {
        "id": track.get("id"),
        "name": track.get("name", ""),
        "artists": _artist_list(track.get("artists")),
        "album": album_legacy,
        "duration_ms": track.get("duration_ms", 0),
        "__type": "track",
    }


def _album_to_legacy(album: Dict[str, Any]) -> Dict[str, Any]:
    tracks = [_track_to_legacy(t) for t in album.get("tracks", [])]
    return {
        "id": album.get("id"),
        "name": album.get("name", ""),
        "artists": _artist_list(album.get("artists")),
        "images": _images(album.get("images")),
        "release_date": (album.get("release_date") or "")[:10],
        "tracks": {"items": tracks, "total": len(tracks)},
        "__type": "album",
    }


def _playlist_to_legacy(playlist: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for entry in playlist.get("tracks", []):
        track = entry.get("track") if isinstance(entry, dict) else None
        if track:
            items.append({"track": _track_to_legacy(track)})

    owner = playlist.get("owner") or {}
    return {
        "id": playlist.get("id"),
        "name": playlist.get("name", ""),
        "owner": {"display_name": owner.get("name", "Desconocido")},
        "images": _images(playlist.get("images")),
        "tracks": {"items": items, "total": len(items)},
        "__type": "playlist",
    }


def get_spotify_item_public(id_or_url: str) -> Optional[Dict[str, Any]]:
    """
    Reemplazo de spotify.get_spotify_item() que no requiere client_id/client_secret.
    Soporta track, album y playlist (con paginación COMPLETA de pistas,
    no solo la vista previa).
    """
    tipo, real_id = parse_spotify_reference(id_or_url)
    if not real_id:
        logger.error(f"No se pudo parsear la URL/ID de Spotify: {id_or_url}")
        return None

    candidatos = ["track", "album", "playlist"] if tipo in (None, "unknown") else [tipo]

    try:
        with SpotifyClient() as client:
            for candidate_type in candidatos:
                try:
                    if candidate_type == "track":
                        track = client.get_track(real_id)
                        return _track_to_legacy(track.to_dict())
                    elif candidate_type == "album":
                        album = client.get_album(real_id)
                        return _album_to_legacy(album.to_dict())
                    elif candidate_type == "playlist":
                        playlist = client.get_playlist(real_id, max_tracks=None)
                        return _playlist_to_legacy(playlist.to_dict())
                except SpotifyScraperError as e:
                    logger.debug(f"{candidate_type} no coincide para {real_id}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error obteniendo datos públicos de Spotify: {e}")
        return None

    logger.error(f"No se pudo obtener información pública de Spotify para: {id_or_url}")
    return None