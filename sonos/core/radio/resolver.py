"""Radio station resolver — alias lookup → Radio Browser search → scoring."""

from __future__ import annotations

import logging
import unicodedata

from sonos.core.config import SonosLocalConfig
from sonos.core.errors import RadioAmbiguousError, RadioResolutionError
from sonos.core.radio.browser_client import RadioBrowserClient
from sonos.core.radio.models import RadioStation, ResolvedRadioUrl
from sonos.storage.sqlite import get_db
from sonos.storage.repositories import RadioAliasRepository

log = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _score_station(station: RadioStation, query: str) -> int:
    score = 0
    norm_name = _normalize(station.name)
    norm_query = _normalize(query)
    if norm_name == norm_query:
        score += 100
    elif norm_name.startswith(norm_query):
        score += 50
    elif norm_query in norm_name:
        score += 25
    score += min(station.clickcount // 1000, 20)
    if station.lastcheckok:
        score += 10
    return score


class RadioResolver:
    def __init__(self, client: RadioBrowserClient, config: SonosLocalConfig) -> None:
        self._client = client
        self._config = config

    async def search(
        self, query: str, countrycode: str | None, limit: int
    ) -> list[RadioStation]:
        pol = self._config.policies.radio
        results = await self._client.search(
            query=query,
            countrycode=countrycode or pol.default_countrycode,
            limit=limit * 3,
            hidebroken=pol.hide_broken,
            lastcheckok=pol.require_lastcheckok,
            min_bitrate=pol.min_bitrate,
        )
        filtered = _apply_policy(results, pol)
        return filtered[:limit]

    async def resolve_play_url(self, query: str) -> ResolvedRadioUrl:
        """
        Resolution order:
        1. SQLite alias
        2. config.toml [radio.aliases] section
        3. Exact UUID
        4. Normalised name match
        5. Radio Browser search + scoring
        """
        # 1. SQLite alias
        try:
            async with get_db() as db:
                repo = RadioAliasRepository(db)
                alias_row = await repo.get(query)
            if alias_row:
                return await self._client.resolve_play_url(alias_row["stationuuid"])
        except Exception as exc:  # noqa: BLE001
            log.debug("SQLite alias lookup failed: %s", exc)

        # 2. config.toml aliases
        norm_query = _normalize(query)
        for key, alias_cfg in self._config.radio.aliases.items():
            if (
                _normalize(key) == norm_query
                or norm_query in [_normalize(a) for a in alias_cfg.aliases]
            ):
                if alias_cfg.stationuuid:
                    return await self._client.resolve_play_url(alias_cfg.stationuuid)

        # 3. Exact UUID
        if len(query) == 36 and query.count("-") == 4:  # noqa: PLR2004
            try:
                return await self._client.resolve_play_url(query)
            except Exception as exc:  # noqa: BLE001
                log.debug("UUID lookup failed: %s", exc)

        # 4+5. Radio Browser search
        pol = self._config.policies.radio
        candidates = await self._client.search(
            query=query,
            countrycode=pol.default_countrycode,
            limit=10,
            hidebroken=pol.hide_broken,
            lastcheckok=pol.require_lastcheckok,
            min_bitrate=pol.min_bitrate,
        )
        filtered = _apply_policy(candidates, pol)
        if not filtered:
            raise RadioResolutionError(
                f"No radio stations found for {query!r}. "
                "Try `sonos radio search` to find a station and bind an alias."
            )

        scored = sorted(filtered, key=lambda s: _score_station(s, query), reverse=True)
        best = scored[0]
        second = scored[1] if len(scored) > 1 else None

        # Ambiguous if top two scores are within 20 points and both name-match
        if second and _score_station(best, query) - _score_station(second, query) < 20:  # noqa: PLR2004
            top_two = [
                {"stationuuid": s.stationuuid, "name": s.name, "country": s.countrycode}
                for s in scored[:3]
            ]
            raise RadioAmbiguousError(query, top_two)

        return await self._client.resolve_play_url(best.stationuuid)


def _apply_policy(stations: list[RadioStation], pol) -> list[RadioStation]:  # type: ignore[no-untyped-def]  # noqa: ANN001
    result = []
    preferred_codecs = [c.upper() for c in pol.preferred_codecs]
    for s in stations:
        if pol.hide_broken and not s.lastcheckok:
            continue
        if not pol.allow_hls and s.hls:
            continue
        if pol.min_bitrate and s.bitrate < pol.min_bitrate:
            continue
        result.append(s)
    # Sort preferred codecs to front
    if preferred_codecs:
        result.sort(key=lambda s: (s.codec.upper() not in preferred_codecs, -s.clickcount))
    return result
