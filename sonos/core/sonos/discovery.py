"""Discovery helpers: SSDP, Zeroconf, static hosts."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


async def discover_zeroconf(timeout: float = 5.0) -> list[str]:
    """Discover Sonos IP addresses via Zeroconf _sonos._tcp.local."""
    try:
        from zeroconf import ServiceBrowser, Zeroconf
        from zeroconf._utils.ipaddress import cached_ip_addresses
    except ImportError:
        log.debug("zeroconf not available; skipping mDNS discovery")
        return []

    found: list[str] = []
    loop = asyncio.get_event_loop()

    class _Handler:
        def add_service(self, zc: Any, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info:
                for addr in info.parsed_addresses():
                    if addr not in found:
                        found.append(addr)
                        log.debug("Zeroconf found Sonos at %s", addr)

        def remove_service(self, zc: Any, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Any, type_: str, name: str) -> None:
            pass

    def _browse() -> list[str]:
        zc = Zeroconf()
        browser = ServiceBrowser(zc, "_sonos._tcp.local.", _Handler())  # noqa: F841
        import time

        time.sleep(timeout)
        zc.close()
        return found

    return await asyncio.to_thread(_browse)
