"""Tests for storage layer — migrations and repositories."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from sonos.storage.migrations import run_migrations
from sonos.storage.repositories import (
    AppleMusicAliasRepository,
    FavoritesRepository,
    GroupRepository,
    RadioAliasRepository,
    SnapshotRepository,
    SpeakerRepository,
)
from sonos.storage.sqlite import init_db, set_db_path


@pytest.fixture()
async def db(tmp_path: Path) -> aiosqlite.Connection:
    path = tmp_path / "test.sqlite"
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)
        yield conn


async def test_schema_version(db: aiosqlite.Connection) -> None:
    cur = await db.execute("SELECT MAX(version) FROM schema_version")
    row = await cur.fetchone()
    assert row[0] == 1


async def test_speaker_upsert_and_get(db: aiosqlite.Connection) -> None:
    repo = SpeakerRepository(db)
    speaker = {
        "uid": "RINCON_001",
        "name": "Wohnzimmer",
        "ip_address": "192.168.1.10",
        "household_id": "HH1",
        "visible": 1,
        "available": 1,
        "boot_seqnum": "42",
        "model_name": "Sonos One",
    }
    await repo.upsert(speaker)
    result = await repo.get("RINCON_001")
    assert result is not None
    assert result["name"] == "Wohnzimmer"


async def test_speaker_update(db: aiosqlite.Connection) -> None:
    repo = SpeakerRepository(db)
    base = {"uid": "RINCON_001", "name": "A", "ip_address": "1.1.1.1", "household_id": None, "visible": 1, "available": 1, "boot_seqnum": None, "model_name": None}
    await repo.upsert(base)
    await repo.upsert({**base, "name": "B"})
    result = await repo.get("RINCON_001")
    assert result["name"] == "B"


async def test_group_upsert(db: aiosqlite.Connection) -> None:
    repo = GroupRepository(db)
    await repo.upsert({
        "group_uid": "GRP1",
        "household_id": "HH1",
        "coordinator_uid": "RINCON_001",
        "member_uids": ["RINCON_001", "RINCON_002"],
    })
    groups = await repo.get_all()
    assert len(groups) == 1
    assert "RINCON_002" in groups[0]["member_uids"]


async def test_favorites_upsert_and_filter(db: aiosqlite.Connection) -> None:
    repo = FavoritesRepository(db)
    fav = {"household_id": "HH1", "item_id": "FAV1", "title": "Chill Mix", "source": "apple_music", "uri": None, "metadata_xml": None, "resource_metadata_xml": None, "playable": 1}
    await repo.upsert(fav)
    results = await repo.get_by_household("HH1")
    assert len(results) == 1
    assert results[0]["title"] == "Chill Mix"


async def test_radio_alias_crud(db: aiosqlite.Connection) -> None:
    repo = RadioAliasRepository(db)
    await repo.upsert("einslive", "uuid-123", ["einslive", "1live"])
    result = await repo.get("einslive")
    assert result is not None
    assert result["stationuuid"] == "uuid-123"
    assert "1live" in result["aliases"]


async def test_apple_music_alias_crud(db: aiosqlite.Connection) -> None:
    repo = AppleMusicAliasRepository(db)
    await repo.upsert("chillmix", "favorite", ["chill mix", "chillmix"], favorite_item_id="FAV1")
    result = await repo.get("chillmix")
    assert result is not None
    assert result["kind"] == "favorite"
    all_aliases = await repo.get_all()
    assert len(all_aliases) == 1


async def test_snapshot_save_and_get(db: aiosqlite.Connection) -> None:
    repo = SnapshotRepository(db)
    await repo.save("snap-001", "before-test", {"rooms": ["wohnzimmer"]})
    result = await repo.get("before-test")
    assert result is not None
    assert result["payload"]["rooms"] == ["wohnzimmer"]


async def test_init_db(tmp_path: Path) -> None:
    path = tmp_path / "init_test.sqlite"
    await init_db(path)
    assert path.exists()
