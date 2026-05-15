"""Apple Music playback via SoCo ShareLinkPlugin."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sonos.core.errors import (
    AppleMusicNotAuthorizedOnSonos,
    AppleMusicQueueAddFailed,
    InvalidAppleMusicShareLink,
)
from sonos.core.result import CommandResult

log = logging.getLogger(__name__)


class AppleMusicSonosPlayback:
    def __init__(self, registry: Any, timeout: float = 30.0) -> None:
        self._registry = registry
        self._timeout = timeout

    async def play_share_link(
        self,
        coordinator_uid: str,
        url: str,
        replace_queue: bool,
        title: str | None,
    ) -> CommandResult:
        from soco.plugins.sharelink import ShareLinkPlugin

        soco = self._registry.get(coordinator_uid)

        def sync_call() -> int:
            plugin = ShareLinkPlugin(soco)
            if not plugin.is_share_link(url):
                raise InvalidAppleMusicShareLink(url)
            if replace_queue:
                soco.clear_queue()
            try:
                queue_no = plugin.add_share_link_to_queue(
                    url, dc_title=title or "", timeout=self._timeout
                )
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc).lower()
                if "unauthorized" in err_msg or "not authorized" in err_msg:
                    raise AppleMusicNotAuthorizedOnSonos(
                        "Apple Music is not authorized on this Sonos system. "
                        "Add Apple Music in the Sonos app and try again."
                    ) from exc
                raise AppleMusicQueueAddFailed(
                    f"Failed to add Apple Music share link to queue: {exc}"
                ) from exc
            soco.play_from_queue(queue_no - 1)
            return queue_no

        queue_no = await asyncio.to_thread(sync_call)
        return CommandResult.success(
            "apple_music.play_share_link",
            media={
                "source": "apple_music",
                "kind": "share_link",
                "url": url,
                "title": title,
            },
            data={"queue_position": queue_no},
        )
