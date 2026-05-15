"""AlarmClock helpers — list, enable, disable, update."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def alarm_to_dict(alarm: object) -> dict:
    """Convert a soco.alarms.Alarm to a plain dict."""
    return {
        "alarm_id": str(getattr(alarm, "alarm_id", "")),
        "enabled": getattr(alarm, "enabled", False),
        "time": str(getattr(alarm, "start_time", "")),
        "recurrence": getattr(alarm, "recurrence", ""),
        "volume": getattr(alarm, "volume", 0),
        "program_uri": getattr(alarm, "program_uri", None),
        "include_linked_zones": getattr(alarm, "include_linked_zones", False),
    }
