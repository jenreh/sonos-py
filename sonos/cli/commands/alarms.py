"""CLI commands: sonos alarms."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table
from sonos.core.models import AlarmPatch

app = typer.Typer(help="Sonos alarm management.")


@app.command("list")
def alarms_list(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List all alarms."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        alarms = await svc.list_alarms()
        await svc.shutdown()
        return alarms

    try:
        alarms = run(_run())
    except SonosError as exc:
        handle_error(exc, "alarms.list", json_output)
        return

    rows = [
        {
            "id": a.alarm_id,
            "enabled": "yes" if a.enabled else "no",
            "time": a.time,
            "recurrence": a.recurrence,
            "vol": str(a.volume),
            "room": a.room_name or "—",
            "content": a.program_metadata or "—",
        }
        for a in alarms
    ]

    if json_output:
        raw = [
            {
                "alarm_id": a.alarm_id,
                "enabled": a.enabled,
                "time": a.time,
                "recurrence": a.recurrence,
                "volume": a.volume,
                "room_name": a.room_name,
                "content": a.program_metadata,
                "program_uri": a.program_uri,
            }
            for a in alarms
        ]
        print(_json.dumps({"alarms": raw, "total": len(raw)}, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No alarms found.")
    else:
        print_table(rows, title="Alarms")


@app.command("enable")
def alarms_enable(
    alarm_id: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Enable an alarm."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.update_alarm(alarm_id, AlarmPatch(enabled=True))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "alarms.enable", json_output)


@app.command("disable")
def alarms_disable(
    alarm_id: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Disable an alarm."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.update_alarm(alarm_id, AlarmPatch(enabled=False))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "alarms.disable", json_output)


@app.command("update")
def alarms_update(
    alarm_id: str = typer.Argument(...),
    time: str | None = typer.Option(None, "--time"),
    enabled: bool | None = typer.Option(None, "--enabled/--disabled"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Update alarm properties."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        patch = AlarmPatch(enabled=enabled, time=time)
        result = await svc.update_alarm(alarm_id, patch)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "alarms.update", json_output)


@app.command("set")
def alarms_set(
    target: str = typer.Argument(..., help="Room / speaker name"),
    time: str = typer.Argument(..., help="Start time HH:MM or HH:MM:SS"),
    recurrence: str = typer.Option(
        "DAILY",
        "--recurrence",
        help="DAILY, WEEKDAYS, WEEKENDS, ONCE, or ON_<bitmask> (e.g. ON_1111100)",
    ),
    volume: int = typer.Option(20, "--volume", min=0, max=100),
    duration: str | None = typer.Option(None, "--duration", help="Play duration HH:MM"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
    station: str | None = typer.Option(
        None, "--station", help="Radio station alias/UUID (omit for buzzer)"
    ),
    linked_zones: bool = typer.Option(False, "--linked-zones"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create a new alarm on a room."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)

        program_uri: str | None = None
        program_metadata: str = ""

        if station:
            from sonos.core.radio.browser_client import RadioBrowserClient
            from sonos.core.radio.resolver import RadioResolver

            client = RadioBrowserClient()
            resolver = RadioResolver(client, svc._config)  # noqa: SLF001
            resolved = await resolver.resolve_play_url(station)
            program_uri = resolved.url

        result = await svc.create_alarm(
            target=target,
            start_time=time,
            recurrence=recurrence,
            volume=volume,
            duration=duration,
            enabled=enabled,
            program_uri=program_uri,
            program_metadata=program_metadata,
            include_linked_zones=linked_zones,
        )
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "alarms.set", json_output)
