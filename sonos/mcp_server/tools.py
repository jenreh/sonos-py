"""FastMCP tools for sonos MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from fastmcp import Context, FastMCP

from sonos.core.models import Scope, TransportCommand

if TYPE_CHECKING:
    pass


def register_tools(mcp: FastMCP) -> None:  # noqa: C901, PLR0915
    """Register all sonos_* tools on the given FastMCP instance."""

    def _svc(ctx: Context) -> Any:
        return ctx.lifespan_context["service"]

    @mcp.tool(description="Listet alle verfügbaren Sonos-Lautsprecher auf.")
    async def sonos_list_speakers(ctx: Context) -> dict[str, Any]:
        speakers = await _svc(ctx).list_speakers()
        return {
            "speakers": [
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
            ],
            "total": len(speakers),
        }

    @mcp.tool(description="Listet alle Sonos-Gruppen auf.")
    async def sonos_list_groups(ctx: Context) -> dict[str, Any]:
        groups = await _svc(ctx).list_groups()
        return {
            "groups": [
                {
                    "group_uid": g.group_uid,
                    "coordinator_uid": g.coordinator_uid,
                    "member_uids": list(g.member_uids),
                    "household_id": g.household_id,
                }
                for g in groups
            ],
            "total": len(groups),
        }

    @mcp.tool(description="Gibt den aktuellen Zustand eines oder aller Lautsprecher zurück.")
    async def sonos_get_state(
        ctx: Context,
        target: str | None = None,
    ) -> dict[str, Any]:
        result = await _svc(ctx).get_state(target)
        if isinstance(result, list):
            return {
                "states": [_state_dict(s) for s in result],
                "total": len(result),
            }
        return _state_dict(result)

    @mcp.tool(description="Passt die Lautstärke relativ an (delta positiv = lauter, negativ = leiser).")
    async def sonos_adjust_volume(
        ctx: Context,
        target: str,
        delta: int,
        scope: Literal["room", "group", "all"] = "room",
    ) -> dict[str, Any]:
        result = await _svc(ctx).adjust_volume(target, delta, Scope(scope))
        return result.to_dict()

    @mcp.tool(description="Setzt die Lautstärke auf einen absoluten Wert (0–100).")
    async def sonos_set_volume(
        ctx: Context,
        target: str,
        volume: int,
        scope: Literal["room", "group"] = "room",
    ) -> dict[str, Any]:
        result = await _svc(ctx).set_volume(target, volume, Scope(scope))
        return result.to_dict()

    @mcp.tool(description="Schaltet den Stummodus ein oder aus.")
    async def sonos_set_mute(
        ctx: Context,
        target: str,
        muted: bool,
        scope: Literal["room", "group", "all"] = "room",
    ) -> dict[str, Any]:
        result = await _svc(ctx).set_mute(target, muted, Scope(scope))
        return result.to_dict()

    @mcp.tool(description="Steuert die Wiedergabe: play, pause, stop, next, previous.")
    async def sonos_transport(
        ctx: Context,
        target: str,
        command: Literal["play", "pause", "stop", "next", "previous"],
        scope: Literal["group", "room", "all"] = "group",
    ) -> dict[str, Any]:
        result = await _svc(ctx).transport(target, TransportCommand(command), Scope(scope))
        return result.to_dict()

    @mcp.tool(description="Spielt einen Sonos-Favoriten auf einem Lautsprecher ab.")
    async def sonos_play_favorite(
        ctx: Context,
        target: str,
        favorite: str,
        scope: Literal["group", "room"] = "group",
        isolate: bool = False,
    ) -> dict[str, Any]:
        result = await _svc(ctx).play_favorite(target, favorite, Scope(scope), isolate)
        return result.to_dict()

    @mcp.tool(description="Durchsucht Radio Browser nach Sendern.")
    async def sonos_search_radio(
        ctx: Context,
        query: str,
        countrycode: str | None = "DE",
        limit: int = 10,
    ) -> dict[str, Any]:
        stations = await _svc(ctx).search_radio(query, countrycode, limit)
        return {
            "stations": [
                {
                    "stationuuid": s.stationuuid,
                    "name": s.name,
                    "url": s.url,
                    "codec": s.codec,
                    "bitrate": s.bitrate,
                    "country": s.country,
                    "countrycode": s.countrycode,
                }
                for s in stations
            ],
            "total": len(stations),
        }

    @mcp.tool(description="Spielt einen Radiosender (via Alias, UUID oder Suchbegriff) auf einem Lautsprecher ab.")
    async def sonos_play_radio(
        ctx: Context,
        target: str,
        station: str,
        stationuuid: str | None = None,
        scope: Literal["group", "room"] = "group",
        isolate: bool = False,
    ) -> dict[str, Any]:
        effective = stationuuid or station
        result = await _svc(ctx).play_radio(target, effective, Scope(scope), isolate)
        return result.to_dict()

    @mcp.tool(description="Sucht im Apple Music Katalog nach Songs, Alben oder Playlists.")
    async def sonos_search_apple_music(
        ctx: Context,
        query: str,
        media_types: list[Literal["songs", "albums", "playlists", "stations"]] | None = None,
        storefront: str | None = "de",
        limit: int = 10,
    ) -> dict[str, Any]:
        types = media_types or ["songs", "albums", "playlists"]
        result = await _svc(ctx).search_apple_music(
            query, types, storefront or "de", limit
        )
        return {
            "query": result.query,
            "storefront": result.storefront,
            "total": result.total,
            "items": [
                {
                    "id": i.id,
                    "type": i.type,
                    "name": i.name,
                    "artist_name": i.artist_name,
                    "album_name": i.album_name,
                    "url": i.url,
                }
                for i in result.items
            ],
        }

    @mcp.tool(description="Spielt Apple Music (Alias, Favorit, Song, Album, Playlist) auf einem Lautsprecher ab.")
    async def sonos_play_apple_music(
        ctx: Context,
        target: str,
        item: str,
        media_type: Literal[
            "alias", "favorite", "song", "album", "playlist", "station", "url"
        ] = "alias",
        url: str | None = None,
        scope: Literal["group", "room"] = "group",
        isolate: bool = False,
        replace_queue: bool = True,
    ) -> dict[str, Any]:
        svc = _svc(ctx)
        if media_type == "url" and url:
            result = await svc.play_apple_music_share_link(
                target, url, Scope(scope), isolate, replace_queue
            )
        else:
            result = await svc.play_apple_music(
                target, item, Scope(scope), isolate, replace_queue
            )
        return result.to_dict()

    @mcp.tool(description="Spielt einen Apple Music Share Link direkt auf einem Lautsprecher ab.")
    async def sonos_play_apple_music_share_link(
        ctx: Context,
        target: str,
        url: str,
        scope: Literal["group", "room"] = "group",
        isolate: bool = False,
        replace_queue: bool = True,
    ) -> dict[str, Any]:
        result = await _svc(ctx).play_apple_music_share_link(
            target, url, Scope(scope), isolate, replace_queue
        )
        return result.to_dict()

    @mcp.tool(description="Gruppiert Lautsprecher unter einem Koordinator.")
    async def sonos_group(
        ctx: Context,
        coordinator: str,
        members: list[str],
    ) -> dict[str, Any]:
        result = await _svc(ctx).group(coordinator, members)
        return result.to_dict()

    @mcp.tool(description="Löst eine oder mehrere Gruppen auf (jeder Lautsprecher solo).")
    async def sonos_ungroup(
        ctx: Context,
        targets: list[str],
    ) -> dict[str, Any]:
        result = await _svc(ctx).ungroup(targets)
        return result.to_dict()

    @mcp.tool(description="Trennt einen Lautsprecher von seiner Gruppe.")
    async def sonos_isolate(
        ctx: Context,
        target: str,
    ) -> dict[str, Any]:
        result = await _svc(ctx).isolate(target)
        return result.to_dict()

    @mcp.tool(description="Speichert einen Snapshot (Lautstärke, Quelle, Gruppe) für eine Liste von Zielen.")
    async def sonos_snapshot_save(
        ctx: Context,
        targets: list[str],
        name: str | None = None,
    ) -> dict[str, Any]:
        result = await _svc(ctx).save_snapshot(targets, name)
        return {
            "snapshot_id": result.snapshot_id,
            "name": result.name,
            "targets": list(result.targets),
            "created_at": result.created_at,
        }

    @mcp.tool(description="Stellt einen gespeicherten Snapshot wieder her.")
    async def sonos_snapshot_restore(
        ctx: Context,
        snapshot_id_or_name: str,
    ) -> dict[str, Any]:
        result = await _svc(ctx).restore_snapshot(snapshot_id_or_name)
        return result.to_dict()

    @mcp.tool(description="Listet die Warteschlange auf oder führt Aktionen darauf aus (clear, remove, play).")
    async def sonos_queue(
        ctx: Context,
        target: str,
        action: Literal["list", "clear", "remove", "play"] = "list",
        index: int | None = None,
    ) -> dict[str, Any]:
        svc = _svc(ctx)
        if action == "list":
            queue = await svc.list_queue(target)
            return {
                "target": queue.target,
                "total": queue.total,
                "items": [
                    {
                        "index": i.index,
                        "title": i.title,
                        "artist": i.artist,
                        "album": i.album,
                        "uri": i.uri,
                    }
                    for i in queue.items
                ],
            }
        if action == "clear":
            result = await svc.clear_queue(target)
            return result.to_dict()
        if action == "play" and index is not None:
            result = await svc.play_queue_index(target, index)
            return result.to_dict()
        return {"ok": False, "error": "action 'remove' requires index or is unsupported"}

    @mcp.tool(description="Setzt oder löscht einen Sleep-Timer (seconds=None zum Löschen).")
    async def sonos_sleep_timer(
        ctx: Context,
        target: str,
        seconds: int | None,
    ) -> dict[str, Any]:
        svc = _svc(ctx)
        if seconds is None:
            result = await svc.clear_sleep_timer(target)
        else:
            result = await svc.set_sleep_timer(target, seconds)
        return result.to_dict()

    @mcp.tool(description="Listet alle Alarme im Haushalt auf.")
    async def sonos_list_alarms(ctx: Context) -> dict[str, Any]:
        alarms = await _svc(ctx).list_alarms()
        return {
            "alarms": [
                {
                    "alarm_id": a.alarm_id,
                    "enabled": a.enabled,
                    "time": a.time,
                    "recurrence": a.recurrence,
                    "volume": a.volume,
                    "room_name": a.room_name,
                }
                for a in alarms
            ],
            "total": len(alarms),
        }

    @mcp.tool(description="Erzwingt eine neue Netzwerk-Erkennung der Sonos-Geräte.")
    async def sonos_discover(ctx: Context) -> dict[str, Any]:
        topology = await _svc(ctx).discover(refresh=True)
        return {
            "speakers": len(topology.speakers),
            "groups": len(topology.groups),
            "household_ids": list(topology.household_ids),
        }


def _state_dict(state: Any) -> dict[str, Any]:
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
