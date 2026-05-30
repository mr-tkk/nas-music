from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from nasmusic.utils.progress import print_success, print_error, print_info

app = typer.Typer(no_args_is_help=True)
console = Console()


def _do_download(query: str):
    from nasmusic.core import get_config, get_music_dir
    from nasmusic.core.database import get_database
    from nasmusic.metadata import read_tags, write_tags, has_cover_art
    from nasmusic.metadata.cover_art import fetch_and_embed_cover
    from nasmusic.organizer import convert_to_mp3, needs_conversion
    from nasmusic.organizer.mover import organize_file
    from nasmusic.downloaders.youtube import YouTubeDownloader

    cfg = get_config()
    music_dir = get_music_dir()
    db = get_database()

    print_info(f"Downloading: {query}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dl = YouTubeDownloader()
        result = dl.download(query, tmp_path)

        if not result.success:
            print_error(f"Download failed: {result.error}")
            db.add_download_history(query=query, source="youtube", status="failed", error_message=result.error)
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
                source="youtube",
                source_id=result.source_id,
                has_cover_art=1 if has_cover_art(final_path) else 0,
            )
            db.add_download_history(query=query, source="youtube", status="success")
        else:
            print_error("Failed to organize file")
            db.add_download_history(query=query, source="youtube", status="failed", error_message="Organization failed")


@app.command("get")
def download_get(query: str = typer.Argument(..., help="Song name or YouTube URL")):
    """Download a song from YouTube."""
    _do_download(query)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n"),
):
    """Search for music on YouTube."""
    from nasmusic.downloaders.youtube import YouTubeDownloader

    dl = YouTubeDownloader()
    results = dl.search(query, limit=limit)

    if not results:
        print_info("No results found.")
        return

    table = Table(title="Search Results (YouTube)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan")
    table.add_column("Artist", style="green")
    table.add_column("Duration", style="dim")

    for i, r in enumerate(results, 1):
        duration = f"{int(r.duration_seconds // 60)}:{int(r.duration_seconds % 60):02d}" if r.duration_seconds else ""
        table.add_row(str(i), r.title, r.artist, duration)

    console.print(table)


@app.command()
def batch(
    file: Path = typer.Argument(..., help="Text file with one query per line"),
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
            _do_download(query)
            success += 1
        except (typer.Exit, SystemExit):
            failed += 1
        except Exception as e:
            print_error(str(e))
            failed += 1

    console.print(f"\n[bold]Done:[/] {success} succeeded, {failed} failed")
