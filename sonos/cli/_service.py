"""Shared helper for running SonsoLocalService from CLI commands."""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, TypeVar

import typer

from sonos.cli.render import err_console, print_error

T = TypeVar("T")

_EXIT_CODES: dict[str, int] = {
    "config_error": 1,
    "network_error": 2,
    "target_not_found": 3,
    "policy_error": 4,
    "not_implemented": 5,
    "ambiguous_target": 6,
    "confirmation_required": 7,
    "playback_error": 8,
    "invalid_input": 9,
    "unknown": 10,
}


def run(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


async def make_service(config_dir: Path | None = None) -> Any:
    from sonos.core.app import SonsoLocalService

    svc = SonsoLocalService(config_dir=config_dir)
    await svc.startup()
    return svc


def handle_error(exc: Exception, action: str, json_output: bool) -> None:

    code = getattr(exc, "code", "unknown")
    exit_code = _EXIT_CODES.get(code, 8)
    if json_output:
        data = {"ok": False, "action": action, "error": {"code": code, "message": str(exc)}}
        print(json.dumps(data, ensure_ascii=False, indent=2))  # noqa: T201
    else:
        print_error(f"{action}: {exc}")
    raise typer.Exit(exit_code)


def output_result(result: Any, json_output: bool) -> None:
    """Print a CommandResult or dict."""
    if json_output:
        data = result.to_dict() if hasattr(result, "to_dict") else result
        print(json.dumps(data, ensure_ascii=False, indent=2))  # noqa: T201
        if hasattr(result, "ok") and not result.ok:
            sys.exit(result.exit_code or 1)
    elif hasattr(result, "ok"):
        if result.ok:
            from sonos.cli.render import print_ok
            print_ok(result.action)
        else:
            err = result.error
            msg = err.message if err else "unknown error"
            print_error(f"{result.action}: {msg}")
            raise typer.Exit(result.exit_code or 1)
    elif hasattr(result, "warnings") and result.warnings:
        for w in result.warnings:
            err_console.print(f"[yellow]![/yellow] {w}")
