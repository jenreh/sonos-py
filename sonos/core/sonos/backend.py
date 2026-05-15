"""SonosBackend Protocol — the interface all SoCo operations go through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sonos.core.models import (
    EqPatch,
    SonosTopology,
    SpeakerState,
    TransportCommand,
)
from sonos.core.result import CommandResult


@runtime_checkable
class SonosBackend(Protocol):
    async def discover(self, refresh: bool = False) -> SonosTopology: ...

    async def subscribe_events(self) -> None: ...

    async def poll_state(self) -> None: ...

    async def get_speaker_state(self, speaker_uid: str) -> SpeakerState: ...

    async def set_volume(self, speaker_uid: str, volume: int) -> SpeakerState: ...

    async def adjust_volume(self, speaker_uid: str, delta: int) -> SpeakerState: ...

    async def set_mute(self, speaker_uid: str, muted: bool) -> SpeakerState: ...

    async def set_eq(self, speaker_uid: str, patch: EqPatch) -> SpeakerState: ...

    async def transport(
        self, coordinator_uid: str, command: TransportCommand
    ) -> CommandResult: ...

    async def play_uri(
        self,
        coordinator_uid: str,
        uri: str,
        title: str | None,
        force_radio: bool,
    ) -> CommandResult: ...

    async def play_favorite(
        self,
        coordinator_uid: str,
        favorite_item_id: str,
        replace_queue: bool,
    ) -> CommandResult: ...

    async def play_share_link(
        self,
        coordinator_uid: str,
        url: str,
        replace_queue: bool,
        title: str | None,
    ) -> CommandResult: ...

    async def join(
        self, coordinator_uid: str, member_uids: list[str]
    ) -> CommandResult: ...

    async def unjoin(self, speaker_uids: list[str]) -> CommandResult: ...

    async def seek(self, coordinator_uid: str, position: str) -> CommandResult: ...

    async def list_queue(self, coordinator_uid: str) -> list[dict]: ...

    async def clear_queue(self, coordinator_uid: str) -> CommandResult: ...

    async def play_from_queue(
        self, coordinator_uid: str, index: int
    ) -> CommandResult: ...

    async def remove_from_queue(
        self, coordinator_uid: str, index: int
    ) -> CommandResult: ...

    async def list_favorites(self, speaker_uid: str) -> list[dict]: ...

    async def list_alarms(self, speaker_uid: str) -> list[dict]: ...

    async def update_alarm(
        self, speaker_uid: str, alarm_id: str, patch: dict
    ) -> CommandResult: ...

    async def set_sleep_timer(
        self, speaker_uid: str, seconds: int
    ) -> CommandResult: ...

    async def clear_sleep_timer(self, speaker_uid: str) -> CommandResult: ...
