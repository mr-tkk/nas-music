from __future__ import annotations

import re
from typing import Optional

from nasmusic.core.models import SearchResult, PlaylistInfo
from nasmusic.core.database import get_database
from nasmusic.playlists import create_playlist, add_track_to_playlist


def import_netease_playlist(url: str) -> Optional[PlaylistInfo]:
    match = re.search(r"id=(\d+)", url)
    if not match:
        match = re.search(r"playlist/(\d+)", url)
    if not match:
        return None

    playlist_id = match.group(1)

    try:
        from nasmusic.downloaders.netease import NeteaseDownloader
        dl = NeteaseDownloader()
        tracks = dl.get_playlist(playlist_id)

        if not tracks:
            return None

        return PlaylistInfo(
            name=f"NetEase Playlist {playlist_id}",
            source="netease",
            source_id=playlist_id,
            source_url=url,
            tracks=tracks,
        )
    except Exception:
        return None


def import_spotify_playlist(url: str) -> Optional[PlaylistInfo]:
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    if not match:
        return None

    playlist_id = match.group(1)

    return PlaylistInfo(
        name=f"Spotify Playlist {playlist_id}",
        source="spotify",
        source_id=playlist_id,
        source_url=url,
        tracks=[],
    )


def save_playlist_to_db(info: PlaylistInfo) -> int:
    db = get_database()
    pl_id = create_playlist(
        name=info.name,
        description=info.description,
        source=info.source,
    )

    for i, track in enumerate(info.tracks, 1):
        existing = db.get_track_by_source(track.source, track.source_id)
        if existing:
            add_track_to_playlist(pl_id, existing["id"], position=i)
        else:
            db.conn.execute(
                """INSERT INTO playlist_tracks
                (playlist_id, position, pending_title, pending_artist, pending_source, pending_source_id)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (pl_id, i, track.title, track.artist, track.source, track.source_id),
            )
    db.conn.commit()
    return pl_id
