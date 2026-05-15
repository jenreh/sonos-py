"""Media source detection and track metadata utilities."""

from __future__ import annotations

from sonos.core.models import MediaSource
from sonos.core.sonos.soco_backend import _detect_source


def detect_media_source(uri: str) -> MediaSource:
    return _detect_source(uri)


def format_duration(secs: int | None) -> str:
    if secs is None:
        return ""
    h, remainder = divmod(secs, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
