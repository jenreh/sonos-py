"""Snapshot and restore helpers."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def build_snapshot_payload(
    speaker_states: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a serialisable snapshot payload from a list of speaker state dicts."""
    return {
        "version": 1,
        "targets": {
            s["uid"]: {
                "uid": s["uid"],
                "name": s["name"],
                "volume": s["volume"],
                "muted": s["muted"],
                "group_uid": s.get("group_uid"),
                "coordinator_uid": s.get("coordinator_uid"),
                "track_uri": s.get("track_uri"),
                "playback_state": s.get("playback_state", "STOPPED"),
            }
            for s in speaker_states
        },
    }
