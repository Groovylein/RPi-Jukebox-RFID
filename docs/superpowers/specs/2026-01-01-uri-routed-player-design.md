# URI-routed player backends (short design)

## Intent
Let the player play a track on whichever service owns it (MPD today, Spotify/Deezer later),
decided by the track URI alone. Cards and the webapp store one string, no `provider` field.

## Goals
- `PlayerCoordinator` routes by URI scheme (`mpd:...`, later `spotify:...`, `deezer:...`).
- A URI without a scheme falls back to MPD, so existing cards and bare library paths keep working.
- A `BackendPlayer` ABC defines what a backend implements, so new services have a contract.

## Non-goals
- No Spotify/Deezer backend now.
- No `can_handle()` chain or `https://` stream detection.
- No card migration.
- Library listing (`list_albums`, `list_library_items`, ...) stays per backend, as today.

## Anti-goals
- Existing MPD playback or stored cards must not break.
- Two backends must never be able to claim the same URI.

## Constraints
- Builds on develop's `PlayerCoordinator` (`components/player/coordinator.py`).
- Webapp and RPC currently send `song_url` + `provider` (`commands/index.js`, `song-list-item.jsx`).

## Approaches
- **A. Scheme table in coordinator (chosen):** `register_backend(name, backend, schemes=[...])`, parse `scheme:rest`, strip the prefix, call the backend. Small, and no ambiguity.
- B. `can_handle(uri)` per backend: more flexible, but order-dependent and ambiguous. Rejected, YAGNI.
- C. Separate `TrackUri` + router classes: more types than the logic needs. Rejected.

## Design
- `register_backend` gains `schemes`. Each scheme maps to exactly one backend; a duplicate raises `ValueError`.
- `_split_uri(uri) -> (scheme, rest)`. No scheme, or an unregistered scheme, means the default backend (MPD) with the whole string as `rest`.
- `play_single`, `get_single_coverart`, `get_song_by_url` and the other URI-taking methods resolve the backend from the URI. `provider` is removed from their signatures.
- Webapp: send only `uri` (`argKeys: ['uri']`), drop `provider`.
- `BackendPlayer` ABC restored in `components/player/backends/__init__.py`. `PlayerMPD` subclasses it.
- Tests: scheme routing, bare path fallback, duplicate scheme error, MPD receives the stripped URI.

## Left to the builder
- Exact ABC method list: derive from what the coordinator calls.
- Whether to keep `provider` accepted but ignored for one release. My call: remove it, since the webapp is in this repo.
- Whether to strip `mpd:` before handing to MPD. My call: strip, so the backend sees its native form.
