from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from nasmusic.utils.progress import print_success, print_error, print_info

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="list")
def list_playlists():
    """List all playlists."""
    from nasmusic.playlists import get_playlists

    playlists = get_playlists()
    if not playlists:
        print_info("No playlists yet. Use 'nasmusic playlist create' or 'nasmusic playlist import-*'.")
        return

    table = Table(title="Playlists")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name", style="cyan")
    table.add_column("Tracks", width=6)
    table.add_column("Source", style="dim")
    table.add_column("Created", style="dim")

    for pl in playlists:
        table.add_row(
            str(pl["id"]),
            pl["name"],
            str(pl.get("track_count", 0)),
            pl.get("source", "local"),
            pl.get("created_at", "")[:10],
        )

    console.print(table)


@app.command()
def create(name: str = typer.Argument(..., help="Playlist name")):
    """Create a new empty playlist."""
    from nasmusic.playlists import create_playlist

    pl_id = create_playlist(name)
    print_success(f"Created playlist '{name}' (ID: {pl_id})")


@app.command(name="import-netease")
def import_netease(url: str = typer.Argument(..., help="NetEase playlist URL")):
    """Import a playlist from NetEase Cloud Music."""
    from nasmusic.playlists.importer import import_netease_playlist, save_playlist_to_db

    print_info(f"Importing from NetEase: {url}")
    info = import_netease_playlist(url)

    if info is None:
        print_error("Failed to import playlist. Check the URL.")
        raise typer.Exit(1)

    console.print(f"[bold]{info.name}[/] - {len(info.tracks)} tracks")
    pl_id = save_playlist_to_db(info)
    print_success(f"Imported playlist '{info.name}' (ID: {pl_id})")


@app.command(name="import-spotify")
def import_spotify(url: str = typer.Argument(..., help="Spotify playlist URL")):
    """Import a Spotify playlist (downloads all tracks)."""
    from nasmusic.playlists.importer import import_spotify_playlist, save_playlist_to_db

    print_info(f"Importing from Spotify: {url}")
    info = import_spotify_playlist(url)

    if info is None:
        print_error("Failed to import playlist. Check the URL.")
        raise typer.Exit(1)

    pl_id = save_playlist_to_db(info)
    print_success(f"Imported playlist '{info.name}' (ID: {pl_id})")
    print_info("Use 'nasmusic download spotify <url>' to download all tracks.")


@app.command()
def export(
    name: str = typer.Argument(..., help="Playlist name or ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path"),
):
    """Export a playlist to M3U8 format (Navidrome compatible)."""
    from nasmusic.playlists import export_m3u8, get_playlists

    playlists = get_playlists()
    playlist = None

    if name.isdigit():
        playlist = next((p for p in playlists if p["id"] == int(name)), None)
    else:
        playlist = next((p for p in playlists if p["name"] == name), None)

    if not playlist:
        print_error(f"Playlist not found: {name}")
        raise typer.Exit(1)

    path = export_m3u8(playlist["id"], output)
    print_success(f"Exported to: {path}")


@app.command()
def sync():
    """Export all playlists to M3U8 for Navidrome."""
    from nasmusic.playlists import export_all_playlists

    paths = export_all_playlists()
    if not paths:
        print_info("No playlists to export.")
        return

    for p in paths:
        print_success(f"Exported: {p.name}")
    console.print(f"\n[bold]Synced {len(paths)} playlists[/]")


@app.command()
def download_all(
    name: str = typer.Argument(..., help="Playlist name or ID"),
    source: str = typer.Option("spotify", "--source", "-s"),
):
    """Download all pending tracks in a playlist."""
    from nasmusic.core.database import get_database
    from nasmusic.playlists import get_playlists
    from nasmusic.cli.download import _do_download

    db = get_database()
    playlists = get_playlists()

    playlist = None
    if name.isdigit():
        playlist = next((p for p in playlists if p["id"] == int(name)), None)
    else:
        playlist = next((p for p in playlists if p["name"] == name), None)

    if not playlist:
        print_error(f"Playlist not found: {name}")
        raise typer.Exit(1)

    cur = db.conn.execute(
        """SELECT pending_title, pending_artist, pending_source, pending_source_id
        FROM playlist_tracks
        WHERE playlist_id = ? AND track_id IS NULL AND pending_title IS NOT NULL""",
        (playlist["id"],),
    )
    pending = cur.fetchall()

    if not pending:
        print_info("No pending tracks to download.")
        return

    console.print(f"[bold]Downloading {len(pending)} pending tracks[/]")
    for row in pending:
        query = f"{row[1]} - {row[0]}" if row[1] else row[0]
        try:
            _do_download(source, query)
        except (typer.Exit, SystemExit):
            pass
        except Exception as e:
            print_error(str(e))
