from __future__ import annotations

from pathlib import Path
from typing import Optional
from collections import defaultdict

from nasmusic.core import get_music_dir
from nasmusic.core.database import get_database


def find_duplicates(method: str = "metadata") -> list[dict]:
    db = get_database()
    tracks = db.get_all_tracks(limit=100000)

    if method == "hash":
        return _find_by_hash(tracks)
    elif method == "metadata":
        return _find_by_metadata(tracks)
    return []


def _find_by_hash(tracks: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for track in tracks:
        if track.get("file_hash"):
            groups[track["file_hash"]].append(track)

    duplicates = []
    for file_hash, group in groups.items():
        if len(group) > 1:
            duplicates.append({
                "method": "hash",
                "tracks": group,
                "count": len(group),
            })
    return duplicates


def _find_by_metadata(tracks: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for track in tracks:
        title = (track.get("title") or "").lower().strip()
        artist = (track.get("artist") or "").lower().strip()
        if title and artist:
            key = f"{artist}|{title}"
            groups[key].append(track)

    duplicates = []
    for key, group in groups.items():
        if len(group) > 1:
            duplicates.append({
                "method": "metadata",
                "key": key,
                "tracks": group,
                "count": len(group),
            })
    return duplicates
