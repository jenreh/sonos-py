"""Repository classes for each SQLite table."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)

_NOW = lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return dict(row)


# ---------------------------------------------------------------------------
# Speaker Repository
# ---------------------------------------------------------------------------


class SpeakerRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(self, speaker: dict[str, Any]) -> None:
        await self._db.execute(
            """
            INSERT INTO speakers (uid, name, ip_address, household_id, visible,
                available, boot_seqnum, model_name, updated_at)
            VALUES (:uid, :name, :ip_address, :household_id, :visible,
                :available, :boot_seqnum, :model_name, :updated_at)
            ON CONFLICT(uid) DO UPDATE SET
                name=excluded.name, ip_address=excluded.ip_address,
                household_id=excluded.household_id, visible=excluded.visible,
                available=excluded.available, boot_seqnum=excluded.boot_seqnum,
                model_name=excluded.model_name, updated_at=excluded.updated_at
            """,
            {**speaker, "updated_at": _NOW()},
        )
        await self._db.commit()

    async def get_all(self) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM speakers ORDER BY name")
        return [_row_to_dict(r) for r in await cur.fetchall()]

    async def get(self, uid: str) -> dict[str, Any] | None:
        cur = await self._db.execute("SELECT * FROM speakers WHERE uid = ?", (uid,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None

    async def mark_unavailable(self, uid: str) -> None:
        await self._db.execute(
            "UPDATE speakers SET available=0, updated_at=? WHERE uid=?", (_NOW(), uid)
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Group Repository
# ---------------------------------------------------------------------------


class GroupRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(self, group: dict[str, Any]) -> None:
        member_uids = group.get("member_uids", [])
        await self._db.execute(
            """
            INSERT INTO groups (group_uid, household_id, coordinator_uid,
                member_uids_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_uid) DO UPDATE SET
                household_id=excluded.household_id,
                coordinator_uid=excluded.coordinator_uid,
                member_uids_json=excluded.member_uids_json,
                updated_at=excluded.updated_at
            """,
            (
                group["group_uid"],
                group["household_id"],
                group["coordinator_uid"],
                json.dumps(list(member_uids)),
                _NOW(),
            ),
        )
        await self._db.commit()

    async def get_all(self) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM groups")
        rows = []
        for row in await cur.fetchall():
            d = _row_to_dict(row)
            d["member_uids"] = json.loads(d.pop("member_uids_json", "[]"))
            rows.append(d)
        return rows

    async def delete_all(self) -> None:
        await self._db.execute("DELETE FROM groups")
        await self._db.commit()


# ---------------------------------------------------------------------------
# Favorites Repository
# ---------------------------------------------------------------------------


class FavoritesRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(self, fav: dict[str, Any]) -> None:
        await self._db.execute(
            """
            INSERT INTO favorites (household_id, item_id, title, source, uri,
                metadata_xml, resource_metadata_xml, playable, updated_at)
            VALUES (:household_id, :item_id, :title, :source, :uri,
                :metadata_xml, :resource_metadata_xml, :playable, :updated_at)
            ON CONFLICT(household_id, item_id) DO UPDATE SET
                title=excluded.title, source=excluded.source, uri=excluded.uri,
                metadata_xml=excluded.metadata_xml,
                resource_metadata_xml=excluded.resource_metadata_xml,
                playable=excluded.playable, updated_at=excluded.updated_at
            """,
            {**fav, "updated_at": _NOW()},
        )
        await self._db.commit()

    async def get_by_household(self, household_id: str) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM favorites WHERE household_id = ? ORDER BY title",
            (household_id,),
        )
        return [_row_to_dict(r) for r in await cur.fetchall()]

    async def delete_by_household(self, household_id: str) -> None:
        await self._db.execute(
            "DELETE FROM favorites WHERE household_id = ?", (household_id,)
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Radio Alias Repository
# ---------------------------------------------------------------------------


class RadioAliasRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(self, alias: str, stationuuid: str, aliases: list[str]) -> None:
        await self._db.execute(
            """
            INSERT INTO radio_aliases (alias, stationuuid, aliases_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET
                stationuuid=excluded.stationuuid,
                aliases_json=excluded.aliases_json,
                updated_at=excluded.updated_at
            """,
            (alias, stationuuid, json.dumps(aliases), _NOW()),
        )
        await self._db.commit()

    async def get(self, alias: str) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM radio_aliases WHERE alias = ?", (alias,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["aliases"] = json.loads(d.pop("aliases_json", "[]"))
        return d

    async def get_all(self) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM radio_aliases ORDER BY alias")
        rows = []
        for row in await cur.fetchall():
            d = _row_to_dict(row)
            d["aliases"] = json.loads(d.pop("aliases_json", "[]"))
            rows.append(d)
        return rows

    async def delete(self, alias: str) -> None:
        await self._db.execute("DELETE FROM radio_aliases WHERE alias = ?", (alias,))
        await self._db.commit()


# ---------------------------------------------------------------------------
# Radio Cache Repository
# ---------------------------------------------------------------------------


class RadioCacheRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(self, stationuuid: str, station_json: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO radio_cache (stationuuid, station_json, last_seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(stationuuid) DO UPDATE SET
                station_json=excluded.station_json,
                last_seen_at=excluded.last_seen_at
            """,
            (stationuuid, json.dumps(station_json), _NOW()),
        )
        await self._db.commit()

    async def get(self, stationuuid: str) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM radio_cache WHERE stationuuid = ?", (stationuuid,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["station"] = json.loads(d.pop("station_json"))
        return d

    async def mark_played(self, stationuuid: str) -> None:
        await self._db.execute(
            "UPDATE radio_cache SET last_played_at=? WHERE stationuuid=?",
            (_NOW(), stationuuid),
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Apple Music Alias Repository
# ---------------------------------------------------------------------------


class AppleMusicAliasRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def upsert(
        self,
        alias: str,
        kind: str,
        aliases: list[str],
        favorite_item_id: str | None = None,
        share_url: str | None = None,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO apple_music_aliases
                (alias, kind, favorite_item_id, share_url, aliases_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET
                kind=excluded.kind, favorite_item_id=excluded.favorite_item_id,
                share_url=excluded.share_url, aliases_json=excluded.aliases_json,
                updated_at=excluded.updated_at
            """,
            (alias, kind, favorite_item_id, share_url, json.dumps(aliases), _NOW()),
        )
        await self._db.commit()

    async def get(self, alias: str) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM apple_music_aliases WHERE alias = ?", (alias,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["aliases"] = json.loads(d.pop("aliases_json", "[]"))
        return d

    async def get_all(self) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM apple_music_aliases ORDER BY alias"
        )
        rows = []
        for row in await cur.fetchall():
            d = _row_to_dict(row)
            d["aliases"] = json.loads(d.pop("aliases_json", "[]"))
            rows.append(d)
        return rows

    async def delete(self, alias: str) -> None:
        await self._db.execute(
            "DELETE FROM apple_music_aliases WHERE alias = ?", (alias,)
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Apple Music Cache Repository
# ---------------------------------------------------------------------------


class AppleMusicCacheRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM apple_music_cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, _NOW()),
        )
        row = await cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["result"] = json.loads(d.pop("result_json"))
        return d

    async def set(
        self,
        cache_key: str,
        result: dict,
        storefront: str,
        expires_at: str,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO apple_music_cache
                (cache_key, result_json, storefront, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                result_json=excluded.result_json, storefront=excluded.storefront,
                expires_at=excluded.expires_at, updated_at=excluded.updated_at
            """,
            (cache_key, json.dumps(result), storefront, expires_at, _NOW()),
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Snapshot Repository
# ---------------------------------------------------------------------------


class SnapshotRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save(self, snapshot_id: str, name: str | None, payload: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO snapshots (snapshot_id, name, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, name, json.dumps(payload), _NOW()),
        )
        await self._db.commit()

    async def get(self, snapshot_id_or_name: str) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM snapshots WHERE snapshot_id = ? OR name = ? ORDER BY created_at DESC LIMIT 1",
            (snapshot_id_or_name, snapshot_id_or_name),
        )
        row = await cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["payload"] = json.loads(d.pop("payload_json"))
        return d

    async def list_all(self) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT snapshot_id, name, created_at FROM snapshots ORDER BY created_at DESC"
        )
        return [_row_to_dict(r) for r in await cur.fetchall()]

    async def delete(self, snapshot_id: str) -> None:
        await self._db.execute(
            "DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
        )
        await self._db.commit()
