import sys
import io

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True)


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def print_track_table(tracks: list[dict]):
    table = Table(title="Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan")
    table.add_column("Artist", style="green")
    table.add_column("Album", style="yellow")
    table.add_column("Source", style="dim")

    for i, t in enumerate(tracks, 1):
        table.add_row(
            str(i),
            t.get("title", "?"),
            t.get("artist", "?"),
            t.get("album", ""),
            t.get("source", ""),
        )

    console.print(table)


def print_success(msg: str):
    console.print(f"[bold green][OK][/] {msg}")


def print_error(msg: str):
    console.print(f"[bold red][FAIL][/] {msg}")


def print_warning(msg: str):
    console.print(f"[bold yellow][WARN][/] {msg}")


def print_info(msg: str):
    console.print(f"[bold blue][INFO][/] {msg}")
