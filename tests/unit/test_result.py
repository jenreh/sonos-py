"""Tests for CommandResult / ErrorDetail."""

from sonos.core.result import CommandResult, ErrorDetail


def test_success_result_to_dict() -> None:
    r = CommandResult.success("volume.up", target={"input": "wohnzimmer"}, scope="room")
    d = r.to_dict()
    assert d["ok"] is True
    assert d["action"] == "volume.up"
    assert d["scope"] == "room"
    assert "error" not in d


def test_failure_result_to_dict() -> None:
    r = CommandResult.failure(
        "volume.up",
        code="target_not_found",
        message="No speaker found",
        exit_code=3,
    )
    d = r.to_dict()
    assert d["ok"] is False
    assert d["error"]["code"] == "target_not_found"
    assert r.exit_code == 3


def test_failure_with_confirmation() -> None:
    r = CommandResult.failure(
        "playback.play",
        code="confirmation_required",
        message="Target is grouped",
        exit_code=7,
        requires_confirmation=True,
        suggested_arguments={"isolate": True},
    )
    d = r.to_dict()
    assert d["error"]["requires_confirmation"] is True
    assert d["error"]["suggested_arguments"]["isolate"] is True


def test_error_detail_candidates() -> None:
    e = ErrorDetail(
        code="apple_music_ambiguous_result",
        message="Multiple results",
        candidates=[{"id": "1", "name": "Chill Mix"}],
    )
    d = e.to_dict()
    assert len(d["candidates"]) == 1
