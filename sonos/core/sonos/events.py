"""SoCo event subscription manager.

Subscribes to Sonos UPnP event services and fires state-update callbacks.
Falls back to polling (managed by scheduler.py) when events are unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

log = logging.getLogger(__name__)

_EventCallback = Callable[[str, str, dict[str, Any]], None]


class EventManager:
    """Manages SoCo event subscriptions for a set of registered speakers."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Any]] = {}
        self._callbacks: list[_EventCallback] = []
        self._active = False

    def add_callback(self, callback: _EventCallback) -> None:
        self._callbacks.append(callback)

    async def subscribe_all(self, soco_by_uid: dict[str, Any]) -> None:
        """Subscribe to relevant services on each speaker."""
        for uid, soco in soco_by_uid.items():
            await self._subscribe_speaker(uid, soco)
        self._active = True

    async def _subscribe_speaker(self, uid: str, soco: Any) -> None:
        services = [
            ("ZoneGroupTopology", soco.zoneGroupTopology),
            ("RenderingControl", soco.renderingControl),
            ("AVTransport", soco.avTransport),
            ("ContentDirectory", soco.contentDirectory),
            ("DeviceProperties", soco.deviceProperties),
            ("AlarmClock", soco.alarmClock),
        ]
        self._subscriptions[uid] = []
        for name, service in services:
            try:
                sub = await asyncio.to_thread(service.subscribe, auto_renew=True)
                self._subscriptions[uid].append(sub)
                log.debug("Subscribed %s to %s events", uid, name)
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to subscribe %s to %s: %s", uid, name, exc)

    async def unsubscribe_all(self) -> None:
        for uid, subs in self._subscriptions.items():
            for sub in subs:
                try:
                    await asyncio.to_thread(sub.unsubscribe)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Failed to unsubscribe %s: %s", uid, exc)
        self._subscriptions.clear()
        self._active = False

    @property
    def active(self) -> bool:
        return self._active
