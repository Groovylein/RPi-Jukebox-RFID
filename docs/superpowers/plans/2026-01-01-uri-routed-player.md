# URI-routed player backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PlayerCoordinator` picks the playback backend from the track URI scheme; `provider` is removed from URI-taking calls.

**Architecture:** `register_backend` gets a `schemes` list. A private `_split_uri` maps `scheme:rest` to `(backend_name, rest)`. Unknown or missing scheme goes to the default backend (MPD) with the whole string. A restored `BackendPlayer` ABC gives backends a contract.

**Tech Stack:** Python 3 / pytest (`test/player/test_player_coordinator.py`), React + vitest (`src/webapp`).

**Spec:** `docs/superpowers/specs/2026-01-01-uri-routed-player-design.md`

## Global Constraints

- Scheme to backend is 1:1; a duplicate scheme raises `ValueError`.
- No scheme or unregistered scheme means default backend (MPD), whole string passed through.
- MPD receives the URI with the `mpd:` prefix stripped.
- Library listing (`list_albums`, `list_library_items`, `list_library_sources`) keeps its `provider` argument.
- Existing MPD playback and stored bare-path cards must keep working.
- Python style: flake8 clean (`.flake8`).

## Review Focus

- Bare path containing a colon (`Stories/Chapter 1: Arrival.mp3`): must go to MPD whole, not be split as scheme `Stories/Chapter 1`. Scheme = text before the first `:` only if it matches `^[a-z][a-z0-9+.-]*$` (lowercased).
- Windows-style or `https://x` URI with unregistered scheme: falls back to MPD, unmodified.
- Empty or `None` URI: raises `ValueError`, no backend call.
- Registered scheme whose backend is missing a method: existing `NotImplementedError` surfaces.
- Webapp still passes old `song_url`/`provider` keys: stale saved cards. See Task 3.

---

### Task 1: Scheme routing in the coordinator

**Files:**
- Modify: `src/jukebox/components/player/coordinator.py` (`register_backend`, `play_single`, `get_single_coverart`, `get_song_by_url`, `play_album`, `list_songs_by_artist_and_album`)
- Test: `test/player/test_player_coordinator.py`

**Interfaces:**
- Produces: `register_backend(self, name: str, backend: Any, make_active: bool = False, schemes: Sequence[str] = ()) -> None`
- Produces: `PlayerCoordinator._split_uri(self, uri: str) -> Tuple[str, str]` returning `(backend_name, rest)`
- Produces: `play_single(self, uri: str)`, `get_single_coverart(self, uri: str)`, `get_song_by_url(self, uri: str)`, `play_album(self, albumartist, album, content_uri=None)`, `list_songs_by_artist_and_album(self, albumartist, album, content_uri=None)`. None takes `provider` any more.

- [ ] **Step 1: Write failing tests** (replace the existing `provider=`-based tests at lines ~108-170 that call `play_single(..., provider=...)`/`play_album(..., provider=...)`):
  - `test_uri_scheme_selects_registered_backend`: register `mpd` (schemes `['mpd']`) and `streaming` (schemes `['spotify']`); `play_single('spotify:track:123')` calls `streaming.play_single('track:123')`, not mpd.
  - `test_bare_path_falls_back_to_default_backend`: `play_single('Album/song.mp3')` calls mpd with `'Album/song.mp3'`.
  - `test_path_with_colon_is_not_a_scheme`: `play_single('Stories/Chapter 1: Arrival.mp3')` calls mpd with that exact string.
  - `test_unregistered_scheme_falls_back_to_default`: `play_single('https://x/y')` calls mpd with `'https://x/y'`.
  - `test_mpd_prefix_is_stripped`: `play_single('mpd:Album/song.mp3')` calls mpd with `'Album/song.mp3'`.
  - `test_duplicate_scheme_rejected`: second backend registering `'mpd'` scheme raises `ValueError` matching `"already"`.
  - `test_empty_uri_rejected`: `play_single('')` raises `ValueError`; backend not called.
  - `test_content_uri_routes_album_calls`: `play_album('a', 'b', content_uri='spotify:album:1')` selects the streaming backend; `list_songs_by_artist_and_album` the same way.
  - `test_coverart_and_song_lookup_route_by_uri`: `get_single_coverart('spotify:track:1')` and `get_song_by_url('spotify:track:1')` hit the streaming backend with `'track:1'`.
- [ ] **Step 2: Run** `pytest test/player/test_player_coordinator.py -v`. Expected: new tests FAIL (unknown kwarg `schemes` / `provider` mismatch).
- [ ] **Step 3: Implement.** `register_backend` stores `self._schemes: Dict[str, str]` (scheme to name), validating duplicates before storing the backend. `_split_uri` as in Review Focus; raises `ValueError` on empty. The five URI methods call `_split_uri`, then select the backend via `_select_backend`/`_call_named` as they do now, passing `rest`. For album calls, route on `content_uri` when given, else the default backend, passing `content_uri` stripped of its scheme.
- [ ] **Step 4: Run** the same command. Expected: all PASS, including untouched `list_*` provider tests.
- [ ] **Step 5: Commit** `git add test/player src/jukebox/components/player/coordinator.py && git commit -m "feat(player): route backend by URI scheme"`

### Task 2: `BackendPlayer` ABC and MPD registration

**Files:**
- Modify: `src/jukebox/components/player/backends/__init__.py`, `src/jukebox/components/player/backends/mpd.py:140` (class line), `src/jukebox/components/player/mpd_plugin.py`
- Test: `test/player/test_player_coordinator.py`

**Interfaces:**
- Consumes: `register_backend(..., schemes=...)` from Task 1.
- Produces: `class BackendPlayer(ABC)` in `components/player/backends/__init__.py`, with abstract methods for every backend method the coordinator calls by name via `_call_*`/`_call_backend` (derive the list by grepping `coordinator.py`; MPD-only helpers like `is_second_swipe` stay abstract too, since the coordinator calls them). `PlayerMPD(BackendPlayer)`.

- [ ] **Step 1: Write failing tests:** `test_player_mpd_is_a_backend_player` (`issubclass(PlayerMPD, BackendPlayer)`); `test_backend_player_cannot_be_instantiated` (`TypeError`); `test_initialize_registers_mpd_scheme`: with `PlayerMPD` patched, `initialize_mpd_player('x')` leaves `coordinator._split_uri('mpd:a.mp3') == ('mpd', 'a.mp3')`.
- [ ] **Step 2: Run** `pytest test/player -v`. Expected: the three new tests FAIL.
- [ ] **Step 3: Implement** the ABC, make `PlayerMPD` inherit it (every abstract method already exists on it; add none), and change `mpd_plugin.py` to `register_backend('mpd', PlayerMPD(), schemes=['mpd'])`.
- [ ] **Step 4: Run** `pytest test/player -v && flake8 src/jukebox/components/player`. Expected: PASS, no output from flake8.
- [ ] **Step 5: Commit** `git commit -am "feat(player): add BackendPlayer ABC and register mpd scheme"`

### Task 3: Webapp sends only `uri`

**Files:**
- Modify: `src/webapp/src/commands/index.js` (lines 41, 76: `get_song_by_url`, `play_single`), `song-list-item.jsx:30,34`, `Cards/controls/actions/play-music/selected-single.jsx`, `Library/lists/folders/folder-list-item.jsx:33,43`, `Player/index.jsx:31`, and `getSingleCoverArt` caller if it passes `song_url`/`provider`.
- Test: `src/webapp/src/components/Cards/utils.test.js`

**Interfaces:**
- Consumes: Task 1 RPC signatures (`uri` only).
- Produces: `commands.play_single.argKeys` and `commands.getSongByUrl.argKeys` equal `['uri']`; every call site passes `{ uri: ... }`.

- [ ] **Step 1: Write failing test** in `utils.test.js`: both commands' `argKeys` equal `['uri']`.
- [ ] **Step 2: Run** `cd src/webapp && npx vitest run src/components/Cards/utils.test.js`. Expected: FAIL.
- [ ] **Step 3: Implement:** change `argKeys` and replace `{ song_url, provider }` with `{ uri }` at each call site. Library items carrying a non-MPD provider must already hold a full `scheme:...` URI in `file`; do not add provider back. Album commands keep `provider` (non-goal).
- [ ] **Step 4: Run** `npx vitest run && npm run lint` in `src/webapp`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(webapp): send uri only for single-track commands"`
