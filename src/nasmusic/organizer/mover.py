from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from nasmusic.core import get_config, get_music_dir
from nasmusic.core.models import TrackMetadata
from nasmusic.metadata import read_tags
from nasmusic.utils import build_track_path


def organize_file(
    filepath: Path,
    metadata: Optional[TrackMetadata] = None,
    music_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Optional[Path]:
    filepath = Path(filepath)
    if not filepath.exists():
        return None

    if music_dir is None:
        music_dir = get_music_dir()

    if metadata is None:
        metadata = read_tags(filepath)

    artist = metadata.artist or metadata.album_artist or "Unknown Artist"
    album = metadata.album or "Unknown Album"
    title = metadata.title or filepath.stem

    target = build_track_path(
        music_dir=music_dir,
        artist=artist,
        album=album,
        title=title,
        track_number=metadata.track_number,
        ext=filepath.suffix.lstrip("."),
    )

    if filepath == target:
        return target

    if dry_run:
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(filepath), str(target))
    return target


def organize_directory(
    source_dir: Path,
    music_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    from nasmusic.utils import find_audio_files

    if music_dir is None:
        music_dir = get_music_dir()

    moves = []
    for filepath in find_audio_files(source_dir):
        target = organize_file(filepath, music_dir=music_dir, dry_run=dry_run)
        if target and target != filepath:
            moves.append((filepath, target))

    return moves
