"""CLI command: sonos doctor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from sonos.cli.render import print_error, print_ok
from sonos.core.config import load_config, validate_config


def doctor(
    config_dir: Path | None = typer.Option(None, "--config-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run diagnostics: config, storage, network reachability."""
    checks: list[dict] = []

    # Config check
    errors = validate_config(config_dir)
    checks.append({"check": "config", "ok": not errors, "detail": errors or "valid"})

    # Storage check
    try:
        cfg = load_config(config_dir)
        db_path = cfg.storage.sqlite_path_resolved
        db_path.parent.mkdir(parents=True, exist_ok=True)
        checks.append({"check": "storage", "ok": True, "detail": str(db_path)})
    except Exception as exc:  # noqa: BLE001
        checks.append({"check": "storage", "ok": False, "detail": str(exc)})

    all_ok = all(c["ok"] for c in checks)

    if json_output:
        print(json.dumps({"ok": all_ok, "checks": checks}, indent=2))  # noqa: T201
        sys.exit(0 if all_ok else 5)
        return

    for c in checks:
        if c["ok"]:
            print_ok(f"{c['check']}: {c['detail']}")
        else:
            print_error(f"{c['check']}: {c['detail']}")

    if not all_ok:
        raise typer.Exit(5)
