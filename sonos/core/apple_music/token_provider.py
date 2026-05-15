"""Apple Music developer token (JWT) and user token provider."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from sonos.core.config import AppleMusicConfig
from sonos.core.errors import AppleMusicDeveloperTokenMissing, AppleMusicUserTokenMissing

log = logging.getLogger(__name__)

_TOKEN_TTL = 15_777_000  # ~6 months in seconds
_cached_developer_token: str | None = None
_cached_token_expiry: float = 0.0


class AppleMusicTokenProvider:
    def __init__(self, config: AppleMusicConfig) -> None:
        self._config = config

    async def get_developer_token(self) -> str:
        global _cached_developer_token, _cached_token_expiry

        if _cached_developer_token and time.time() < _cached_token_expiry - 60:
            return _cached_developer_token

        dev = self._config.developer
        if not dev.enabled or not dev.team_id or not dev.key_id:
            raise AppleMusicDeveloperTokenMissing(
                "Apple Music developer credentials not configured. "
                "Set [apple_music.developer] in config.toml."
            )

        key_path = Path(dev.private_key_path).expanduser()
        if not key_path.exists():
            raise AppleMusicDeveloperTokenMissing(
                f"Apple Music private key not found: {key_path}"
            )

        # Check file permissions
        mode = oct(key_path.stat().st_mode)[-3:]
        if mode not in ("600", "400"):
            log.warning(
                "Apple Music key file %s has permissions %s; recommend 600",
                key_path,
                mode,
            )

        import jwt

        private_key = key_path.read_text(encoding="utf-8")
        now = int(time.time())
        exp = now + _TOKEN_TTL
        payload = {
            "iss": dev.team_id,
            "iat": now,
            "exp": exp,
        }
        token = jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers={"kid": dev.key_id},
        )
        _cached_developer_token = token
        _cached_token_expiry = exp
        log.debug("Generated Apple Music developer token (expires %s)", exp)
        return token

    async def get_user_token(self) -> str | None:
        auth = self._config.auth
        # Try env var first
        env_token = os.environ.get(auth.user_token_env)
        if env_token:
            return env_token
        # Try keyring
        try:
            import keyring

            token = keyring.get_password(auth.keyring_service, auth.keyring_username)
            if token:
                return token
        except Exception as exc:  # noqa: BLE001
            log.debug("Keyring lookup failed: %s", exc)
        return None

    async def require_user_token(self) -> str:
        token = await self.get_user_token()
        if not token:
            raise AppleMusicUserTokenMissing(
                f"Apple Music user token not found. "
                f"Set env var {self._config.auth.user_token_env!r} or store in keyring."
            )
        return token
