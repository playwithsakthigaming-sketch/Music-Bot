import re
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


TRACK_RE = re.compile(
    r"https?://open\.spotify\.com/track/([A-Za-z0-9]+)"
)

ALBUM_RE = re.compile(
    r"https?://open\.spotify\.com/album/([A-Za-z0-9]+)"
)

PLAYLIST_RE = re.compile(
    r"https?://open\.spotify\.com/playlist/([A-Za-z0-9]+)"
)


class SpotifyManager:
    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
    ):
        self.client = None

        if not client_id or not client_secret:
            return

        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )

        self.client = spotipy.Spotify(
            auth_manager=auth_manager
        )

    @property
    def configured(self) -> bool:
        return self.client is not None

    @staticmethod
    def is_spotify_url(url: str) -> bool:
        return any(
            regex.match(url.strip())
            for regex in (
                TRACK_RE,
                ALBUM_RE,
                PLAYLIST_RE,
            )
        )

    def parse_url(self, url: str):
        url = url.strip()

        match = TRACK_RE.match(url)
        if match:
            return "track", match.group(1)

        match = ALBUM_RE.match(url)
        if match:
            return "album", match.group(1)

        match = PLAYLIST_RE.match(url)
        if match:
            return "playlist", match.group(1)

        return None, None

    @staticmethod
    def clean_track(track, album_name=None):
        if not track:
            return None

        if track.get("is_local"):
            return None

        artists = ", ".join(
            artist["name"]
            for artist in track.get("artists", [])
        )

        if not artists:
            artists = "Unknown Artist"

        title = track.get(
            "name",
            "Unknown Track",
        )

        album = album_name or (
            track.get("album", {}).get(
                "name",
                "Unknown Album",
            )
        )

        duration_ms = track.get(
            "duration_ms",
            0,
        )

        external_urls = track.get(
            "external_urls",
            {},
        )

        return {
            "title": title,
            "artist": artists,
            "album": album,
            "duration": duration_ms // 1000,
            "query": f"{title} {artists}",
            "spotify_url": external_urls.get(
                "spotify"
            ),
        }

    def get_track(self, track_id: str):
        if not self.client:
            raise RuntimeError(
                "Spotify is not configured."
            )

        track = self.client.track(track_id)

        result = self.clean_track(track)

        if not result:
            raise RuntimeError(
                "This Spotify track is unavailable."
            )

        return result

    def get_album_tracks(
        self,
        album_id: str,
    ) -> list[dict]:

        if not self.client:
            raise RuntimeError(
                "Spotify is not configured."
            )

        album = self.client.album(album_id)

        album_name = album.get(
            "name",
            "Unknown Album",
        )

        result = []

        tracks = album["tracks"]

        while True:
            for track in tracks["items"]:
                cleaned = self.clean_track(
                    track,
                    album_name,
                )

                if cleaned:
                    result.append(cleaned)

            if not tracks.get("next"):
                break

            tracks = self.client.next(tracks)

        return result

    def get_playlist_tracks(
        self,
        playlist_id: str,
    ) -> list[dict]:

        if not self.client:
            raise RuntimeError(
                "Spotify is not configured."
            )

        result = []

        tracks = self.client.playlist_items(
            playlist_id,
            additional_types=("track",),
        )

        while True:
            for item in tracks["items"]:
                track = item.get("track")

                cleaned = self.clean_track(track)

                if cleaned:
                    result.append(cleaned)

            if not tracks.get("next"):
                break

            tracks = self.client.next(tracks)

        return result

    def resolve(
        self,
        url: str,
    ) -> tuple[str, list[dict]]:

        content_type, content_id = (
            self.parse_url(url)
        )

        if not content_type:
            raise ValueError(
                "Invalid Spotify URL."
            )

        if content_type == "track":
            return (
                "track",
                [self.get_track(content_id)],
            )

        if content_type == "album":
            return (
                "album",
                self.get_album_tracks(content_id),
            )

        if content_type == "playlist":
            return (
                "playlist",
                self.get_playlist_tracks(
                    content_id
                ),
            )

        raise ValueError(
            "Unsupported Spotify URL."
      )
