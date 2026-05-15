"""Per-speaker state cache, updated by events or polling."""

from __future__ import annotations

import logging
from typing import Any

from sonos.core.models import MediaSource, SpeakerState, TrackInfo
from sonos.core.sonos.soco_backend import _detect_source, _parse_secs

log = logging.getLogger(__name__)


class SpeakerStateCache:
    """In-memory cache of the last-known state for each speaker."""

    def __init__(self) -> None:
        self._states: dict[str, SpeakerState] = {}

    def update(self, uid: str, state: SpeakerState) -> None:
        self._states[uid] = state

    def get(self, uid: str) -> SpeakerState | None:
        return self._states.get(uid)

    def apply_rendering_control_event(self, uid: str, event: dict[str, Any]) -> None:
        state = self._states.get(uid)
        if state is None:
            return
        volume = int(event.get("volume", {}).get("Master", state.volume))
        muted_raw = event.get("mute", {}).get("Master", str(int(state.muted)))
        muted = muted_raw in ("1", "true", True, 1)
        self._states[uid] = SpeakerState(
            uid=state.uid,
            name=state.name,
            volume=volume,
            muted=muted,
            treble=state.treble,
            bass=state.bass,
            loudness=state.loudness,
            playback_state=state.playback_state,
            source=state.source,
            track_info=state.track_info,
            group_uid=state.group_uid,
            coordinator_uid=state.coordinator_uid,
        )

    def apply_av_transport_event(self, uid: str, event: dict[str, Any]) -> None:
        state = self._states.get(uid)
        if state is None:
            return
        playback_state = event.get(
            "transport_state", state.playback_state
        )
        uri = event.get("current_track_uri", "")
        source = _detect_source(uri) if uri else state.source

        track_meta = event.get("current_track_meta_data", {})
        if track_meta:
            track = TrackInfo(
                title=track_meta.get("title") or None,
                artist=track_meta.get("creator") or None,
                album=track_meta.get("album") or None,
                uri=uri or None,
                duration_secs=_parse_secs(track_meta.get("duration")),
                position_secs=None,
                album_art_uri=track_meta.get("album_art_uri") or None,
            )
        else:
            track = state.track_info

        self._states[uid] = SpeakerState(
            uid=state.uid,
            name=state.name,
            volume=state.volume,
            muted=state.muted,
            treble=state.treble,
            bass=state.bass,
            loudness=state.loudness,
            playback_state=playback_state,
            source=source,
            track_info=track,
            group_uid=state.group_uid,
            coordinator_uid=state.coordinator_uid,
        )
