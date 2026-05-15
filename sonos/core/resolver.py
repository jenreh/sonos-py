"""TargetResolver — maps user-supplied room names/aliases to Speaker UIDs."""

from __future__ import annotations

import logging
import unicodedata

from sonos.core.config import SonosLocalConfig
from sonos.core.errors import AmbiguousTargetError, TargetNotFoundError
from sonos.core.models import Speaker, SonosTopology

log = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lowercase + strip diacritics for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class TargetResolver:
    """Resolve a user-supplied target string to a Speaker from the topology."""

    def __init__(self, config: SonosLocalConfig) -> None:
        self._config = config

    def resolve(self, target: str, topology: SonosTopology) -> Speaker:
        """
        Resolution order:
        1. Exact UID match
        2. Exact Sonos player_name match (case-insensitive)
        3. Match against rooms.toml sonos_names (normalised)
        4. Match against rooms.toml aliases (normalised)
        5. Fuzzy prefix match on all names
        """
        norm_target = _normalize(target)
        candidates: list[Speaker] = []

        visible = [s for s in topology.speakers if s.visible and s.available]

        # 1. Exact UID
        exact_uid = next((s for s in visible if s.uid == target), None)
        if exact_uid is not None:
            return exact_uid

        # 2. Exact name (case-insensitive normalised)
        for speaker in visible:
            if _normalize(speaker.name) == norm_target:
                candidates.append(speaker)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise AmbiguousTargetError(target, [s.name for s in candidates])

        # 3 & 4. rooms.toml lookups
        for room_key, room_cfg in self._config.rooms.items():
            sonos_names_norm = [_normalize(n) for n in room_cfg.sonos_names]
            alias_norms = [_normalize(a) for a in room_cfg.aliases]
            if norm_target in sonos_names_norm or norm_target in alias_norms or _normalize(room_key) == norm_target:
                # Find speaker matching any of the sonos_names
                matched = [
                    s for s in visible
                    if _normalize(s.name) in sonos_names_norm
                ]
                candidates.extend(matched)

        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            names = list({s.name for s in candidates})
            raise AmbiguousTargetError(target, names)

        # 5. Prefix match
        prefix_matches = [s for s in visible if _normalize(s.name).startswith(norm_target)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        if len(prefix_matches) > 1:
            raise AmbiguousTargetError(target, [s.name for s in prefix_matches])

        raise TargetNotFoundError(target)

    def resolve_coordinator(self, target: str, topology: SonosTopology) -> Speaker:
        """Resolve target → speaker → group coordinator."""
        from sonos.core.sonos.topology import find_coordinator

        speaker = self.resolve(target, topology)
        coordinator = find_coordinator(topology, speaker.uid)
        return coordinator or speaker
