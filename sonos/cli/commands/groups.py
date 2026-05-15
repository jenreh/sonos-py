"""CLI commands: sonos groups."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table

app = typer.Typer(help="Group management.")


@app.command("list")
def groups_list(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List current speaker groups."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        groups = await svc.list_groups()
        speakers = await svc.list_speakers()
        await svc.shutdown()
        return groups, {s.uid: s.name for s in speakers}

    try:
        groups, uid_names = run(_run())
    except SonosError as exc:
        handle_error(exc, "groups.list", json_output)
        return

    rows = [
        {
            "group": g.group_uid,
            "coordinator": uid_names.get(g.coordinator_uid, g.coordinator_uid),
            "members": ", ".join(uid_names.get(u, u) for u in g.member_uids),
        }
        for g in groups
    ]

    if json_output:
        print(_json.dumps({"groups": rows, "total": len(rows)}, indent=2))  # noqa: T201
    else:
        print_table(rows, title="Groups")


@app.command("join")
def groups_join(
    coordinator: str = typer.Argument(...),
    members: list[str] = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Add speakers to a group under coordinator."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.group(coordinator, list(members))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "groups.join", json_output)


@app.command("ungroup")
def groups_ungroup(
    targets: list[str] = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Remove speakers from their group."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.ungroup(list(targets))
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "groups.ungroup", json_output)


@app.command("isolate")
def groups_isolate(
    target: str = typer.Argument(...),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Isolate a speaker from its group."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.isolate(target)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "groups.isolate", json_output)
