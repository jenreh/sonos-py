"""CLI commands: sonos favorites."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table
from sonos.core.models import Scope

app = typer.Typer(help="Sonos favorites.")


@app.command("list")
def favorites_list(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
    source: str | None = typer.Option(None, "--source"),
) -> None:
    """List Sonos favorites."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        topology = await svc.discover()
        hids = list(topology.household_ids)
        result = []
        for hid in hids:
            favs = await svc._backend.list_favorites(hid)  # noqa: SLF001
            result.extend(favs)
        await svc.shutdown()
        return result

    try:
        favs = run(_run())
    except SonosError as exc:
        handle_error(exc, "favorites.list", json_output)
        return

    rows = [
        {
            "title": f.get("title", ""),
            "source": f.get("source", ""),
            "playable": str(f.get("playable", True)),
        }
        for f in favs
        if source is None or f.get("source") == source
    ]

    if json_output:
        print(_json.dumps({"favorites": rows, "total": len(rows)}, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No favorites found.")
    else:
        print_table(rows, title="Sonos Favorites")


@app.command("play")
def favorites_play(
    target: str = typer.Argument(...),
    favorite: str = typer.Argument(...),
    scope: str = typer.Option("group", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Play a Sonos favorite."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.play_favorite(target, favorite, Scope(scope), False)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "favorites.play", json_output)


@app.command("refresh")
def favorites_refresh(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
) -> None:
    """Refresh favorites cache from Sonos (re-discover topology)."""
    from sonos.cli.render import print_ok
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        await svc.discover(refresh=True)
        await svc.shutdown()

    try:
        run(_run())
        print_ok("Favorites refreshed.")
    except SonosError as exc:
        handle_error(exc, "favorites.refresh", False)
