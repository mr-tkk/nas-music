from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from nasmusic.utils.progress import print_success, print_error, print_info, create_progress

app = typer.Typer(no_args_is_help=True)
console = Console()


def _do_download(source: str, query: str):
    from nasmusic.core import get_config, get_music_dir
    from nasmusic.core.database import get_database
    from nasmusic.metadata import read_tags, write_tags, has_cover_art
    from nasmusic.metadata.cover_art import fetch_and_embed_cover
    from nasmusic.organizer import convert_to_mp3, needs_conversion
    from nasmusic.organizer.mover import organize_file

    cfg = get_config()
    music_dir = get_music_dir()
    db = get_database()

    print_info(f"Downloading from {source}: {query}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        if source == "spotify":
            from nasmusic.downloaders.spotify import SpotifyDownloader
            dl = SpotifyDownloader()
        elif source == "netease":
            from nasmusic.downloaders.netease import NeteaseDownloader
            dl = NeteaseDownloader()
        elif source == "qq":
            from nasmusic.downloaders.qqmusic import QQMusicDownloader
            dl = QQMusicDownloader(cookie=cfg.qqmusic.cookie)
        else:
            print_error(f"Unknown source: {source}")
            raise typer.Exit(1)

        result = dl.download(query, tmp_path)

        if not result.success:
            print_error(f"Download failed: {result.error}")
            db.add_download_history(query=query, source=source, status="failed", error_message=result.error)
            raise typer.Exit(1)

        filepath = result.file_path
        print_success(f"Downloaded: {filepath.name}")

        if needs_conversion(filepath, cfg.library.format):
            print_info("Converting to MP3 320kbps...")
            filepath = convert_to_mp3(filepath, bitrate=cfg.library.bitrate)
            print_success("Conversion complete")

        if result.metadata:
            write_tags(filepath, result.metadata)
            if result.metadata.cover_url and not has_cover_art(filepath):
                fetch_and_embed_cover(filepath, result.metadata.cover_url)

        metadata = read_tags(filepath)
        final_path = organize_file(filepath, metadata=metadata, music_dir=music_dir)

        if final_path:
            print_success(f"Organized to: {final_path.relative_to(music_dir)}")

            from nasmusic.utils import get_relative_path
            rel_path = get_relative_path(final_path, music_dir)
            db.add_track(
                file_path=rel_path,
                title=metadata.title,
                artist=metadata.artist,
                album_artist=metadata.album_artist,
                album=metadata.album,
                track_number=metadata.track_number,
                year=metadata.year,
                genre=metadata.genre,
                duration_seconds=metadata.duration_seconds,
                source=source,
                source_id=result.source_id,
                has_cover_art=1 if has_cover_art(final_path) else 0,
            )
            db.add_download_history(query=query, source=source, status="success")
        else:
            print_error("Failed to organize file")
            db.add_download_history(query=query, source=source, status="failed", error_message="Organization failed")


@app.command()
def spotify(query: str = typer.Argument(..., help="Song name, artist, or Spotify URL")):
    """Download music via Spotify/YouTube source."""
    _do_download("spotify", query)


@app.command()
def netease(query: str = typer.Argument(..., help="Song name or NetEase URL/ID")):
    """Download music from NetEase Cloud Music."""
    _do_download("netease", query)


@app.command()
def qq(query: str = typer.Argument(..., help="Song name or QQ Music URL/ID")):
    """Download music from QQ Music."""
    _do_download("qq", query)


@app.command()
def url(link: str = typer.Argument(..., help="Direct URL to download")):
    """Download from any URL supported by yt-dlp."""
    _do_download("spotify", link)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option("spotify", "--source", "-s", help="Source: spotify, netease, qq"),
    limit: int = typer.Option(10, "--limit", "-n"),
):
    """Search for music without downloading."""
    from nasmusic.core import get_config

    cfg = get_config()

    if source == "spotify":
        from nasmusic.downloaders.spotify import SpotifyDownloader
        dl = SpotifyDownloader()
    elif source == "netease":
        from nasmusic.downloaders.netease import NeteaseDownloader
        dl = NeteaseDownloader()
    elif source == "qq":
        from nasmusic.downloaders.qqmusic import QQMusicDownloader
        dl = QQMusicDownloader(cookie=cfg.qqmusic.cookie)
    else:
        print_error(f"Unknown source: {source}")
        raise typer.Exit(1)

    results = dl.search(query, limit=limit)

    if not results:
        print_info("No results found.")
        return

    table = Table(title=f"Search Results ({source})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan")
    table.add_column("Artist", style="green")
    table.add_column("Album", style="yellow")
    table.add_column("Duration", style="dim")

    for i, r in enumerate(results, 1):
        duration = f"{int(r.duration_seconds // 60)}:{int(r.duration_seconds % 60):02d}" if r.duration_seconds else ""
        table.add_row(str(i), r.title, r.artist, r.album, duration)

    console.print(table)


@app.command()
def batch(
    file: Path = typer.Argument(..., help="Text file with one query per line"),
    source: str = typer.Option("spotify", "--source", "-s", help="Source: spotify, netease, qq"),
):
    """Batch download from a text file (one query per line)."""
    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    queries = [line.strip() for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
    console.print(f"[bold]Processing {len(queries)} items from {file.name}[/]")

    success = 0
    failed = 0
    for i, query in enumerate(queries, 1):
        console.print(f"\n[dim][{i}/{len(queries)}][/] {query}")
        try:
            _do_download(source, query)
            success += 1
        except (typer.Exit, SystemExit):
            failed += 1
        except Exception as e:
            print_error(str(e))
            failed += 1

    console.print(f"\n[bold]Done:[/] {success} succeeded, {failed} failed")
