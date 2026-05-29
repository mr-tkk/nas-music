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
def scan(path: Optional[Path] = typer.Argument(None, help="Directory to scan (defaults to music_dir)")):
    """Scan music directory and update database."""
    from nasmusic.organizer.scanner import scan_library

    print_info("Scanning library...")
    stats = scan_library(path)

    console.print(f"\n[bold]Scan complete:[/]")
    console.print(f"  Total files: {stats['total']}")
    console.print(f"  New: [green]{stats['new']}[/]")
    console.print(f"  Updated: [yellow]{stats['updated']}[/]")


@app.command()
def organize(
    path: Optional[Path] = typer.Argument(None, help="Source directory (defaults to music_dir)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be moved"),
):
    """Organize files into Artist/Album/Track structure."""
    from nasmusic.core import get_music_dir
    from nasmusic.organizer.mover import organize_directory

    target = path or get_music_dir()
    moves = organize_directory(target, dry_run=True)

    if not moves:
        print_info("All files are already organized.")
        return

    table = Table(title=f"{'Would move' if dry_run else 'Moving'} {len(moves)} files")
    table.add_column("From", style="dim")
    table.add_column("To", style="cyan")

    for src, dst in moves[:20]:
        table.add_row(src.name, str(dst.relative_to(target)))

    if len(moves) > 20:
        table.add_row("...", f"and {len(moves) - 20} more")

    console.print(table)

    if not dry_run:
        if typer.confirm(f"Move {len(moves)} files?", default=True):
            organize_directory(target, dry_run=False)
            print_success(f"Organized {len(moves)} files")


@app.command()
def duplicates(
    method: str = typer.Option("metadata", "--method", "-m", help="Detection method: metadata, hash"),
):
    """Find duplicate tracks in the library."""
    from nasmusic.organizer.duplicates import find_duplicates

    print_info(f"Searching for duplicates (method: {method})...")
    dupes = find_duplicates(method=method)

    if not dupes:
        print_success("No duplicates found.")
        return

    console.print(f"\n[bold]Found {len(dupes)} duplicate groups:[/]\n")
    for group in dupes[:20]:
        console.print(f"[yellow]Group ({group['count']} copies):[/]")
        for track in group["tracks"]:
            console.print(f"  - {track.get('file_path', '?')}")
        console.print()


@app.command()
def stats():
    """Show library statistics."""
    from nasmusic.core.database import get_database

    db = get_database()
    total = db.track_count()
    tracks = db.get_all_tracks(limit=100000)

    artists = set(t.get("artist") for t in tracks if t.get("artist"))
    albums = set((t.get("artist"), t.get("album")) for t in tracks if t.get("album"))
    with_cover = sum(1 for t in tracks if t.get("has_cover_art"))
    with_lyrics = sum(1 for t in tracks if t.get("has_lyrics"))
    complete_meta = sum(1 for t in tracks if t.get("metadata_quality") == "complete")

    sources = {}
    for t in tracks:
        s = t.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    console.print("\n[bold]Library Statistics[/]\n")
    table = Table(show_header=False, box=None)
    table.add_column("", style="dim", width=20)
    table.add_column("")

    table.add_row("Total tracks", str(total))
    table.add_row("Artists", str(len(artists)))
    table.add_row("Albums", str(len(albums)))
    table.add_row("With cover art", f"{with_cover}/{total}")
    table.add_row("With lyrics", f"{with_lyrics}/{total}")
    table.add_row("Complete metadata", f"{complete_meta}/{total}")

    console.print(table)

    if sources:
        console.print("\n[bold]By source:[/]")
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            console.print(f"  {src}: {count}")


@app.command()
def verify(path: Optional[Path] = typer.Argument(None, help="Directory to verify")):
    """Verify library integrity (missing files, incomplete metadata)."""
    from nasmusic.organizer.scanner import verify_library

    print_info("Verifying library...")
    issues = verify_library(path)

    total_issues = sum(len(v) for v in issues.values())
    if total_issues == 0:
        print_success("Library is healthy!")
        return

    console.print(f"\n[bold yellow]Found {total_issues} issues:[/]\n")

    if issues["missing_files"]:
        console.print(f"[red]Missing files ({len(issues['missing_files'])}):[/]")
        for f in issues["missing_files"][:10]:
            console.print(f"  - {f}")

    if issues["incomplete_metadata"]:
        console.print(f"\n[yellow]Incomplete metadata ({len(issues['incomplete_metadata'])}):[/]")
        for f in issues["incomplete_metadata"][:10]:
            console.print(f"  - {f}")

    if issues["no_cover"]:
        console.print(f"\n[dim]No cover art ({len(issues['no_cover'])})[/]")

    if issues["no_lyrics"]:
        console.print(f"\n[dim]No lyrics ({len(issues['no_lyrics'])})[/]")


@app.command()
def convert(
    path: Path = typer.Argument(..., help="File or directory to convert"),
    format: str = typer.Option("mp3", "--format", "-f"),
    bitrate: int = typer.Option(320, "--bitrate", "-b"),
):
    """Convert audio files to target format."""
    from nasmusic.organizer import convert_to_mp3, needs_conversion
    from nasmusic.utils import find_audio_files

    files = [path] if path.is_file() else find_audio_files(path)
    to_convert = [f for f in files if needs_conversion(f, format)]

    if not to_convert:
        print_info("No files need conversion.")
        return

    console.print(f"[bold]Converting {len(to_convert)} files to {format} {bitrate}kbps[/]")
    converted = 0

    for f in to_convert:
        try:
            convert_to_mp3(f, bitrate=bitrate)
            converted += 1
            print_success(f"Converted: {f.name}")
        except Exception as e:
            print_error(f"Failed: {f.name} - {e}")

    console.print(f"\n[bold]Converted {converted}/{len(to_convert)} files[/]")
