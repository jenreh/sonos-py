"""Configuration loading from a single ~/.config/sonos-local/config.toml."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import tomli_w

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-reuse-of-module-level-import]

from pydantic import BaseModel, Field, model_validator

log = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = Path.home() / ".config" / "sonos-local"


def _config_dir() -> Path:
    env = os.environ.get("SONSO_LOCAL_CONFIG_DIR")
    return Path(env) if env else _DEFAULT_CONFIG_DIR


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class NetworkConfig(BaseModel):
    hosts: list[str] = Field(default_factory=list)
    discovery_timeout_seconds: float = 5.0
    request_timeout_seconds: float = 9.5
    enable_ssdp: bool = True
    enable_zeroconf: bool = True
    enable_events: bool = True
    advertise_addr: str = ""
    poll_interval_seconds: float = 15.0
    availability_check_seconds: float = 60.0


class SonosConfig(BaseModel):
    ignore_invisible_devices: bool = True
    refresh_topology_on_command: bool = True
    wait_for_group_timeout_seconds: float = 30.0
    long_service_timeout_seconds: float = 30.0


class StorageConfig(BaseModel):
    sqlite_path: str = str(_DEFAULT_CONFIG_DIR / "state.sqlite")
    log_path: str = str(_DEFAULT_CONFIG_DIR / "logs" / "sonos.jsonl")

    @property
    def sqlite_path_resolved(self) -> Path:
        return Path(self.sqlite_path).expanduser()

    @property
    def log_path_resolved(self) -> Path:
        return Path(self.log_path).expanduser()


class RoomConfig(BaseModel):
    sonos_names: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class VolumePolicy(BaseModel):
    default_delta: int = 5
    max_room_volume: int = 70
    max_group_volume: int = 60
    max_all_volume: int = 40
    require_confirmation_for_all_rooms: bool = False


class PlaybackPolicy(BaseModel):
    group_playback_policy: str = "use_existing_group"
    allow_arbitrary_urls: bool = False
    allowed_url_hosts: list[str] = Field(default_factory=list)
    block_private_network_urls: bool = True


class RadioPolicy(BaseModel):
    default_countrycode: str = "DE"
    hide_broken: bool = True
    require_lastcheckok: bool = True
    allow_hls: bool = False
    min_bitrate: int = 64
    preferred_codecs: list[str] = Field(default_factory=lambda: ["MP3", "AAC", "AAC+"])


class AppleMusicPolicy(BaseModel):
    require_sonos_service: bool = True
    allow_share_links: bool = True
    allow_catalog_search: bool = True
    allow_library_search: bool = False
    allow_airplay_bridge: bool = False


class PoliciesConfig(BaseModel):
    volume: VolumePolicy = Field(default_factory=VolumePolicy)
    playback: PlaybackPolicy = Field(default_factory=PlaybackPolicy)
    radio: RadioPolicy = Field(default_factory=RadioPolicy)
    apple_music: AppleMusicPolicy = Field(default_factory=AppleMusicPolicy)


class RadioAliasConfig(BaseModel):
    stationuuid: str = ""
    preferred_name: str = ""
    countrycode: str = "DE"
    aliases: list[str] = Field(default_factory=list)


class RadioConfig(BaseModel):
    aliases: dict[str, RadioAliasConfig] = Field(default_factory=dict)


class AppleMusicAliasConfig(BaseModel):
    kind: str = "favorite"
    favorite_item_id: str = ""
    url: str = ""
    aliases: list[str] = Field(default_factory=list)


class AppleMusicDeveloperConfig(BaseModel):
    enabled: bool = False
    team_id: str = ""
    key_id: str = ""
    private_key_path: str = str(_DEFAULT_CONFIG_DIR / "apple" / "AuthKey_XXXX.p8")


class AppleMusicAuthConfig(BaseModel):
    user_token_env: str = "SONSO_APPLE_MUSIC_USER_TOKEN"
    keyring_service: str = "sonos"
    keyring_username: str = "apple_music_user_token"


class AppleMusicConfig(BaseModel):
    enabled: bool = True
    mode: str = "sonos_share_link"
    default_storefront: str = "de"
    aliases: dict[str, AppleMusicAliasConfig] = Field(default_factory=dict)
    developer: AppleMusicDeveloperConfig = Field(default_factory=AppleMusicDeveloperConfig)
    auth: AppleMusicAuthConfig = Field(default_factory=AppleMusicAuthConfig)


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------


class SonosLocalConfig(BaseModel):
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    sonos: SonosConfig = Field(default_factory=SonosConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    rooms: dict[str, RoomConfig] = Field(default_factory=dict)
    policies: PoliciesConfig = Field(default_factory=PoliciesConfig)
    radio: RadioConfig = Field(default_factory=RadioConfig)
    apple_music: AppleMusicConfig = Field(default_factory=AppleMusicConfig)

    @model_validator(mode="before")
    @classmethod
    def _flatten_policies(cls, data: Any) -> Any:
        """Accept flat [volume], [playback], etc. at top level as well."""
        if not isinstance(data, dict):
            return data
        if "volume" in data and "policies" not in data:
            data = dict(data)
            data["policies"] = {
                k: data.pop(k)
                for k in ("volume", "playback", "radio", "apple_music")
                if k in data
            }
        return data


# ---------------------------------------------------------------------------
# Defaults TOML text
# ---------------------------------------------------------------------------

_DEFAULT_TOML = """\
[network]
hosts = []
discovery_timeout_seconds = 5
request_timeout_seconds = 9.5
enable_ssdp = true
enable_zeroconf = true
enable_events = true
advertise_addr = ""
poll_interval_seconds = 15
availability_check_seconds = 60

[sonos]
ignore_invisible_devices = true
refresh_topology_on_command = true
wait_for_group_timeout_seconds = 30
long_service_timeout_seconds = 30

[storage]
sqlite_path = "~/.config/sonos-local/state.sqlite"
log_path = "~/.config/sonos-local/logs/sonos.jsonl"

[policies.volume]
default_delta = 5
max_room_volume = 70
max_group_volume = 60
max_all_volume = 40
require_confirmation_for_all_rooms = false

[policies.playback]
group_playback_policy = "use_existing_group"
allow_arbitrary_urls = false
allowed_url_hosts = []
block_private_network_urls = true

[policies.radio]
default_countrycode = "DE"
hide_broken = true
require_lastcheckok = true
allow_hls = false
min_bitrate = 64
preferred_codecs = ["MP3", "AAC", "AAC+"]

[policies.apple_music]
require_sonos_service = true
allow_share_links = true
allow_catalog_search = true
allow_library_search = false
allow_airplay_bridge = false

[apple_music]
enabled = true
mode = "sonos_share_link"
default_storefront = "de"

[apple_music.developer]
enabled = false
team_id = ""
key_id = ""
private_key_path = "~/.config/sonos-local/apple/AuthKey_XXXX.p8"

[apple_music.auth]
user_token_env = "SONSO_APPLE_MUSIC_USER_TOKEN"
keyring_service = "sonos"
keyring_username = "apple_music_user_token"

# Example room configuration — edit to match your Sonos setup.
# [rooms.wohnzimmer]
# sonos_names = ["Wohnzimmer"]
# aliases = ["wohnzimmer", "living room", "wz"]
#
# [rooms.buero]
# sonos_names = ["Büro"]
# aliases = ["büro", "buero", "office"]

# Example radio alias — edit to match your preferred stations.
# [radio.aliases.einslive]
# stationuuid = ""
# preferred_name = "1LIVE"
# countrycode = "DE"
# aliases = ["einslive", "1live"]
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def config_path(config_dir: Path | None = None) -> Path:
    d = config_dir or _config_dir()
    return d / "config.toml"


def bootstrap_config_dir(config_dir: Path | None = None) -> Path:
    """Create config dir and default config.toml if missing; return config path."""
    d = config_dir or _config_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "logs").mkdir(exist_ok=True)
    (d / "apple").mkdir(exist_ok=True)
    cfg = d / "config.toml"
    if not cfg.exists():
        cfg.write_text(_DEFAULT_TOML, encoding="utf-8")
        log.info("Created default config at %s", cfg)
    return cfg


def load_config(config_dir: Path | None = None) -> SonosLocalConfig:
    """Load and validate config.toml; create defaults if missing."""
    cfg = bootstrap_config_dir(config_dir)
    raw = tomllib.loads(cfg.read_text(encoding="utf-8"))
    return SonosLocalConfig.model_validate(raw)


def save_config(config: SonosLocalConfig, config_dir: Path | None = None) -> None:
    """Serialise config back to config.toml."""
    cfg = config_path(config_dir)
    data = config.model_dump(mode="json")
    cfg.write_bytes(tomli_w.dumps(data).encode())


def validate_config(config_dir: Path | None = None) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors: list[str] = []
    try:
        cfg = config_path(config_dir)
        if not cfg.exists():
            errors.append(f"Config file not found: {cfg}")
            return errors
        raw = tomllib.loads(cfg.read_text(encoding="utf-8"))
        SonosLocalConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return errors
