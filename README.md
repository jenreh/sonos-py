# sonos-py

![Version](https://img.shields.io/badge/version-0.3.1-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.14%2B-orange)](https://www.python.org)

> Local Sonos controller — CLI and MCP server. No cloud, no account, no internet required.

Control your Sonos speakers directly over your LAN via a full-featured CLI or as an [MCP server](https://modelcontextprotocol.io) that exposes every capability as an AI tool.

## Features

- **Full CLI** — discover, status, volume, playback, groups, favorites, radio, Apple Music, queue, alarms, snapshots, sleep timer
- **MCP server** — all features available as tools for LLM agents (stdio and streamable-HTTP transports)
- **Favorites & playlists** — play Sonos favorites, radio stations, and Apple Music by name (fuzzy match)
- **Radio Browser** — search and play any station from the [radio-browser.info](https://www.radio-browser.info) directory
- **Apple Music** — catalog search, share-link playback, alias bookmarks
- **Snapshots** — save and restore volume/source/group state
- **Policy engine** — volume caps, URL allowlists, confirmation guards
- **Zero cloud** — every command hits your speakers directly over UPnP/SoCo

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Sonos speakers on the same LAN (S1 or S2 firmware)

## Installation

```bash
# from PyPI (once published)
pip install sonos-py

# from source
git clone https://github.com/jenreh/sonos-py
cd sonos-py
uv sync
```

The `sonos` command is available after install. Run `sonos discover` to verify your speakers are reachable.

## Quick start

```bash
# Find all speakers on the network
sonos discover

# Show playback state for all rooms
sonos status

# Play a Sonos favorite (fuzzy name match)
sonos favorites play Büro "Lieblingstitel"

# Play a radio station by alias
sonos radio play Büro 1LIVE

# Adjust volume
sonos volume up Büro --step 10

# Pause / resume
sonos playback pause Büro
sonos playback play Büro
```

## CLI reference

```text
sonos [OPTIONS] COMMAND [ARGS]

Options:
  --config-dir PATH   Override config directory
  --json              Output JSON instead of rich tables
  --dry-run           Preview action without executing
  --log-level TEXT    Logging level  [default: WARNING]
  --refresh           Force topology refresh before command
```

| Command group | Description |
| --- | --- |
| `discover` | Scan LAN for Sonos speakers |
| `rooms` | List speakers and their network info |
| `status [ROOM]` | Playback state for one room or all |
| `volume get/set/up/down` | Volume control (room / group / all scopes) |
| `mute / unmute` | Mute control |
| `playback play/pause/stop/next/previous` | Transport controls |
| `favorites list/play/refresh` | Sonos favorites |
| `radio search/play/bind/aliases` | Internet radio via Radio Browser |
| `apple auth/search/play/bind/aliases/enqueue` | Apple Music |
| `groups list/join/ungroup/isolate` | Group management |
| `queue list/clear/play` | Queue management |
| `alarms list/enable/disable/update/set` | Alarm clock management |
| `snapshot save/restore/list` | State snapshots |
| `sleep [ROOM] [SECONDS]` | Sleep timer (omit seconds to clear) |
| `config show` | Display current configuration |
| `doctor` | Diagnose config, storage, and network |

## MCP server

```bash
# stdio (default — use with Claude Desktop or any MCP host)
sonos-mcp

# streamable-HTTP
sonos-mcp --transport streamable-http --port 8765
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sonos": {
      "command": "sonos-mcp"
    }
  }
}
```

### Available MCP tools

| Tool | Description |
| --- | --- |
| `sonos_list_speakers` | List all speakers |
| `sonos_list_groups` | List speaker groups |
| `sonos_get_state` | Playback state (one or all) |
| `sonos_set_volume` / `sonos_adjust_volume` | Volume control |
| `sonos_set_mute` | Mute / unmute |
| `sonos_transport` | play / pause / stop / next / previous |
| `sonos_play_favorite` | Play a Sonos favorite by name |
| `sonos_search_radio` / `sonos_play_radio` | Radio Browser search and playback |
| `sonos_search_apple_music` / `sonos_play_apple_music` | Apple Music |
| `sonos_group` / `sonos_ungroup` / `sonos_isolate` | Group management |
| `sonos_queue` | List, clear, or play from queue |
| `sonos_snapshot_save` / `sonos_snapshot_restore` | State snapshots |
| `sonos_sleep_timer` | Set or clear sleep timer |
| `sonos_list_alarms` | List household alarms |
| `sonos_discover` | Force network rediscovery |

### MCP resources

| Resource URI | Content |
| --- | --- |
| `sonos://speakers` | All speaker metadata |
| `sonos://groups` | Current group topology |
| `sonos://state` | Live playback state |
| `sonos://capabilities` | Enabled features and transports |
| `sonos://config/policies` | Active policy limits |
| `sonos://radio/aliases` | Saved radio aliases |
| `sonos://apple-music/aliases` | Saved Apple Music aliases |

## Configuration

Config lives at `~/.config/sonos-local/config.toml` (created automatically on first run). Override the directory with `SONSO_LOCAL_CONFIG_DIR`.

```toml
[network]
hosts = []                        # static IPs — leave empty for auto-discovery
discovery_timeout_seconds = 5
request_timeout_seconds = 9.5

[policies.volume]
max_room_volume = 70
max_group_volume = 60
max_all_volume = 40

[policies.playback]
allow_arbitrary_urls = false      # block arbitrary stream URLs
block_private_network_urls = true

[policies.radio]
default_countrycode = "DE"
min_bitrate = 64
preferred_codecs = ["MP3", "AAC", "AAC+"]

# Optional room aliases
[rooms.buero]
sonos_names = ["Büro"]
aliases = ["büro", "buero", "office"]

# Optional radio aliases
[radio.aliases.einslive]
stationuuid = "9606f727-0601-11e8-ae97-52543be04c81"
preferred_name = "1LIVE"
aliases = ["einslive", "1live"]
```

### Apple Music

Apple Music playback works in two modes:

| Mode | How to set up |
| --- | --- |
| **Share links** (default) | No credentials needed — paste `music.apple.com` share links |
| **Catalog search** | Requires a Developer Token and User Token — set `apple_music.developer.enabled = true` and configure keys |

```bash
# Check auth status
sonos apple auth

# Play via share link
sonos apple play Büro --url "https://music.apple.com/de/album/..."

# Search and play
sonos apple search "Olivia Rodrigo GUTS"
sonos apple play Büro "GUTS" --type album
```

> [!NOTE]
> For catalog search and library access, add your Apple Developer team credentials under `[apple_music.developer]` in `config.toml`. The user token is read from the env var `SONSO_APPLE_MUSIC_USER_TOKEN` or from the system keychain.

## Using as a Python library

`SonsoLocalService` is the single facade used by the CLI and MCP server. You can use it directly in your own async code:

```python
import asyncio
from sonos.core.app import SonsoLocalService
from sonos.core.models import Scope, TransportCommand

async def main() -> None:
    svc = SonsoLocalService()        # reads ~/.config/sonos-local/config.toml
    await svc.startup()

    try:
        # discover speakers
        topology = await svc.discover()
        print(f"Found {len(topology.speakers)} speaker(s)")

        # list current state
        states = await svc.get_state()
        for s in states:
            print(f"{s.name}: {s.playback_state}, vol={s.volume}")

        # volume
        await svc.set_volume("Büro", 20, Scope.ROOM)
        await svc.adjust_volume("Büro", -5, Scope.GROUP)

        # transport
        await svc.transport("Büro", TransportCommand.PAUSE, Scope.GROUP)
        await svc.transport("Büro", TransportCommand.PLAY, Scope.GROUP)

        # play a Sonos favorite (fuzzy name match)
        result = await svc.play_favorite("Büro", "1LIVE", Scope.GROUP, isolate=False)
        print(result.ok, result.action)

        # play a radio station by alias or search term
        await svc.play_radio("Büro", "1LIVE", Scope.GROUP, isolate=False)

        # group management
        await svc.group(coordinator="Büro", members=["Schlafzimmer"])
        await svc.ungroup(["Schlafzimmer"])

        # snapshot: save and restore
        snap = await svc.save_snapshot(["Büro"], name="before-party")
        await svc.restore_snapshot(snap.snapshot_id)

        # alarms
        alarms = await svc.list_alarms()
        for a in alarms:
            print(f"alarm {a.alarm_id}: {a.time} enabled={a.enabled}")

    finally:
        await svc.shutdown()

asyncio.run(main())
```

Pass a custom config directory or a pre-built `SonosLocalConfig` object to the constructor:

```python
from pathlib import Path
from sonos.core.app import SonsoLocalService

svc = SonsoLocalService(config_dir=Path("/etc/myapp/sonos"))
```

All methods raise `sonos.core.errors.SonosError` subclasses on failure — never raw SoCo or network exceptions:

| Exception | Code | Meaning |
| --- | --- | --- |
| `TargetNotFoundError` | `target_not_found` | Room or favorite not found |
| `NetworkError` | `network_error` | Speaker unreachable |
| `PlaybackError` | `playback_error` | UPnP playback failure |
| `InvalidInputError` | `invalid_input` | Bad argument (time format, etc.) |
| `PolicyError` | `policy_error` | Volume cap or URL policy blocked |
| `AmbiguousTargetError` | `ambiguous_target` | Name matches multiple speakers |

## Development

```bash
# Set up environment
task init

# Run tests
task test

# Lint and format
task lint
task format

# Type check
task typecheck
```

Tests require no real hardware. Live integration tests (marked `sonos_live`) need speakers on the network:

```bash
task test:live
```

## Architecture

```text
sonos/
├── cli/          # Typer CLI — one file per command group
├── core/
│   ├── app.py    # SonsoLocalService — the single application facade
│   ├── sonos/    # SoCo backend (async wrapper + discovery + favorites)
│   ├── radio/    # Radio Browser client and resolver
│   ├── apple_music/  # Apple Music client (catalog + share links)
│   ├── config.py # Pydantic config model, TOML load/save
│   └── policy.py # Volume/playback/URL policy enforcement
├── mcp_server/   # FastMCP server — tools and resources
└── storage/      # aiosqlite — snapshots, radio aliases, Apple Music aliases
```

The `SonsoLocalService` is the single entry point used by both the CLI and the MCP server. All SoCo calls run in a thread pool via `asyncio.to_thread`; all domain exceptions are `SonosError` subclasses so callers never see raw library exceptions.
