from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from nasmusic.core.models import TrackMetadata
from nasmusic.metadata import write_tags


def fetch_cover_from_url(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30, verify=False)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "image" in content_type or len(resp.content) > 1000:
            return resp.content
    except Exception:
        pass
    return None


def embed_cover(filepath: Path, cover_data: bytes):
    from nasmusic.metadata import read_tags
    metadata = read_tags(filepath)
    write_tags(filepath, metadata, cover_data=cover_data)


def fetch_and_embed_cover(filepath: Path, cover_url: str) -> bool:
    cover_data = fetch_cover_from_url(cover_url)
    if cover_data:
        embed_cover(filepath, cover_data)
        return True
    return False


def save_cover_to_album_dir(album_dir: Path, cover_data: bytes, filename: str = "cover.jpg"):
    cover_path = album_dir / filename
    cover_path.write_bytes(cover_data)
    return cover_path
