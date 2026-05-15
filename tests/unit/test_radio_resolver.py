"""Unit tests for RadioResolver using a mock RadioBrowserClient."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from sonos.core.config import SonosLocalConfig, RadioConfig, RadioAliasConfig
from sonos.core.errors import RadioAmbiguousError, RadioResolutionError
from sonos.core.radio.models import RadioStation, ResolvedRadioUrl
from sonos.core.radio.resolver import RadioResolver, _normalize


def _make_station(
    uuid: str,
    name: str,
    clicks: int = 1000,
    codec: str = "MP3",
    bitrate: int = 128,
    hls: bool = False,
    ok: bool = True,
) -> RadioStation:
    return RadioStation(
        stationuuid=uuid,
        name=name,
        url=f"http://stream.example.com/{uuid}",
        url_resolved=f"http://stream.example.com/{uuid}",
        homepage="",
        country="Germany",
        countrycode="DE",
        codec=codec,
        bitrate=bitrate,
        hls=hls,
        lastcheckok=ok,
        clickcount=clicks,
    )


@pytest.fixture()
def config_with_alias() -> SonosLocalConfig:
    cfg = SonosLocalConfig()
    cfg.radio.aliases["einslive"] = RadioAliasConfig(
        stationuuid="uuid-einslive",
        preferred_name="1LIVE",
        countrycode="DE",
        aliases=["einslive", "1live", "eins live"],
    )
    return cfg


def test_normalize() -> None:
    assert _normalize("1LIVE") == "1live"
    assert _normalize("Ö3") == "o3"


async def test_resolve_config_alias(config_with_alias: SonosLocalConfig) -> None:
    client = AsyncMock()
    client.resolve_play_url.return_value = ResolvedRadioUrl(
        stationuuid="uuid-einslive",
        name="1LIVE",
        url="http://stream.example.com/einslive",
        codec="MP3",
        bitrate=128,
    )
    resolver = RadioResolver(client, config_with_alias)
    result = await resolver.resolve_play_url("einslive")
    assert result.stationuuid == "uuid-einslive"
    client.resolve_play_url.assert_called_once_with("uuid-einslive")


async def test_search_applies_policy(config_with_alias: SonosLocalConfig) -> None:
    client = AsyncMock()
    hls_station = _make_station("uuid-hls", "HLS Radio", hls=True)
    low_bitrate = _make_station("uuid-low", "Low Bitrate", bitrate=32)
    good_station = _make_station("uuid-good", "Good Station", bitrate=128)
    client.search.return_value = [hls_station, low_bitrate, good_station]

    resolver = RadioResolver(client, config_with_alias)
    results = await resolver.search("radio", "DE", 10)

    uuids = [r.stationuuid for r in results]
    assert "uuid-good" in uuids
    assert "uuid-hls" not in uuids  # HLS blocked
    assert "uuid-low" not in uuids  # below min_bitrate


async def test_no_results_raises(config_with_alias: SonosLocalConfig) -> None:
    client = AsyncMock()
    client.search.return_value = []
    resolver = RadioResolver(client, config_with_alias)
    with pytest.raises(RadioResolutionError):
        await resolver.resolve_play_url("nonexistent station xyz")
