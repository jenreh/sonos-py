"""CLI commands: sonos queue."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table

app = typer.Typer(help="Queue management.")


@app.command("list")
def queue_list(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List items in the current queue."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        queue = await svc.list_queue(target)
        await svc.shutdown()
        return queue

    try:
        queue = run(_run())
    except SonosError as exc:
        handle_error(exc, "queue.list", json_output)
        return

    rows = [
        {
            "#": str(i.index),
            "title": i.title or "—",
            "artist": i.artist or "—",
            "album": i.album or "—",
        }
        for i in queue.items
    ]

    if json_output:
        print(_json.dumps(  # noqa: T201
            {
                "target": queue.target,
                "total": queue.total,
                "items": [{"index": i.index, "title": i.title, "artist": i.artist, "uri": i.uri} for i in queue.items],
            },
            indent=2,
        ))
    elif not rows:
        typer.echo("Queue is empty.")
    else:
        print_table(rows, title=f"Queue: {target}")


@app.command("clear")
def queue_clear(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Clear the current queue."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.clear_queue(target)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "queue.clear", json_output)


@app.command("play")
def queue_play(
    target: str = typer.Argument(...),
    index: int = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Play a specific queue item by index."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.play_queue_index(target, index)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "queue.play", json_output)


@app.command("remove")
def queue_remove(
    target: str = typer.Argument(...),
    index: int = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Remove an item from the queue (not yet supported)."""
    typer.echo("queue remove: not supported in this build", err=True)
    raise typer.Exit(5)
