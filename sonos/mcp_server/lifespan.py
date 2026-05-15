"""FastMCP lifespan: starts/stops SonsoLocalService."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from sonos.core.app import SonsoLocalService
from sonos.core.config import load_config


@asynccontextmanager
async def app_lifespan(mcp: FastMCP) -> AsyncIterator[dict[str, Any]]:  # noqa: ARG001
    config_dir: Path | None = getattr(mcp, "_sonos_config_dir", None)
    config = load_config(config_dir)
    service = SonsoLocalService(config)
    await service.startup()
    try:
        yield {"service": service}
    finally:
        await service.shutdown()
