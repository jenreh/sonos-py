"""Domain exception hierarchy for the Sonos local controller."""

from __future__ import annotations


class SonosError(Exception):
    """Base exception; all domain errors carry an error code."""

    code: str = "sonos_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class ConfigError(SonosError):
    code = "config_error"


class TargetNotFoundError(SonosError):
    code = "target_not_found"

    def __init__(self, target: str) -> None:
        super().__init__(f"Target not found: {target!r}")
        self.target = target


class AmbiguousTargetError(SonosError):
    code = "ambiguous_target"

    def __init__(self, target: str, candidates: list[str]) -> None:
        super().__init__(
            f"Ambiguous target {target!r}: matches {candidates}"
        )
        self.target = target
        self.candidates = candidates


class NetworkError(SonosError):
    code = "network_error"


class PolicyError(SonosError):
    code = "policy_error"


class ConfirmationRequired(SonosError):
    """Raised when a mutating action needs explicit confirmation."""

    code = "confirmation_required"

    def __init__(self, message: str, suggested_arguments: dict | None = None) -> None:
        super().__init__(message)
        self.suggested_arguments = suggested_arguments or {}


class RadioResolutionError(SonosError):
    code = "radio_resolution_failed"


class RadioAmbiguousError(SonosError):
    code = "radio_ambiguous_result"

    def __init__(self, query: str, candidates: list[dict]) -> None:
        super().__init__(f"Ambiguous radio query: {query!r}")
        self.query = query
        self.candidates = candidates


class AppleMusicDisabledError(SonosError):
    code = "apple_music_disabled"


class AppleMusicDeveloperTokenMissing(SonosError):
    code = "apple_music_developer_token_missing"


class AppleMusicUserTokenMissing(SonosError):
    code = "apple_music_user_token_missing"


class AppleMusicSearchFailed(SonosError):
    code = "apple_music_search_failed"


class AppleMusicNoResult(SonosError):
    code = "apple_music_no_result"


class AppleMusicAmbiguousResult(SonosError):
    code = "apple_music_ambiguous_result"

    def __init__(self, query: str, candidates: list[dict]) -> None:
        super().__init__(f"Multiple Apple Music results for {query!r}")
        self.query = query
        self.candidates = candidates


class InvalidAppleMusicShareLink(SonosError):
    code = "apple_music_invalid_share_link"

    def __init__(self, url: str) -> None:
        super().__init__(f"Not a valid Apple Music share link: {url!r}")
        self.url = url


class AppleMusicNotAuthorizedOnSonos(SonosError):
    code = "apple_music_not_authorized_on_sonos"


class AppleMusicQueueAddFailed(SonosError):
    code = "apple_music_queue_add_failed"
