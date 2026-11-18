"""CLI entry point for py-file-organizer."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from py_file_organizer.models import OrganizeMode
from py_file_organizer.organizer import Organizer
from py_file_organizer.rules import DEFAULT_RULES_FILE, init_rules_file, load_rules

app = typer.Typer(help="Batch file organizer with YAML rules, dry-run and undo.")
console = Console()
logger = logging.getLogger(__name__)


def _get_organizer() -> Organizer:
    return Organizer()


_DEFAULT_MODE = OrganizeMode.extension
_FOLDER_ARGUMENT = typer.Argument(..., help="Folder to organize.")
_RULES_OPTION = typer.Option(
    DEFAULT_RULES_FILE, "--rules", "-r", help="YAML rules file."
)
_STEPS_OPTION = typer.Option(
    1, "--steps", "-s", help="Number of last operations to revert."
)


@app.command()
def organize(
    folder: Path = _FOLDER_ARGUMENT,
    mode: Annotated[
        OrganizeMode,
        typer.Option("--mode", "-m", help="Grouping strategy."),
    ] = _DEFAULT_MODE,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Preview moves without touching disk."
    ),
    rules: Path = _RULES_OPTION,
) -> None:
    """Organize files in a folder by extension, date or size."""
    if not folder.is_dir():
        console.print(f"[red]Not a directory:[/red] {folder}")
        raise typer.Exit(code=1)

    rule_list = load_rules(rules)
    organizer = _get_organizer()

    result = organizer.organize(folder, mode, rule_list, dry_run=dry_run)

    table = Table(
        title="Organize result",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Mode", mode.value)
    table.add_row("Dry-run", "yes" if dry_run else "no")
    table.add_row("Moved", str(result.moved))
    table.add_row("Skipped", str(result.skipped))
    console.print(table)

    if result.operations and not dry_run:
        console.print("[green]Done.[/green] Use ``undo`` to revert.")
    elif dry_run:
        console.print("[yellow]Dry-run: no files were moved.[/yellow]")


@app.command()
def undo(
    steps: int = _STEPS_OPTION,
) -> None:
    """Undo the last N move operations."""
    organizer = _get_organizer()
    undone = organizer.undo(steps=steps)
    console.print(f"[green]Undid {undone} operation(s).[/green]")


@app.command()
def init_rules() -> None:
    """Generate a sample ``rules.yaml`` config file."""
    init_rules_file()
    console.print(f"[green]Sample rules written to[/green] {DEFAULT_RULES_FILE}")


if __name__ == "__main__":
    app()
