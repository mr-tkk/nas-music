from __future__ import annotations

import typer
from rich.console import Console

from nasmusic.cli.download import app as download_app
from nasmusic.cli.metadata import app as metadata_app
from nasmusic.cli.library import app as library_app
from nasmusic.cli.playlist import app as playlist_app

app = typer.Typer(
    name="nasmusic",
    help="NAS Music Library Manager - Download, organize, and manage your music for Navidrome",
    no_args_is_help=True,
)

app.add_typer(download_app, name="download", help="Download music from YouTube")
app.add_typer(metadata_app, name="metadata", help="Manage music metadata and tags")
app.add_typer(library_app, name="library", help="Manage music library organization")
app.add_typer(playlist_app, name="playlist", help="Manage playlists")

console = Console()


@app.command()
def config_init():
    """Initialize configuration file interactively."""
    from nasmusic.core import save_default_config, DEFAULT_CONFIG_PATH

    if DEFAULT_CONFIG_PATH.exists():
        overwrite = typer.confirm(f"Config already exists at {DEFAULT_CONFIG_PATH}. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    path = save_default_config()
    console.print(f"[green]Config created at:[/] {path}")
    console.print("Edit this file to set your music directory and API credentials.")


@app.command()
def config_show():
    """Show current configuration."""
    from nasmusic.core import get_config
    cfg = get_config()
    console.print(cfg.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
