"""Policy enforcement: volume caps, URL policy, playback confirmation gates."""

from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

from sonos.core.config import SonosLocalConfig
from sonos.core.errors import ConfirmationRequired, PolicyError
from sonos.core.models import Scope

log = logging.getLogger(__name__)


class PolicyEnforcer:
    def __init__(self, config: SonosLocalConfig) -> None:
        self._cfg = config

    # ------------------------------------------------------------------
    # Volume policy
    # ------------------------------------------------------------------

    def cap_volume(self, volume: int, scope: Scope, dry_run: bool = False) -> int:
        """Return capped volume; raise PolicyError if already at max and still capped."""
        pol = self._cfg.policies.volume
        if scope == Scope.ROOM:
            cap = pol.max_room_volume
        elif scope == Scope.GROUP:
            cap = pol.max_group_volume
        else:
            cap = pol.max_all_volume

        if volume > cap:
            log.debug("Volume %d capped to %d for scope %s", volume, cap, scope)
            return cap
        return volume

    def check_all_rooms_confirmation(
        self, scope: Scope, confirmed: bool, dry_run: bool = False
    ) -> None:
        pol = self._cfg.policies.volume
        if (
            scope == Scope.ALL
            and pol.require_confirmation_for_all_rooms
            and not confirmed
            and not dry_run
        ):
            raise ConfirmationRequired(
                "Action affects all rooms — pass --confirm to proceed.",
                suggested_arguments={"confirm": True},
            )

    def check_volume_delta(self, delta: int, scope: Scope) -> int:
        """Return validated delta; use default_delta if zero."""
        if delta == 0:
            return self._cfg.policies.volume.default_delta
        return delta

    # ------------------------------------------------------------------
    # URL policy
    # ------------------------------------------------------------------

    def check_url(self, url: str) -> None:
        """Raise PolicyError if the URL is not allowed by policy."""
        pol = self._cfg.policies.playback
        parsed = urlparse(url)

        # Apple Music share links are always allowed
        if parsed.netloc.endswith("music.apple.com"):
            return

        if not pol.allow_arbitrary_urls:
            # Only allow if explicitly in the allowed hosts list
            if parsed.netloc not in (pol.allowed_url_hosts or []):
                raise PolicyError(
                    f"Arbitrary URLs not allowed. Add {parsed.netloc!r} to "
                    "policies.playback.allowed_url_hosts or set allow_arbitrary_urls=true."
                )

        if pol.block_private_network_urls:
            _check_not_private(parsed.netloc)

    # ------------------------------------------------------------------
    # Playback group policy
    # ------------------------------------------------------------------

    def check_group_playback(
        self,
        target_name: str,
        is_grouped: bool,
        confirmed: bool,
        dry_run: bool = False,
    ) -> None:
        policy = self._cfg.policies.playback.group_playback_policy
        if not is_grouped:
            return
        if policy == "use_existing_group":
            return
        if policy == "require_confirmation" and not confirmed and not dry_run:
            raise ConfirmationRequired(
                f"{target_name!r} is grouped — pass --confirm or --isolate.",
                suggested_arguments={"scope": "group", "isolate": False},
            )


def _check_not_private(netloc: str) -> None:
    host = netloc.split(":")[0]
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise PolicyError(
                f"Private/loopback/link-local URLs are blocked: {netloc!r}. "
                "Set policies.playback.block_private_network_urls=false to allow."
            )
    except ValueError:
        # Not an IP; domain name — allow
        pass
