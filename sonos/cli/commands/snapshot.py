"""CLI commands: sonos snapshot."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_ok, print_table

app = typer.Typer(help="Snapshot and restore.")


@app.command("save")
def snapshot_save(
    targets: list[str] = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Save a snapshot of current state."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.save_snapshot(list(targets), name)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
    except SonosError as exc:
        handle_error(exc, "snapshot.save", json_output)
        return

    if json_output:
        print(_json.dumps(  # noqa: T201
            {"snapshot_id": result.snapshot_id, "name": result.name, "targets": list(result.targets)},
            indent=2,
        ))
    else:
        print_ok(f"Snapshot saved: {result.snapshot_id} (name={result.name or '—'})")


@app.command("restore")
def snapshot_restore(
    name_or_id: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Restore a saved snapshot."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.restore_snapshot(name_or_id)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "snapshot.restore", json_output)


@app.command("list")
def snapshot_list(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List saved snapshots."""
    from sonos.core.config import load_config
    from sonos.core.errors import SonosError
    from sonos.storage.repositories import SnapshotRepository
    from sonos.storage.sqlite import get_db, set_db_path

    async def _run():
        cfg = load_config(config_dir)
        set_db_path(cfg.storage.sqlite_path_resolved)
        async with get_db() as db:
            repo = SnapshotRepository(db)
            return await repo.list_all()

    try:
        snaps = run(_run())
    except SonosError as exc:
        handle_error(exc, "snapshot.list", json_output)
        return

    rows = [
        {
            "id": s["snapshot_id"][:8] + "…",
            "name": s.get("name") or "—",
            "created": s.get("created_at", ""),
        }
        for s in snaps
    ]

    if json_output:
        print(_json.dumps(snaps, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No snapshots saved.")
    else:
        print_table(rows, title="Snapshots")
