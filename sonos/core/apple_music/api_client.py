"""Apple Music API HTTP client (MusicKit catalog and library search)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from sonos.core.errors import AppleMusicSearchFailed
from sonos.core.models import AppleMusicItem, AppleMusicSearchResult

log = logging.getLogger(__name__)

_BASE_URL = "https://api.music.apple.com/v1"
_USER_AGENT = "sonos-py/0.1.0"


class AppleMusicApiClient:
    def __init__(self, token_provider) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001
        self._tokens = token_provider

    async def _headers(self, require_user_token: bool = False) -> dict[str, str]:
        dev_token = await self._tokens.get_developer_token()
        headers = {
            "Authorization": f"Bearer {dev_token}",
            "User-Agent": _USER_AGENT,
        }
        if require_user_token:
            user_token = await self._tokens.require_user_token()
            headers["Music-User-Token"] = user_token
        return headers

    async def search_catalog(
        self,
        term: str,
        storefront: str,
        types: list[str],
        limit: int = 10,
    ) -> AppleMusicSearchResult:
        url = f"{_BASE_URL}/catalog/{storefront}/search"
        params: dict[str, Any] = {
            "term": term,
            "types": ",".join(types),
            "limit": limit,
        }
        try:
            headers = await self._headers(require_user_token=False)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
        except Exception as exc:  # noqa: BLE001
            raise AppleMusicSearchFailed(f"Catalog search failed: {exc}") from exc

        return _parse_search_result(term, storefront, data)

    async def search_library(
        self,
        term: str,
        types: list[str],
        limit: int = 10,
    ) -> AppleMusicSearchResult:
        url = f"{_BASE_URL}/me/library/search"
        params: dict[str, Any] = {"term": term, "types": ",".join(types), "limit": limit}
        try:
            headers = await self._headers(require_user_token=True)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
        except Exception as exc:  # noqa: BLE001
            raise AppleMusicSearchFailed(f"Library search failed: {exc}") from exc

        return _parse_search_result(term, "library", data)


def _parse_search_result(term: str, storefront: str, data: dict) -> AppleMusicSearchResult:
    items: list[AppleMusicItem] = []
    results = data.get("results", {})

    for type_key in ("songs", "albums", "playlists", "stations"):
        type_data = results.get(type_key, {})
        for item in type_data.get("data", []):
            attrs = item.get("attributes", {})
            art = attrs.get("artwork", {})
            art_url: str | None = None
            if art:
                w, h = art.get("width", 500), art.get("height", 500)
                art_url = art.get("url", "").replace("{w}", str(w)).replace("{h}", str(h))

            items.append(
                AppleMusicItem(
                    id=item.get("id", ""),
                    type=type_key.rstrip("s"),  # songs→song, etc.
                    name=attrs.get("name", ""),
                    artist_name=attrs.get("artistName") or None,
                    album_name=attrs.get("albumName") or None,
                    url=attrs.get("url", ""),
                    artwork_url=art_url,
                    storefront=storefront,
                    duration_ms=attrs.get("durationInMillis"),
                    explicit=attrs.get("contentRating") == "explicit",
                    playable_via_sonos=bool(attrs.get("url")),
                    playable_reason=None,
                )
            )

    return AppleMusicSearchResult(
        query=term,
        storefront=storefront,
        items=tuple(items),
        total=len(items),
    )
