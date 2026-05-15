"""Apple Music alias CRUD operations."""

from __future__ import annotations

import logging

from sonos.storage.sqlite import get_db
from sonos.storage.repositories import AppleMusicAliasRepository

log = logging.getLogger(__name__)


async def upsert_alias(
    alias: str,
    kind: str,
    aliases: list[str],
    favorite_item_id: str | None = None,
    share_url: str | None = None,
) -> None:
    async with get_db() as db:
        repo = AppleMusicAliasRepository(db)
        await repo.upsert(alias, kind, aliases, favorite_item_id, share_url)


async def get_alias(alias: str) -> dict | None:
    async with get_db() as db:
        repo = AppleMusicAliasRepository(db)
        return await repo.get(alias)


async def list_aliases() -> list[dict]:
    async with get_db() as db:
        repo = AppleMusicAliasRepository(db)
        return await repo.get_all()
