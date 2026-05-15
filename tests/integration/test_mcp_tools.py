"""Integration tests for the FastMCP server tool registration."""

from __future__ import annotations

import asyncio

import pytest

from sonos.mcp_server.server import mcp


def test_all_tools_registered() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    required = {
        "sonos_list_speakers",
        "sonos_list_groups",
        "sonos_get_state",
        "sonos_adjust_volume",
        "sonos_set_volume",
        "sonos_set_mute",
        "sonos_transport",
        "sonos_play_favorite",
        "sonos_search_radio",
        "sonos_play_radio",
        "sonos_search_apple_music",
        "sonos_play_apple_music",
        "sonos_play_apple_music_share_link",
        "sonos_group",
        "sonos_ungroup",
        "sonos_isolate",
        "sonos_snapshot_save",
        "sonos_snapshot_restore",
        "sonos_queue",
        "sonos_sleep_timer",
        "sonos_list_alarms",
        "sonos_discover",
    }
    missing = required - names
    assert not missing, f"Missing tools: {missing}"


def test_all_resources_registered() -> None:
    resources = asyncio.run(mcp.list_resources())
    uris = {str(r.uri) for r in resources}
    required = {
        "sonos://speakers",
        "sonos://groups",
        "sonos://state",
        "sonos://capabilities",
        "sonos://config/policies",
        "sonos://radio/aliases",
        "sonos://apple-music/aliases",
    }
    missing = required - uris
    assert not missing, f"Missing resources: {missing}"


def test_tool_descriptions_present() -> None:
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        assert tool.description, f"Tool {tool.name!r} has no description"


def test_tool_schemas_have_no_ctx_param() -> None:
    """Context param must NOT appear in the MCP-exposed JSON schema."""
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        mcp_tool = tool.to_mcp_tool()
        schema = mcp_tool.inputSchema or {}
        props = schema.get("properties", {})
        assert "ctx" not in props, f"Tool {tool.name!r} leaks 'ctx' into schema"
