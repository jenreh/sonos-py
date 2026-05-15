"""CLI commands: sonos radio."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table
from sonos.core.models import Scope

app = typer.Typer(help="Internet radio via Radio Browser.")


@app.command("search")
def radio_search(
    query: str = typer.Argument(...),
    country: str = typer.Option("DE", "--country"),
    limit: int = typer.Option(10, "--limit"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Search Radio Browser for stations."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        results = await svc.search_radio(query, country, limit)
        await svc.shutdown()
        return results

    try:
        stations = run(_run())
    except SonosError as exc:
        handle_error(exc, "radio.search", json_output)
        return

    rows = [
        {
            "name": s.name,
            "stationuuid": s.stationuuid,
            "codec": s.codec,
            "bitrate": s.bitrate,
            "country": s.countrycode,
        }
        for s in stations
    ]

    if json_output:
        print(_json.dumps({"stations": rows, "total": len(rows)}, indent=2))  # noqa: T201
    elif not rows:
        typer.echo(f"No stations found for {query!r}.")
    else:
        print_table(rows, title=f"Radio: {query}")


@app.command("bind")
def radio_bind(
    alias: str = typer.Argument(...),
    stationuuid: str = typer.Option(..., "--stationuuid"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
) -> None:
    """Bind an alias to a station UUID."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.bind_radio_alias(alias, stationuuid, [alias])
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, False)
    except SonosError as exc:
        handle_error(exc, "radio.bind", False)


@app.command("play")
def radio_play(
    target: str = typer.Argument(...),
    station: str = typer.Argument(...),
    scope: str = typer.Option("group", "--scope"),
    isolate: bool = typer.Option(False, "--isolate"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Play a radio station on a speaker."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.play_radio(target, station, Scope(scope), isolate)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "radio.play", json_output)


@app.command("aliases")
def radio_aliases(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List saved radio aliases."""
    from sonos.core.errors import SonosError
    from sonos.storage.repositories import RadioAliasRepository
    from sonos.storage.sqlite import get_db

    async def _run():
        from sonos.core.config import load_config
        from sonos.storage.sqlite import set_db_path

        cfg = load_config(config_dir)
        set_db_path(cfg.storage.sqlite_path_resolved)
        async with get_db() as db:
            repo = RadioAliasRepository(db)
            return await repo.get_all()

    try:
        rows_raw = run(_run())
    except SonosError as exc:
        handle_error(exc, "radio.aliases", json_output)
        return

    rows = [
        {
            "alias": r["alias"],
            "stationuuid": r["stationuuid"],
            "aliases": r.get("aliases", ""),
        }
        for r in rows_raw
    ]

    if json_output:
        print(_json.dumps(rows, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No radio aliases saved.")
    else:
        print_table(rows, title="Radio Aliases")
