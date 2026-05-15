"""Tests for TargetResolver."""

from __future__ import annotations

import pytest

from sonos.core.config import SonosLocalConfig, RoomConfig
from sonos.core.errors import AmbiguousTargetError, TargetNotFoundError
from sonos.core.models import Speaker, SonosGroup, SonosTopology
from sonos.core.resolver import TargetResolver, _normalize


def _make_speaker(uid: str, name: str, visible: bool = True) -> Speaker:
    return Speaker(
        uid=uid,
        name=name,
        ip_address="192.168.1.1",
        household_id="HH1",
        visible=visible,
        available=True,
        boot_seqnum=None,
        model_name=None,
        coordinator_uid=uid,
        group_uid="GRP1",
        is_coordinator=True,
    )


def _make_topology(*speakers: Speaker) -> SonosTopology:
    return SonosTopology(
        speakers=tuple(speakers),
        groups=(),
        household_ids=frozenset(["HH1"]),
    )


@pytest.fixture()
def config_with_rooms() -> SonosLocalConfig:
    cfg = SonosLocalConfig()
    cfg.rooms["wohnzimmer"] = RoomConfig(
        sonos_names=["Wohnzimmer"], aliases=["wohnzimmer", "wz", "living room"]
    )
    cfg.rooms["buero"] = RoomConfig(
        sonos_names=["Büro"], aliases=["büro", "buero", "office"]
    )
    return cfg


def test_normalize_umlauts() -> None:
    assert _normalize("Büro") == "buro"
    assert _normalize("Wohnzimmer") == "wohnzimmer"


def test_exact_uid(config_with_rooms: SonosLocalConfig) -> None:
    s = _make_speaker("RINCON_001", "Wohnzimmer")
    topology = _make_topology(s)
    resolver = TargetResolver(config_with_rooms)
    assert resolver.resolve("RINCON_001", topology).uid == "RINCON_001"


def test_exact_name(config_with_rooms: SonosLocalConfig) -> None:
    s = _make_speaker("RINCON_001", "Wohnzimmer")
    topology = _make_topology(s)
    resolver = TargetResolver(config_with_rooms)
    assert resolver.resolve("wohnzimmer", topology).uid == "RINCON_001"


def test_alias_match(config_with_rooms: SonosLocalConfig) -> None:
    s = _make_speaker("RINCON_001", "Wohnzimmer")
    topology = _make_topology(s)
    resolver = TargetResolver(config_with_rooms)
    assert resolver.resolve("wz", topology).uid == "RINCON_001"


def test_umlaut_alias(config_with_rooms: SonosLocalConfig) -> None:
    s = _make_speaker("RINCON_002", "Büro")
    topology = _make_topology(s)
    resolver = TargetResolver(config_with_rooms)
    # "buero" alias should match "Büro"
    assert resolver.resolve("buero", topology).uid == "RINCON_002"
    assert resolver.resolve("büro", topology).uid == "RINCON_002"


def test_not_found(config_with_rooms: SonosLocalConfig) -> None:
    topology = _make_topology(_make_speaker("RINCON_001", "Wohnzimmer"))
    resolver = TargetResolver(config_with_rooms)
    with pytest.raises(TargetNotFoundError):
        resolver.resolve("kueche", topology)


def test_invisible_not_resolved(config_with_rooms: SonosLocalConfig) -> None:
    visible = _make_speaker("RINCON_001", "Wohnzimmer")
    invisible = Speaker(
        uid="RINCON_003",
        name="Wohnzimmer Sub",
        ip_address="192.168.1.3",
        household_id="HH1",
        visible=False,
        available=True,
        boot_seqnum=None,
        model_name=None,
        coordinator_uid="RINCON_001",
        group_uid="GRP1",
        is_coordinator=False,
    )
    topology = _make_topology(visible, invisible)
    resolver = TargetResolver(config_with_rooms)
    result = resolver.resolve("Wohnzimmer", topology)
    assert result.uid == "RINCON_001"
