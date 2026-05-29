from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class TrackMetadata(BaseModel):
    title: str = ""
    artist: str = ""
    album_artist: str = ""
    album: str = ""
    track_number: int = 0
    disc_number: int = 1
    year: Optional[int] = None
    genre: str = ""
    duration_seconds: float = 0.0
    cover_url: Optional[str] = None
    lyrics: Optional[str] = None


class SearchResult(BaseModel):
    title: str
    artist: str
    album: str = ""
    source: str
    source_id: str
    source_url: str = ""
    duration_seconds: float = 0.0
    cover_url: str = ""
    year: Optional[int] = None


class DownloadResult(BaseModel):
    success: bool
    file_path: Optional[Path] = None
    metadata: Optional[TrackMetadata] = None
    error: Optional[str] = None
    source: str = ""
    source_id: str = ""


class PlaylistInfo(BaseModel):
    name: str
    description: str = ""
    source: str = ""
    source_id: str = ""
    source_url: str = ""
    tracks: list[SearchResult] = []
