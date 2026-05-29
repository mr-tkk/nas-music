from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

import httpx

from nasmusic.downloaders import BaseDownloader
from nasmusic.core.models import SearchResult, DownloadResult, TrackMetadata
from nasmusic.utils import safe_filename


class QQMusicDownloader(BaseDownloader):
    source_name = "qqmusic"

    SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    SONG_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"

    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self._client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://y.qq.com/",
            },
            timeout=30,
            verify=False,
        )
        if cookie:
            self._client.headers["Cookie"] = cookie

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        params = {
            "w": query,
            "format": "json",
            "p": 1,
            "n": limit,
            "cr": 1,
            "new_json": 1,
        }

        try:
            resp = self._client.get(self.SEARCH_URL, params=params)
            data = resp.json()
        except Exception:
            return []

        results = []
        songs = data.get("data", {}).get("song", {}).get("list", [])
        for song in songs:
            artists = ", ".join(s.get("name", "") for s in song.get("singer", []))
            album = song.get("album", {})
            mid = song.get("mid", "")
            results.append(
                SearchResult(
                    title=song.get("name", song.get("title", "")),
                    artist=artists,
                    album=album.get("name", ""),
                    source="qqmusic",
                    source_id=mid,
                    source_url=f"https://y.qq.com/n/ryqq/songDetail/{mid}",
                    duration_seconds=song.get("interval", 0),
                    cover_url=f"https://y.qq.com/music/photo_new/T002R300x300M000{album.get('mid', '')}.jpg",
                )
            )
        return results

    def download(self, identifier: str, output_dir: Path) -> DownloadResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        song_mid = identifier
        if "y.qq.com" in identifier:
            match = re.search(r"songDetail/([a-zA-Z0-9]+)", identifier)
            if match:
                song_mid = match.group(1)

        try:
            audio_url = self._get_audio_url(song_mid)
            if not audio_url:
                return DownloadResult(
                    success=False,
                    error="Cannot get audio URL (may require VIP)",
                    source="qqmusic",
                    source_id=song_mid,
                )

            song_detail = self._get_song_detail(song_mid)
            title = song_detail.get("title", "unknown")
            artist = song_detail.get("artist", "unknown")

            response = self._client.get(audio_url, follow_redirects=True, timeout=120)
            response.raise_for_status()

            filename = safe_filename(f"{artist} - {title}.mp3")
            filepath = output_dir / filename
            filepath.write_bytes(response.content)

            metadata = TrackMetadata(
                title=title,
                artist=artist,
                album=song_detail.get("album", ""),
                cover_url=song_detail.get("cover_url"),
                duration_seconds=song_detail.get("duration", 0),
            )

            return DownloadResult(
                success=True,
                file_path=filepath,
                metadata=metadata,
                source="qqmusic",
                source_id=song_mid,
            )

        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="qqmusic",
                source_id=song_mid,
            )

    def _get_audio_url(self, song_mid: str) -> Optional[str]:
        req_data = {
            "req_0": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    "guid": "1234567890",
                    "songmid": [song_mid],
                    "songtype": [0],
                    "uin": "0",
                    "loginflag": 1,
                    "platform": "20",
                    "filename": [f"M800{song_mid}.mp3"],
                },
            }
        }

        try:
            resp = self._client.get(
                self.SONG_URL,
                params={"data": json.dumps(req_data)},
            )
            data = resp.json()
            midurlinfo = data.get("req_0", {}).get("data", {}).get("midurlinfo", [{}])[0]
            purl = midurlinfo.get("purl", "")
            if purl:
                sip = data.get("req_0", {}).get("data", {}).get("sip", [""])[0]
                return f"{sip}{purl}"
        except Exception:
            pass
        return None

    def _get_song_detail(self, song_mid: str) -> dict:
        req_data = {
            "req_0": {
                "module": "music.pf_song_detail_svr",
                "method": "get_song_detail_yqq",
                "param": {"song_mid": song_mid},
            }
        }

        try:
            resp = self._client.get(
                self.SONG_URL,
                params={"data": json.dumps(req_data)},
            )
            data = resp.json()
            track = data.get("req_0", {}).get("data", {}).get("track_info", {})
            artists = ", ".join(s.get("name", "") for s in track.get("singer", []))
            album = track.get("album", {})
            return {
                "title": track.get("name", ""),
                "artist": artists,
                "album": album.get("name", ""),
                "duration": track.get("interval", 0),
                "cover_url": f"https://y.qq.com/music/photo_new/T002R300x300M000{album.get('mid', '')}.jpg",
            }
        except Exception:
            return {}
