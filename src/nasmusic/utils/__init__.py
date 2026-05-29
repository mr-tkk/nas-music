from __future__ import annotations

import re
import unicodedata
from pathlib import Path


WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str, max_length: int = 200) -> str:
    name = unicodedata.normalize("NFC", name)
    name = INVALID_CHARS.sub("_", name)
    name = name.strip(". ")

    stem = Path(name).stem
    if stem.upper() in WINDOWS_RESERVED:
        name = f"_{name}"

    if len(name) > max_length:
        name = name[:max_length]

    return name or "unknown"


def build_track_path(
    music_dir: Path,
    artist: str,
    album: str,
    title: str,
    track_number: int = 0,
    ext: str = "mp3",
) -> Path:
    artist_dir = safe_filename(artist or "Unknown Artist")
    album_dir = safe_filename(album or "Unknown Album")

    if track_number > 0:
        filename = f"{track_number:02d} - {safe_filename(title)}.{ext}"
    else:
        filename = f"{safe_filename(title)}.{ext}"

    return music_dir / artist_dir / album_dir / filename


def find_audio_files(directory: Path, recursive: bool = True) -> list[Path]:
    extensions = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".wma", ".aac"}
    files = []

    if recursive:
        for f in directory.rglob("*"):
            if f.suffix.lower() in extensions and f.is_file():
                files.append(f)
    else:
        for f in directory.iterdir():
            if f.suffix.lower() in extensions and f.is_file():
                files.append(f)

    return sorted(files)


def get_relative_path(file_path: Path, music_dir: Path) -> str:
    try:
        return str(file_path.relative_to(music_dir)).replace("\\", "/")
    except ValueError:
        return str(file_path).replace("\\", "/")
