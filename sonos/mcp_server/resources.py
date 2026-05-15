"""FastMCP resources for sonos MCP server."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register all sonos:// resources on the given FastMCP instance."""

    def _svc(ctx: Context) -> Any:
        return ctx.lifespan_context["service"]

    @mcp.resource("sonos://speakers")
    async def speakers_resource(ctx: Context) -> list[dict[str, Any]]:
        speakers = await _svc(ctx).list_speakers()
        return [
            {
                "uid": s.uid,
                "name": s.name,
                "ip_address": s.ip_address,
                "model_name": s.model_name,
                "is_coordinator": s.is_coordinator,
                "group_uid": s.group_uid,
                "household_id": s.household_id,
            }
            for s in speakers
        ]

    @mcp.resource("sonos://groups")
    async def groups_resource(ctx: Context) -> list[dict[str, Any]]:
        groups = await _svc(ctx).list_groups()
        return [
            {
                "group_uid": g.group_uid,
                "coordinator_uid": g.coordinator_uid,
                "member_uids": list(g.member_uids),
                "household_id": g.household_id,
            }
            for g in groups
        ]

    @mcp.resource("sonos://state")
    async def state_resource(ctx: Context) -> dict[str, Any]:
        result = await _svc(ctx).get_state(None)
        if isinstance(result, list):
            return {"states": [_fmt_state(s) for s in result], "total": len(result)}
        return _fmt_state(result)

    @mcp.resource("sonos://capabilities")
    async def capabilities_resource(ctx: Context) -> dict[str, Any]:  # noqa: ARG001
        return {
            "features": [
                "volume",
                "mute",
                "transport",
                "favorites",
                "radio",
                "apple_music",
                "groups",
                "queue",
                "snapshot",
                "sleep_timer",
                "alarms",
            ],
            "transports": ["stdio", "streamable-http"],
        }

    @mcp.resource("sonos://config/policies")
    async def policies_resource(ctx: Context) -> dict[str, Any]:
        cfg = _svc(ctx)._config  # noqa: SLF001
        p = cfg.policies
        return {
            "volume": {
                "max_room_volume": p.volume.max_room_volume,
                "max_group_volume": p.volume.max_group_volume,
                "max_all_volume": p.volume.max_all_volume,
                "require_confirmation_for_all_rooms": p.volume.require_confirmation_for_all_rooms,
            },
            "playback": {
                "allow_arbitrary_urls": p.playback.allow_arbitrary_urls,
                "block_private_network_urls": p.playback.block_private_network_urls,
                "allowed_url_hosts": p.playback.allowed_url_hosts,
            },
            "apple_music": {
                "allow_catalog_search": p.apple_music.allow_catalog_search,
                "require_sonos_service": p.apple_music.require_sonos_service,
            },
        }

    @mcp.resource("sonos://radio/aliases")
    async def radio_aliases_resource(ctx: Context) -> dict[str, Any]:
        cfg = _svc(ctx)._config  # noqa: SLF001
        return {
            key: {
                "stationuuid": a.stationuuid,
                "preferred_name": a.preferred_name,
                "aliases": a.aliases,
                "countrycode": a.countrycode,
            }
            for key, a in cfg.radio.aliases.items()
        }

    @mcp.resource("sonos://apple-music/aliases")
    async def apple_music_aliases_resource(ctx: Context) -> dict[str, Any]:
        cfg = _svc(ctx)._config  # noqa: SLF001
        return {
            key: {
                "kind": a.kind,
                "url": a.url,
                "favorite_item_id": a.favorite_item_id,
                "aliases": a.aliases,
            }
            for key, a in cfg.apple_music.aliases.items()
        }


def _fmt_state(state: Any) -> dict[str, Any]:
    track = None
    if state.track_info:
        t = state.track_info
        track = {
            "title": t.title,
            "artist": t.artist,
            "album": t.album,
            "duration_secs": t.duration_secs,
            "position_secs": t.position_secs,
        }
    return {
        "uid": state.uid,
        "name": state.name,
        "volume": state.volume,
        "muted": state.muted,
        "playback_state": state.playback_state,
        "source": state.source.value if state.source else None,
        "track": track,
        "group_uid": state.group_uid,
        "coordinator_uid": state.coordinator_uid,
    }
