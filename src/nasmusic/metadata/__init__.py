from __future__ import annotations

from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TPOS, TDRC, TCON, APIC
from mutagen.flac import FLAC
from mutagen import File as MutagenFile

from nasmusic.core.models import TrackMetadata


def read_tags(filepath: Path) -> TrackMetadata:
    filepath = Path(filepath)
    audio = MutagenFile(str(filepath), easy=True)

    if audio is None:
        return TrackMetadata()

    def get_first(key: str) -> str:
        val = audio.get(key, [""])
        return val[0] if val else ""

    track_str = get_first("tracknumber")
    track_num = 0
    if track_str:
        track_num = int(track_str.split("/")[0]) if "/" in track_str else int(track_str or "0")

    disc_str = get_first("discnumber")
    disc_num = 1
    if disc_str:
        disc_num = int(disc_str.split("/")[0]) if "/" in disc_str else int(disc_str or "1")

    year = None
    date_str = get_first("date")
    if date_str:
        try:
            year = int(date_str[:4])
        except (ValueError, IndexError):
            pass

    duration = audio.info.length if audio.info else 0.0

    return TrackMetadata(
        title=get_first("title"),
        artist=get_first("artist"),
        album_artist=get_first("albumartist"),
        album=get_first("album"),
        track_number=track_num,
        disc_number=disc_num,
        year=year,
        genre=get_first("genre"),
        duration_seconds=duration,
    )


def write_tags(filepath: Path, metadata: TrackMetadata, cover_data: Optional[bytes] = None):
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if suffix == ".mp3":
        _write_mp3_tags(filepath, metadata, cover_data)
    elif suffix == ".flac":
        _write_flac_tags(filepath, metadata, cover_data)
    else:
        _write_easy_tags(filepath, metadata)


def _write_mp3_tags(filepath: Path, metadata: TrackMetadata, cover_data: Optional[bytes] = None):
    try:
        audio = MP3(str(filepath), ID3=ID3)
    except Exception:
        audio = MP3(str(filepath))

    if audio.tags is None:
        audio.add_tags()

    tags = audio.tags
    if metadata.title:
        tags["TIT2"] = TIT2(encoding=3, text=[metadata.title])
    if metadata.artist:
        tags["TPE1"] = TPE1(encoding=3, text=[metadata.artist])
    if metadata.album_artist:
        tags["TPE2"] = TPE2(encoding=3, text=[metadata.album_artist])
    if metadata.album:
        tags["TALB"] = TALB(encoding=3, text=[metadata.album])
    if metadata.track_number:
        tags["TRCK"] = TRCK(encoding=3, text=[str(metadata.track_number)])
    if metadata.disc_number:
        tags["TPOS"] = TPOS(encoding=3, text=[str(metadata.disc_number)])
    if metadata.year:
        tags["TDRC"] = TDRC(encoding=3, text=[str(metadata.year)])
    if metadata.genre:
        tags["TCON"] = TCON(encoding=3, text=[metadata.genre])

    if cover_data:
        tags["APIC"] = APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=cover_data,
        )

    audio.save()


def _write_flac_tags(filepath: Path, metadata: TrackMetadata, cover_data: Optional[bytes] = None):
    audio = FLAC(str(filepath))

    if metadata.title:
        audio["title"] = metadata.title
    if metadata.artist:
        audio["artist"] = metadata.artist
    if metadata.album_artist:
        audio["albumartist"] = metadata.album_artist
    if metadata.album:
        audio["album"] = metadata.album
    if metadata.track_number:
        audio["tracknumber"] = str(metadata.track_number)
    if metadata.disc_number:
        audio["discnumber"] = str(metadata.disc_number)
    if metadata.year:
        audio["date"] = str(metadata.year)
    if metadata.genre:
        audio["genre"] = metadata.genre

    if cover_data:
        from mutagen.flac import Picture
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover_data
        audio.clear_pictures()
        audio.add_picture(pic)

    audio.save()


def _write_easy_tags(filepath: Path, metadata: TrackMetadata):
    audio = MutagenFile(str(filepath), easy=True)
    if audio is None:
        return

    if audio.tags is None:
        audio.add_tags()

    if metadata.title:
        audio["title"] = metadata.title
    if metadata.artist:
        audio["artist"] = metadata.artist
    if metadata.album_artist:
        audio["albumartist"] = metadata.album_artist
    if metadata.album:
        audio["album"] = metadata.album
    if metadata.track_number:
        audio["tracknumber"] = str(metadata.track_number)
    if metadata.disc_number:
        audio["discnumber"] = str(metadata.disc_number)
    if metadata.year:
        audio["date"] = str(metadata.year)
    if metadata.genre:
        audio["genre"] = metadata.genre

    audio.save()


def has_cover_art(filepath: Path) -> bool:
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if suffix == ".mp3":
        try:
            audio = MP3(str(filepath), ID3=ID3)
            return any(k.startswith("APIC") for k in (audio.tags or {}))
        except Exception:
            return False
    elif suffix == ".flac":
        try:
            audio = FLAC(str(filepath))
            return len(audio.pictures) > 0
        except Exception:
            return False
    return False
