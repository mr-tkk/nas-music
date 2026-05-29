from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from nasmusic.utils.progress import print_success, print_error, print_info

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def show(path: Path = typer.Argument(..., help="File or directory to show tags for")):
    """Show metadata tags for a file or all files in a directory."""
    from nasmusic.metadata import read_tags, has_cover_art
    from nasmusic.utils import find_audio_files

    files = [path] if path.is_file() else find_audio_files(path)

    for f in files:
        meta = read_tags(f)
        has_art = has_cover_art(f)

        console.print(f"\n[bold cyan]{f.name}[/]")
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="dim", width=14)
        table.add_column("Value")

        table.add_row("Title", meta.title or "[dim]empty[/dim]")
        table.add_row("Artist", meta.artist or "[dim]empty[/dim]")
        table.add_row("Album Artist", meta.album_artist or "[dim]empty[/dim]")
        table.add_row("Album", meta.album or "[dim]empty[/dim]")
        table.add_row("Track #", str(meta.track_number) if meta.track_number else "[dim]empty[/dim]")
        table.add_row("Disc #", str(meta.disc_number))
        table.add_row("Year", str(meta.year) if meta.year else "[dim]empty[/dim]")
        table.add_row("Genre", meta.genre or "[dim]empty[/dim]")
        table.add_row("Duration", f"{int(meta.duration_seconds // 60)}:{int(meta.duration_seconds % 60):02d}")
        table.add_row("Cover Art", "[green]Yes[/]" if has_art else "[red]No[/]")

        console.print(table)


@app.command()
def edit(
    path: Path = typer.Argument(..., help="File to edit tags for"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    artist: Optional[str] = typer.Option(None, "--artist", "-a"),
    album: Optional[str] = typer.Option(None, "--album", "-A"),
    album_artist: Optional[str] = typer.Option(None, "--album-artist"),
    track_number: Optional[int] = typer.Option(None, "--track", "-n"),
    year: Optional[int] = typer.Option(None, "--year", "-y"),
    genre: Optional[str] = typer.Option(None, "--genre", "-g"),
):
    """Edit metadata tags for a file."""
    from nasmusic.metadata import read_tags, write_tags

    if not path.is_file():
        print_error(f"Not a file: {path}")
        raise typer.Exit(1)

    meta = read_tags(path)

    if title is not None:
        meta.title = title
    if artist is not None:
        meta.artist = artist
    if album is not None:
        meta.album = album
    if album_artist is not None:
        meta.album_artist = album_artist
    if track_number is not None:
        meta.track_number = track_number
    if year is not None:
        meta.year = year
    if genre is not None:
        meta.genre = genre

    write_tags(path, meta)
    print_success(f"Updated tags for: {path.name}")


@app.command()
def match(
    path: Path = typer.Argument(..., help="File or directory to match against MusicBrainz"),
    auto: bool = typer.Option(False, "--auto", help="Auto-apply best match without confirming"),
):
    """Match files against MusicBrainz database."""
    from nasmusic.metadata import read_tags, write_tags
    from nasmusic.metadata.matcher import match_track
    from nasmusic.utils import find_audio_files

    files = [path] if path.is_file() else find_audio_files(path)

    matched = 0
    for f in files:
        meta = read_tags(f)
        if not meta.title:
            continue

        result = match_track(meta)
        if result is None:
            print_info(f"No match: {f.name}")
            continue

        console.print(f"\n[cyan]{f.name}[/]")
        console.print(f"  Current: {meta.artist} - {meta.title} [{meta.album}]")
        console.print(f"  Match:   {result.artist} - {result.title} [{result.album}] ({result.year})")

        if auto or typer.confirm("  Apply?", default=True):
            if result.title:
                meta.title = result.title
            if result.artist:
                meta.artist = result.artist
            if result.album:
                meta.album = result.album
            if result.year:
                meta.year = result.year
            if result.album_artist:
                meta.album_artist = result.album_artist
            write_tags(f, meta)
            matched += 1
            print_success("  Applied")

    console.print(f"\n[bold]Matched {matched}/{len(files)} files[/]")


@app.command(name="fetch-lyrics")
def fetch_lyrics(
    path: Path = typer.Argument(..., help="File or directory"),
    source: str = typer.Option("netease", "--source", "-s", help="Lyrics source: netease, qq"),
):
    """Fetch lyrics (LRC) for music files."""
    from nasmusic.metadata import read_tags
    from nasmusic.metadata.lyrics import save_lrc_file, has_lrc_file
    from nasmusic.utils import find_audio_files

    files = [path] if path.is_file() else find_audio_files(path)
    fetched = 0

    for f in files:
        if has_lrc_file(f):
            continue

        meta = read_tags(f)
        if not meta.title:
            continue

        query = f"{meta.artist} - {meta.title}" if meta.artist else meta.title
        lrc_content = None

        if source == "netease":
            from nasmusic.downloaders.netease import NeteaseDownloader
            dl = NeteaseDownloader()
            results = dl.search(query, limit=1)
            if results:
                lrc_content = dl.get_lyrics(results[0].source_id)
        elif source == "qq":
            from nasmusic.metadata.lyrics import fetch_lyrics_qqmusic
            from nasmusic.downloaders.qqmusic import QQMusicDownloader
            dl = QQMusicDownloader()
            results = dl.search(query, limit=1)
            if results:
                lrc_content = fetch_lyrics_qqmusic(results[0].source_id)

        if lrc_content:
            save_lrc_file(f, lrc_content)
            fetched += 1
            print_success(f"Lyrics: {f.name}")
        else:
            print_info(f"No lyrics: {f.name}")

    console.print(f"\n[bold]Fetched lyrics for {fetched}/{len(files)} files[/]")


@app.command(name="fetch-cover")
def fetch_cover(
    path: Path = typer.Argument(..., help="File or directory"),
    source: str = typer.Option("netease", "--source", "-s"),
):
    """Fetch and embed cover art for music files."""
    from nasmusic.metadata import read_tags, has_cover_art
    from nasmusic.metadata.cover_art import fetch_and_embed_cover
    from nasmusic.utils import find_audio_files

    files = [path] if path.is_file() else find_audio_files(path)
    fetched = 0

    for f in files:
        if has_cover_art(f):
            continue

        meta = read_tags(f)
        if not meta.title:
            continue

        query = f"{meta.artist} - {meta.title}" if meta.artist else meta.title

        if source == "netease":
            from nasmusic.downloaders.netease import NeteaseDownloader
            dl = NeteaseDownloader()
            results = dl.search(query, limit=1)
            if results and results[0].cover_url:
                if fetch_and_embed_cover(f, results[0].cover_url):
                    fetched += 1
                    print_success(f"Cover: {f.name}")
                    continue
        elif source == "qq":
            from nasmusic.downloaders.qqmusic import QQMusicDownloader
            dl = QQMusicDownloader()
            results = dl.search(query, limit=1)
            if results and results[0].cover_url:
                if fetch_and_embed_cover(f, results[0].cover_url):
                    fetched += 1
                    print_success(f"Cover: {f.name}")
                    continue

        print_info(f"No cover: {f.name}")

    console.print(f"\n[bold]Fetched covers for {fetched}/{len(files)} files[/]")


@app.command()
def fix(
    path: Path = typer.Argument(None, help="Directory to fix (defaults to music_dir)"),
    auto: bool = typer.Option(False, "--auto", help="Auto-fix without confirmation"),
):
    """Auto-fix common metadata issues (empty fields, inconsistencies)."""
    from nasmusic.core import get_music_dir
    from nasmusic.metadata import read_tags, write_tags
    from nasmusic.utils import find_audio_files

    target = path or get_music_dir()
    files = find_audio_files(target)
    fixed = 0

    for f in files:
        meta = read_tags(f)
        changed = False

        if not meta.title and f.stem:
            parts = f.stem.split(" - ", 1)
            if len(parts) == 2:
                meta.artist = meta.artist or parts[0].strip()
                meta.title = parts[1].strip()
            else:
                meta.title = f.stem
            changed = True

        if not meta.album_artist and meta.artist:
            meta.album_artist = meta.artist
            changed = True

        if not meta.album and f.parent.name != target.name:
            meta.album = f.parent.name
            changed = True

        if changed:
            if auto or typer.confirm(f"Fix {f.name}? ({meta.artist} - {meta.title})", default=True):
                write_tags(f, meta)
                fixed += 1

    console.print(f"\n[bold]Fixed {fixed}/{len(files)} files[/]")
