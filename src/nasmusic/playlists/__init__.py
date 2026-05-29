from __future__ import annotations

from pathlib import Path
from typing import Optional

from nasmusic.core.database import get_database
from nasmusic.core import get_music_dir


def create_playlist(name: str, description: str = "", source: str = "local") -> int:
    db = get_database()
    return db.create_playlist(name=name, description=description, source=source)


def get_playlists() -> list[dict]:
    db = get_database()
    return db.get_playlists()


def get_playlist_tracks(playlist_id: int) -> list[dict]:
    db = get_database()
    return db.get_playlist_tracks(playlist_id)


def add_track_to_playlist(playlist_id: int, track_id: int, position: Optional[int] = None):
    db = get_database()
    if position is None:
        tracks = db.get_playlist_tracks(playlist_id)
        position = len(tracks) + 1
    db.add_playlist_track(playlist_id, track_id, position)


def export_m3u8(playlist_id: int, output_path: Optional[Path] = None) -> Path:
    db = get_database()
    tracks = db.get_playlist_tracks(playlist_id)
    playlists = db.get_playlists()
    playlist = next((p for p in playlists if p["id"] == playlist_id), None)

    if output_path is None:
        music_dir = get_music_dir()
        playlist_dir = music_dir / "Playlists"
        playlist_dir.mkdir(exist_ok=True)
        name = playlist["name"] if playlist else f"playlist_{playlist_id}"
        output_path = playlist_dir / f"{name}.m3u8"

    lines = ["#EXTM3U"]
    for track in tracks:
        duration = int(track.get("duration_seconds", 0))
        title = track.get("title", "")
        artist = track.get("artist", "")
        display = f"{artist} - {title}" if artist else title
        lines.append(f"#EXTINF:{duration},{display}")
        lines.append(f"../{track['file_path']}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_all_playlists() -> list[Path]:
    db = get_database()
    playlists = db.get_playlists()
    exported = []
    for pl in playlists:
        path = export_m3u8(pl["id"])
        exported.append(path)
    return exported
