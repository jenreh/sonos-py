"""CLI commands: sonos config init / show / validate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.syntax import Syntax

from sonos.cli.render import console, print_error, print_ok
from sonos.core.config import (
    bootstrap_config_dir,
    config_path,
    load_config,
    validate_config,
)

app = typer.Typer(help="Manage sonos configuration.")


@app.command("init")
def config_init(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Create default config.toml (skips if already exists unless --force)."""
    d = config_dir or Path.home() / ".config" / "sonos-local"
    cfg = d / "config.toml"
    if cfg.exists() and not force:
        print_ok(f"Config already exists: {cfg}")
        return
    if cfg.exists() and force:
        cfg.unlink()
    bootstrap_config_dir(d)
    print_ok(f"Config created: {cfg}")


@app.command("show")
def config_show(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Display current effective configuration."""
    try:
        cfg = load_config(config_dir)
    except Exception as exc:
        print_error(f"Failed to load config: {exc}")
        raise typer.Exit(2) from exc

    if json_output:
        print(json.dumps(cfg.model_dump(mode="json"), ensure_ascii=False, indent=2))  # noqa: T201
        return

    path = config_path(config_dir)
    raw = path.read_text(encoding="utf-8") if path.exists() else "(file not found)"
    console.print(Syntax(raw, "toml", theme="monokai", line_numbers=True))


@app.command("validate")
def config_validate(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Validate config.toml and report errors."""
    errors = validate_config(config_dir)
    if json_output:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))  # noqa: T201
        sys.exit(0 if not errors else 2)

    if errors:
        for e in errors:
            print_error(e)
        raise typer.Exit(2)

    path = config_path(config_dir)
    print_ok(f"Config valid: {path}")
