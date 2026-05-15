"""Tests for PolicyEnforcer."""

from __future__ import annotations

import pytest

from sonos.core.config import SonosLocalConfig, PoliciesConfig, VolumePolicy, PlaybackPolicy
from sonos.core.errors import ConfirmationRequired, PolicyError
from sonos.core.models import Scope
from sonos.core.policy import PolicyEnforcer


@pytest.fixture()
def default_policy() -> PolicyEnforcer:
    return PolicyEnforcer(SonosLocalConfig())


def test_cap_volume_room(default_policy: PolicyEnforcer) -> None:
    assert default_policy.cap_volume(80, Scope.ROOM) == 70  # capped at 70


def test_cap_volume_group(default_policy: PolicyEnforcer) -> None:
    assert default_policy.cap_volume(70, Scope.GROUP) == 60  # capped at 60


def test_cap_volume_all(default_policy: PolicyEnforcer) -> None:
    assert default_policy.cap_volume(100, Scope.ALL) == 40  # capped at 40


def test_cap_volume_within_limit(default_policy: PolicyEnforcer) -> None:
    assert default_policy.cap_volume(50, Scope.ROOM) == 50


def test_all_rooms_confirmation_required() -> None:
    cfg = SonosLocalConfig()
    cfg.policies.volume.require_confirmation_for_all_rooms = True
    enforcer = PolicyEnforcer(cfg)
    with pytest.raises(ConfirmationRequired):
        enforcer.check_all_rooms_confirmation(Scope.ALL, confirmed=False)


def test_all_rooms_confirmation_not_required_when_confirmed() -> None:
    cfg = SonosLocalConfig()
    cfg.policies.volume.require_confirmation_for_all_rooms = True
    enforcer = PolicyEnforcer(cfg)
    enforcer.check_all_rooms_confirmation(Scope.ALL, confirmed=True)  # should not raise


def test_url_apple_music_always_allowed(default_policy: PolicyEnforcer) -> None:
    default_policy.check_url("https://music.apple.com/de/album/test/123")  # no raise


def test_url_arbitrary_blocked(default_policy: PolicyEnforcer) -> None:
    with pytest.raises(PolicyError):
        default_policy.check_url("https://example.com/stream.mp3")


def test_url_allowed_if_in_list() -> None:
    cfg = SonosLocalConfig()
    cfg.policies.playback.allowed_url_hosts = ["streams.example.com"]
    enforcer = PolicyEnforcer(cfg)
    enforcer.check_url("https://streams.example.com/live.mp3")  # no raise


def test_url_private_ip_blocked(default_policy: PolicyEnforcer) -> None:
    with pytest.raises(PolicyError):
        default_policy.check_url("http://192.168.1.100/stream.mp3")


def test_url_localhost_blocked(default_policy: PolicyEnforcer) -> None:
    with pytest.raises(PolicyError):
        default_policy.check_url("http://127.0.0.1:8080/stream.mp3")
