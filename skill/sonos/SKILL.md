---
name: sonos
description: Voice-style remote control for Sonos speakers. Translate natural-language requests ("spiel 1LIVE im Büro", "lauter", "mach das Wohnzimmer leiser") into sonos_* MCP tool calls.
trigger: /sonos
---

# sonos — Remote control

User talks like a remote. You translate to a Sonos action. No technical terms in replies — keep it short and human ("1LIVE läuft im Büro", "Lautstärke rauf", "Wohnzimmer pausiert").

Prefer MCP tools (`sonos_*`) when available. Fall back to the `sonos` CLI otherwise. Never show JSON, tool names, or error stack traces to the user.

---

## Hard rules

1. **Volume up/down without a target → get state first.** Call `sonos_get_state` to find what's playing, then apply the delta to that room. Never guess.
2. **Fuzzy names.** Room names tolerate typos — the tools do fuzzy matching. Pass the user's room name as-is unless it's clearly wrong.
3. **"Meine Lieblingslieder" / favorites** → `sonos_play_favorite` with the user's phrase. If it fails, try `sonos_search_apple_music` or `sonos_play_apple_music` with the same term.
4. **Radio by name** → `sonos_play_radio` with the station name as `station`. The backend resolves aliases and searches Radio Browser automatically.
5. **Group scope default = `"group"`**, room scope = `"room"`. Use `"group"` unless the user explicitly says "nur im Büro" / "only in the bedroom".
6. Reply in **one short sentence** in the user's language. Examples: *"1LIVE läuft im Büro."* — *"Lautstärke runter."* — *"Wohnzimmer pausiert."*

---

## Intent map

| Intent | Examples (de/en) | Workflow |
| ------ | ---------------- | -------- |
| Play radio | "spiel 1LIVE im Büro", "play BBC Radio 4 in the kitchen" | `sonos_play_radio(target, station)` |
| Play favorite | "spiel meine Lieblingslieder im Wohnzimmer", "play Chillout" | `sonos_play_favorite(target, favorite)` |
| Play Apple Music | "spiel das Album GUTS im Büro", "play Olivia Rodrigo" | `sonos_play_apple_music(target, item)` or `sonos_search_apple_music` then `sonos_play_apple_music` |
| Volume up | "lauter", "mach das Büro lauter", "louder" | get state if no target → `sonos_adjust_volume(target, +delta)` |
| Volume down | "leiser", "mach das Wohnzimmer leiser", "quieter" | get state if no target → `sonos_adjust_volume(target, -delta)` |
| Set volume | "Büro auf 30", "set kitchen to 40" | `sonos_set_volume(target, volume)` |
| Mute / unmute | "stumm", "mute", "Ton aus/an" | `sonos_set_mute(target, true/false)` |
| Pause | "pause", "stop", "Büro pausieren" | `sonos_transport(target, "pause")` |
| Play / resume | "weiter", "play", "Wohnzimmer weiter" | `sonos_transport(target, "play")` |
| Next track | "nächster Song", "skip", "weiter" (context: music) | `sonos_transport(target, "next")` |
| Previous track | "vorheriger Song", "back" | `sonos_transport(target, "previous")` |
| What's playing? | "was läuft", "what's on", "status" | `sonos_get_state(target)` → report room, title, artist |
| All rooms status | "was läuft überall", "all rooms" | `sonos_get_state()` (no target) |
| Group rooms | "Büro zum Wohnzimmer", "sync Büro and Wohnzimmer" | `sonos_group(coordinator, members)` |
| Ungroup | "Büro abtrennen", "ungroup Büro" | `sonos_ungroup(["Büro"])` |
| Sleep timer | "Büro in 30 Minuten aus", "sleep timer 30 min" | `sonos_sleep_timer(target, seconds)` |
| Cancel sleep timer | "Sleep-Timer weg", "cancel sleep" | `sonos_sleep_timer(target, null)` |
| List speakers | "welche Lautsprecher gibt es", "list rooms" | `sonos_list_speakers()` |
| List favorites | — | `sonos_play_favorite` with empty/list query; or just say what you know |
| Discover | "neu suchen", "discover" | `sonos_discover()` |

---

## Volume delta defaults

| User phrase | Delta |
| ----------- | ----- |
| "lauter" / "louder" | +10 |
| "viel lauter" / "much louder" | +20 |
| "ein bisschen lauter" / "a little louder" | +5 |
| "leiser" / "quieter" | -10 |
| "viel leiser" | -20 |
| "ein bisschen leiser" | -5 |

---

## How to handle "lauter" (no room given)

1. `sonos_get_state()` — find all rooms with `playback_state == "PLAYING"`.
2. If exactly one → `sonos_adjust_volume(that_room, +10, scope="room")`.
3. If multiple → pick the one the user most recently mentioned, or ask which room.
4. Reply: *"Lautstärke rauf."*

---

## How to handle "spiel 1LIVE im Büro"

1. `sonos_play_radio(target="Büro", station="1LIVE")`.
2. If error `target_not_found` → `sonos_list_speakers()`, re-try with closest match.
3. If error `station_not_found` → `sonos_search_radio(query="1LIVE")`, pick top hit, then `sonos_play_radio(target, stationuuid=<uuid>)`.
4. Reply: *"1LIVE läuft im Büro."*

---

## How to handle "spiel meine Lieblingslieder im Wohnzimmer"

1. `sonos_play_favorite(target="Wohnzimmer", favorite="Lieblingslieder")`.
2. If error → `sonos_play_apple_music(target="Wohnzimmer", item="Lieblingslieder")`.
3. Reply: *"Lieblingslieder laufen im Wohnzimmer."*

---

## How to handle "mach das Büro lauter"

1. `sonos_adjust_volume(target="Büro", delta=10, scope="room")`.
2. Reply: *"Büro lauter."*

---

## CLI fallback equivalents

When MCP tools are unavailable, use the `sonos` CLI:

| MCP tool call | CLI equivalent |
| ------------- | -------------- |
| `sonos_get_state()` | `sonos status` |
| `sonos_get_state("Büro")` | `sonos status Büro` |
| `sonos_list_speakers()` | `sonos rooms` |
| `sonos_play_radio("Büro", "1LIVE")` | `sonos radio play Büro 1LIVE` |
| `sonos_play_favorite("Büro", "Lieblingslieder")` | `sonos favorites play Büro "Lieblingslieder"` |
| `sonos_play_apple_music("Büro", "GUTS")` | `sonos apple play Büro "GUTS"` |
| `sonos_adjust_volume("Büro", 10)` | `sonos volume up Büro --step 10` |
| `sonos_adjust_volume("Büro", -10)` | `sonos volume down Büro --step 10` |
| `sonos_set_volume("Büro", 30)` | `sonos volume set Büro 30` |
| `sonos_set_mute("Büro", true)` | `sonos mute Büro` |
| `sonos_set_mute("Büro", false)` | `sonos unmute Büro` |
| `sonos_transport("Büro", "play")` | `sonos playback play Büro` |
| `sonos_transport("Büro", "pause")` | `sonos playback pause Büro` |
| `sonos_transport("Büro", "next")` | `sonos playback next Büro` |
| `sonos_transport("Büro", "previous")` | `sonos playback previous Büro` |
| `sonos_group("Wohnzimmer", ["Büro"])` | `sonos groups join Wohnzimmer Büro` |
| `sonos_ungroup(["Büro"])` | `sonos groups ungroup Büro` |
| `sonos_sleep_timer("Büro", 1800)` | `sonos sleep Büro 1800` |
| `sonos_sleep_timer("Büro", null)` | `sonos sleep Büro` |
| `sonos_discover()` | `sonos discover` |
| `sonos_search_radio("1LIVE")` | `sonos radio search "1LIVE"` |

CLI scope flags: `--scope group` (default) or `--scope room`.

---

## Known rooms (examples — actual names come from `sonos_list_speakers`)

| User says | Likely Sonos name |
| --------- | ----------------- |
| Büro, buero, office | Büro |
| Wohnzimmer, wz, living room | Wohnzimmer |
| Schlafzimmer, bedroom | Schlafzimmer |
| Küche, kitchen | Küche |
| Bad, bathroom | Bad |

If unsure → call `sonos_list_speakers()` once and cache the names for the session.

---

## Tone

- Reply in the language the user used (de/en).
- One short sentence. No CLI output, no JSON, no tool names.
- Examples: *"1LIVE läuft im Büro."* — *"Lautstärke runter."* — *"Wohnzimmer pausiert."* — *"Läuft: Nothing Else Matters – Metallica."*
