"""SQLite schema migrations — append-only after initial creation."""

from __future__ import annotations

import logging

import aiosqlite

log = logging.getLogger(__name__)

# Each entry is (version, sql).  Applied in order; idempotent via version table.
_MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS speakers (
            uid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            household_id TEXT,
            visible INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1,
            boot_seqnum TEXT,
            model_name TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS groups (
            group_uid TEXT PRIMARY KEY,
            household_id TEXT NOT NULL,
            coordinator_uid TEXT NOT NULL,
            member_uids_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS favorites (
            household_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            uri TEXT,
            metadata_xml TEXT,
            resource_metadata_xml TEXT,
            playable INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (household_id, item_id)
        );

        CREATE TABLE IF NOT EXISTS radio_aliases (
            alias TEXT PRIMARY KEY,
            stationuuid TEXT NOT NULL,
            aliases_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS radio_cache (
            stationuuid TEXT PRIMARY KEY,
            station_json TEXT NOT NULL,
            last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_played_at TEXT
        );

        CREATE TABLE IF NOT EXISTS apple_music_aliases (
            alias TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            favorite_item_id TEXT,
            share_url TEXT,
            aliases_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apple_music_cache (
            cache_key TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            storefront TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            name TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """,
    ),
]


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Apply all pending migrations to the database."""
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    await db.commit()

    row = await (await db.execute("SELECT MAX(version) FROM schema_version")).fetchone()
    current = row[0] if row and row[0] is not None else 0

    for version, sql in _MIGRATIONS:
        if version <= current:
            continue
        log.info("Applying migration %d", version)
        await db.executescript(sql)
        await db.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (version,)
        )
        await db.commit()
        log.info("Migration %d applied", version)
