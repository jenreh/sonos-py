"""Per-resource async locks for thread-safe SoCo operations."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class LockRegistry:
    """Maintains named asyncio.Lock instances, creating them on first use."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def _get(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    @asynccontextmanager
    async def speaker(self, uid: str) -> AsyncIterator[None]:
        async with self._get(f"speaker:{uid}"):
            yield

    @asynccontextmanager
    async def group(self, group_uid: str) -> AsyncIterator[None]:
        async with self._get(f"group:{group_uid}"):
            yield

    @asynccontextmanager
    async def topology(self) -> AsyncIterator[None]:
        async with self._get("topology"):
            yield

    @asynccontextmanager
    async def favorites(self, household_id: str) -> AsyncIterator[None]:
        async with self._get(f"favorites:{household_id}"):
            yield


_registry = LockRegistry()


def get_locks() -> LockRegistry:
    return _registry
