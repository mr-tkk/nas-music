from __future__ import annotations

from pathlib import Path
from typing import Optional

import musicbrainzngs

from nasmusic.core.models import TrackMetadata
from nasmusic.core import get_config

_initialized = False


def _init_mb():
    global _initialized
    if not _initialized:
        cfg = get_config()
        musicbrainzngs.set_useragent(
            "NASMusic",
            "0.1.0",
            cfg.musicbrainz.user_agent,
        )
        _initialized = True


def search_recording(title: str, artist: str = "", limit: int = 5) -> list[dict]:
    _init_mb()
    query = title
    if artist:
        query = f'"{title}" AND artist:"{artist}"'

    try:
        result = musicbrainzngs.search_recordings(query=query, limit=limit)
        recordings = result.get("recording-list", [])
        matches = []
        for rec in recordings:
            artists = ", ".join(
                a.get("artist", {}).get("name", "")
                for a in rec.get("artist-credit", [])
                if isinstance(a, dict)
            )
            releases = rec.get("release-list", [])
            album = releases[0].get("title", "") if releases else ""
            year = None
            if releases and releases[0].get("date"):
                try:
                    year = int(releases[0]["date"][:4])
                except (ValueError, IndexError):
                    pass

            matches.append({
                "mbid": rec.get("id", ""),
                "title": rec.get("title", ""),
                "artist": artists,
                "album": album,
                "year": year,
                "score": rec.get("ext:score", 0),
            })
        return matches
    except Exception:
        return []


def match_track(metadata: TrackMetadata) -> Optional[TrackMetadata]:
    _init_mb()
    matches = search_recording(metadata.title, metadata.artist, limit=3)

    if not matches:
        return None

    best = matches[0]
    if int(best.get("score", 0)) < 80:
        return None

    return TrackMetadata(
        title=best["title"] or metadata.title,
        artist=best["artist"] or metadata.artist,
        album=best["album"] or metadata.album,
        year=best["year"] or metadata.year,
        album_artist=best["artist"],
    )


def search_release(album: str, artist: str = "", limit: int = 5) -> list[dict]:
    _init_mb()
    query = album
    if artist:
        query = f'"{album}" AND artist:"{artist}"'

    try:
        result = musicbrainzngs.search_releases(query=query, limit=limit)
        releases = result.get("release-list", [])
        matches = []
        for rel in releases:
            artists = ", ".join(
                a.get("artist", {}).get("name", "")
                for a in rel.get("artist-credit", [])
                if isinstance(a, dict)
            )
            year = None
            if rel.get("date"):
                try:
                    year = int(rel["date"][:4])
                except (ValueError, IndexError):
                    pass

            matches.append({
                "mbid": rel.get("id", ""),
                "title": rel.get("title", ""),
                "artist": artists,
                "year": year,
                "track_count": rel.get("medium-list", [{}])[0].get("track-count", 0) if rel.get("medium-list") else 0,
                "score": rel.get("ext:score", 0),
            })
        return matches
    except Exception:
        return []
