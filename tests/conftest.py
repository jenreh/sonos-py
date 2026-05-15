"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sonos.core.config import SonosLocalConfig, RoomConfig, bootstrap_config_dir
from sonos.core.models import Speaker, SonosGroup, SonosTopology


@pytest.fixture()
def tmp_config(tmp_path: Path) -> SonosLocalConfig:
    bootstrap_config_dir(tmp_path)
    cfg = SonosLocalConfig()
    cfg.storage.sqlite_path = str(tmp_path / "state.sqlite")
    cfg.storage.log_path = str(tmp_path / "logs" / "sonos.jsonl")
    return cfg


@pytest.fixture()
def two_speaker_topology() -> SonosTopology:
    wohnzimmer = Speaker(
        uid="RINCON_WZ",
        name="Wohnzimmer",
        ip_address="192.168.1.10",
        household_id="HH1",
        visible=True,
        available=True,
        boot_seqnum="1",
        model_name="Sonos One",
        coordinator_uid="RINCON_WZ",
        group_uid="GRP_WZ",
        is_coordinator=True,
    )
    buero = Speaker(
        uid="RINCON_BU",
        name="Büro",
        ip_address="192.168.1.11",
        household_id="HH1",
        visible=True,
        available=True,
        boot_seqnum="2",
        model_name="Sonos Era 100",
        coordinator_uid="RINCON_BU",
        group_uid="GRP_BU",
        is_coordinator=True,
    )
    return SonosTopology(
        speakers=(wohnzimmer, buero),
        groups=(
            SonosGroup("GRP_WZ", "HH1", "RINCON_WZ", ("RINCON_WZ",)),
            SonosGroup("GRP_BU", "HH1", "RINCON_BU", ("RINCON_BU",)),
        ),
        household_ids=frozenset(["HH1"]),
    )
