"""Radio station SQLite cache."""

from __future__ import annotations

import logging
from dataclasses import asdict

from sonos.core.radio.models import RadioStation
from sonos.storage.sqlite import get_db
from sonos.storage.repositories import RadioCacheRepository

log = logging.getLogger(__name__)


async def cache_station(station: RadioStation) -> None:
    async with get_db() as db:
        repo = RadioCacheRepository(db)
        await repo.upsert(station.stationuuid, _station_to_dict(station))


async def get_cached_station(stationuuid: str) -> RadioStation | None:
    async with get_db() as db:
        repo = RadioCacheRepository(db)
        row = await repo.get(stationuuid)
    if not row:
        return None
    return _dict_to_station(row["station"])


async def mark_played(stationuuid: str) -> None:
    async with get_db() as db:
        repo = RadioCacheRepository(db)
        await repo.mark_played(stationuuid)


def _station_to_dict(s: RadioStation) -> dict:
    d = {
        "stationuuid": s.stationuuid,
        "name": s.name,
        "url": s.url,
        "url_resolved": s.url_resolved,
        "homepage": s.homepage,
        "country": s.country,
        "countrycode": s.countrycode,
        "codec": s.codec,
        "bitrate": s.bitrate,
        "hls": s.hls,
        "lastcheckok": s.lastcheckok,
        "clickcount": s.clickcount,
        "tags": list(s.tags),
        "favicon": s.favicon,
    }
    return d


def _dict_to_station(d: dict) -> RadioStation:
    return RadioStation(
        stationuuid=d["stationuuid"],
        name=d["name"],
        url=d["url"],
        url_resolved=d.get("url_resolved", ""),
        homepage=d.get("homepage", ""),
        country=d.get("country", ""),
        countrycode=d.get("countrycode", ""),
        codec=d.get("codec", ""),
        bitrate=int(d.get("bitrate", 0) or 0),
        hls=bool(d.get("hls", False)),
        lastcheckok=bool(d.get("lastcheckok", False)),
        clickcount=int(d.get("clickcount", 0) or 0),
        tags=tuple(d.get("tags") or []),
        favicon=d.get("favicon"),
    )
