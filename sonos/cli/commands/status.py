"""CLI command: sonos status."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

import typer

from sonos.cli._service import handle_error, make_service, run
from sonos.cli.render import print_table


def status(
    target: str | None = typer.Argument(None, help="Room or speaker name"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show current playback status for a room or all rooms."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.get_state(target)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
    except SonosError as exc:
        handle_error(exc, "status", json_output)
        return

    states = result if isinstance(result, list) else [result]

    def _fmt(s: Any) -> dict:
        track = ""
        if s.track_info:
            t = s.track_info
            parts = [p for p in [t.artist, t.title] if p]
            track = " – ".join(parts) if parts else t.uri or ""
        return {
            "name": s.name,
            "state": s.playback_state or "—",
            "volume": s.volume,
            "muted": "yes" if s.muted else "",
            "track": track,
        }

    rows = [_fmt(s) for s in states]

    if json_output:
        raw = [
            {
                "uid": s.uid,
                "name": s.name,
                "volume": s.volume,
                "muted": s.muted,
                "playback_state": s.playback_state,
                "source": s.source.value if s.source else None,
                "track": {
                    "title": s.track_info.title,
                    "artist": s.track_info.artist,
                    "album": s.track_info.album,
                    "uri": s.track_info.uri,
                } if s.track_info else None,
            }
            for s in states
        ]
        print(_json.dumps(raw if len(raw) > 1 else raw[0], indent=2))  # noqa: T201
    else:
        print_table(rows, columns=["name", "state", "volume", "muted", "track"], title="Status")
