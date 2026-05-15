"""FastMCP server entry point for sonos-py."""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from sonos.mcp_server.lifespan import app_lifespan
from sonos.mcp_server.resources import register_resources
from sonos.mcp_server.tools import register_tools

log = logging.getLogger(__name__)

mcp = FastMCP(
    "sonos",
    instructions=(
        "Lokaler Sonos-Controller. Steuere Lautsprecher, Gruppen, Wiedergabe, "
        "Lautstärke, Radio, Apple Music und Snapshots über dein Heimnetzwerk."
    ),
    lifespan=app_lifespan,
)

register_tools(mcp)
register_resources(mcp)


def main(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8765,
    config_dir: Path | None = None,
) -> None:
    if config_dir is not None:
        mcp._sonos_config_dir = config_dir  # noqa: SLF001

    if transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    elif transport in ("streamable-http", "http"):
        mcp.run_http_async(
            transport="streamable-http",
            host=host,
            port=port,
            show_banner=False,
        )
    else:
        raise ValueError(f"Unknown transport: {transport!r}. Use 'stdio' or 'streamable-http'.")
