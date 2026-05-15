"""Main Typer CLI entry point for the sonos command."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from sonos.cli.commands import (
    alarms,
    apple_music,
    config as config_cmd,
    discover,
    doctor,
    favorites,
    groups,
    mcp,
    playback,
    queue,
    radio,
    rooms,
    snapshot,
    sleep,
    status,
    volume,
)

app = typer.Typer(
    name="sonos",
    help="Local Sonos controller — no cloud, no account required.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Register sub-apps
app.add_typer(config_cmd.app, name="config")
app.add_typer(volume.app, name="volume")
app.add_typer(playback.app, name="playback")
app.add_typer(groups.app, name="groups")
app.add_typer(favorites.app, name="favorites")
app.add_typer(radio.app, name="radio")
app.add_typer(apple_music.app, name="apple")
app.add_typer(queue.app, name="queue")
app.add_typer(snapshot.app, name="snapshot")
app.add_typer(alarms.app, name="alarms")

# Single commands
app.command("discover")(discover.discover)
app.command("rooms")(rooms.rooms)
app.command("status")(status.status)
app.command("mute")(volume.mute)
app.command("unmute")(volume.unmute)
app.command("sleep")(sleep.sleep_set)
app.command("doctor")(doctor.doctor)
app.command("mcp")(mcp.mcp_server)


# ---------------------------------------------------------------------------
# Global state injected via callback
# ---------------------------------------------------------------------------

_state: dict = {}


@app.callback()
def _global_options(
    ctx: typer.Context,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", help="Override config directory"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output JSON instead of Rich text"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview action without executing"),
    ] = False,
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="Logging level"),
    ] = "WARNING",
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Force topology refresh before command"),
    ] = False,
) -> None:
    from sonos.core.logging import setup_logging

    setup_logging(level=log_level)
    _state.update(
        {
            "config_dir": config_dir,
            "json": json_output,
            "dry_run": dry_run,
            "refresh": refresh,
        }
    )
    ctx.ensure_object(dict)
    ctx.obj = _state


def get_state() -> dict:
    return _state


if __name__ == "__main__":
    app()
