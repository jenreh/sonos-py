"""Sleep timer helpers."""

from __future__ import annotations


def seconds_to_sonos_time(seconds: int) -> str:
    """Convert seconds to Sonos time format HH:MM:SS."""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
