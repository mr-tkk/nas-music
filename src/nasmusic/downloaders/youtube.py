from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from nasmusic.downloaders import BaseDownloader
from nasmusic.core.models import SearchResult, DownloadResult


def _bin(name: str) -> str:
    venv_bin = Path(sys.executable).parent / (name + ".exe" if sys.platform == "win32" else name)
    if venv_bin.exists():
        return str(venv_bin)
    return name


class YouTubeDownloader(BaseDownloader):
    source_name = "youtube"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
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

        is_url = identifier.startswith("http://") or identifier.startswith("https://")
        search_query = identifier if is_url else f"ytsearch1:{identifier}"
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
                    source_id=identifier,
                )

            mp3_files = list(output_dir.glob("*.mp3"))
            if mp3_files:
                newest = max(mp3_files, key=lambda f: f.stat().st_mtime)
                return DownloadResult(
                    success=True,
                    file_path=newest,
                    source="youtube",
                    source_id=identifier,
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
