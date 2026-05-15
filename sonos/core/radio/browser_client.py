"""Radio Browser API client with DNS SRV mirror discovery and failover."""

from __future__ import annotations

import logging
import socket
from typing import Any

import aiohttp

from sonos.core.radio.models import RadioStation, ResolvedRadioUrl

log = logging.getLogger(__name__)

_USER_AGENT = "sonos-py/0.1.0 (https://github.com/jenreh/sonos-py)"
_FALLBACK_SERVERS = [
    "de1.api.radio-browser.info",
    "nl1.api.radio-browser.info",
    "at1.api.radio-browser.info",
]


def _discover_mirrors() -> list[str]:
    """Discover Radio Browser mirrors via DNS SRV records."""
    try:
        answers = socket.getaddrinfo(
            "_api._tcp.radio-browser.info", None, socket.AF_INET
        )
        servers = list({ans[4][0] for ans in answers})
        log.debug("Radio Browser mirrors: %s", servers)
        return servers if servers else _FALLBACK_SERVERS
    except Exception as exc:  # noqa: BLE001
        log.debug("DNS discovery failed: %s; using fallbacks", exc)
        return _FALLBACK_SERVERS


class RadioBrowserClient:
    def __init__(self, servers: list[str] | None = None, timeout: float = 10.0) -> None:
        self._servers = servers or _discover_mirrors()
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_exc: Exception | None = None
        for server in self._servers:
            url = f"https://{server}{path}"
            try:
                async with aiohttp.ClientSession(
                    headers={"User-Agent": _USER_AGENT},
                    timeout=self._timeout,
                ) as session:
                    async with session.get(url, params=params) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as exc:  # noqa: BLE001
                log.debug("Radio Browser server %s failed: %s", server, exc)
                last_exc = exc
        raise RuntimeError(f"All Radio Browser servers failed. Last: {last_exc}")

    async def search(
        self,
        query: str,
        countrycode: str | None = None,
        limit: int = 10,
        hidebroken: bool = True,
        lastcheckok: bool = True,
        codec: str | None = None,
        min_bitrate: int = 0,
    ) -> list[RadioStation]:
        params: dict[str, Any] = {
            "name": query,
            "limit": limit,
            "order": "clickcount",
            "reverse": "true",
            "hidebroken": "true" if hidebroken else "false",
            "lastcheckok": "1" if lastcheckok else "0",
        }
        if countrycode:
            params["countrycode"] = countrycode.upper()
        if codec:
            params["codec"] = codec
        if min_bitrate:
            params["bitrateMin"] = min_bitrate

        raw = await self._get("/json/stations/search", params)
        return [_parse_station(s) for s in raw]

    async def get_by_uuid(self, stationuuid: str) -> RadioStation:
        raw = await self._get(f"/json/stations/byuuid/{stationuuid}")
        if not raw:
            raise ValueError(f"Station {stationuuid!r} not found")
        return _parse_station(raw[0])

    async def resolve_play_url(self, stationuuid: str) -> ResolvedRadioUrl:
        raw = await self._get(f"/json/url/{stationuuid}")
        station = await self.get_by_uuid(stationuuid)
        url = raw.get("url") or station.url_resolved or station.url
        return ResolvedRadioUrl(
            stationuuid=stationuuid,
            name=station.name,
            url=url,
            codec=station.codec,
            bitrate=station.bitrate,
        )


def _parse_station(data: dict[str, Any]) -> RadioStation:
    return RadioStation(
        stationuuid=data.get("stationuuid", ""),
        name=data.get("name", ""),
        url=data.get("url", ""),
        url_resolved=data.get("url_resolved", ""),
        homepage=data.get("homepage", ""),
        country=data.get("country", ""),
        countrycode=data.get("countrycode", ""),
        codec=data.get("codec", ""),
        bitrate=int(data.get("bitrate", 0) or 0),
        hls=bool(data.get("hls", False)),
        lastcheckok=bool(data.get("lastcheckok", False)),
        clickcount=int(data.get("clickcount", 0) or 0),
        tags=tuple(t.strip() for t in (data.get("tags") or "").split(",") if t.strip()),
        favicon=data.get("favicon") or None,
    )
