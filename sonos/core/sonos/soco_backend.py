"""SoCo-backed implementation of SonosBackend.

All SoCo calls are synchronous; they run in a thread pool via asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sonos.core.errors import InvalidInputError, NetworkError, PlaybackError, TargetNotFoundError
from sonos.core.models import (
    EqPatch,
    MediaSource,
    Speaker,
    SonosGroup,
    SonosTopology,
    SpeakerState,
    TrackInfo,
    TransportCommand,
)
from sonos.core.result import CommandResult

log = logging.getLogger(__name__)

_RE_PLAYLIST_NO_NAME = __import__("re").compile(
    r"(https://music\.apple\.com/\w+/playlist/)(pl\.[-a-zA-Z0-9]+)$"
)


def _normalize_apple_music_url(url: str) -> str:
    """Add a placeholder name segment if the playlist URL is missing it.

    SoCo's AppleMusicShare regex requires /playlist/<name>/<pl.id>
    but share links are sometimes served without the name component.
    """
    m = _RE_PLAYLIST_NO_NAME.match(url)
    if m:
        return f"{m.group(1)}playlist/{m.group(2)}"
    return url


class SoCoRegistry:
    """Thread-safe map from uid → soco.SoCo instances."""

    def __init__(self) -> None:
        self._soco_by_uid: dict[str, Any] = {}

    def register(self, uid: str, soco: Any) -> None:
        self._soco_by_uid[uid] = soco

    def get(self, uid: str) -> Any:
        soco = self._soco_by_uid.get(uid)
        if soco is None:
            raise NetworkError(f"Speaker {uid!r} not in registry; run discover first.")
        return soco

    def all_uids(self) -> list[str]:
        return list(self._soco_by_uid.keys())


class SoCoBackend:
    """Async wrapper around the synchronous SoCo library."""

    def __init__(
        self,
        discovery_timeout: float = 5.0,
        static_hosts: list[str] | None = None,
        ignore_invisible: bool = True,
    ) -> None:
        self._discovery_timeout = discovery_timeout
        self._static_hosts = static_hosts or []
        self._ignore_invisible = ignore_invisible
        self._registry = SoCoRegistry()
        self._topology: SonosTopology | None = None

    async def _run_soco(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001,ANN201
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            # Translate SoCo-specific and network exceptions to domain errors.
            cls_name = type(exc).__name__
            module = type(exc).__module__ or ""
            if cls_name == "SoCoUPnPException":
                code = getattr(exc, "error_code", "") or "?"
                raise PlaybackError(f"UPnP error {code}: {exc}") from exc
            if cls_name in ("SoCoException", "SoCoSlaveException"):
                raise NetworkError(str(exc)) from exc
            if cls_name in ("ReadTimeout", "ConnectTimeout", "ConnectionError") or "requests" in module:
                raise NetworkError(f"Network timeout/error reaching Sonos device: {exc}") from exc
            raise

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _sync_discover(self, refresh: bool) -> SonosTopology:  # noqa: ARG002
        import soco
        import soco.discovery

        zones: set = set()

        # SSDP discovery
        try:
            discovered = soco.discover(timeout=self._discovery_timeout) or set()
            zones |= discovered
        except Exception as exc:  # noqa: BLE001
            log.warning("SSDP discovery failed: %s", exc)

        # Static hosts
        for host in self._static_hosts:
            try:
                zones.add(soco.SoCo(host))
            except Exception as exc:  # noqa: BLE001
                log.warning("Static host %s unreachable: %s", host, exc)

        if not zones:
            log.warning("No Sonos devices found")
            return SonosTopology(speakers=(), groups=(), household_ids=frozenset())

        speakers: list[Speaker] = []
        groups: dict[str, list[str]] = {}
        coordinators: dict[str, str] = {}
        household_ids: set[str] = set()

        for zone in zones:
            try:
                info = zone.get_speaker_info(refresh=True)
                group_info = zone.group
                household_id: str | None = None
                try:
                    household_id = zone.household_id
                except Exception:  # noqa: BLE001
                    pass

                if household_id:
                    household_ids.add(household_id)

                group_uid: str | None = None
                coordinator_uid: str | None = None
                is_coordinator = False

                if group_info:
                    group_uid = group_info.uid
                    if group_info.coordinator:
                        coordinator_uid = group_info.coordinator.uid
                        is_coordinator = zone.uid == coordinator_uid
                    members = [m.uid for m in group_info.members]
                    groups[group_uid] = members
                    coordinators[group_uid] = coordinator_uid or zone.uid

                speaker = Speaker(
                    uid=zone.uid,
                    name=info.get("zone_name", zone.player_name),
                    ip_address=zone.ip_address,
                    household_id=household_id,
                    visible=True,
                    available=True,
                    boot_seqnum=info.get("serial_number"),
                    model_name=info.get("model_name"),
                    coordinator_uid=coordinator_uid,
                    group_uid=group_uid,
                    is_coordinator=is_coordinator,
                    capabilities=frozenset(),
                )
                speakers.append(speaker)
                self._registry.register(zone.uid, zone)
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to get info for %s: %s", zone.ip_address, exc)

        sonos_groups = tuple(
            SonosGroup(
                group_uid=gid,
                household_id=next(
                    (s.household_id or "" for s in speakers if s.group_uid == gid),
                    "",
                ),
                coordinator_uid=coordinators.get(gid, ""),
                member_uids=tuple(members),
            )
            for gid, members in groups.items()
        )

        return SonosTopology(
            speakers=tuple(speakers),
            groups=sonos_groups,
            household_ids=frozenset(household_ids),
        )

    async def discover(self, refresh: bool = False) -> SonosTopology:
        if self._topology is not None and not refresh:
            return self._topology
        self._topology = await self._run_soco(self._sync_discover, refresh)
        return self._topology

    # ------------------------------------------------------------------
    # Events / Polling (stubs — implemented in Phase 4)
    # ------------------------------------------------------------------

    async def subscribe_events(self) -> None:
        log.debug("Event subscription not yet active")

    async def poll_state(self) -> None:
        log.debug("Polling not yet active")

    # ------------------------------------------------------------------
    # Speaker state
    # ------------------------------------------------------------------

    def _sync_get_speaker_state(self, uid: str) -> SpeakerState:
        soco = self._registry.get(uid)
        volume = soco.volume
        muted = soco.mute
        transport_info = soco.get_current_transport_info()
        track_info_raw = soco.get_current_track_info()

        playback_state = transport_info.get("current_transport_state", "STOPPED")

        uri = track_info_raw.get("uri", "")
        source = _detect_source(uri)

        track = TrackInfo(
            title=track_info_raw.get("title") or None,
            artist=track_info_raw.get("artist") or None,
            album=track_info_raw.get("album") or None,
            uri=uri or None,
            duration_secs=_parse_secs(track_info_raw.get("duration")),
            position_secs=_parse_secs(track_info_raw.get("position")),
            album_art_uri=track_info_raw.get("album_art") or None,
        )

        return SpeakerState(
            uid=uid,
            name=soco.player_name,
            volume=volume,
            muted=muted,
            treble=soco.treble,
            bass=soco.bass,
            loudness=soco.loudness,
            playback_state=playback_state,
            source=source,
            track_info=track,
            group_uid=soco.group.uid if soco.group else None,
            coordinator_uid=soco.group.coordinator.uid if soco.group and soco.group.coordinator else None,
        )

    async def get_speaker_state(self, speaker_uid: str) -> SpeakerState:
        return await self._run_soco(self._sync_get_speaker_state, speaker_uid)

    # ------------------------------------------------------------------
    # Volume / Mute / EQ
    # ------------------------------------------------------------------

    async def set_volume(self, speaker_uid: str, volume: int) -> SpeakerState:
        soco = self._registry.get(speaker_uid)
        await self._run_soco(setattr, soco, "volume", volume)
        return await self.get_speaker_state(speaker_uid)

    async def adjust_volume(self, speaker_uid: str, delta: int) -> SpeakerState:
        soco = self._registry.get(speaker_uid)
        current = await self._run_soco(getattr, soco, "volume")
        new_vol = max(0, min(100, current + delta))
        await self._run_soco(setattr, soco, "volume", new_vol)
        return await self.get_speaker_state(speaker_uid)

    async def set_mute(self, speaker_uid: str, muted: bool) -> SpeakerState:
        soco = self._registry.get(speaker_uid)
        await self._run_soco(setattr, soco, "mute", muted)
        return await self.get_speaker_state(speaker_uid)

    async def set_eq(self, speaker_uid: str, patch: EqPatch) -> SpeakerState:
        soco = self._registry.get(speaker_uid)

        def _apply() -> None:
            if patch.treble is not None:
                soco.treble = patch.treble
            if patch.bass is not None:
                soco.bass = patch.bass
            if patch.loudness is not None:
                soco.loudness = patch.loudness

        await self._run_soco(_apply)
        return await self.get_speaker_state(speaker_uid)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    async def transport(
        self, coordinator_uid: str, command: TransportCommand
    ) -> CommandResult:
        soco = self._registry.get(coordinator_uid)

        def _run() -> None:
            if command == TransportCommand.PLAY:
                soco.play()
            elif command == TransportCommand.PAUSE:
                soco.pause()
            elif command == TransportCommand.STOP:
                soco.stop()
            elif command == TransportCommand.NEXT:
                soco.next()
            elif command == TransportCommand.PREVIOUS:
                soco.previous()

        await self._run_soco(_run)
        return CommandResult.success(f"transport.{command}")

    async def play_uri(
        self,
        coordinator_uid: str,
        uri: str,
        title: str | None,
        force_radio: bool,
    ) -> CommandResult:
        soco = self._registry.get(coordinator_uid)

        def _run() -> None:
            soco.play_uri(uri=uri, title=title or "", force_radio=force_radio)

        await self._run_soco(_run)
        return CommandResult.success("transport.play_uri", media={"uri": uri, "title": title})

    async def play_favorite(
        self,
        coordinator_uid: str,
        favorite_item_id: str,
        replace_queue: bool,
    ) -> CommandResult:
        soco = self._registry.get(coordinator_uid)

        def _run() -> None:
            import difflib  # noqa: PLC0415

            favorites = list(soco.music_library.get_sonos_favorites())
            needle = favorite_item_id.lower()
            titles = [f.title for f in favorites]
            titles_lower = [t.lower() for t in titles]

            # exact id or case-insensitive title
            match = next(
                (
                    f
                    for f in favorites
                    if f.title.lower() == needle or getattr(f, "item_id", None) == favorite_item_id
                ),
                None,
            )
            # fuzzy fallback
            if match is None:
                close = difflib.get_close_matches(needle, titles_lower, n=1, cutoff=0.6)
                if close:
                    match = favorites[titles_lower.index(close[0])]
            if match is None:
                raise TargetNotFoundError(favorite_item_id)
            from soco.data_structures import DidlFavorite, to_didl_string  # noqa: PLC0415

            playable = match.reference if isinstance(match, DidlFavorite) else match
            uri = playable.resources[0].uri if playable.resources else ""
            meta = to_didl_string(playable)
            if replace_queue:
                soco.clear_queue()
            # container URIs (playlists) must go via queue; streams play directly
            if uri.startswith("x-rincon-cpcontainer:") or uri.startswith("x-rincon-playlist:"):
                # large playlists can take >20s to load; bump timeout
                soco.add_to_queue(playable, timeout=90)
                soco.play_from_queue(0)
            else:
                soco.play_uri(uri, meta=meta, start=True)

        await self._run_soco(_run)
        return CommandResult.success("transport.play_favorite")

    async def play_share_link(
        self,
        coordinator_uid: str,
        url: str,
        replace_queue: bool,
        title: str | None,
    ) -> CommandResult:
        from soco.plugins.sharelink import ShareLinkPlugin

        soco = self._registry.get(coordinator_uid)
        timeout = 30

        def _run() -> int:
            from soco.exceptions import SoCoUPnPException

            from sonos.core.errors import (
                AppleMusicNotAuthorizedOnSonos,
                AppleMusicQueueAddFailed,
                InvalidAppleMusicShareLink,
            )

            plugin = ShareLinkPlugin(soco)
            effective_url = _normalize_apple_music_url(url)
            if not plugin.is_share_link(effective_url):
                raise InvalidAppleMusicShareLink(url)
            if replace_queue:
                soco.clear_queue()
            try:
                queue_no = plugin.add_share_link_to_queue(
                    effective_url, dc_title=title or "", timeout=timeout
                )
            except SoCoUPnPException as exc:
                code = getattr(exc, "error_code", "") or ""
                msg = str(exc).lower()
                if code in ("801", "802") or "unauthorized" in msg or "not authorized" in msg:
                    raise AppleMusicNotAuthorizedOnSonos(
                        "Apple Music is not authorized on this Sonos system. "
                        "Open the Sonos app → Settings → Services & Voice → Music & Content, "
                        "add Apple Music, then retry."
                    ) from exc
                # Error 800 = generic playback failure (content unavailable, region, etc.)
                raise AppleMusicQueueAddFailed(
                    f"Sonos could not play this Apple Music content (UPnP {code or '?'}). "
                    "Check that Apple Music is set up in the Sonos app and the content is available in your region."
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise AppleMusicQueueAddFailed(str(exc)) from exc
            soco.play_from_queue(queue_no - 1)
            return queue_no

        queue_no = await self._run_soco(_run)
        return CommandResult.success(
            "transport.play_share_link",
            media={"url": url, "queue_position": queue_no},
        )

    async def seek(self, coordinator_uid: str, position: str) -> CommandResult:
        soco = self._registry.get(coordinator_uid)
        await self._run_soco(soco.seek, position)
        return CommandResult.success("transport.seek", data={"position": position})

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    async def list_queue(self, coordinator_uid: str) -> list[dict]:
        soco = self._registry.get(coordinator_uid)
        items = await self._run_soco(soco.get_queue)
        return [
            {
                "index": i,
                "title": getattr(item, "title", None),
                "artist": getattr(item, "creator", None),
                "album": getattr(item, "album", None),
                "uri": getattr(item, "resources", [None])[0].uri if getattr(item, "resources", None) else None,
                "duration": getattr(item, "duration", None),
            }
            for i, item in enumerate(items)
        ]

    async def clear_queue(self, coordinator_uid: str) -> CommandResult:
        soco = self._registry.get(coordinator_uid)
        await self._run_soco(soco.clear_queue)
        return CommandResult.success("queue.clear")

    async def play_from_queue(self, coordinator_uid: str, index: int) -> CommandResult:
        soco = self._registry.get(coordinator_uid)
        await self._run_soco(soco.play_from_queue, index)
        return CommandResult.success("queue.play", data={"index": index})

    async def remove_from_queue(self, coordinator_uid: str, index: int) -> CommandResult:
        soco = self._registry.get(coordinator_uid)
        queue = await self._run_soco(soco.get_queue)
        if index >= len(queue):
            raise IndexError(f"Queue index {index} out of range")
        await self._run_soco(soco.remove_from_queue, queue[index])
        return CommandResult.success("queue.remove", data={"index": index})

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    async def join(self, coordinator_uid: str, member_uids: list[str]) -> CommandResult:
        coordinator = self._registry.get(coordinator_uid)

        def _run() -> None:
            for uid in member_uids:
                member = self._registry.get(uid)
                member.join(coordinator)

        await self._run_soco(_run)
        return CommandResult.success("groups.join")

    async def unjoin(self, speaker_uids: list[str]) -> CommandResult:
        def _run() -> None:
            for uid in speaker_uids:
                soco = self._registry.get(uid)
                soco.unjoin()

        await self._run_soco(_run)
        return CommandResult.success("groups.unjoin")

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    async def list_favorites(self, speaker_uid: str) -> list[dict]:
        from sonos.core.sonos.favorites import _detect_favorite_source  # noqa: PLC0415

        soco = self._registry.get(speaker_uid)
        result = await self._run_soco(soco.music_library.get_sonos_favorites)
        out = []
        for item in result:
            uri = item.resources[0].uri if item.resources else ""
            out.append(
                {
                    "item_id": getattr(item, "item_id", ""),
                    "title": item.title,
                    "uri": uri,
                    "source": _detect_favorite_source(uri).value,
                }
            )
        return out

    # ------------------------------------------------------------------
    # Alarms
    # ------------------------------------------------------------------

    async def list_alarms(self, speaker_uid: str) -> list[dict]:
        from soco.alarms import get_alarms

        soco = self._registry.get(speaker_uid)
        alarms_set = await self._run_soco(get_alarms, soco)
        return [
            {
                "alarm_id": str(a.alarm_id),
                "enabled": a.enabled,
                "time": str(a.start_time),
                "duration": str(a.duration) if hasattr(a, "duration") else None,
                "recurrence": a.recurrence,
                "volume": a.volume,
                "room_uuid": getattr(a, "room_uuid", None),
                "program_uri": a.program_uri,
                "program_metadata": getattr(a, "program_metadata", None),
                "include_linked_zones": a.include_linked_zones,
            }
            for a in alarms_set
        ]

    async def update_alarm(
        self, speaker_uid: str, alarm_id: str, patch: dict
    ) -> CommandResult:
        from soco.alarms import get_alarms

        soco = self._registry.get(speaker_uid)

        def _run() -> None:
            alarms_set = get_alarms(soco)
            alarm = next((a for a in alarms_set if str(a.alarm_id) == alarm_id), None)
            if alarm is None:
                raise TargetNotFoundError(alarm_id)
            for key, value in patch.items():
                setattr(alarm, key, value)
            alarm.save()

        await self._run_soco(_run)
        return CommandResult.success("alarms.update", data={"alarm_id": alarm_id})

    async def create_alarm(
        self,
        speaker_uid: str,
        start_time: str,
        recurrence: str,
        volume: int,
        duration: str | None,
        enabled: bool,
        program_uri: str | None,
        program_metadata: str,
        include_linked_zones: bool,
    ) -> CommandResult:
        import datetime

        from soco.alarms import Alarm

        soco = self._registry.get(speaker_uid)

        def _parse_time(s: str) -> datetime.time:
            parts = s.split(":")
            if len(parts) == 2:  # noqa: PLR2004
                return datetime.time(int(parts[0]), int(parts[1]))
            if len(parts) == 3:  # noqa: PLR2004
                return datetime.time(int(parts[0]), int(parts[1]), int(parts[2]))
            raise InvalidInputError(f"Cannot parse time {s!r}. Use HH:MM or HH:MM:SS.")

        def _run() -> str:
            alarm = Alarm(
                zone=soco,
                start_time=_parse_time(start_time),
                duration=_parse_time(duration) if duration else None,
                recurrence=recurrence.upper(),
                enabled=enabled,
                program_uri=program_uri,
                program_metadata=program_metadata,
                volume=volume,
                include_linked_zones=include_linked_zones,
            )
            return str(alarm.save())

        alarm_id = await self._run_soco(_run)
        return CommandResult.success(
            "alarms.create",
            data={"alarm_id": alarm_id, "time": start_time, "recurrence": recurrence},
        )

    # ------------------------------------------------------------------
    # Sleep timer
    # ------------------------------------------------------------------

    async def set_sleep_timer(self, speaker_uid: str, seconds: int) -> CommandResult:
        soco = self._registry.get(speaker_uid)
        await self._run_soco(soco.set_sleep_timer, seconds)
        return CommandResult.success("sleep.set", data={"seconds": seconds})

    async def clear_sleep_timer(self, speaker_uid: str) -> CommandResult:
        soco = self._registry.get(speaker_uid)
        await self._run_soco(soco.set_sleep_timer, None)
        return CommandResult.success("sleep.clear")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_source(uri: str) -> MediaSource:
    if not uri:
        return MediaSource.UNKNOWN
    if "x-rincon-queue:" in uri:
        return MediaSource.QUEUE
    if "x-sonosapi-radio:" in uri or "x-rincon-mp3radio:" in uri:
        return MediaSource.RADIO
    if "x-sonos-spotify:" in uri or "x-sonos-spconnect:" in uri:
        return MediaSource.SPOTIFY_CONNECT
    if "x-rincon-stream:" in uri:
        return MediaSource.LINE_IN
    if "x-sonos-htastream:" in uri:
        return MediaSource.TV
    if "x-sonosapi-hls:" in uri and "applemusic" in uri.lower():
        return MediaSource.APPLE_MUSIC
    if "x-sonosapi-stream:" in uri:
        return MediaSource.SONOS_FAVORITE
    return MediaSource.UNKNOWN


def _parse_secs(duration: str | None) -> int | None:
    if not duration:
        return None
    try:
        parts = duration.split(":")
        if len(parts) == 3:  # noqa: PLR2004
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:  # noqa: PLR2004
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None
