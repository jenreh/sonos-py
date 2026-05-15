"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sonos.core.config import (
    SonosLocalConfig,
    bootstrap_config_dir,
    load_config,
    validate_config,
)


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """Bootstrap a fresh config dir in tmp_path."""
    bootstrap_config_dir(tmp_path)
    return tmp_path


def test_default_config_loads(tmp_config: Path) -> None:
    cfg = load_config(tmp_config)
    assert isinstance(cfg, SonosLocalConfig)
    assert cfg.network.discovery_timeout_seconds == 5.0
    assert cfg.policies.volume.max_room_volume == 70


def test_validate_passes_for_defaults(tmp_config: Path) -> None:
    errors = validate_config(tmp_config)
    assert errors == []


def test_validate_missing_file(tmp_path: Path) -> None:
    errors = validate_config(tmp_path / "nonexistent")
    assert any("not found" in e for e in errors)


def test_rooms_section_parsed(tmp_config: Path) -> None:
    cfg_file = tmp_config / "config.toml"
    extra = """
[rooms.wohnzimmer]
sonos_names = ["Wohnzimmer"]
aliases = ["wohnzimmer", "wz"]
"""
    cfg_file.write_text(cfg_file.read_text() + extra, encoding="utf-8")
    cfg = load_config(tmp_config)
    assert "wohnzimmer" in cfg.rooms
    assert "wz" in cfg.rooms["wohnzimmer"].aliases


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bootstrap_config_dir(tmp_path)
    monkeypatch.setenv("SONSO_LOCAL_CONFIG_DIR", str(tmp_path))
    cfg = load_config()
    assert isinstance(cfg, SonosLocalConfig)


def test_policy_defaults(tmp_config: Path) -> None:
    cfg = load_config(tmp_config)
    assert cfg.policies.playback.allow_arbitrary_urls is False
    assert cfg.policies.radio.min_bitrate == 64
    assert cfg.policies.apple_music.require_sonos_service is True


def test_apple_music_config(tmp_config: Path) -> None:
    cfg = load_config(tmp_config)
    assert cfg.apple_music.mode == "sonos_share_link"
    assert cfg.apple_music.default_storefront == "de"
