"""Core domain models for the Sonos local controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Scope(StrEnum):
    ROOM = "room"
    GROUP = "group"
    ALL = "all"


class MediaSource(StrEnum):
    QUEUE = "queue"
    RADIO = "radio"
    APPLE_MUSIC = "apple_music"
    SONOS_FAVORITE = "sonos_favorite"
    SONOS_PLAYLIST = "sonos_playlist"
    AIRPLAY = "airplay"
    SPOTIFY_CONNECT = "spotify_connect"
    LINE_IN = "line_in"
    TV = "tv"
    UNKNOWN = "unknown"


class TransportCommand(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"


@dataclass(frozen=True)
class Speaker:
    uid: str
    name: str
    ip_address: str
    household_id: str | None
    visible: bool
    available: bool
    boot_seqnum: str | None
    model_name: str | None
    coordinator_uid: str | None
    group_uid: str | None
    is_coordinator: bool
    capabilities: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SonosGroup:
    group_uid: str
    household_id: str
    coordinator_uid: str
    member_uids: tuple[str, ...]


@dataclass(frozen=True)
class SonosTopology:
    speakers: tuple[Speaker, ...]
    groups: tuple[SonosGroup, ...]
    household_ids: frozenset[str]


@dataclass(frozen=True)
class SonosFavorite:
    household_id: str
    item_id: str
    title: str
    source: MediaSource
    uri: str | None
    metadata_xml: str | None
    resource_metadata_xml: str | None
    playable: bool
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrackInfo:
    title: str | None
    artist: str | None
    album: str | None
    uri: str | None
    duration_secs: int | None
    position_secs: int | None
    album_art_uri: str | None


@dataclass(frozen=True)
class SpeakerState:
    uid: str
    name: str
    volume: int
    muted: bool
    treble: int
    bass: int
    loudness: bool
    playback_state: Literal["PLAYING", "PAUSED_PLAYBACK", "STOPPED", "TRANSITIONING"]
    source: MediaSource
    track_info: TrackInfo | None
    group_uid: str | None
    coordinator_uid: str | None


@dataclass(frozen=True)
class EqPatch:
    treble: int | None = None
    bass: int | None = None
    loudness: bool | None = None


@dataclass(frozen=True)
class AppleMusicItem:
    id: str
    type: Literal["song", "album", "playlist", "station"]
    name: str
    artist_name: str | None
    album_name: str | None
    url: str
    artwork_url: str | None
    storefront: str
    duration_ms: int | None
    explicit: bool | None
    playable_via_sonos: bool
    playable_reason: str | None


@dataclass(frozen=True)
class AppleMusicSearchResult:
    query: str
    storefront: str
    items: tuple[AppleMusicItem, ...]
    total: int


@dataclass(frozen=True)
class QueueItem:
    index: int
    title: str | None
    artist: str | None
    album: str | None
    uri: str
    duration_secs: int | None


@dataclass(frozen=True)
class QueueState:
    target: str
    coordinator_uid: str
    items: tuple[QueueItem, ...]
    total: int


@dataclass(frozen=True)
class Alarm:
    alarm_id: str
    enabled: bool
    time: str
    recurrence: str
    room_uid: str
    room_name: str
    volume: int
    program_uri: str | None
    program_metadata: str | None
    include_linked_zones: bool


@dataclass(frozen=True)
class AlarmPatch:
    enabled: bool | None = None
    time: str | None = None
    recurrence: str | None = None
    volume: int | None = None
    include_linked_zones: bool | None = None


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_id: str
    name: str | None
    targets: tuple[str, ...]
    created_at: str
