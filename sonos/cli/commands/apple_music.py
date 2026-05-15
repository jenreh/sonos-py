"""CLI commands: sonos apple."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from sonos.cli._service import handle_error, make_service, output_result, run
from sonos.cli.render import print_table
from sonos.core.models import Scope

app = typer.Typer(help="Apple Music integration.")


@app.command("auth")
def apple_auth(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
) -> None:
    """Show Apple Music auth status."""
    from sonos.core.config import load_config

    cfg = load_config(config_dir)
    am = cfg.apple_music
    dev = am.developer

    typer.echo(f"enabled:          {am.enabled}")
    typer.echo(f"developer.enabled:{dev.enabled}")
    typer.echo(f"key_id:           {dev.key_id or '—'}")
    typer.echo(f"team_id:          {dev.team_id or '—'}")
    typer.echo(f"key_path:         {dev.key_path or '—'}")
    typer.echo(f"default_storefront: {am.default_storefront}")


@app.command("search")
def apple_search(
    query: str = typer.Argument(...),
    type_: str = typer.Option("songs", "--type"),
    storefront: str = typer.Option("de", "--storefront"),
    limit: int = typer.Option(10, "--limit"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Search Apple Music catalog."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.search_apple_music(query, [type_], storefront, limit)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
    except SonosError as exc:
        handle_error(exc, "apple.search", json_output)
        return

    rows = [
        {
            "name": i.name,
            "artist": i.artist_name or "",
            "type": i.type,
            "url": i.url or "",
        }
        for i in result.items
    ]

    if json_output:
        print(_json.dumps(  # noqa: T201
            {"query": result.query, "total": result.total, "items": rows}, indent=2
        ))
    elif not rows:
        typer.echo(f"No Apple Music results for {query!r}.")
    else:
        print_table(rows, columns=["name", "artist", "type"], title=f"Apple Music: {query}")


@app.command("bind")
def apple_bind(
    alias: str = typer.Argument(...),
    url: str | None = typer.Option(None, "--url"),
    favorite: str | None = typer.Option(None, "--favorite"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
) -> None:
    """Bind an alias to an Apple Music share link or favorite ID."""
    from sonos.core.errors import SonosError

    if not url and not favorite:
        typer.echo("Provide --url or --favorite", err=True)
        raise typer.Exit(1)

    value = url or favorite

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.bind_apple_music_alias(alias, value, [alias])
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, False)
    except SonosError as exc:
        handle_error(exc, "apple.bind", False)


@app.command("play")
def apple_play(
    target: str = typer.Argument(...),
    item: str | None = typer.Argument(None),
    url: str | None = typer.Option(None, "--url"),
    scope: str = typer.Option("group", "--scope"),
    replace_queue: bool = typer.Option(True, "--replace-queue/--no-replace-queue"),
    isolate: bool = typer.Option(False, "--isolate"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Play Apple Music via alias, URL, or search."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        if url:
            result = await svc.play_apple_music_share_link(
                target, url, Scope(scope), isolate, replace_queue
            )
        elif item:
            result = await svc.play_apple_music(
                target, item, Scope(scope), isolate, replace_queue
            )
        else:
            typer.echo("Provide an item name or --url", err=True)
            raise typer.Exit(1)
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "apple.play", json_output)


@app.command("enqueue")
def apple_enqueue(
    target: str = typer.Argument(...),
    url: str = typer.Option(..., "--url"),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Add Apple Music share link to queue (append, don't replace)."""
    from sonos.core.errors import SonosError

    async def _run():
        svc = await make_service(config_dir)
        result = await svc.play_apple_music_share_link(
            target, url, Scope.GROUP, False, replace_queue=False
        )
        await svc.shutdown()
        return result

    try:
        result = run(_run())
        output_result(result, json_output)
    except SonosError as exc:
        handle_error(exc, "apple.enqueue", json_output)


@app.command("aliases")
def apple_aliases(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List saved Apple Music aliases."""
    from sonos.core.apple_music.aliases import list_aliases
    from sonos.core.config import load_config
    from sonos.core.errors import SonosError
    from sonos.storage.sqlite import set_db_path

    async def _run():
        cfg = load_config(config_dir)
        set_db_path(cfg.storage.sqlite_path_resolved)
        return await list_aliases()

    try:
        rows_raw = run(_run())
    except SonosError as exc:
        handle_error(exc, "apple.aliases", json_output)
        return

    rows = [
        {
            "alias": r["alias"],
            "kind": r.get("kind", ""),
            "url": r.get("share_url") or r.get("favorite_item_id") or "",
        }
        for r in rows_raw
    ]

    if json_output:
        print(_json.dumps(rows, indent=2))  # noqa: T201
    elif not rows:
        typer.echo("No Apple Music aliases saved.")
    else:
        print_table(rows, title="Apple Music Aliases")
