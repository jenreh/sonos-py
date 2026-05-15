# Implementierungsplan: `sonos` CLI und FastMCP Server für Sonos

**Stand:** 2026-05-15
**Ziel:** Eine vollständige lokale Python-Anwendung zur Steuerung von Sonos-Geräten im LAN, mit deterministischer CLI und separatem FastMCP-Server. Beide Adapter nutzen denselben Core. Die Konfiguration liegt unter `~/.config/sonos-local`.

---

## 1. Ergebnisbild

`sonos` besteht aus drei sauber getrennten Schichten:

```text
┌────────────────────────────────────────┐
│ CLI                                    │
│ - deterministische Kommandos           │
│ - keine LLM-/Chat-/Freitextlogik       │
│ - Admin, Diagnose, Scripting           │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│ Core                                   │
│ - Sonos Domain Model                   │
│ - SoCo Backend                         │
│ - Discovery, Events, Polling           │
│ - Gruppen, Queue, Favorites, Radio     │
│ - Apple Music via Sonos/Share Links    │
│ - Policies, Cache, Storage             │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│ FastMCP Server                         │
│ - typed Tools                          │
│ - Resources                            │
│ - keine eigene LLM-Interpretation      │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│ Assistant / MCP Client                 │
│ - übersetzt natürliche Sprache         │
│   in Tool Calls                        │
└────────────────────────────────────────┘
```

Beispiele:

```bash
sonos volume up wohnzimmer --step 5
sonos mute --all --confirm
sonos radio play buero einslive
sonos apple play wohnzimmer "chill mix"
sonos apple play buero --url "https://music.apple.com/de/album/..."
sonos mcp --transport stdio
```

MCP-seitig wird natürliche Sprache nicht im Server geparst. Ein Assistant mappt zum Beispiel:

```json
{
  "tool": "sonos_adjust_volume",
  "arguments": {
    "target": "wohnzimmer",
    "delta": 5,
    "scope": "room"
  }
}
```

---

## 2. Kernentscheidungen

| Bereich | Entscheidung |
|---|---|
| Sonos-LAN-Zugriff | `soco` als Basisbibliothek |
| MCP | `fastmcp` als MCP-Framework, nicht Low-Level-MCP-SDK direkt |
| Radio | eigener Radio-Browser-Client von Anfang an |
| Apple Music | unterstützt über Sonos-native Apple-Music-Integration, Sonos Favorites/Playlists und Apple-Music-Share-Links über SoCo ShareLinkPlugin |
| CLI | Typer/Rich, strikt deterministisch, kein LLM |
| Config | `~/.config/sonos-local` auf Linux und macOS |
| State | SQLite unter `~/.config/sonos-local/state.sqlite` |
| Async | Core async nach außen; blockierende SoCo-Calls via Threadpool |
| Events | SoCo Events, Fallback-Polling wie Home Assistant |
| Sicherheit | keine beliebige URL-Wiedergabe im MCP-Default; URL-/Volume-/Scope-Policies |

---

## 3. Wichtige Erkenntnisse aus Home Assistant Sonos

Home Assistant ist als Architekturvorbild relevant, aber nicht als Abhängigkeit. Die Sonos-Integration arbeitet lokal, nutzt SSDP/Zeroconf-Erkennung, ist als `local_push` klassifiziert und verwendet SoCo plus zusätzliche Schichten für Discovery, Push-Events, Polling-Fallback, Favorites, Gruppen-Topologie und Services.

Relevante Home-Assistant-Prinzipien, die übernommen werden sollen:

1. **Discovery ist ein eigener Subsystem-Teil.**
   Home Assistant kombiniert automatische Discovery mit manuell konfigurierten Hosts. Für `sonos` bedeutet das: SSDP, Zeroconf und statische Hosts werden zusammengeführt.

2. **Push-Events sind bevorzugt, Polling ist Pflicht-Fallback.**
   Sonos muss den Host erreichen können. Wenn Event-Callbacks nicht funktionieren, muss Polling den Zustand aktuell halten.

3. **UPnP-Fehler müssen explizit diagnostiziert werden.**
   Home Assistant behandelt HTTP 403 beim Zugriff auf Sonos als Hinweis auf deaktiviertes UPnP. `sonos doctor` soll diesen Fall explizit melden.

4. **Favorites sind household-bezogen zu cachen.**
   Home Assistant führt einen Household-Favorites-Cache, aktualisiert ihn über Events und filtert nicht spielbare Favorites. Dieses Muster wird übernommen.

5. **Gruppen- und Coordinator-Semantik sind zentral.**
   Transport- und Queue-Kommandos müssen auf dem Group Coordinator laufen. Volume/Mute können speaker-, gruppen- oder global angewendet werden.

6. **Medienquellen werden differenziert.**
   Home Assistant unterscheidet Radio, Line-in, TV, AirPlay, Spotify Connect, Queue und Favorites. `sonos` übernimmt dieses Quellenmodell im Core-State.

7. **Share Links sind für Musikdienste relevant.**
   Home Assistant verarbeitet unter anderem Apple-Music-, Deezer-, Sonos- und Tidal-Share-Links in der Sonos-Media-Playback-Schicht. `sonos` soll dafür direkt SoCos ShareLinkPlugin nutzen.

---

## 4. Apple-Music-Strategie

Apple Music wird unterstützt, aber nicht durch Extraktion von DRM-Streams oder private Apple-/Sonos-Hacks. Die Unterstützung wird als **Sonos-native Apple-Music-Steuerung** implementiert.

### 4.1 Voraussetzungen

Apple Music muss im Sonos-System bereits eingerichtet sein:

```text
Sonos App -> Musikdienst hinzufügen -> Apple Music -> anmelden/autorisieren
```

Sonos dokumentiert Apple Music als unterstützten Dienst mit Zugriff auf Apple-Music-Katalog und Bibliothek innerhalb Sonos; ein aktives Apple-Music-Abonnement ist erforderlich. Sonos Favorites können Songs, Playlists und Stations als Shortcuts speichern.

### 4.2 Unterstützte Apple-Music-Modi

#### Modus A: Apple Music über Sonos Favorites und Sonos Playlists

Dies ist der stabilste Modus.

Ablauf:

```text
1. Nutzer speichert Apple-Music-Song/-Album/-Playlist/-Station in der Sonos-App als Sonos Favorite.
2. `sonos` lädt Sonos Favorites über SoCo.
3. Apple-Music-Favorite wird im Household-Favorites-Cache gespeichert.
4. CLI/MCP spielt den Favorite per item_id oder Alias ab.
```

CLI:

```bash
sonos favorites list --source apple_music
sonos apple aliases
sonos apple bind chillmix --favorite "Chill Mix"
sonos apple play wohnzimmer chillmix
```

MCP:

```json
{
  "tool": "sonos_play_apple_music",
  "arguments": {
    "target": "wohnzimmer",
    "item": "chillmix",
    "scope": "group"
  }
}
```

#### Modus B: Apple-Music-Share-Link-Wiedergabe

SoCo enthält ein ShareLinkPlugin mit AppleMusicShare-Unterstützung. Der Plugin erkennt Apple-Music-Links und kann diese als service-spezifische Sonos-Queue-Items hinzufügen. Unterstützte Linkklassen laut Plugin-Quelle sind insbesondere:

```text
https://music.apple.com/<country>/album/<slug>/<album_id>
https://music.apple.com/<country>/album/<slug>/<album_id>?i=<song_id>
https://music.apple.com/<country>/playlist/<slug>/pl.<playlist_id>
```

Core-Ablauf:

```python
from soco.plugins.sharelink import ShareLinkPlugin

plugin = ShareLinkPlugin(coordinator_soco)
if plugin.is_share_link(url):
    if replace_queue:
        coordinator_soco.clear_queue()
    queue_number = plugin.add_share_link_to_queue(url, dc_title=title, timeout=timeout)
    coordinator_soco.play_from_queue(queue_number - 1)
```

CLI:

```bash
sonos apple play buero --url "https://music.apple.com/de/album/..."
sonos apple enqueue wohnzimmer --url "https://music.apple.com/de/playlist/..." --as-next
```

MCP:

```json
{
  "tool": "sonos_play_apple_music_share_link",
  "arguments": {
    "target": "buero",
    "url": "https://music.apple.com/de/album/...",
    "scope": "group",
    "replace_queue": true
  }
}
```

Fehlerbehandlung:

```json
{
  "ok": false,
  "error": {
    "code": "apple_music_not_authorized_on_sonos",
    "message": "Apple Music scheint im Sonos-System nicht autorisiert zu sein oder der Link konnte von Sonos nicht aufgelöst werden.",
    "remediation": "Apple Music in der Sonos-App erneut autorisieren und den Link dort testweise abspielen."
  }
}
```

#### Modus C: Apple-Music-Suche über Apple Music API, Playback über Share Link

Für eine vollständige Assistant-Erfahrung soll zusätzlich eine Apple-Music-Metadatenintegration vorhanden sein.

Ablauf:

```text
1. CLI/MCP sucht via Apple Music API nach Song/Album/Playlist/Station.
2. Ergebnis enthält Apple-Music-Metadaten und eine Apple-Music-URL.
3. Wiedergabe erfolgt nicht über einen Raw-Audio-Stream, sondern über Modus B: ShareLinkPlugin -> Sonos Queue.
```

Das trennt sauber:

```text
Apple Music API     -> Suche, Metadaten, Katalog-/Bibliotheksdaten
SoCo ShareLink      -> Sonos-kompatible Queue-Wiedergabe
Sonos Apple Music   -> eigentliche Authentifizierung und Streaming
```

Konfiguration:

```toml
[apple_music]
enabled = true
mode = "sonos_share_link"
default_storefront = "de"
allow_catalog_search = true
allow_library_search = false
require_sonos_service = true

[apple_music.developer]
team_id = ""
key_id = ""
private_key_path = "~/.config/sonos-local/apple/AuthKey_XXXX.p8"

[apple_music.auth]
# Nicht im TOML speichern: User Token in Keychain/Keyring oder env var.
user_token_env = "SONSO_APPLE_MUSIC_USER_TOKEN"
```

CLI:

```bash
sonos apple auth status
sonos apple search "daft punk instant crush" --type songs --storefront de
sonos apple play buero "daft punk instant crush" --type songs
sonos apple bind instant-crush --url "https://music.apple.com/de/album/...?..."
```

MCP:

```python
@mcp.tool
async def sonos_search_apple_music(
    query: str,
    media_types: list[Literal["songs", "albums", "playlists", "stations"]] = ["songs", "albums", "playlists"],
    storefront: str | None = None,
    limit: int = 10,
) -> AppleMusicSearchResult: ...

@mcp.tool
async def sonos_play_apple_music(
    target: str,
    item: str,
    media_type: Literal["song", "album", "playlist", "station", "favorite", "alias", "url"] = "alias",
    url: str | None = None,
    scope: Literal["room", "group"] = "group",
    replace_queue: bool = True,
    isolate: bool = False,
) -> CommandResult: ...
```

#### Modus D: AirPlay als optionaler externer Adapter

AirPlay ist keine SoCo-/UPnP-Steuerung und wird nicht als Standardpfad genutzt. Optional kann später ein macOS-spezifischer Adapter ergänzt werden, der Apple Music auf dem Mac öffnet und AirPlay-Ausgabe setzt. Dieser Adapter bleibt getrennt vom Sonos-Core:

```text
core.apple_music.sonos_share_link  -> Standard
core.apple_music.airplay_bridge     -> optional, macOS-only, nicht Headless-freundlich
```

### 4.3 Apple-Music-Grenzen

Nicht implementieren:

```text
- DRM-Stream-Extraktion
- Scraping privater Apple-Music-Web-APIs
- Speicherung von Apple-Login-Daten
- direkte Übergabe nicht autorisierter Apple-Music-Media-URLs an Sonos
```

Implementieren:

```text
- Sonos Favorites mit Apple-Music-Inhalten
- Sonos Playlists mit Apple-Music-Inhalten
- Apple-Music-Share-Links via SoCo ShareLinkPlugin
- optionale Apple-Music-API-Suche zur Erzeugung valider Share Links
- saubere Fehlermeldung, wenn Apple Music in Sonos nicht autorisiert ist
```

---

## 5. Bibliotheken und Dependencies

`pyproject.toml`:

```toml
[project]
name = "sonos"
requires-python = ">=3.11"
dependencies = [
  "soco[events-asyncio]>=0.31,<0.33",
  "fastmcp>=3.3,<4",
  "typer>=0.16,<1",
  "rich>=14,<16",
  "pydantic>=2.7,<3",
  "pydantic-settings>=2.10,<3",
  "aiohttp>=3.11,<4",
  "aiosqlite>=0.20,<1",
  "zeroconf>=0.140,<1",
  "defusedxml>=0.7,<1",
  "tomli-w>=1.1,<2",
  "PyYAML>=6,<7",
  "keyring>=25,<26",
  "PyJWT[crypto]>=2.10,<3"
]

[project.optional-dependencies]
dev = [
  "pytest>=8,<9",
  "pytest-asyncio>=0.25,<1",
  "pytest-httpserver>=1,<2",
  "ruff>=0.9,<1",
  "mypy>=1.14,<2",
  "types-PyYAML"
]

[project.scripts]
sonos = "sonso_local.cli.main:app"
```

Hinweise:

- `soco` bleibt hinter einem eigenen Backend-Interface.
- `fastmcp` wird direkt verwendet: `from fastmcp import FastMCP`.
- `aiohttp` ist für Radio Browser und Apple Music API geeignet.
- `keyring` speichert Apple-Music-User-Token, falls Library-Zugriff aktiviert wird.
- `PyJWT[crypto]` erzeugt Apple-Music-Developer-Tokens aus `.p8`-Keys.

---

## 6. Paketstruktur

```text
sonso_local/
  __init__.py

  core/
    app.py
    models.py
    errors.py
    result.py
    config.py
    policy.py
    resolver.py
    locks.py
    logging.py
    scheduler.py

    sonos/
      backend.py
      soco_backend.py
      discovery.py
      events.py
      topology.py
      speaker_state.py
      favorites.py
      media.py
      queue.py
      groups.py
      snapshot.py
      alarms.py
      sleep_timer.py
      eq.py
      share_links.py

    radio/
      browser_client.py
      resolver.py
      cache.py
      models.py

    apple_music/
      models.py
      config.py
      token_provider.py
      api_client.py
      resolver.py
      sonos_playback.py
      aliases.py

  cli/
    main.py
    render.py
    json_output.py
    commands/
      config.py
      doctor.py
      discover.py
      rooms.py
      status.py
      volume.py
      playback.py
      groups.py
      favorites.py
      radio.py
      apple_music.py
      queue.py
      snapshot.py
      sleep.py
      alarms.py
      mcp.py

  mcp_server/
    server.py
    lifespan.py
    schemas.py
    resources.py
    tools.py

  storage/
    sqlite.py
    migrations.py
    repositories.py

tests/
  unit/
  integration/
  live_sonos/
```

---

## 7. Core API

CLI und MCP nutzen ausschließlich `SonsoLocalService`.

```python
class SonsoLocalService:
    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def discover(self, refresh: bool = False) -> SonosTopology: ...
    async def list_speakers(self) -> list[Speaker]: ...
    async def list_groups(self) -> list[SonosGroup]: ...
    async def get_state(self, target: str | None = None) -> SonosState: ...

    async def set_volume(self, target: str, volume: int, scope: Scope) -> CommandResult: ...
    async def adjust_volume(self, target: str, delta: int, scope: Scope) -> CommandResult: ...
    async def set_mute(self, target: str, muted: bool, scope: Scope) -> CommandResult: ...
    async def set_eq(self, target: str, patch: EqPatch, scope: Scope) -> CommandResult: ...

    async def transport(self, target: str, command: TransportCommand, scope: Scope) -> CommandResult: ...
    async def play_favorite(self, target: str, favorite: str, scope: Scope, isolate: bool) -> CommandResult: ...

    async def search_radio(self, query: str, countrycode: str | None, limit: int) -> list[RadioStation]: ...
    async def play_radio(self, target: str, station: str, scope: Scope, isolate: bool) -> CommandResult: ...
    async def bind_radio_alias(self, alias: str, stationuuid: str, aliases: list[str]) -> CommandResult: ...

    async def search_apple_music(self, query: str, media_types: list[str], storefront: str, limit: int) -> AppleMusicSearchResult: ...
    async def play_apple_music(self, target: str, item: str, scope: Scope, isolate: bool, replace_queue: bool) -> CommandResult: ...
    async def play_apple_music_share_link(self, target: str, url: str, scope: Scope, isolate: bool, replace_queue: bool) -> CommandResult: ...
    async def bind_apple_music_alias(self, alias: str, url_or_favorite: str, aliases: list[str]) -> CommandResult: ...

    async def group(self, coordinator: str, members: list[str]) -> CommandResult: ...
    async def ungroup(self, targets: list[str]) -> CommandResult: ...
    async def isolate(self, target: str) -> CommandResult: ...

    async def list_queue(self, target: str) -> QueueState: ...
    async def clear_queue(self, target: str) -> CommandResult: ...
    async def play_queue_index(self, target: str, index: int) -> CommandResult: ...

    async def save_snapshot(self, targets: list[str], name: str | None) -> SnapshotResult: ...
    async def restore_snapshot(self, snapshot_id_or_name: str) -> CommandResult: ...

    async def list_alarms(self) -> list[Alarm]: ...
    async def update_alarm(self, alarm_id: str, patch: AlarmPatch) -> CommandResult: ...

    async def set_sleep_timer(self, target: str, seconds: int) -> CommandResult: ...
    async def clear_sleep_timer(self, target: str) -> CommandResult: ...
```

---

## 8. Domain-Modelle

```python
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
```

```python
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
    capabilities: frozenset[str]
```

```python
@dataclass(frozen=True)
class SonosGroup:
    group_uid: str
    household_id: str
    coordinator_uid: str
    member_uids: tuple[str, ...]
```

```python
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
    aliases: tuple[str, ...]
```

```python
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
```

---

## 9. Konfiguration

Pfad:

```text
~/.config/sonos-local
```

Dateien:

```text
~/.config/sonos-local/
  config.toml
  rooms.toml
  radio.toml
  apple_music.toml
  policies.toml
  state.sqlite
  logs/
    sonos.jsonl
  apple/
    AuthKey_<KEY_ID>.p8       # optional, nur wenn Apple-Music-API-Suche aktiviert ist
```

Optionaler Override:

```bash
export SONSO_LOCAL_CONFIG_DIR=/path/to/config
```

### 9.1 `config.toml`

```toml
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
sqlite_path = "~/.config/sonos/state.sqlite"
log_path = "~/.config/sonos/logs/sonos.jsonl"
```

### 9.2 `rooms.toml`

```toml
[rooms.wohnzimmer]
sonos_names = ["Wohnzimmer"]
aliases = ["wohnzimmer", "living room", "wz"]

[rooms.buero]
sonos_names = ["Büro"]
aliases = ["büro", "buero", "office", "arbeitszimmer"]
```

### 9.3 `policies.toml`

```toml
[volume]
default_delta = 5
max_room_volume = 70
max_group_volume = 60
max_all_volume = 40
require_confirmation_for_all_rooms = false

[playback]
group_playback_policy = "use_existing_group" # use_existing_group | require_confirmation | isolate_target
allow_arbitrary_urls = false
allowed_url_hosts = []
block_private_network_urls = true

[radio]
default_countrycode = "DE"
hide_broken = true
require_lastcheckok = true
allow_hls = false
min_bitrate = 64
preferred_codecs = ["MP3", "AAC", "AAC+"]

[apple_music]
require_sonos_service = true
allow_share_links = true
allow_catalog_search = true
allow_library_search = false
allow_airplay_bridge = false
```

### 9.4 `radio.toml`

```toml
[aliases.einslive]
stationuuid = ""
preferred_name = "1LIVE"
countrycode = "DE"
aliases = ["einslive", "1live", "eins live", "wdr 1live"]
```

### 9.5 `apple_music.toml`

```toml
[apple_music]
enabled = true
mode = "sonos_share_link"
default_storefront = "de"

[aliases.chillmix]
kind = "favorite"       # favorite | share_link
favorite_item_id = ""   # stable Sonos Favorite ID, wenn gebunden
url = ""                # Apple Music Share Link, wenn share_link
aliases = ["chill mix", "chillmix", "entspannte musik"]

[developer]
enabled = false
team_id = ""
key_id = ""
private_key_path = "~/.config/sonos/apple/AuthKey_XXXX.p8"

[auth]
user_token_env = "SONSO_APPLE_MUSIC_USER_TOKEN"
keyring_service = "sonos"
keyring_username = "apple_music_user_token"
```

---

## 10. Storage-Modell

SQLite-Tabellen:

```sql
CREATE TABLE speakers (
  uid TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  household_id TEXT,
  visible INTEGER NOT NULL,
  available INTEGER NOT NULL,
  boot_seqnum TEXT,
  model_name TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE groups (
  group_uid TEXT PRIMARY KEY,
  household_id TEXT NOT NULL,
  coordinator_uid TEXT NOT NULL,
  member_uids_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE favorites (
  household_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  uri TEXT,
  metadata_xml TEXT,
  resource_metadata_xml TEXT,
  playable INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (household_id, item_id)
);

CREATE TABLE radio_aliases (
  alias TEXT PRIMARY KEY,
  stationuuid TEXT NOT NULL,
  aliases_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE radio_cache (
  stationuuid TEXT PRIMARY KEY,
  station_json TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_played_at TEXT
);

CREATE TABLE apple_music_aliases (
  alias TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  favorite_item_id TEXT,
  share_url TEXT,
  aliases_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE apple_music_cache (
  cache_key TEXT PRIMARY KEY,
  result_json TEXT NOT NULL,
  storefront TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE snapshots (
  snapshot_id TEXT PRIMARY KEY,
  name TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

---

## 11. Discovery, Events und Polling

### 11.1 Discovery-Quellen

```text
1. SoCo/SSDP
2. Zeroconf: _sonos._tcp.local.
3. statische Hosts aus config.toml
```

Algorithmus:

```text
- Initiale Discovery mit Timeout.
- Alle sichtbaren Zonen ermitteln.
- Invisible Devices separat merken, aber nicht als steuerbare Räume anzeigen.
- Household ID, UID, IP, Boot Seqnum und Model Name cachen.
- Wenn statische Hosts gesetzt sind, regelmäßig heartbeat/poll.
- Wenn ein Device rebooted oder vanished, State invalidieren und neu laden.
```

### 11.2 Events

Zu abonnierende Sonos-Services:

```text
ZoneGroupTopology  -> Gruppen, Coordinator, sichtbare Zonen
RenderingControl   -> Volume, Mute, EQ
AVTransport        -> Playback State, URI, Track Info, Queue Info
ContentDirectory   -> Favorites, Playlists
DeviceProperties   -> Room Name, Config Changes
AlarmClock         -> Alarms
```

### 11.3 Polling-Fallback

Polling läuft, wenn:

```text
- Event-Subscription fehlschlägt
- Event-Callback vom Sonos-Gerät nicht erreichbar ist
- Speaker als unavailable markiert wurde
- manuelle Hosts verwendet werden
- ein Kommando einen Topology-Refresh erfordert
```

---

## 12. SoCo Backend

### 12.1 Backend-Interface

```python
class SonosBackend(Protocol):
    async def discover(self, refresh: bool = False) -> SonosTopology: ...
    async def subscribe_events(self) -> None: ...
    async def poll_state(self) -> None: ...

    async def set_volume(self, speaker_uid: str, volume: int) -> SpeakerState: ...
    async def adjust_volume(self, speaker_uid: str, delta: int) -> SpeakerState: ...
    async def set_mute(self, speaker_uid: str, muted: bool) -> SpeakerState: ...

    async def transport(self, coordinator_uid: str, command: TransportCommand) -> CommandResult: ...
    async def play_uri(self, coordinator_uid: str, uri: str, title: str | None, force_radio: bool) -> CommandResult: ...
    async def play_favorite(self, coordinator_uid: str, favorite_item_id: str, replace_queue: bool) -> CommandResult: ...
    async def play_share_link(self, coordinator_uid: str, url: str, replace_queue: bool, title: str | None) -> CommandResult: ...

    async def join(self, coordinator_uid: str, member_uids: list[str]) -> CommandResult: ...
    async def unjoin(self, speaker_uids: list[str]) -> CommandResult: ...
```

### 12.2 Threading-Modell

SoCo ist synchron. Nach außen bleibt der Core async:

```python
async def _run_soco(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    return await asyncio.to_thread(fn, *args, **kwargs)
```

Locks:

```text
- speaker lock für Volume/Mute/EQ
- group lock für Transport/Queue/Playback
- topology lock für Join/Unjoin/Discovery Refresh
- favorites lock pro Household
```

---

## 13. Gruppen- und Scope-Semantik

```python
class Scope(StrEnum):
    ROOM = "room"
    GROUP = "group"
    ALL = "all"
```

Defaults:

| Aktion | Default Scope | Bemerkung |
|---|---:|---|
| Volume up/down | room | einzelne Raumlautstärke |
| Set volume | room | policy-capped |
| Mute/unmute | room | `--all` explizit |
| Play/Pause/Stop | group | Transport läuft über Coordinator |
| Radio/Favorite/Apple Music play | group | optional `--isolate` |
| Queue | group | Queue gehört zur Gruppe/Coordinator |
| Snapshot | room/group/all | explizit |

Grouped Playback Policies:

```toml
group_playback_policy = "use_existing_group"
# Alternativen:
# require_confirmation
# isolate_target
```

Bei mehrdeutigen Gruppeneffekten:

```json
{
  "ok": false,
  "requires_confirmation": true,
  "reason": "target_is_grouped",
  "message": "Büro ist aktuell mit Wohnzimmer gruppiert. Die Wiedergabe würde die ganze Gruppe ändern.",
  "suggested_arguments": {
    "target": "büro",
    "scope": "group",
    "isolate": true
  }
}
```

---

## 14. Radio Browser

### 14.1 Client-Regeln

Der Radio-Browser-Client muss:

```text
- beschreibenden User-Agent senden
- Server/Mirrors dynamisch auflösen
- Retry/Failover über mehrere Server machen
- stationuuid statt numerischer IDs verwenden
- hidebroken/lastcheckok beachten
- vor Playback /json/url/{stationuuid} aufrufen
- url_resolved bevorzugen, falls vorhanden
```

### 14.2 API

```python
class RadioBrowserClient:
    async def search(self, query: str, countrycode: str | None, limit: int) -> list[RadioStation]: ...
    async def get_by_uuid(self, stationuuid: str) -> RadioStation: ...
    async def resolve_play_url(self, stationuuid: str) -> ResolvedRadioUrl: ...
```

### 14.3 Resolver

Suchstrategie für `einslive`:

```text
1. Alias in radio.toml / SQLite prüfen.
2. stationuuid exact prüfen.
3. normalisierten exakten Namen prüfen.
4. Radio Browser search:
   - name=einslive
   - countrycode=DE
   - hidebroken=true
   - order=clickcount
   - reverse=true
   - limit=10
5. Score berechnen.
6. Bei Mehrdeutigkeit Kandidaten zurückgeben, nicht raten.
```

Playback:

```python
station = await radio_resolver.resolve("einslive")
resolved = await radio_client.resolve_play_url(station.stationuuid)
await sonos_backend.play_uri(
    coordinator_uid=target.coordinator_uid,
    uri=resolved.url,
    title=station.name,
    force_radio=True,
)
```

---

## 15. Apple Music Implementierungsdetails

### 15.1 Module

```text
core/apple_music/models.py          # AppleMusicItem, AppleMusicSearchResult
core/apple_music/token_provider.py  # Developer Token + optional Music User Token
core/apple_music/api_client.py      # Apple Music API HTTP Client
core/apple_music/resolver.py        # Alias/Favorite/ShareLink/API-Auflösung
core/apple_music/sonos_playback.py  # ShareLinkPlugin + Sonos queue playback
core/apple_music/aliases.py         # Persistente Bindings
```

### 15.2 Token Provider

```python
class AppleMusicTokenProvider:
    async def get_developer_token(self) -> str:
        """JWT aus Team ID, Key ID und .p8 Private Key erzeugen."""

    async def get_user_token(self) -> str | None:
        """Aus Keyring oder env var lesen; nur für Library-Zugriff erforderlich."""
```

### 15.3 API Client

```python
class AppleMusicApiClient:
    async def search_catalog(
        self,
        term: str,
        storefront: str,
        types: list[str],
        limit: int,
    ) -> AppleMusicSearchResult: ...

    async def search_library(
        self,
        term: str,
        types: list[str],
        limit: int,
    ) -> AppleMusicSearchResult: ...
```

### 15.4 Resolver-Reihenfolge

```text
1. Alias in apple_music.toml / SQLite.
2. Sonos Favorite mit Apple-Music-Quelle.
3. Direkter Apple-Music-Share-Link.
4. Apple Music API Katalogsuche -> URL -> ShareLinkPlugin.
5. Optional Library-Suche, wenn User Token vorhanden.
```

### 15.5 Playback über SoCo ShareLinkPlugin

```python
class AppleMusicSonosPlayback:
    async def play_share_link(
        self,
        coordinator_uid: str,
        url: str,
        replace_queue: bool,
        title: str | None,
    ) -> CommandResult:
        soco = self._registry.get_soco(coordinator_uid)
        plugin = ShareLinkPlugin(soco)

        if not plugin.is_share_link(url):
            raise InvalidAppleMusicShareLink(url)

        def sync_call() -> int:
            if replace_queue:
                soco.clear_queue()
            queue_no = plugin.add_share_link_to_queue(
                url,
                dc_title=title or "",
                timeout=self._settings.long_service_timeout_seconds,
            )
            soco.play_from_queue(queue_no - 1)
            return queue_no

        queue_no = await asyncio.to_thread(sync_call)
        return CommandResult.ok(...)
```

### 15.6 Fehlercodes

```text
apple_music_disabled
apple_music_developer_token_missing
apple_music_user_token_missing
apple_music_search_failed
apple_music_no_result
apple_music_ambiguous_result
apple_music_invalid_share_link
apple_music_not_authorized_on_sonos
apple_music_queue_add_failed
```

---

## 16. CLI-Design

Die CLI bietet keine Chat-Funktion und kein LLM. Alle Kommandos sind explizit.

### 16.1 Globale Optionen

```bash
--config-dir PATH
--json
--dry-run
--refresh
--scope room|group|all
--confirm
--timeout SECONDS
--log-level debug|info|warning|error
```

### 16.2 Kommandobaum

```bash
sonos config init
sonos config show
sonos config validate
sonos doctor

sonos discover
sonos rooms
sonos status [TARGET]

sonos volume get TARGET
sonos volume set TARGET VALUE
sonos volume up TARGET --step 5
sonos volume down TARGET --step 5
sonos mute TARGET
sonos unmute TARGET
sonos mute --all --confirm

sonos playback play TARGET
sonos playback pause TARGET
sonos playback stop TARGET
sonos playback next TARGET
sonos playback previous TARGET
sonos playback seek TARGET 00:01:30

sonos groups list
sonos groups join COORDINATOR MEMBER...
sonos groups ungroup TARGET...
sonos groups isolate TARGET

sonos favorites list
sonos favorites play TARGET FAVORITE
sonos favorites refresh

sonos radio search QUERY --country DE
sonos radio bind ALIAS --stationuuid UUID
sonos radio play TARGET ALIAS_OR_QUERY
sonos radio aliases

sonos apple auth status
sonos apple search QUERY --type songs --storefront de
sonos apple bind ALIAS --url URL
sonos apple bind ALIAS --favorite FAVORITE_NAME
sonos apple play TARGET ALIAS_OR_QUERY
sonos apple play TARGET --url URL
sonos apple enqueue TARGET --url URL --as-next
sonos apple aliases

sonos queue list TARGET
sonos queue clear TARGET
sonos queue play TARGET INDEX
sonos queue remove TARGET INDEX

sonos snapshot save TARGET... --name NAME
sonos snapshot restore NAME_OR_ID
sonos snapshot list

sonos sleep set TARGET SECONDS
sonos sleep clear TARGET

sonos alarms list
sonos alarms enable ALARM_ID
sonos alarms disable ALARM_ID
sonos alarms update ALARM_ID --time 07:30 --enabled true

sonos mcp --transport stdio
sonos mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

### 16.3 JSON-Ausgabe

Erfolg:

```json
{
  "ok": true,
  "action": "apple_music.play",
  "target": {
    "input": "buero",
    "resolved_name": "Büro",
    "speaker_uid": "RINCON_...",
    "coordinator_uid": "RINCON_..."
  },
  "media": {
    "source": "apple_music",
    "kind": "share_link",
    "title": "Instant Crush",
    "url": "https://music.apple.com/de/album/..."
  },
  "scope": "group",
  "queue_position": 1,
  "warnings": []
}
```

Mehrdeutigkeit:

```json
{
  "ok": false,
  "error": {
    "code": "apple_music_ambiguous_result",
    "message": "Mehrere Apple-Music-Ergebnisse passen zu 'chill mix'.",
    "candidates": [
      {"id": "...", "type": "playlist", "name": "Chill Mix", "url": "..."},
      {"id": "...", "type": "album", "name": "Chill Mix", "url": "..."}
    ]
  }
}
```

### 16.4 Exit Codes

```text
0  success
1  generic error
2  config error
3  target not found
4  ambiguous target
5  network/backend error
6  policy prevented action
7  confirmation required
8  radio resolution failed
9  apple music resolution failed
10 apple music authorization missing
```

---

## 17. FastMCP Server

### 17.1 Grundstruktur

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import FastMCP

from sonso_local.core.app import SonsoLocalService
from sonso_local.core.config import load_config


@dataclass
class McpAppContext:
    service: SonsoLocalService


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[McpAppContext]:
    config = load_config()
    service = SonsoLocalService(config)
    await service.startup()
    try:
        yield McpAppContext(service=service)
    finally:
        await service.shutdown()


mcp = FastMCP("sonos", lifespan=lifespan)
```

### 17.2 Tools

```python
@mcp.tool
async def sonos_list_speakers() -> SpeakersResult: ...

@mcp.tool
async def sonos_get_state(target: str | None = None) -> StateResult: ...

@mcp.tool
async def sonos_adjust_volume(
    target: str,
    delta: int,
    scope: Literal["room", "group", "all"] = "room",
) -> CommandResult: ...

@mcp.tool
async def sonos_set_volume(
    target: str,
    volume: int,
    scope: Literal["room", "group"] = "room",
) -> CommandResult: ...

@mcp.tool
async def sonos_set_mute(
    target: str,
    muted: bool,
    scope: Literal["room", "group", "all"] = "room",
) -> CommandResult: ...

@mcp.tool
async def sonos_transport(
    target: str,
    command: Literal["play", "pause", "stop", "next", "previous"],
    scope: Literal["group", "room", "all"] = "group",
) -> CommandResult: ...

@mcp.tool
async def sonos_play_favorite(
    target: str,
    favorite: str,
    scope: Literal["group", "room"] = "group",
    isolate: bool = False,
) -> CommandResult: ...

@mcp.tool
async def sonos_search_radio(
    query: str,
    countrycode: str | None = "DE",
    limit: int = 10,
) -> RadioSearchResult: ...

@mcp.tool
async def sonos_play_radio(
    target: str,
    station: str,
    stationuuid: str | None = None,
    scope: Literal["group", "room"] = "group",
    isolate: bool = False,
) -> CommandResult: ...

@mcp.tool
async def sonos_search_apple_music(
    query: str,
    media_types: list[Literal["songs", "albums", "playlists", "stations"]] = ["songs", "albums", "playlists"],
    storefront: str | None = "de",
    limit: int = 10,
) -> AppleMusicSearchResult: ...

@mcp.tool
async def sonos_play_apple_music(
    target: str,
    item: str,
    media_type: Literal["alias", "favorite", "song", "album", "playlist", "station", "url"] = "alias",
    url: str | None = None,
    scope: Literal["group", "room"] = "group",
    isolate: bool = False,
    replace_queue: bool = True,
) -> CommandResult: ...

@mcp.tool
async def sonos_play_apple_music_share_link(
    target: str,
    url: str,
    scope: Literal["group", "room"] = "group",
    isolate: bool = False,
    replace_queue: bool = True,
) -> CommandResult: ...

@mcp.tool
async def sonos_group(coordinator: str, members: list[str]) -> CommandResult: ...

@mcp.tool
async def sonos_ungroup(targets: list[str]) -> CommandResult: ...

@mcp.tool
async def sonos_snapshot_save(targets: list[str], name: str | None = None) -> SnapshotResult: ...

@mcp.tool
async def sonos_snapshot_restore(snapshot_id_or_name: str) -> CommandResult: ...

@mcp.tool
async def sonos_queue(
    target: str,
    action: Literal["list", "clear", "remove", "play"],
    index: int | None = None,
) -> CommandResult: ...

@mcp.tool
async def sonos_sleep_timer(target: str, seconds: int | None) -> CommandResult: ...
```

### 17.3 Resources

```python
@mcp.resource("sonos://speakers")
async def speakers_resource() -> list[SpeakerResource]: ...

@mcp.resource("sonos://groups")
async def groups_resource() -> list[GroupResource]: ...

@mcp.resource("sonos://state")
async def state_resource() -> SonosStateResource: ...

@mcp.resource("sonos://favorites")
async def favorites_resource() -> list[FavoriteResource]: ...

@mcp.resource("sonos://radio/aliases")
async def radio_aliases_resource() -> dict[str, RadioAliasResource]: ...

@mcp.resource("sonos://apple-music/aliases")
async def apple_music_aliases_resource() -> dict[str, AppleMusicAliasResource]: ...

@mcp.resource("sonos://capabilities")
async def capabilities_resource() -> CapabilitiesResource: ...

@mcp.resource("sonos://config/policies")
async def policies_resource() -> PolicyResource: ...
```

### 17.4 Assistant-Beispiele

„mach die musik im wohnzimmer lauter“:

```json
{
  "tool": "sonos_adjust_volume",
  "arguments": {
    "target": "wohnzimmer",
    "delta": 5,
    "scope": "room"
  }
}
```

„alles stumm“:

```json
{
  "tool": "sonos_set_mute",
  "arguments": {
    "target": "all",
    "muted": true,
    "scope": "all"
  }
}
```

„spiel einslive im büro“:

```json
{
  "tool": "sonos_play_radio",
  "arguments": {
    "target": "büro",
    "station": "einslive",
    "scope": "group",
    "isolate": false
  }
}
```

„spiel meine Apple Music Chill Mix im Wohnzimmer“:

```json
{
  "tool": "sonos_play_apple_music",
  "arguments": {
    "target": "wohnzimmer",
    "item": "chill mix",
    "media_type": "alias",
    "scope": "group",
    "replace_queue": true
  }
}
```

### 17.5 Transports

Default:

```bash
sonos mcp --transport stdio
```

Optional lokal:

```bash
sonos mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

Remote nur mit Auth/Proxy:

```bash
sonos mcp --transport streamable-http --host 0.0.0.0 --port 8765 --auth-token-env SONSO_MCP_TOKEN
```

---

## 18. Policies und Sicherheit

### 18.1 URL-Policy

Default:

```toml
[playback]
allow_arbitrary_urls = false
block_private_network_urls = true
allowed_url_hosts = []
```

Erlaubt im Default:

```text
- Radio-Browser-URLs, nachdem sie über stationuuid resolved wurden
- Apple-Music-Share-Links von music.apple.com
- Sonos Favorites / Sonos Playlists
```

Nicht erlaubt im Default:

```text
- beliebige http(s)-URLs
- private IPs / localhost / link-local URLs als Media-URL
- file:// URLs im MCP-Kontext
```

### 18.2 Volume-Policy

```text
- room cap
- group cap
- all cap
- optional confirmation for all-room actions
- dry-run support
```

### 18.3 Apple-Music-Security

```text
- keine Apple-ID-Passwörter speichern
- Developer Key als Datei mit 0600-Rechten prüfen
- Music User Token im OS Keyring oder env var
- keine privaten/scraped Apple APIs
- kein DRM-Bypass
```

---

## 19. Implementierungsphasen

Diese Phasen sind Liefer-/Bauabschnitte, nicht funktionale MVP-Abgrenzungen. Das Zielprodukt umfasst alle beschriebenen Funktionen.

### Phase 1: Projektfundament

Ergebnis:

```text
- installierbares Paket
- Config Bootstrap
- Result/Error-System
- Logging
- Testgerüst
```

Tasks:

```text
- pyproject.toml
- src-layout
- pydantic config models
- ~/.config/sonos anlegen
- config init/show/validate
- structured JSON logs
- Domain exceptions
- CommandResult/ErrorResult
- pytest/ruff/mypy setup
```

Akzeptanz:

```bash
sonos config init
sonos config validate
sonos --help
```

### Phase 2: Storage und Repositories

Ergebnis:

```text
- SQLite initialisiert
- Migrationen
- Repositories für Speaker, Groups, Favorites, Radio, Apple Music, Snapshots
```

Akzeptanz:

```bash
sonos doctor --json
```

### Phase 3: SoCo Discovery und Topology

Ergebnis:

```text
- SSDP/SoCo Discovery
- Zeroconf Discovery
- statische Hosts
- visible/invisible zones
- Household und Gruppenmodell
```

Akzeptanz:

```bash
sonos discover
sonos rooms
sonos groups list
```

### Phase 4: Events und Polling-Fallback

Ergebnis:

```text
- Event Subscriptions
- AVTransport/RenderingControl/ZoneGroupTopology/ContentDirectory/AlarmClock
- Polling-Fallback
- Availability Recovery
```

Akzeptanz:

```text
- Änderung in Sonos-App wird im CLI status sichtbar.
- Wenn Eventing blockiert ist, bleibt Polling funktionsfähig.
```

### Phase 5: Volume, Mute, EQ und Status

Ergebnis:

```text
- Room/Group/All scope
- Policy caps
- per speaker locks
- status resource
```

Akzeptanz:

```bash
sonos volume up wohnzimmer --step 5
sonos mute --all --confirm
sonos status wohnzimmer --json
```

### Phase 6: Transport und Media State

Ergebnis:

```text
- play/pause/stop/next/previous/seek
- coordinator resolution
- media source detection
- current track metadata
```

Akzeptanz:

```bash
sonos playback pause wohnzimmer
sonos playback play wohnzimmer
```

### Phase 7: Gruppen

Ergebnis:

```text
- join
- ungroup
- isolate
- wait_for_topology
- grouped playback policies
```

Akzeptanz:

```bash
sonos groups join wohnzimmer kueche
sonos groups isolate buero
```

### Phase 8: Favorites und Sonos Playlists

Ergebnis:

```text
- Household Favorites Cache
- Sonos Playlists Cache
- ContentDirectory invalidation
- playable filtering
- play favorite by item_id/name/alias
```

Akzeptanz:

```bash
sonos favorites list
sonos favorites play wohnzimmer "Chill Mix"
```

### Phase 9: Radio Browser

Ergebnis:

```text
- Server discovery/failover
- User-Agent
- search
- stationuuid resolve
- aliases
- playback force_radio=True
```

Akzeptanz:

```bash
sonos radio search einslive --country DE
sonos radio bind einslive --stationuuid <uuid>
sonos radio play buero einslive
```

### Phase 10: Apple Music

Ergebnis:

```text
- Apple-Music-Favorites erkennen und binden
- Apple-Music-Share-Links validieren
- ShareLinkPlugin Playback
- optional Apple Music API search
- aliases
- MCP tools
```

Akzeptanz:

```bash
sonos apple bind chillmix --favorite "Chill Mix"
sonos apple play wohnzimmer chillmix
sonos apple play buero --url "https://music.apple.com/de/album/..."
sonos apple search "daft punk instant crush" --type songs --storefront de
```

### Phase 11: Queue

Ergebnis:

```text
- list
- clear
- remove
- play index
- enqueue favorite/radio/apple share link
```

Akzeptanz:

```bash
sonos queue list wohnzimmer
sonos queue clear wohnzimmer
```

### Phase 12: Snapshot und Restore

Ergebnis:

```text
- group topology snapshot
- volume/mute snapshot
- queue/source snapshot soweit möglich
- restore order: groups -> queue/source -> playback -> volume/mute
```

Akzeptanz:

```bash
sonos snapshot save wohnzimmer --name before-test
sonos snapshot restore before-test
```

### Phase 13: Sleep Timer und Alarms

Ergebnis:

```text
- sleep set/clear
- alarm list
- alarm enable/disable/update
- AlarmClock event invalidation
```

Akzeptanz:

```bash
sonos sleep set wohnzimmer 1800
sonos alarms list
```

### Phase 14: CLI fertigstellen

Ergebnis:

```text
- vollständiger Typer command tree
- Rich-Ausgabe
- JSON-Ausgabe überall
- dry-run überall bei mutierenden Aktionen
- stabile Exit-Codes
- shell completion
```

### Phase 15: FastMCP Server fertigstellen

Ergebnis:

```text
- FastMCP lifespan
- Tools
- Resources
- Pydantic Schemas
- stdio transport
- streamable HTTP optional
- Auth bei HTTP
- Tool descriptions mit deutschen Beispielen
```

Akzeptanz:

```bash
sonos mcp --transport stdio
```

MCP Client Config:

```json
{
  "mcpServers": {
    "sonos": {
      "command": "sonos",
      "args": ["mcp", "--transport", "stdio"]
    }
  }
}
```

### Phase 16: Tests und Packaging

Ergebnis:

```text
- Unit Tests mit FakeSonosBackend
- HTTP Mock Tests für Radio Browser und Apple Music API
- Event parser fixtures
- Integration Tests mit mocked SoCo
- Live Tests mit echten Sonos-Geräten
- pipx/uv installierbar
```

Live Tests:

```bash
pytest -m sonos_live --sonos-room Wohnzimmer
```

---

## 20. Teststrategie

### 20.1 Unit Tests

```text
- TargetResolver: Aliases, Umlaute, Ambiguity
- ScopeResolver: room/group/all
- Policy: volume caps, all-room confirmation, URL blocklist
- RadioResolver: alias/search/ranking
- AppleMusicResolver: alias/favorite/share-link/API result
- CommandResult serialization
```

### 20.2 Integration Tests ohne echte Sonos

```text
- FakeSonosBackend
- Fake Radio Browser HTTP server
- Fake Apple Music API server
- SQLite migration tests
- FastMCP tool schema tests
```

### 20.3 Live Sonos Tests

```text
- discovery
- volume/mute roundtrip
- favorites list
- radio playback with known station
- Apple Music favorite playback, wenn Dienst eingerichtet
- Apple Music share link playback, wenn Dienst eingerichtet
- group join/isolate
- snapshot/restore
```

---

## 21. Kritische Fallstricke

### 21.1 UPnP deaktiviert

Symptom:

```text
HTTP 403 oder keine Steuerbarkeit trotz IP-Erreichbarkeit
```

Gegenmaßnahme:

```text
sonos doctor erkennt den Fall und gibt konkrete Sonos-App-Hinweise aus.
```

### 21.2 VLAN, Docker, Multicast

Symptom:

```text
Discovery findet keine Geräte.
```

Gegenmaßnahmen:

```text
- statische Hosts konfigurieren
- Host-Netzwerkmodus bei Docker
- UDP 1900 / TCP 1400 prüfen
- advertise_addr setzen
- SSDP/mDNS Reflection prüfen
```

### 21.3 Event Callback nicht erreichbar

Symptom:

```text
Status ändert sich nicht live.
```

Gegenmaßnahme:

```text
Polling-Fallback aktivieren, doctor-Warnung ausgeben.
```

### 21.4 SoCo blockiert async Server

Gegenmaßnahme:

```text
Alle SoCo-Aufrufe über asyncio.to_thread und Locks.
```

### 21.5 Gruppen wirken anders als Nutzer erwarten

Gegenmaßnahme:

```text
Explizite Scopes, require_confirmation, isolate option.
```

### 21.6 Radio-Browser-Datenqualität

Gegenmaßnahme:

```text
hidebroken, lastcheckok, codec/hls policy, alias binding, click endpoint.
```

### 21.7 Apple Music ist kein Raw-Stream-Backend

Gegenmaßnahme:

```text
Apple Music nur über Sonos Service/Favorites/Share Links/API-Metadaten unterstützen.
Keine DRM-Stream-Extraktion.
```

### 21.8 Apple Music API Search != Sonos Playback

Gegenmaßnahme:

```text
API liefert nur Metadaten/URLs. Playback läuft über SoCo ShareLinkPlugin und Sonos Apple-Music-Service.
```

### 21.9 MCP-Sicherheitsrisiken

Gegenmaßnahme:

```text
- stdio als Default
- HTTP nur localhost oder auth-protected
- keine arbitrary URL tools im Default
- structured confirmation payloads
- audit logging
```

---

## 22. Quellen

- Home Assistant Sonos Integration: <https://www.home-assistant.io/integrations/sonos/>
- Home Assistant Sonos Source: <https://github.com/home-assistant/core/tree/dev/homeassistant/components/sonos>
- Home Assistant Sonos Manifest: <https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sonos/manifest.json>
- Home Assistant Sonos Init/Discovery: <https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sonos/__init__.py>
- Home Assistant Sonos Favorites: <https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sonos/favorites.py>
- Home Assistant Sonos Media: <https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sonos/media.py>
- Home Assistant Sonos Media Player: <https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sonos/media_player.py>
- SoCo PyPI: <https://pypi.org/project/soco/>
- SoCo Docs: <https://docs.python-soco.com/en/latest/>
- SoCo Core API: <https://docs.python-soco.com/en/latest/api/soco.core.html>
- SoCo ShareLinkPlugin Docs: <https://docs.python-soco.com/en/latest/api/soco.plugins.sharelink.html>
- SoCo ShareLinkPlugin Source: <https://raw.githubusercontent.com/SoCo/SoCo/master/soco/plugins/sharelink.py>
- FastMCP PyPI: <https://pypi.org/project/fastmcp/>
- FastMCP Docs: <https://gofastmcp.com/getting-started/welcome>
- Radio Browser API: <https://docs.radio-browser.info/>
- Sonos Apple Music: <https://support.sonos.com/en-us/services/apple-music>
- Sonos Favorites: <https://support.sonos.com/en-us/article/add-favorites-to-your-home-screen>
- Sonos AirPlay: <https://support.sonos.com/en/article/stream-airplay-audio-to-sonos>
- Sonos Control API: <https://docs.sonos.com/docs/control-sonos-players>
- Apple Music / MusicKit: <https://developer.apple.com/musickit/>
