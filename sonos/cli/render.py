"""Rich rendering helpers for CLI output."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def print_table(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
    title: str | None = None,
) -> None:
    if not rows:
        console.print("[dim]No results.[/dim]")
        return
    cols = columns or list(rows[0].keys())
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in cols:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(row.get(c, "")) for c in cols])
    console.print(table)


def print_ok(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_warn(message: str) -> None:
    err_console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message: str) -> None:
    err_console.print(f"[red]✗[/red] {message}")
