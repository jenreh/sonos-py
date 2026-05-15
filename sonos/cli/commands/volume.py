"""CLI commands: sonos volume / mute / unmute."""

from __future__ import annotations

from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.core.models import Scope

app = typer.Typer(help="Volume and mute controls.")


def _scope(s: str) -> Scope:
    try:
        return Scope(s)
    except ValueError:
        typer.echo(f"Invalid scope {s!r}. Use: room, group, all", err=True)
        raise typer.Exit(1) from None


@app.command("get")
def volume_get(
    target: str = typer.Argument(..., help="Room or speaker name"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Get current volume for a room."""
    import json as _json

    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        state = await svc.get_state(target)
        await svc.shutdown()
        return state

    try:
        state = run(_run())
    except SonosError as exc:
        handle_error(exc, "volume.get", json_output)
        return

    if json_output:
        print(_json.dumps({"target": target, "volume": state.volume, "muted": state.muted}, indent=2))  # noqa: T201
    else:
        typer.echo(f"{state.name}: volume={state.volume}  muted={state.muted}")


@app.command("set")
def volume_set(
    target: str = typer.Argument(...),
    value: int = typer.Argument(..., min=0, max=100),
    scope: str = typer.Option("room", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Set absolute volume."""
    from sonos.core.errors import SonosError

    if dry_run:
        typer.echo(f"[dry-run] would set volume {value} on {target!r} (scope={scope})")
        return

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.set_volume(target, value, _scope(scope))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "volume.set", json_output)


@app.command("up")
def volume_up(
    target: str = typer.Argument(...),
    step: int = typer.Option(5, "--step"),
    scope: str = typer.Option("room", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Increase volume by step."""
    from sonos.core.errors import SonosError

    if dry_run:
        typer.echo(f"[dry-run] would increase volume by {step} on {target!r}")
        return

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.adjust_volume(target, step, _scope(scope))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "volume.up", json_output)


@app.command("down")
def volume_down(
    target: str = typer.Argument(...),
    step: int = typer.Option(5, "--step"),
    scope: str = typer.Option("room", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Decrease volume by step."""
    from sonos.core.errors import SonosError

    if dry_run:
        typer.echo(f"[dry-run] would decrease volume by {step} on {target!r}")
        return

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.adjust_volume(target, -step, _scope(scope))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "volume.down", json_output)


def mute(
    target: str | None = typer.Argument(None),
    all_rooms: bool = typer.Option(False, "--all"),
    confirm: bool = typer.Option(False, "--confirm"),
    scope: str = typer.Option("room", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Mute a room (or all rooms with --all)."""
    from sonos.core.errors import ConfirmationRequired, SonosError

    effective_target = target or "all"
    effective_scope = Scope.ALL if all_rooms else _scope(scope)

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.set_mute(effective_target, True, effective_scope)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except ConfirmationRequired:
        typer.echo("Confirmation required for all rooms. Re-run with --confirm.", err=True)
        raise typer.Exit(7) from None
    except SonosError as exc:
        handle_error(exc, "mute", json_output)


def unmute(
    target: str | None = typer.Argument(None),
    all_rooms: bool = typer.Option(False, "--all"),
    scope: str = typer.Option("room", "--scope"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Unmute a room (or all rooms with --all)."""
    from sonos.core.errors import SonosError

    effective_target = target or "all"
    effective_scope = Scope.ALL if all_rooms else _scope(scope)

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.set_mute(effective_target, False, effective_scope)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "unmute", json_output)
