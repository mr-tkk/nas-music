from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx

from nasmusic.downloaders import BaseDownloader
from nasmusic.core.models import SearchResult, DownloadResult, TrackMetadata
from nasmusic.utils import safe_filename


class NeteaseDownloader(BaseDownloader):
    """NetEase Cloud Music downloader using direct HTTP API (no pyncm dependency)."""

    source_name = "netease"

    BASE_URL = "https://music.163.com"
    API_URL = "https://music.163.com/api"

    def __init__(self):
        self._client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
            follow_redirects=True,
            verify=False,
        )

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        results = self._search_v1(query, limit)
        if not results:
            results = self._search_cloudsearch(query, limit)
        return results

    def _search_v1(self, query: str, limit: int = 10) -> list[SearchResult]:
        url = f"{self.API_URL}/search/get"
        params = {"s": query, "type": 1, "limit": limit, "offset": 0}

        try:
            resp = self._client.post(url, data=params)
            data = resp.json()
        except Exception:
            return []

        results = []
        songs = data.get("result", {}).get("songs", [])
        for song in songs:
            artists = ", ".join(a.get("name", "") for a in song.get("artists", []))
            album = song.get("album", {})
            results.append(
                SearchResult(
                    title=song.get("name", ""),
                    artist=artists,
                    album=album.get("name", ""),
                    source="netease",
                    source_id=str(song.get("id", "")),
                    source_url=f"https://music.163.com/song?id={song.get('id', '')}",
                    duration_seconds=(song.get("duration", 0) or 0) / 1000,
                    cover_url=album.get("picUrl", album.get("img1v1Url", "")),
                )
            )
        return results

    def _search_cloudsearch(self, query: str, limit: int = 10) -> list[SearchResult]:
        url = f"{self.API_URL}/cloudsearch/get/web"
        params = {"s": query, "type": 1, "limit": limit, "offset": 0}

        try:
            resp = self._client.post(url, data=params)
            data = resp.json()
        except Exception:
            return []

        results = []
        songs = data.get("result", {}).get("songs", [])
        for song in songs:
            artists = ", ".join(a.get("name", "") for a in song.get("artists", []))
            album = song.get("album", {})
            results.append(
                SearchResult(
                    title=song.get("name", ""),
                    artist=artists,
                    album=album.get("name", ""),
                    source="netease",
                    source_id=str(song.get("id", "")),
                    source_url=f"https://music.163.com/song?id={song.get('id', '')}",
                    duration_seconds=(song.get("duration", 0) or 0) / 1000,
                    cover_url=album.get("picUrl", album.get("img1v1Url", "")),
                )
            )
        return results

    def download(self, identifier: str, output_dir: Path) -> DownloadResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        song_id = self._extract_id(identifier)

        if not song_id:
            results = self.search(identifier, limit=1)
            if not results:
                return DownloadResult(
                    success=False, error="Song not found", source="netease"
                )
            song_id = results[0].source_id

        try:
            detail = self._get_song_detail(song_id)
            if not detail:
                return DownloadResult(
                    success=False, error="Cannot get song detail", source="netease", source_id=song_id
                )

            title = detail.get("name", "unknown")
            artists = ", ".join(a.get("name", "") for a in detail.get("ar", detail.get("artists", [])))
            album_info = detail.get("al", detail.get("album", {}))

            audio_url = self._get_audio_url(song_id)
            if not audio_url:
                audio_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"

            response = self._client.get(audio_url, follow_redirects=True, timeout=120)
            if response.status_code != 200 or len(response.content) < 1000:
                return DownloadResult(
                    success=False,
                    error="Audio not available (may require VIP or login)",
                    source="netease",
                    source_id=song_id,
                )

            content_type = response.headers.get("content-type", "")
            ext = "mp3"
            if "flac" in content_type:
                ext = "flac"
            elif "m4a" in content_type or "mp4" in content_type:
                ext = "m4a"

            filename = safe_filename(f"{artists} - {title}.{ext}")
            filepath = output_dir / filename
            filepath.write_bytes(response.content)

            metadata = TrackMetadata(
                title=title,
                artist=artists,
                album=album_info.get("name", ""),
                cover_url=album_info.get("picUrl"),
                duration_seconds=(detail.get("dt", detail.get("duration", 0)) or 0) / 1000,
            )

            return DownloadResult(
                success=True,
                file_path=filepath,
                metadata=metadata,
                source="netease",
                source_id=song_id,
            )

        except Exception as e:
            return DownloadResult(
                success=False, error=str(e), source="netease", source_id=song_id
            )

    def get_metadata(self, identifier: str) -> Optional[TrackMetadata]:
        song_id = self._extract_id(identifier) or identifier
        detail = self._get_song_detail(song_id)
        if not detail:
            return None

        artists = ", ".join(a.get("name", "") for a in detail.get("ar", detail.get("artists", [])))
        album = detail.get("al", detail.get("album", {}))

        return TrackMetadata(
            title=detail.get("name", ""),
            artist=artists,
            album=album.get("name", ""),
            cover_url=album.get("picUrl"),
            duration_seconds=(detail.get("dt", detail.get("duration", 0)) or 0) / 1000,
        )

    def get_lyrics(self, song_id: str) -> Optional[str]:
        url = f"{self.API_URL}/song/lyric"
        params = {"id": song_id, "lv": -1, "tv": -1}

        try:
            resp = self._client.get(url, params=params)
            data = resp.json()
            lrc = data.get("lrc", {}).get("lyric", "")
            return lrc if lrc else None
        except Exception:
            return None

    def get_playlist(self, playlist_id: str) -> list[SearchResult]:
        url = f"{self.API_URL}/v6/playlist/detail"
        params = {"id": playlist_id, "n": 1000}

        try:
            resp = self._client.post(url, data=params)
            data = resp.json()
            tracks = data.get("playlist", {}).get("tracks", [])

            results = []
            for song in tracks:
                artists = ", ".join(a.get("name", "") for a in song.get("ar", []))
                album = song.get("al", {})
                results.append(
                    SearchResult(
                        title=song.get("name", ""),
                        artist=artists,
                        album=album.get("name", ""),
                        source="netease",
                        source_id=str(song.get("id", "")),
                        source_url=f"https://music.163.com/song?id={song.get('id', '')}",
                        duration_seconds=(song.get("dt", 0) or 0) / 1000,
                        cover_url=album.get("picUrl", ""),
                    )
                )
            return results
        except Exception:
            return []

    def _extract_id(self, identifier: str) -> Optional[str]:
        if identifier.isdigit():
            return identifier
        match = re.search(r"id=(\d+)", identifier)
        if match:
            return match.group(1)
        match = re.search(r"/song/(\d+)", identifier)
        if match:
            return match.group(1)
        return None

    def _get_song_detail(self, song_id: str) -> Optional[dict]:
        url = f"{self.API_URL}/v3/song/detail"
        data = {"c": json.dumps([{"id": int(song_id)}])}

        try:
            resp = self._client.post(url, data=data)
            result = resp.json()
            songs = result.get("songs", [])
            return songs[0] if songs else None
        except Exception:
            return None

    def _get_audio_url(self, song_id: str) -> Optional[str]:
        url = f"{self.API_URL}/song/enhance/player/url"
        params = {"ids": f"[{song_id}]", "br": 320000}

        try:
            resp = self._client.get(url, params=params)
            data = resp.json()
            items = data.get("data", [])
            if items and items[0].get("url"):
                return items[0]["url"]
        except Exception:
            pass
        return None
