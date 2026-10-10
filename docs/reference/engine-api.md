# Engine API

The browser and desktop UI talk to the Python karaoke engine through a single
bridge: the inline `<script type="py">` block in
[`src/web/index.html`](https://github.com/wilsonify/pykaraoke-ng/blob/main/src/web/index.html)
builds one
[`pykaraoke.webapp.KaraokeApp`](https://github.com/wilsonify/pykaraoke-ng/blob/main/src/pykaraoke/webapp.py)
instance and publishes a dispatcher as `window.pykaraoke_api`.

[← Home](../index.md) · [Python engine](../architecture/engine.md) · [Web application](../architecture/web-app.md)

---

## The dispatcher

Exactly one function crosses the boundary:

```js
window.pykaraoke_api(name, ...args)   // defined by the inline <script type="py">
```

The bridge calls `app.<name>(*args)` with converted arguments and returns the
result. The app script wraps this in `callApi(name, ...args)`.

```js
const result = window.pykaraoke_api('search', 'queen');
```

No other global, module import, or private method is exposed.

### Value conversion

| Direction | Rule |
|-----------|------|
| JS → Python | Objects and arrays are deep-converted with `to_py()`, so the engine sees plain `dict`/`list` |
| JS → Python | `Uint8Array` arguments arrive as `bytes`/`memoryview`, which the engine accepts directly |
| Python → JS | Results are plain Python data structures; the caller converts proxies with `toJs()` |
| Python `None` → JS | Surfaces as `undefined` (the app normalises it to `null`) |

!!! note "JSON-friendly by design"
    Every method returns plain dicts, lists, bytes, or `None` — never an engine
    object that would leak across the boundary. See the
    [web-engine-api spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/web-engine-api/spec.md)
    for the authoritative contract.

### Error handling

Two conventions coexist, deliberately:

- **Structured error payloads.** Methods that parse untrusted bytes or text
  (`parse_midi`, `parse_lrc`, `scan_zip`) return a mapping containing an
  `error` key (or a zero-count result) instead of raising, so a bad file
  surfaces as a status message rather than a dead window.
- **Fail fast.** A genuine programming error still raises — for example,
  `cdg_open` raises `ValueError` when the supplied data cannot be converted to
  bytes.

---

## Persistence

### `to_json() -> str`

Serialize the library and settings to a JSON string, suitable for
`localStorage`.

```py
payload = app.to_json()
```

### `from_json(payload) -> None`

Restore a library previously produced by `to_json`. Input that is not valid
JSON or not a mapping is **ignored** — the current library is left untouched
and no exception is raised. Restoring also clears any open CDG decoders and
cached zip member lists.

| Argument | | |
|----------|---|---|
| `payload` | `str` | JSON text (garbage tolerated) |

```js
callApi('from_json', localStorage.getItem('pykaraoke'));
```

---

## Library

### `scan_files(files, replace=False) -> dict`

Add recognised karaoke songs from folder-picker entries. Each entry is a
mapping `{name, path, size}`; a missing `path` defaults to `name`. Entries
that are not mappings, or whose numeric fields are unusable, are skipped
rather than failing the scan. With `replace=True` previously scanned loose
files and zip expansions are cleared first (settings untouched) — use it to
relocate a library without carrying ghosts of the old root; the default
stays additive.

```json
{ "added": 12, "total": 240 }
```

`total` is the resulting library size.

### `scan_zip(name, data) -> dict`

Scan an archive's bytes and add its karaoke members. The archive is remembered
so members can be read later, and its cached member list is invalidated. Data
that is not a valid archive does **not** raise — the call reports
`{"added": 0, "total": <library size>}`.

### `read_zip_member(zip_name, member) -> bytes | None`

Return the bytes of `member` inside a previously scanned archive. Returns
`None` when the archive was never scanned, the member is missing, or the
archive bytes are unreadable.

### `zip_members(zip_name) -> list`

Member names of a scanned archive, or `[]` when the archive is not loaded.
The list is cached and refreshed when the same archive name is scanned again.
Used to find companion files (e.g. a `.elrc`) without reading them back.

### `search(query, limit=500) -> dict`

Case-insensitive search across the library, capped at `limit`.

```json
{ "results": [ { "id": "…", "artist": "Queen", "title": "…", "…": "…" } ] }
```

### `library_songs() -> dict`

Every song in the library.

```json
{ "songs": [ { "…": "…" } ] }
```

### `song(song_id) -> dict | None`

The record for one song, or `None` when the identifier is unknown.

### `get_settings() -> dict`

The current settings, including `volume` (default `0.75`).

### `set_settings(updates) -> dict`

Apply recognised keys and return the updated settings. Unrecognised keys are
silently ignored — no error is raised.

| Recognised key | Type | Meaning |
|----------------|------|---------|
| `cdg_zoom` | `str` | CD+G canvas zoom (`quick` / `int` / `full` / `soft`) |
| `sort` | `str` | Library sort (`filename` / `title` / `artist`) |
| `volume` | `float` | Playback volume in `[0, 1]` |
| `file_name_type` | `int` | Legacy filename convention selector (`0`–`4`; `4` = spaced disc-track) |
| `derive_song_info` | `bool` | Derive artist/title from the filename |
| `exclude_non_matching` | `bool` | Hide songs without an artist |
| `look_inside_zips` | `bool` | Scan `.zip` archives |
| `folders` | `list[str]` | Configured library folders |
| `include_patterns` | `list[str]` | Case-insensitive `fnmatch` patterns; when non-empty, only matching basenames are scanned |
| `exclude_patterns` | `list[str]` | Case-insensitive `fnmatch` patterns; matching basenames are skipped (exclude wins) |

```js
const settings = callApi('set_settings', { volume: 0.4, sort: 'artist' });
```

### `scan_report() -> dict`

The accumulated scan report: `{ entries: [{category, path}, ...], counts: {unsupported, filtered, corrupt_archive, unsupported_compression, unreadable, parse_failure} }`. Entries are deduplicated per `(category, path)` and survive until cleared; reporting never influences which songs are added.

### `clear_scan_report() -> dict`

Forgets every recorded scan outcome and returns the now-empty report.

```js
const report = callApi('scan_report');
if (report.counts.corrupt_archive) console.warn(report.entries);
callApi('clear_scan_report');
```

### `prune_songs(known) -> dict`

Remove songs whose paths are absent from the caller-supplied `known` list of
paths (loose and zip songs alike); returns `{pruned, total}`. An empty
`known` list is a no-op so an accidental empty call cannot wipe the library.

```js
const { pruned, total } = callApi('prune_songs', onDiskPaths);
```

### `export_json() -> str`

Export the whole library (songs, pairing, folders, settings) as a
self-describing JSON envelope string:
`{"format": "pykaraoke-ng-library", "schema": 1, "library": {…}}`.

### `import_json(payload) -> dict`

Replace the in-memory library from a JSON string — either the export
envelope or a bare serialised library dict. Returns `{ok: true}` on success;
on malformed JSON, an unrecognised schema, or an invalid library it returns
`{ok: false, error}` and leaves the previous library untouched (never a
partial state).

```js
const payload = callApi('export_json');
const result = callApi('import_json', payload); // {ok: true}
```

---

## Playback data

### `parse_midi(data) -> dict`

Parse the bytes of a `.kar`/`.mid` file into the lyrics-and-notes payload the
synthesizer consumes. Bytes that are not a valid MIDI file, or that cannot be
converted to bytes, return `{"error": "…"}` instead of raising.

```json
{ "error": "could not parse MIDI file" }
```

### `parse_lrc(text, elrc_text=None) -> dict`

Parse LRC lyric text into timed lyric events. `text` must be a `str`; empty
text or text with no timestamps returns `{"error": "…"}`.

`elrc_text` is the optional companion `.elrc` file. When it supplies usable
word timing, the payload carries the word-level events and adds
`"elrc": true`; otherwise the plain line timing is preserved and `elrc` is
absent. A **missing or unusable companion is never an error.**

The payload also carries duet information when the lyrics declare it:

| Key | Present when | Value |
|-----|--------------|-------|
| `meta` | always | Parsed metadata (e.g. `ti`) |
| `lyrics` | always | Timed events: `{ms, text, type, line}` |
| `parts` | duet tags present | `{"a": "Alice", "b": "Bob"}` |
| `elrc` | word timing applied | `true` |
| per-event `part` | that line is tagged | `"a"`, `"b"`, or shared `"ab"` |

Solo songs return the same payload as before duet support — no `parts`, no
per-line `part`. Word-level merging preserves each line's `part`.

```js
const parsed = callApi('parse_lrc', decodeText(bytes), elrcText);
```

---

## CDG decoder lifecycle

CD+G decoding is incremental: a decoder is opened for a song, advanced to a
position on each frame, and closed when the song ends.

### `cdg_open(song_id, data) -> str`

Create a decoder for the CD+G bytes and return its key (the string form of
`song_id`). **Raises `ValueError`** when `data` cannot be converted to bytes.

### `cdg_update(decoder_key, ms) -> dict | None`

Advance the decoder to `ms` and return the changed render state, or `None` for
an unknown key.

```json
{
  "border": [0, 0, 0],
  "tiles": [ { "x": 0, "y": 0, "data": "…" } ]
}
```

`border` is the border colour (`None` when unchanged) and `tiles` lists the
dirty tiles for the canvas.

### `cdg_seek(decoder_key, ms) -> None`

Reposition a known decoder. A no-op for an unknown key.

### `cdg_close(decoder_key) -> None`

Discard the decoder. Later `cdg_update` calls for the same key return `None`.

### `cdg_packet_count(data) -> int`

The number of CD+G packets in a buffer, derived from its length in fixed
24-byte packets. Used to compute duration.

```py
app.cdg_packet_count(bytes(24 * 5))   # 5
```

---

## Related

- [Python engine](../architecture/engine.md) — the modules behind this API
- [Web application](../architecture/web-app.md) — how the bridge is wired
- [Configuration](configuration.md) — the user-facing settings
- [web-engine-api specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/web-engine-api/spec.md)
