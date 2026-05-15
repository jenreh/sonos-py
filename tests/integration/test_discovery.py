"""Integration tests for discovery using a FakeBackend."""

from __future__ import annotations

import pytest

from sonos.core.config import SonosLocalConfig
from sonos.core.models import (
    EqPatch,
    SonosTopology,
    SpeakerState,
    TransportCommand,
)
from sonos.core.result import CommandResult
from sonos.core.sonos.backend import SonosBackend


class FakeSonosBackend:
    """In-memory SonosBackend for testing."""

    def __init__(self, topology: SonosTopology) -> None:
        self._topology = topology
        self._volumes: dict[str, int] = {}
        self._muted: dict[str, bool] = {}

    async def discover(self, refresh: bool = False) -> SonosTopology:
        return self._topology

    async def subscribe_events(self) -> None:
        pass

    async def poll_state(self) -> None:
        pass

    async def get_speaker_state(self, speaker_uid: str) -> SpeakerState:
        speaker = next(s for s in self._topology.speakers if s.uid == speaker_uid)
        return SpeakerState(
            uid=speaker_uid,
            name=speaker.name,
            volume=self._volumes.get(speaker_uid, 30),
            muted=self._muted.get(speaker_uid, False),
            treble=0,
            bass=0,
            loudness=False,
            playback_state="STOPPED",
            source="unknown",
            track_info=None,
            group_uid=speaker.group_uid,
            coordinator_uid=speaker.coordinator_uid,
        )

    async def set_volume(self, speaker_uid: str, volume: int) -> SpeakerState:
        self._volumes[speaker_uid] = volume
        return await self.get_speaker_state(speaker_uid)

    async def adjust_volume(self, speaker_uid: str, delta: int) -> SpeakerState:
        current = self._volumes.get(speaker_uid, 30)
        self._volumes[speaker_uid] = max(0, min(100, current + delta))
        return await self.get_speaker_state(speaker_uid)

    async def set_mute(self, speaker_uid: str, muted: bool) -> SpeakerState:
        self._muted[speaker_uid] = muted
        return await self.get_speaker_state(speaker_uid)

    async def set_eq(self, speaker_uid: str, patch: EqPatch) -> SpeakerState:
        return await self.get_speaker_state(speaker_uid)

    async def transport(self, coordinator_uid: str, command: TransportCommand) -> CommandResult:
        return CommandResult.success(f"transport.{command}")

    async def play_uri(self, coordinator_uid: str, uri: str, title: str | None, force_radio: bool) -> CommandResult:
        return CommandResult.success("transport.play_uri")

    async def play_favorite(self, coordinator_uid: str, favorite_item_id: str, replace_queue: bool) -> CommandResult:
        return CommandResult.success("transport.play_favorite")

    async def play_share_link(self, coordinator_uid: str, url: str, replace_queue: bool, title: str | None) -> CommandResult:
        return CommandResult.success("transport.play_share_link")

    async def join(self, coordinator_uid: str, member_uids: list[str]) -> CommandResult:
        return CommandResult.success("groups.join")

    async def unjoin(self, speaker_uids: list[str]) -> CommandResult:
        return CommandResult.success("groups.unjoin")

    async def seek(self, coordinator_uid: str, position: str) -> CommandResult:
        return CommandResult.success("transport.seek")

    async def list_queue(self, coordinator_uid: str) -> list[dict]:
        return []

    async def clear_queue(self, coordinator_uid: str) -> CommandResult:
        return CommandResult.success("queue.clear")

    async def play_from_queue(self, coordinator_uid: str, index: int) -> CommandResult:
        return CommandResult.success("queue.play")

    async def remove_from_queue(self, coordinator_uid: str, index: int) -> CommandResult:
        return CommandResult.success("queue.remove")

    async def list_favorites(self, speaker_uid: str) -> list[dict]:
        return []

    async def list_alarms(self, speaker_uid: str) -> list[dict]:
        return []

    async def update_alarm(self, speaker_uid: str, alarm_id: str, patch: dict) -> CommandResult:
        return CommandResult.success("alarms.update")

    async def set_sleep_timer(self, speaker_uid: str, seconds: int) -> CommandResult:
        return CommandResult.success("sleep.set")

    async def clear_sleep_timer(self, speaker_uid: str) -> CommandResult:
        return CommandResult.success("sleep.clear")


def test_fake_backend_implements_protocol(two_speaker_topology: SonosTopology) -> None:
    backend = FakeSonosBackend(two_speaker_topology)
    assert isinstance(backend, SonosBackend)


async def test_discover_returns_topology(two_speaker_topology: SonosTopology) -> None:
    backend = FakeSonosBackend(two_speaker_topology)
    topology = await backend.discover()
    assert len(topology.speakers) == 2
    assert topology.household_ids == frozenset(["HH1"])


async def test_volume_adjust(two_speaker_topology: SonosTopology) -> None:
    backend = FakeSonosBackend(two_speaker_topology)
    state = await backend.adjust_volume("RINCON_WZ", 10)
    assert state.volume == 40  # 30 + 10

    state2 = await backend.adjust_volume("RINCON_WZ", -50)
    assert state2.volume == 0  # clamp at 0


async def test_mute(two_speaker_topology: SonosTopology) -> None:
    backend = FakeSonosBackend(two_speaker_topology)
    state = await backend.set_mute("RINCON_WZ", True)
    assert state.muted is True
