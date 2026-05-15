"""CLI command: sonos rooms."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, run
from sonos.cli.render import print_table


def rooms(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List configured rooms and their Sonos speaker mappings."""
    from sonos.core.errors import SonosError

    async def _run() -> list:
        svc = await make_service(config_dir)
        speakers = await svc.list_speakers()
        await svc.shutdown()
        return [
            {
                "name": s.name,
                "uid": s.uid,
                "ip": s.ip_address,
                "model": s.model_name,
                "coordinator": s.is_coordinator,
                "group": s.group_uid,
            }
            for s in speakers
        ]

    try:
        rows = run(_run())
    except SonosError as exc:
        handle_error(exc, "rooms", json_output)
        return

    if json_output:
        print(_json.dumps({"rooms": rows, "total": len(rows)}, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No rooms found. Run 'sonos discover' first.")
    else:
        print_table(rows, columns=["name", "ip", "model", "coordinator"], title="Rooms")
