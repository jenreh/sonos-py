"""SonsoLocalService — the single facade used by CLI and MCP server."""

from __future__ import annotations

import logging
from pathlib import Path

from sonos.core.config import SonosLocalConfig, load_config
from sonos.core.models import (
    Alarm,
    AlarmPatch,
    AppleMusicSearchResult,
    EqPatch,
    QueueState,
    Scope,
    SnapshotResult,
    SonosGroup,
    SonosTopology,
    Speaker,
    SpeakerState,
    TransportCommand,
)
from sonos.core.result import CommandResult
from sonos.core.resolver import TargetResolver
from sonos.core.sonos.soco_backend import SoCoBackend
from sonos.core.sonos.topology import find_coordinator
from sonos.storage.sqlite import init_db

log = logging.getLogger(__name__)


class SonsoLocalService:
    """Central service façade.  CLI and MCP both use this exclusively."""

    def __init__(
        self,
        config: SonosLocalConfig | None = None,
        config_dir: Path | None = None,
    ) -> None:
        self._config = config or load_config(config_dir)
        self._backend = SoCoBackend(
            discovery_timeout=self._config.network.discovery_timeout_seconds,
            static_hosts=self._config.network.hosts,
            ignore_invisible=self._config.sonos.ignore_invisible_devices,
        )
        self._resolver = TargetResolver(self._config)
        self._topology: SonosTopology | None = None

    async def startup(self) -> None:
        db_path = self._config.storage.sqlite_path_resolved
        await init_db(db_path)
        log.info("SonsoLocalService started; db=%s", db_path)

    async def shutdown(self) -> None:
        log.info("SonsoLocalService stopped")

    # ------------------------------------------------------------------
    # Topology
    # ------------------------------------------------------------------

    async def discover(self, refresh: bool = False) -> SonosTopology:
        self._topology = await self._backend.discover(refresh=refresh)
        return self._topology

    async def _topology_or_discover(self, refresh: bool = False) -> SonosTopology:
        if self._topology is None or refresh:
            return await self.discover(refresh=True)
        return self._topology

    async def list_speakers(self) -> list[Speaker]:
        topology = await self._topology_or_discover()
        return [s for s in topology.speakers if s.visible and s.available]

    async def list_groups(self) -> list[SonosGroup]:
        topology = await self._topology_or_discover()
        return list(topology.groups)

    async def get_state(self, target: str | None = None) -> SpeakerState | list[SpeakerState]:
        topology = await self._topology_or_discover()
        if target is not None:
            speaker = self._resolver.resolve(target, topology)
            return await self._backend.get_speaker_state(speaker.uid)
        # All speakers
        states = []
        for speaker in topology.speakers:
            if speaker.visible and speaker.available:
                try:
                    state = await self._backend.get_speaker_state(speaker.uid)
                    states.append(state)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Failed to get state for %s: %s", speaker.name, exc)
        return states

    def _resolve_target(
        self, target: str, topology: SonosTopology
    ) -> tuple[Speaker, Speaker]:
        """Return (speaker, coordinator) for a target string."""
        speaker = self._resolver.resolve(target, topology)
        coord = find_coordinator(topology, speaker.uid) or speaker
        return speaker, coord

    # ------------------------------------------------------------------
    # Volume / Mute / EQ
    # ------------------------------------------------------------------

    async def set_volume(self, target: str, volume: int, scope: Scope) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, coord = self._resolve_target(target, topology)
        uids = self._scope_uids(speaker, coord, scope, topology)
        for uid in uids:
            await self._backend.set_volume(uid, volume)
        return CommandResult.success(
            "volume.set",
            target={"input": target, "resolved_name": speaker.name},
            scope=scope,
            data={"volume": volume},
        )

    async def adjust_volume(self, target: str, delta: int, scope: Scope) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, coord = self._resolve_target(target, topology)
        uids = self._scope_uids(speaker, coord, scope, topology)
        for uid in uids:
            await self._backend.adjust_volume(uid, delta)
        return CommandResult.success(
            "volume.adjust",
            target={"input": target, "resolved_name": speaker.name},
            scope=scope,
            data={"delta": delta},
        )

    async def set_mute(self, target: str, muted: bool, scope: Scope) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, coord = self._resolve_target(target, topology)
        uids = self._scope_uids(speaker, coord, scope, topology)
        for uid in uids:
            await self._backend.set_mute(uid, muted)
        return CommandResult.success(
            "volume.mute",
            target={"input": target, "resolved_name": speaker.name},
            scope=scope,
            data={"muted": muted},
        )

    async def set_eq(self, target: str, patch: EqPatch, scope: Scope) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, coord = self._resolve_target(target, topology)
        uids = self._scope_uids(speaker, coord, scope, topology)
        for uid in uids:
            await self._backend.set_eq(uid, patch)
        return CommandResult.success("volume.eq", target={"input": target}, scope=scope)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    async def transport(
        self, target: str, command: TransportCommand, scope: Scope
    ) -> CommandResult:
        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        return await self._backend.transport(coord.uid, command)

    async def play_favorite(
        self, target: str, favorite: str, scope: Scope, isolate: bool
    ) -> CommandResult:
        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        return await self._backend.play_favorite(coord.uid, favorite, replace_queue=True)

    # ------------------------------------------------------------------
    # Radio
    # ------------------------------------------------------------------

    async def search_radio(
        self, query: str, countrycode: str | None, limit: int
    ) -> list:
        from sonos.core.radio.browser_client import RadioBrowserClient
        from sonos.core.radio.resolver import RadioResolver

        client = RadioBrowserClient()
        resolver = RadioResolver(client, self._config)
        return await resolver.search(query, countrycode, limit)

    async def play_radio(
        self, target: str, station: str, scope: Scope, isolate: bool
    ) -> CommandResult:
        from sonos.core.radio.browser_client import RadioBrowserClient
        from sonos.core.radio.resolver import RadioResolver

        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)

        client = RadioBrowserClient()
        resolver = RadioResolver(client, self._config)
        resolved = await resolver.resolve_play_url(station)

        return await self._backend.play_uri(
            coordinator_uid=coord.uid,
            uri=resolved.url,
            title=resolved.name,
            force_radio=True,
        )

    async def bind_radio_alias(
        self, alias: str, stationuuid: str, aliases: list[str]
    ) -> CommandResult:
        from sonos.storage.sqlite import get_db
        from sonos.storage.repositories import RadioAliasRepository

        async with get_db() as db:
            repo = RadioAliasRepository(db)
            await repo.upsert(alias, stationuuid, aliases)
        return CommandResult.success("radio.bind", data={"alias": alias, "stationuuid": stationuuid})

    # ------------------------------------------------------------------
    # Apple Music
    # ------------------------------------------------------------------

    async def search_apple_music(
        self, query: str, media_types: list[str], storefront: str, limit: int
    ) -> AppleMusicSearchResult:
        from sonos.core.apple_music.api_client import AppleMusicApiClient
        from sonos.core.apple_music.token_provider import AppleMusicTokenProvider

        token_provider = AppleMusicTokenProvider(self._config.apple_music)
        client = AppleMusicApiClient(token_provider)
        return await client.search_catalog(query, storefront, media_types, limit)

    async def play_apple_music(
        self,
        target: str,
        item: str,
        scope: Scope,
        isolate: bool,
        replace_queue: bool,
    ) -> CommandResult:
        from sonos.core.apple_music.resolver import AppleMusicResolver

        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        resolver = AppleMusicResolver(self._config)
        url = await resolver.resolve_to_url(item)
        return await self._backend.play_share_link(coord.uid, url, replace_queue, item)

    async def play_apple_music_share_link(
        self,
        target: str,
        url: str,
        scope: Scope,
        isolate: bool,
        replace_queue: bool,
    ) -> CommandResult:
        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        return await self._backend.play_share_link(coord.uid, url, replace_queue, None)

    async def bind_apple_music_alias(
        self, alias: str, url_or_favorite: str, aliases: list[str]
    ) -> CommandResult:
        from sonos.storage.sqlite import get_db
        from sonos.storage.repositories import AppleMusicAliasRepository

        is_url = url_or_favorite.startswith("http")
        async with get_db() as db:
            repo = AppleMusicAliasRepository(db)
            await repo.upsert(
                alias,
                kind="share_link" if is_url else "favorite",
                aliases=aliases,
                share_url=url_or_favorite if is_url else None,
                favorite_item_id=url_or_favorite if not is_url else None,
            )
        return CommandResult.success("apple_music.bind", data={"alias": alias})

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    async def group(self, coordinator: str, members: list[str]) -> CommandResult:
        topology = await self._topology_or_discover()
        coord_speaker = self._resolver.resolve(coordinator, topology)
        member_uids = [self._resolver.resolve(m, topology).uid for m in members]
        return await self._backend.join(coord_speaker.uid, member_uids)

    async def ungroup(self, targets: list[str]) -> CommandResult:
        topology = await self._topology_or_discover()
        uids = [self._resolver.resolve(t, topology).uid for t in targets]
        return await self._backend.unjoin(uids)

    async def isolate(self, target: str) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker = self._resolver.resolve(target, topology)
        return await self._backend.unjoin([speaker.uid])

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    async def list_queue(self, target: str) -> QueueState:
        from sonos.core.models import QueueItem

        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        items_raw = await self._backend.list_queue(coord.uid)
        items = tuple(
            QueueItem(
                index=r["index"],
                title=r.get("title"),
                artist=r.get("artist"),
                album=r.get("album"),
                uri=r.get("uri") or "",
                duration_secs=None,
            )
            for r in items_raw
        )
        return QueueState(
            target=target,
            coordinator_uid=coord.uid,
            items=items,
            total=len(items),
        )

    async def clear_queue(self, target: str) -> CommandResult:
        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        return await self._backend.clear_queue(coord.uid)

    async def play_queue_index(self, target: str, index: int) -> CommandResult:
        topology = await self._topology_or_discover()
        _, coord = self._resolve_target(target, topology)
        return await self._backend.play_from_queue(coord.uid, index)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    async def save_snapshot(
        self, targets: list[str], name: str | None
    ) -> SnapshotResult:
        import uuid
        from datetime import UTC, datetime

        from sonos.storage.sqlite import get_db
        from sonos.storage.repositories import SnapshotRepository

        topology = await self._topology_or_discover()
        snapshot_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload: dict = {"targets": {}}
        for t in targets:
            try:
                speaker = self._resolver.resolve(t, topology)
                state = await self._backend.get_speaker_state(speaker.uid)
                payload["targets"][t] = {
                    "uid": speaker.uid,
                    "volume": state.volume,
                    "muted": state.muted,
                    "group_uid": state.group_uid,
                    "coordinator_uid": state.coordinator_uid,
                }
            except Exception as exc:  # noqa: BLE001
                log.warning("Snapshot: failed to capture %s: %s", t, exc)

        async with get_db() as db:
            repo = SnapshotRepository(db)
            await repo.save(snapshot_id, name, payload)

        return SnapshotResult(
            snapshot_id=snapshot_id,
            name=name,
            targets=tuple(targets),
            created_at=created_at,
        )

    async def restore_snapshot(self, snapshot_id_or_name: str) -> CommandResult:
        from sonos.storage.sqlite import get_db
        from sonos.storage.repositories import SnapshotRepository

        async with get_db() as db:
            repo = SnapshotRepository(db)
            snap = await repo.get(snapshot_id_or_name)

        if snap is None:
            return CommandResult.failure(
                "snapshot.restore",
                code="target_not_found",
                message=f"Snapshot {snapshot_id_or_name!r} not found",
                exit_code=3,
            )

        payload = snap["payload"]
        for target_name, target_state in payload.get("targets", {}).items():
            try:
                uid = target_state["uid"]
                await self._backend.set_volume(uid, target_state["volume"])
                await self._backend.set_mute(uid, target_state["muted"])
            except Exception as exc:  # noqa: BLE001
                log.warning("Restore: failed to restore %s: %s", target_name, exc)

        return CommandResult.success("snapshot.restore", data={"snapshot_id": snap["snapshot_id"]})

    # ------------------------------------------------------------------
    # Alarms
    # ------------------------------------------------------------------

    async def list_alarms(self) -> list[Alarm]:
        topology = await self._topology_or_discover()
        speakers = [s for s in topology.speakers if s.visible and s.available]
        if not speakers:
            return []
        coordinator = next((s for s in speakers if s.is_coordinator), speakers[0])
        raw = await self._backend.list_alarms(coordinator.uid)
        uid_to_name = {s.uid: s.name for s in topology.speakers}
        return [
            Alarm(
                alarm_id=r["alarm_id"],
                enabled=r["enabled"],
                time=r["time"],
                recurrence=r["recurrence"],
                room_uid=r.get("room_uuid") or "",
                room_name=uid_to_name.get(r.get("room_uuid") or "", ""),
                volume=r["volume"],
                program_uri=r.get("program_uri"),
                program_metadata=_extract_title(r.get("program_metadata")),
                include_linked_zones=r.get("include_linked_zones", False),
            )
            for r in raw
        ]

    async def update_alarm(self, alarm_id: str, patch: AlarmPatch) -> CommandResult:
        speakers = await self.list_speakers()
        if not speakers:
            return CommandResult.failure(
                "alarms.update",
                code="network_error",
                message="No speakers available",
                exit_code=5,
            )
        coordinator = next((s for s in speakers if s.is_coordinator), speakers[0])
        patch_dict = {k: v for k, v in patch.__dict__.items() if v is not None}
        return await self._backend.update_alarm(coordinator.uid, alarm_id, patch_dict)

    async def create_alarm(
        self,
        target: str,
        start_time: str,
        recurrence: str = "DAILY",
        volume: int = 20,
        duration: str | None = None,
        enabled: bool = True,
        program_uri: str | None = None,
        program_metadata: str = "",
        include_linked_zones: bool = False,
    ) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker = self._resolver.resolve(target, topology)
        return await self._backend.create_alarm(
            speaker_uid=speaker.uid,
            start_time=start_time,
            recurrence=recurrence,
            volume=volume,
            duration=duration,
            enabled=enabled,
            program_uri=program_uri,
            program_metadata=program_metadata,
            include_linked_zones=include_linked_zones,
        )

    # ------------------------------------------------------------------
    # Sleep timer
    # ------------------------------------------------------------------

    async def set_sleep_timer(self, target: str, seconds: int) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, _ = self._resolve_target(target, topology)
        return await self._backend.set_sleep_timer(speaker.uid, seconds)

    async def clear_sleep_timer(self, target: str) -> CommandResult:
        topology = await self._topology_or_discover()
        speaker, _ = self._resolve_target(target, topology)
        return await self._backend.clear_sleep_timer(speaker.uid)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scope_uids(
        self,
        speaker: Speaker,
        coordinator: Speaker,
        scope: Scope,
        topology: SonosTopology,
    ) -> list[str]:
        if scope == Scope.ROOM:
            return [speaker.uid]
        if scope == Scope.GROUP:
            group = next(
                (g for g in topology.groups if g.group_uid == speaker.group_uid), None
            )
            if group:
                return list(group.member_uids)
            return [speaker.uid]
        # ALL
        return [s.uid for s in topology.speakers if s.visible and s.available]


def _extract_title(metadata: str | None) -> str | None:
    """Pull dc:title from DIDL-Lite metadata XML; return None if not parseable."""
    if not metadata:
        return None
    try:
        import defusedxml.ElementTree as ET  # type: ignore[import-untyped]  # noqa: N817

        root = ET.fromstring(metadata)
        el = root.find(".//{http://purl.org/dc/elements/1.1/}title")
        return el.text if el is not None else None
    except Exception:  # noqa: BLE001
        return None
