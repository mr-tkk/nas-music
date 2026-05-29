from __future__ import annotations

import subprocess
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional

from nasmusic.downloaders import BaseDownloader
from nasmusic.core.models import SearchResult, DownloadResult, TrackMetadata


def _bin(name: str) -> str:
    """Find a binary in the same directory as the current Python interpreter (venv/Scripts)."""
    venv_bin = Path(sys.executable).parent / (name + ".exe" if sys.platform == "win32" else name)
    if venv_bin.exists():
        return str(venv_bin)
    return name


class SpotifyDownloader(BaseDownloader):
    source_name = "spotify"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            result = subprocess.run(
                [_bin("spotdl"), "url", query, "--output", "{list}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # spotdl doesn't have a clean search API via CLI
            # Use yt-dlp ytsearch as fallback for search
            return self._ytdlp_search(query, limit)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._ytdlp_search(query, limit)

    def _ytdlp_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            result = subprocess.run(
                [
                    _bin("yt-dlp"),
                    f"ytsearch{limit}:{query}",
                    "--dump-json",
                    "--flat-playlist",
                    "--no-download",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            results = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    results.append(
                        SearchResult(
                            title=data.get("title", ""),
                            artist=data.get("uploader", data.get("channel", "")),
                            album="",
                            source="youtube",
                            source_id=data.get("id", ""),
                            source_url=data.get("url", f"https://youtube.com/watch?v={data.get('id', '')}"),
                            duration_seconds=data.get("duration", 0) or 0,
                        )
                    )
                except json.JSONDecodeError:
                    continue
            return results
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def download(self, identifier: str, output_dir: Path) -> DownloadResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        is_spotify_url = "spotify.com" in identifier or "open.spotify" in identifier

        if is_spotify_url:
            return self._download_spotdl(identifier, output_dir)
        else:
            return self._download_ytdlp(identifier, output_dir)

    def _download_spotdl(self, url: str, output_dir: Path) -> DownloadResult:
        try:
            result = subprocess.run(
                [
                    _bin("spotdl"),
                    "download",
                    url,
                    "--output", str(output_dir / "{artist} - {title}.{output-ext}"),
                    "--format", "mp3",
                    "--bitrate", "320k",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(output_dir),
            )

            if result.returncode != 0:
                return DownloadResult(
                    success=False,
                    error=result.stderr or "spotdl download failed",
                    source="spotify",
                )

            # Find the downloaded file
            mp3_files = list(output_dir.glob("*.mp3"))
            if mp3_files:
                newest = max(mp3_files, key=lambda f: f.stat().st_mtime)
                return DownloadResult(
                    success=True,
                    file_path=newest,
                    source="spotify",
                    source_id=url,
                )

            return DownloadResult(
                success=False,
                error="Download completed but no file found",
                source="spotify",
            )

        except FileNotFoundError:
            return DownloadResult(
                success=False,
                error="spotdl not found. Install with: pip install spotdl",
                source="spotify",
            )
        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False, error="Download timed out", source="spotify"
            )

    def _download_ytdlp(self, query: str, output_dir: Path) -> DownloadResult:
        is_url = query.startswith("http://") or query.startswith("https://")
        search_query = query if is_url else f"ytsearch1:{query}"

        output_template = str(output_dir / "%(artist,uploader)s - %(title)s.%(ext)s")

        try:
            result = subprocess.run(
                [
                    _bin("yt-dlp"),
                    search_query,
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "0",
                    "--embed-thumbnail",
                    "--embed-metadata",
                    "-o", output_template,
                    "--print", "after_move:filepath",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                return DownloadResult(
                    success=False,
                    error=result.stderr or "yt-dlp download failed",
                    source="youtube",
                )

            filepath = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else None
            if filepath and Path(filepath).exists():
                return DownloadResult(
                    success=True,
                    file_path=Path(filepath),
                    source="youtube",
                    source_id=query,
                )

            mp3_files = list(output_dir.glob("*.mp3"))
            if mp3_files:
                newest = max(mp3_files, key=lambda f: f.stat().st_mtime)
                return DownloadResult(
                    success=True,
                    file_path=newest,
                    source="youtube",
                    source_id=query,
                )

            return DownloadResult(
                success=False, error="Download completed but no file found", source="youtube"
            )

        except FileNotFoundError:
            return DownloadResult(
                success=False,
                error="yt-dlp not found. Install with: pip install yt-dlp",
                source="youtube",
            )
        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False, error="Download timed out", source="youtube"
            )
