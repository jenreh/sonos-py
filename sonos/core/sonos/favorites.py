"""Sonos Favorites cache — per-household, invalidated by ContentDirectory events."""

from __future__ import annotations

import logging

from sonos.core.models import MediaSource, SonosFavorite

log = logging.getLogger(__name__)

_APPLE_MUSIC_URI_PATTERNS = (
    "x-sonosapi-hls:catalog",
    "x-sonos-http:catalog",
    "x-sonosapi-stream:",
    "x-sonos-spotify:",
)


def _detect_favorite_source(uri: str | None) -> MediaSource:
    if not uri:
        return MediaSource.UNKNOWN
    uri_lower = uri.lower()
    if "apple" in uri_lower or "itunes" in uri_lower:
        return MediaSource.APPLE_MUSIC
    if "spotify" in uri_lower:
        return MediaSource.SPOTIFY_CONNECT
    if "x-rincon-mp3radio:" in uri_lower or "x-sonosapi-radio:" in uri_lower:
        return MediaSource.RADIO
    if "x-rincon-stream:" in uri_lower:
        return MediaSource.LINE_IN
    if "x-sonosapi-stream:" in uri_lower:
        return MediaSource.SONOS_FAVORITE
    return MediaSource.SONOS_FAVORITE


def parse_favorites(raw: dict, household_id: str) -> list[SonosFavorite]:
    """Convert SoCo get_sonos_favorites() output to SonosFavorite dataclasses."""
    favorites = raw.get("favorites", [])
    result: list[SonosFavorite] = []
    for fav in favorites:
        uri = fav.get("uri", "")
        source = _detect_favorite_source(uri)
        result.append(
            SonosFavorite(
                household_id=household_id,
                item_id=fav.get("id", ""),
                title=fav.get("title", ""),
                source=source,
                uri=uri or None,
                metadata_xml=fav.get("meta") or None,
                resource_metadata_xml=fav.get("resource_meta") or None,
                playable=bool(uri),
            )
        )
    log.debug(
        "Parsed %d favorites for household %s (%d playable)",
        len(result),
        household_id,
        sum(1 for f in result if f.playable),
    )
    return result
