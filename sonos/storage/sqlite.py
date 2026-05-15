"""aiosqlite database connection management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from sonos.storage.migrations import run_migrations

log = logging.getLogger(__name__)

_db_path: Path | None = None
_initialized: bool = False


def set_db_path(path: Path) -> None:
    global _db_path, _initialized
    _db_path = path
    _initialized = False


def get_db_path() -> Path:
    if _db_path is None:
        raise RuntimeError("Database path not configured; call set_db_path() first.")
    return _db_path


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection, run migrations on first use, yield connection."""
    global _initialized
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        if not _initialized:
            await run_migrations(db)
            _initialized = True
        yield db


async def init_db(path: Path) -> None:
    """Ensure schema is up to date; call at startup."""
    set_db_path(path)
    async with get_db():
        pass
    log.debug("Database initialised at %s", path)
