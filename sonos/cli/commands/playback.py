"""CLI commands: sonos playback."""

from __future__ import annotations

from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.core.models import Scope, TransportCommand

app = typer.Typer(help="Playback transport controls.")


def _transport(target: str, cmd: TransportCommand, config_dir: Path | None, json_output: bool) -> None:
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.transport(target, cmd, Scope.GROUP)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, f"playback.{cmd.value}", json_output)


@app.command("play")
def playback_play(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Resume playback."""
    _transport(target, TransportCommand.PLAY, config_dir, json_output)


@app.command("pause")
def playback_pause(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Pause playback."""
    _transport(target, TransportCommand.PAUSE, config_dir, json_output)


@app.command("stop")
def playback_stop(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Stop playback."""
    _transport(target, TransportCommand.STOP, config_dir, json_output)


@app.command("next")
def playback_next(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Skip to next track."""
    _transport(target, TransportCommand.NEXT, config_dir, json_output)


@app.command("previous")
def playback_previous(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Go to previous track."""
    _transport(target, TransportCommand.PREVIOUS, config_dir, json_output)


@app.command("seek")
def playback_seek(
    target: str = typer.Argument(...),
    position: str = typer.Argument(..., help="Position as HH:MM:SS"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Seek to position (not yet supported by SoCo backend)."""
    typer.echo("seek: not supported in this build", err=True)
    raise typer.Exit(5)
