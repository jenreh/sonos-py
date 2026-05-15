"""CLI command: sonos mcp."""

from __future__ import annotations

from pathlib import Path

import typer


def mcp_server(
    transport: str = typer.Option("stdio", "--transport", help="stdio or streamable-http"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (HTTP transport only)"),
    port: int = typer.Option(8765, "--port", help="Port (HTTP transport only)"),
    auth_token_env: str | None = typer.Option(
        None, "--auth-token-env", help="Env var for bearer token (enables remote)"
    ),
    config_dir: Path | None = typer.Option(None, "--config-dir"),
) -> None:
    """Start the FastMCP server (stdio or streamable-http)."""
    from sonos.mcp_server.server import main as mcp_main

    effective_host = host
    if auth_token_env and host == "127.0.0.1":
        effective_host = "0.0.0.0"  # noqa: S104

    mcp_main(transport=transport, host=effective_host, port=port, config_dir=config_dir)
