"""Unit tests for AppleMusicResolver."""

from __future__ import annotations

import pytest

from sonos.core.config import SonosLocalConfig, AppleMusicConfig, AppleMusicAliasConfig
from sonos.core.errors import AppleMusicDisabledError, AppleMusicNoResult
from sonos.core.apple_music.resolver import AppleMusicResolver, is_share_link


def test_is_share_link() -> None:
    assert is_share_link("https://music.apple.com/de/album/test/123")
    assert not is_share_link("https://open.spotify.com/track/xyz")
    assert not is_share_link("einslive")


async def test_disabled_raises() -> None:
    cfg = SonosLocalConfig()
    cfg.apple_music.enabled = False
    resolver = AppleMusicResolver(cfg)
    with pytest.raises(AppleMusicDisabledError):
        await resolver.resolve_to_url("chillmix")


async def test_direct_share_link_returned() -> None:
    cfg = SonosLocalConfig()
    resolver = AppleMusicResolver(cfg)
    url = "https://music.apple.com/de/album/discovery/697981168"
    result = await resolver.resolve_to_url(url)
    assert result == url


async def test_config_alias_resolved() -> None:
    cfg = SonosLocalConfig()
    cfg.apple_music.aliases["chillmix"] = AppleMusicAliasConfig(
        kind="share_link",
        url="https://music.apple.com/de/playlist/chill/pl.123",
        aliases=["chillmix", "chill mix"],
    )
    resolver = AppleMusicResolver(cfg)
    result = await resolver.resolve_to_url("chillmix")
    assert "music.apple.com" in result


async def test_no_match_raises() -> None:
    cfg = SonosLocalConfig()
    cfg.apple_music.developer.enabled = False
    cfg.policies.apple_music.allow_catalog_search = False
    resolver = AppleMusicResolver(cfg)
    with pytest.raises(AppleMusicNoResult):
        await resolver.resolve_to_url("some unknown track")
