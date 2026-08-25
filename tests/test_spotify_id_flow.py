import importlib
import sys
import types
import unittest
from unittest.mock import patch

from downloader.spotify_id import extract_id, parse_spotify_reference


PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"
TRACK_ID = "11dFghVXANMlKmJXsNCbNl"


class SpotifyIdParsingTests(unittest.TestCase):
    def test_extract_id_preserves_track_type_from_url(self):
        value = f"https://open.spotify.com/track/{TRACK_ID}?si=test"
        self.assertEqual(extract_id(value), f"track/{TRACK_ID}")

    def test_extract_id_preserves_playlist_type_from_url(self):
        value = f"https://open.spotify.com/playlist/{PLAYLIST_ID}?si=test"
        self.assertEqual(extract_id(value), f"playlist/{PLAYLIST_ID}")

    def test_parse_plain_id_marks_unknown(self):
        spotify_type, spotify_id = parse_spotify_reference(PLAYLIST_ID)
        self.assertEqual(spotify_type, "unknown")
        self.assertEqual(spotify_id, PLAYLIST_ID)

    def test_extract_id_supports_intl_open_spotify_link(self):
        value = f"https://open.spotify.com/intl-es/track/{TRACK_ID}?si=test"
        self.assertEqual(extract_id(value), f"track/{TRACK_ID}")

    @patch(
        "downloader.spotify_id._resolve_short_spotify_link",
        return_value=f"https://open.spotify.com/playlist/{PLAYLIST_ID}?si=abc",
    )
    def test_extract_id_supports_short_shared_link(self, _mock_resolver):
        value = "https://spotify.link/abc123xyz"
        self.assertEqual(extract_id(value), f"playlist/{PLAYLIST_ID}")


class SpotifyRawIdResolutionTests(unittest.TestCase):
    @staticmethod
    def _load_spotify_module_with_stubs():
        fake_spotipy = types.ModuleType("spotipy")
        fake_oauth2 = types.ModuleType("spotipy.oauth2")
        fake_exceptions = types.ModuleType("spotipy.exceptions")

        class FakeSpotifyClient:
            def __init__(self, *args, **kwargs):
                pass

        class FakeSpotifyClientCredentials:
            def __init__(self, *args, **kwargs):
                pass

        class FakeSpotifyException(Exception):
            def __init__(self, http_status, msg=""):
                super().__init__(msg)
                self.http_status = http_status
                self.msg = msg

        fake_spotipy.Spotify = FakeSpotifyClient
        fake_oauth2.SpotifyClientCredentials = FakeSpotifyClientCredentials
        fake_exceptions.SpotifyException = FakeSpotifyException

        with patch.dict(
            sys.modules,
            {
                "spotipy": fake_spotipy,
                "spotipy.oauth2": fake_oauth2,
                "spotipy.exceptions": fake_exceptions,
            },
        ):
            sys.modules.pop("downloader.spotify", None)
            spotify_module = importlib.import_module("downloader.spotify")

        return spotify_module, FakeSpotifyException

    def test_plain_playlist_id_is_resolved_with_fallback(self):
        spotify_module, fake_exception = self._load_spotify_module_with_stubs()

        class FakeClient:
            def __init__(self):
                self.calls = []

            def track(self, spotify_id):
                self.calls.append(("track", spotify_id))
                raise fake_exception(404, "track not found")

            def playlist(self, spotify_id):
                self.calls.append(("playlist", spotify_id))
                return {
                    "id": spotify_id,
                    "name": "Mi Playlist",
                    "tracks": {"items": [{"track": {"name": "Cancion A"}}], "next": None},
                }

            def album(self, spotify_id):
                self.calls.append(("album", spotify_id))
                raise fake_exception(404, "album not found")

            def next(self, tracks):
                self.calls.append(("next", None))
                return {"items": [], "next": None}

        fake_client = FakeClient()

        with patch.object(spotify_module, "get_spotify_client", return_value=fake_client):
            item = spotify_module.get_spotify_item(PLAYLIST_ID)

        self.assertIsNotNone(item)
        self.assertEqual(item["__type"], "playlist")
        self.assertEqual(item["name"], "Mi Playlist")
        self.assertEqual(fake_client.calls[:2], [("track", PLAYLIST_ID), ("playlist", PLAYLIST_ID)])

    def test_plain_track_id_stays_track(self):
        spotify_module, _ = self._load_spotify_module_with_stubs()

        class FakeClient:
            def __init__(self):
                self.calls = []

            def track(self, spotify_id):
                self.calls.append(("track", spotify_id))
                return {"id": spotify_id, "name": "Track A"}

            def playlist(self, spotify_id):
                raise AssertionError("No debe consultar playlist cuando el track existe")

            def album(self, spotify_id):
                raise AssertionError("No debe consultar album cuando el track existe")

        fake_client = FakeClient()

        with patch.object(spotify_module, "get_spotify_client", return_value=fake_client):
            item = spotify_module.get_spotify_item(TRACK_ID)

        self.assertIsNotNone(item)
        self.assertEqual(item["__type"], "track")
        self.assertEqual(fake_client.calls, [("track", TRACK_ID)])


if __name__ == "__main__":
    unittest.main()
