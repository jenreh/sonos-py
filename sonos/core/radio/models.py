"""Radio Browser domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RadioStation:
    stationuuid: str
    name: str
    url: str
    url_resolved: str
    homepage: str
    country: str
    countrycode: str
    codec: str
    bitrate: int
    hls: bool
    lastcheckok: bool
    clickcount: int
    tags: tuple[str, ...] = ()
    favicon: str | None = None


@dataclass(frozen=True)
class ResolvedRadioUrl:
    stationuuid: str
    name: str
    url: str
    codec: str
    bitrate: int
