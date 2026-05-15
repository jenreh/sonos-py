"""Group management helpers."""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger(__name__)


async def wait_for_topology_update(
    get_topology_fn,  # type: ignore[no-untyped-def]
    expected_group_uid: str | None,
    timeout: float = 30.0,
) -> bool:
    """Poll topology until the expected group UID appears or timeout expires."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        topology = await get_topology_fn(refresh=True)
        if expected_group_uid is None:
            return True
        if any(g.group_uid == expected_group_uid for g in topology.groups):
            return True
        await asyncio.sleep(1.0)
    log.warning("Topology did not converge within %.0fs", timeout)
    return False
