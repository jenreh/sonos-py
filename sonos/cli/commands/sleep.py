"""CLI commands: sonos sleep."""

from __future__ import annotations

from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run


def sleep_set(
    target: str = typer.Argument(...),
    seconds: int | None = typer.Argument(None, help="Seconds; omit to clear timer"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Set or clear sleep timer."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        if seconds is None:
            result = await svc.clear_sleep_timer(target)
        else:
            result = await svc.set_sleep_timer(target, seconds)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "sleep", json_output)
