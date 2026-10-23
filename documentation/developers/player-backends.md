# Player Backends

The player package exposes one stable RPC and RFID-card contract while routing
content to one of several playback backends. The track URI decides which
backend plays it; the first registered backend (MPD) is the default.

## Register A Backend

Create the backend during player initialization and register it with a stable,
lowercase identifier:

```python
coordinator.register_backend('streaming', backend, schemes=['spotify'])
```

`schemes` lists the URI schemes routed to this backend. A scheme belongs to
exactly one backend; registering a duplicate raises `ValueError`.

Implement the `BackendPlayer` abstract class
(`components/player/backends/__init__.py`). It requires only what every
service needs: transport controls, `playerstatus`, volume, `exit`, and the
URI calls `play_single`, `get_song_by_url` and `get_single_coverart`. Library
and queue extras (`list_albums`, `play_folder`, `queue_load`, ...) are
optional; calling one a backend lacks raises `NotImplementedError`.

Passing `make_active=True` selects the backend immediately. Playing content
selects the backend from the URI; switching stops the previous backend first.

A backend may implement `set_active(active)`. The coordinator calls it whenever
selection changes so polling backends can publish `playerstatus` only while
active. Status payloads must include the backend identifier as `provider`.

## Playback Contract

Content calls take a single URI and route by its scheme:

```python
play_single(uri)
get_single_coverart(uri)
get_song_by_url(uri)
play_album(albumartist, album, content_uri=None)
list_songs_by_artist_and_album(albumartist, album, content_uri=None)
```

A URI looks like `spotify:track:123`. The coordinator matches the text before
the first `:` (case-insensitive) against the registered schemes and passes the
rest (`track:123`) to the backend. MPD is registered as `mpd`, so `mpd:` is
stripped too (`mpd:Album/song.mp3` becomes `Album/song.mp3`).

A URI with no scheme, with an unregistered scheme (`https://...`), or a path
containing a colon (`Stories/Chapter 1: Arrival.mp3`) goes to MPD unchanged.
Existing RFID cards and local paths keep working. An empty URI raises
`ValueError`. The album calls route on `content_uri`; without it they use MPD.

Cards saved before URI routing used `song_url` and `provider` keyword
arguments. `play_single` still accepts `song_url`, and `play_single` and
`play_album` still accept `provider` and ignore it.

Library listing (`list_albums`, `list_library_items`, `list_library_sources`)
still takes an optional `provider`, as it has no single URI to route on.

Folder playback, folder browsing, local library updates, and cover-cache
flushing route to the default backend. Transport controls such as pause, next,
seek, and volume continue to target the active backend.

## Library Contract

Each catalog backend describes its Web App navigation through
`library_source()`:

```python
{
    'id': 'streaming',
    'label': 'Streaming',
    'views': [
        {
            'id': 'playlists',
            'label': 'Playlists',
            'kind': 'items',
            'content_types': ['playlist'],
        },
    ],
}
```

Use `kind: items` for catalog lists rendered with the shared item and track
views. The built-in local backend also uses `kind: folders` for file
management.

Implement `list_library_items(content_types=None)` and return entries in this
shape:

```python
{
    'provider': 'streaming',
    'content_type': 'playlist',
    'content_uri': 'service:playlist:stable-id',
    'albumartist': 'Owner or artist',
    'album': 'Display title',
    'cover_url': 'https://example.test/cover.jpg',
}
```

`content_uri` must remain stable because playback and RFID assignments retain
it. `cover_url` may be `None`; cover lookup can instead return either a remote
URL or a filename from the local cover cache.

The coordinator combines available sources and items for the overview while
isolating failures from optional catalogs. A request for one explicit provider
returns that provider's error to the caller.

## Compatibility

The legacy `list_albums`, album/song lookup, and playback commands remain
available. Local album and song results now carry provider metadata, while
older clients can ignore the additional fields. Existing library URLs are
redirected to the source-aware routes.
