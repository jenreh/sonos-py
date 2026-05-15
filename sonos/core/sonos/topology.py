"""Topology helper utilities."""

from __future__ import annotations

from sonos.core.models import SonosGroup, SonosTopology, Speaker


def find_coordinator(topology: SonosTopology, speaker_uid: str) -> Speaker | None:
    """Return the group coordinator for the speaker with the given UID."""
    speaker = next((s for s in topology.speakers if s.uid == speaker_uid), None)
    if speaker is None:
        return None
    if speaker.coordinator_uid is None or speaker.is_coordinator:
        return speaker
    return next((s for s in topology.speakers if s.uid == speaker.coordinator_uid), speaker)


def find_group(topology: SonosTopology, speaker_uid: str) -> SonosGroup | None:
    """Return the group containing the given speaker UID."""
    speaker = next((s for s in topology.speakers if s.uid == speaker_uid), None)
    if speaker is None or speaker.group_uid is None:
        return None
    return next((g for g in topology.groups if g.group_uid == speaker.group_uid), None)


def visible_speakers(topology: SonosTopology) -> list[Speaker]:
    return [s for s in topology.speakers if s.visible and s.available]
