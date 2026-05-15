"""Apple Music resolution: alias → favorite → share link → API search."""

from __future__ import annotations

import logging

from sonos.core.config import SonosLocalConfig
from sonos.core.errors import (
    AppleMusicAmbiguousResult,
    AppleMusicDisabledError,
    AppleMusicNoResult,
    InvalidAppleMusicShareLink,
)

log = logging.getLogger(__name__)

_APPLE_MUSIC_DOMAINS = ("music.apple.com",)


def is_share_link(url: str) -> bool:
    return any(domain in url for domain in _APPLE_MUSIC_DOMAINS)


class AppleMusicResolver:
    """
    Resolution order (spec §15.4):
    1. SQLite alias
    2. config.toml apple_music.aliases
    3. Direct share link
    4. Apple Music API catalog search → URL
    5. Library search (if user token present)
    """

    def __init__(self, config: SonosLocalConfig) -> None:
        self._config = config

    async def resolve_to_url(self, item: str) -> str:
        cfg = self._config.apple_music
        policy = self._config.policies.apple_music

        if not cfg.enabled:
            raise AppleMusicDisabledError("Apple Music is disabled in config.")

        # 1. SQLite alias (best-effort; skip if DB not yet initialised)
        from sonos.core.apple_music.aliases import get_alias

        try:
            alias_row = await get_alias(item)
        except RuntimeError:
            alias_row = None
        if alias_row:
            url = alias_row.get("share_url") or ""
            if url and is_share_link(url):
                return url

        # 2. config.toml aliases
        for key, alias_cfg in cfg.aliases.items():
            if key == item or item in alias_cfg.aliases:
                if alias_cfg.url and is_share_link(alias_cfg.url):
                    return alias_cfg.url

        # 3. Direct share link
        if is_share_link(item):
            return item

        # 4. API catalog search
        if policy.allow_catalog_search and cfg.developer.enabled:
            from sonos.core.apple_music.api_client import AppleMusicApiClient
            from sonos.core.apple_music.token_provider import AppleMusicTokenProvider

            token_provider = AppleMusicTokenProvider(cfg)
            client = AppleMusicApiClient(token_provider)
            result = await client.search_catalog(
                item, cfg.default_storefront, ["songs", "albums", "playlists"], limit=5
            )
            if result.total == 0:
                raise AppleMusicNoResult(f"No Apple Music results for {item!r}")
            if result.total > 1:
                candidates = [
                    {"id": i.id, "type": i.type, "name": i.name, "url": i.url}
                    for i in result.items[:3]
                ]
                raise AppleMusicAmbiguousResult(item, candidates)
            url = result.items[0].url
            if url and is_share_link(url):
                return url

        raise AppleMusicNoResult(
            f"Could not resolve Apple Music item {item!r}. "
            "Use `sonos apple bind` to create an alias or provide a direct URL."
        )
