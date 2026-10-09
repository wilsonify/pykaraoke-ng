# Python engine

[← Home](../index.md) · [Architecture overview](overview.md) · [Web application](web-app.md)

---

`src/pykaraoke/` is a small, pure-**[standard-library](https://docs.python.org/3/library/index.html)**
Python package. It is the whole product logic: CD+G decoding, MIDI/KAR
parsing, LRC lyrics, the song library, and the JSON-facing API the web page
calls. It contains no pygame, numpy, mutagen, or any third-party import.

## Why standard library only

The same modules run in two places:

* under **CPython**, for the `pytest` suite on the developer's machine and in
  CI;
* under **Pyodide** (CPython compiled to WebAssembly), inside the browser page
  that ships as the desktop app's front end.

A single implementation means one behaviour and one test suite. It also means
the engine can be packaged as **one wheel** that PyScript installs at page
load — there is no second Python process, no service, and nothing to install
on the target machine.

That constraint is binding and lives in the
[project-governance spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/project-governance/spec.md);
proposals to add a runtime dependency for the engine have to argue the case
explicitly.

```text
      src/pykaraoke/                       runtime
┌───────────────────────────┐        ┌────────────────────┐
│  cdg · midi · lrc         │        │  CPython + pytest  │  dev / CI
│  database · filename_     │───────▶│                    │
│  parser · webapp          │        ├────────────────────┤
│  (pure stdlib)            │        │  Pyodide in-page   │  the app
└───────────────────────────┘        └────────────────────┘
```

## Modules

| Module | Responsibility | Key data flow |
|--------|----------------|---------------|
| `webapp.py` | The JSON-friendly API (`KaraokeApp`) the page dispatches to | dict/list/bytes in and out; no UI, no I/O |
| `cdg.py` | CD+G packet decoder | raw `.cdg` bytes → 300×216 colour-index framebuffer, delivered as dirty 48×48 tiles |
| `midi.py` | MIDI/KAR parser | `.kar`/`.mid` bytes → timed lyric syllables, timed note events, instrument programs |
| `lrc.py` | LRC and enhanced-LRC parser | `.lrc`/`.lcr` text (+ optional `.elrc`) → timed lyric events with optional duet parts |
| `database.py` | Song library | file entries → `Song` records, search, sort, companion audio, zip members, `Settings` |
| `filename_parser.py` | "Artist - Title" extraction | filename string → `ParsedSong(artist, title, disc, track)` |

Each module is an isolated unit with no cross-module imports other than the
ones shown by `webapp.py`:

```python
# src/pykaraoke/webapp.py
from pykaraoke import cdg as cdg_module
from pykaraoke import database, lrc, midi
```

### `cdg.py` — CD+G decoding

The decoder keeps a full 300×216 framebuffer of colour **indices** and tracks
which of the 24 visible tiles changed. The web page replays only the dirty
tiles onto a `<canvas>`, so a lyric change does not repaint the whole frame.
CD+G packets stream at 300 per second; `packet_index_at(ms)` converts a
playback position to a packet index so the UI can advance or seek by time.
Colour tables, tile blocks, XOR, scroll, border and memory presets are all
implemented, and `get_border_colour()` exposes the current border for the
page background.

The full behaviour is specified in the
[playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md).

### `midi.py` — MIDI / KAR parsing

A Standard MIDI File parser that also understands karaoke lyric meta-events.
It produces a `MidiFile` containing:

* `lyrics` — timed syllables for the karaoke-style renderer (the same shape
  `lrc.py` emits);
* `notes` — timed note on/off events for the in-page Web Audio synthesizer;
* `programs` — per-channel instrument changes;
* tempo and time-signature metadata, used to convert musical clicks to
  milliseconds.

KAR lyrics are grouped into lines and the run-together spacing is repaired for
display. MIDI/KAR has no way to express duet parts, so it carries none.

### `lrc.py` — LRC and enhanced LRC

Parses `[mm:ss.xx]text` lines plus metadata (`[ar:]`, `[ti:]`, `[al:]`,
`[by:]`, `[length:]`, `[offset:]`). The `offset` is applied so a positive
value makes lyrics appear sooner, matching the LRC convention.

It also supports:

* **enhanced LRC** word tags (`<mm:ss.xx>` inside a line), where the text
  before the first tag takes the line time and each tag times the word that
  follows;
* a companion **`.elrc`** file (`parse_elrc`), whose word entries are aligned
  to the LRC lines by matching on letters alone;
* **duet part tags** immediately after a timestamp — `[a]`, `[b]`, and `[ab]`
  for a shared line (`[ba]` is normalised to `ab`), with optional singer names
  from `[pa:]`/`[pb:]`.

The output uses the same lyric-event shape as `midi.py`, so the page reuses a
single lyric renderer for both formats.

### `database.py` — the song library

`SongLibrary` is an in-memory index fed from the UI's file picker. Everything
is JSON-serializable so the page can persist it in `localStorage`.

* **Scanning** indexes the supported extensions — `.cdg`, `.kar`/`.mid`,
  `.mpg`/`.mpeg`/`.avi`, and `.lrc`/`.lcr` — keyed by path, so re-scanning is
  idempotent.
* **Companion audio** pairs a `.cdg` or `.lrc` with a same-stem
  `.mp3`/`.ogg`/`.wav` next to it, matching exact then normalised stems.
* **Zip support** can look inside `.zip` archives (when enabled) and address a
  song by `zip_name` + member, without extracting to disk.
* **Search** matches all whitespace-separated terms, case-insensitively,
  against title, artist, and filename.
* **Sorting** by `filename`, `title`, or `artist`, with leading articles
  stripped for artist/title ordering.
* **`Settings`** persists `folders`, `cdg_zoom`, `derive_song_info`,
  `file_name_type`, `exclude_non_matching`, `look_inside_zips`, `sort`, and
  `volume`.

The exact contract is in the
[song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).

### `filename_parser.py` — artist and title extraction

`FilenameParser.parse(path)` strips the directory (so dashes in folder names
never interfere) and the final extension, then applies one of two strategies:

1. **Modern** — if the stem contains a spaced dash (`" - "`), everything
   before the *first* one is the artist and everything after it is the title,
   so subtitles and parentheticals survive.
2. **Legacy** — otherwise the stem is split on `-` according to the configured
   `FileNameType` (`DISC_TRACK_ARTIST_TITLE`, `DISCTRACK_ARTIST_TITLE`,
   `DISC_ARTIST_TITLE`, or `ARTIST_TITLE`). `ARTIST_TITLE` groups consecutive
   short all-caps segments so names such as `AC-DC` stay together.

`parse_zip_path()` falls back to the parent directory as the artist when the
filename alone has no separator. Unrecognised input degrades to a title-only
result; the parser never crashes and never does I/O. Unicode dash variants and
full-width characters are **not** handled today — that work is an active
OpenSpec change (`openspec/changes/filename-parser-edge-cases/`).

See the
[filename-parsing spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/filename-parsing/spec.md).

## Packaging

The engine is built as a single wheel by `src/scripts/build-web.py` and written
to `src/web/_wheel/`. PyScript installs that wheel at page load, and the page
reaches the engine through the `window.pykaraoke_api` dispatcher documented in
the [Engine API](../reference/engine-api.md).

```bash
python src/scripts/build-web.py   # wheel + vendored Pyodide/PyScript
```

The wheel output directory is git-ignored: it is regenerated from source on
every build.

## Testing

The engine is covered by `pytest` under `tests/pykaraoke/`, one module per
engine module:

```bash
uv run pytest tests/pykaraoke/ -v
uv run pytest tests/pykaraoke/ --cov=src/pykaraoke --cov-report=html
```

Because the modules are pure and side-effect free, the tests run without a
browser, a sound card, or any fixture of the real app beyond the sample files
in `tests/`.

## Related

* [Architecture overview](overview.md) — the three-layer picture
* [Web application](web-app.md) — the page that calls this engine
* [Engine API](../reference/engine-api.md) — the JavaScript ↔ Python contract
* [Song library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md)
* [Playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md)
