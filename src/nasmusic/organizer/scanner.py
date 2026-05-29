from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from nasmusic.core import get_music_dir
from nasmusic.core.database import get_database
from nasmusic.metadata import read_tags, has_cover_art
from nasmusic.metadata.lyrics import has_lrc_file
from nasmusic.utils import find_audio_files, get_relative_path


def scan_library(music_dir: Optional[Path] = None) -> dict:
    if music_dir is None:
        music_dir = get_music_dir()

    db = get_database()
    stats = {"new": 0, "updated": 0, "total": 0}

    for filepath in find_audio_files(music_dir):
        stats["total"] += 1
        rel_path = get_relative_path(filepath, music_dir)

        existing = db.get_track_by_path(rel_path)
        file_size = filepath.stat().st_size
        file_hash = _compute_hash(filepath)

        if existing and existing.get("file_hash") == file_hash:
            continue

        metadata = read_tags(filepath)
        has_cover = has_cover_art(filepath)
        has_lyrics = has_lrc_file(filepath)

        quality = "complete"
        if not metadata.title or not metadata.artist or not metadata.album:
            quality = "partial"
        if not metadata.title and not metadata.artist:
            quality = "unknown"

        track_data = {
            "file_path": rel_path,
            "file_hash": file_hash,
            "file_size": file_size,
            "duration_seconds": metadata.duration_seconds,
            "title": metadata.title,
            "artist": metadata.artist,
            "album_artist": metadata.album_artist,
            "album": metadata.album,
            "track_number": metadata.track_number,
            "disc_number": metadata.disc_number,
            "year": metadata.year,
            "genre": metadata.genre,
            "has_cover_art": 1 if has_cover else 0,
            "has_lyrics": 1 if has_lyrics else 0,
            "metadata_quality": quality,
        }

        if existing:
            track_data["source"] = existing.get("source", "local")
            track_data["source_id"] = existing.get("source_id", "")
            stats["updated"] += 1
        else:
            track_data["source"] = "local"
            stats["new"] += 1

        db.add_track(**track_data)

    return stats


def _compute_hash(filepath: Path, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def verify_library(music_dir: Optional[Path] = None) -> dict:
    if music_dir is None:
        music_dir = get_music_dir()

    db = get_database()
    issues = {"missing_files": [], "incomplete_metadata": [], "no_cover": [], "no_lyrics": []}

    tracks = db.get_all_tracks(limit=100000)
    for track in tracks:
        filepath = music_dir / track["file_path"]
        if not filepath.exists():
            issues["missing_files"].append(track["file_path"])
            continue

        if track.get("metadata_quality") != "complete":
            issues["incomplete_metadata"].append(track["file_path"])
        if not track.get("has_cover_art"):
            issues["no_cover"].append(track["file_path"])
        if not track.get("has_lyrics"):
            issues["no_lyrics"].append(track["file_path"])

    return issues
