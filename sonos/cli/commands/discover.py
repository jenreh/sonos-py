"""CLI command: sonos discover."""

from __future__ import annotations

from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, run
from sonos.cli.render import print_table


def discover(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
    timeout: float = typer.Option(5.0, "--timeout"),
) -> None:
    """Discover Sonos devices on the local network."""
    import json as _json

    from sonos.core.errors import SonosError

    async def _run() -> list:
        svc = await make_service(config_dir)
        topology = await svc.discover(refresh=True)
        await svc.shutdown()
        return [
            {
                "uid": s.uid,
                "name": s.name,
                "ip": s.ip_address,
                "model": s.model_name,
                "coordinator": s.is_coordinator,
                "group": s.group_uid,
            }
            for s in topology.speakers
            if s.visible
        ]

    try:
        speakers = run(_run())
    except SonosError as exc:
        handle_error(exc, "discover", json_output)
        return

    if json_output:
        print(_json.dumps({"speakers": speakers, "total": len(speakers)}, indent=2))  # noqa: T201
    elif not speakers:
        typer.echo("No Sonos speakers found.")
    else:
        print_table(speakers, columns=["name", "ip", "model", "coordinator", "group"], title="Discovered Speakers")
