"""Background task scheduler for polling and availability checks."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Coroutine, Any

log = logging.getLogger(__name__)


class Scheduler:
    """Runs async periodic tasks with configurable intervals."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []

    def schedule(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, None]],
        interval: float,
    ) -> None:
        """Schedule a coroutine to run every `interval` seconds."""
        task = asyncio.create_task(self._loop(name, coro_fn, interval), name=name)
        self._tasks.append(task)

    async def _loop(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, None]],
        interval: float,
    ) -> None:
        while True:
            try:
                await coro_fn()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("Scheduled task %r failed: %s", name, exc)
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
