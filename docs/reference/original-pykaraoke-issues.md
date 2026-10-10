# Original PyKaraoke issue coverage

PyKaraoke-NG is a rewrite, not a port: the UI, the player, and the library
model are new code, and the engine is pure-stdlib Python that runs under
CPython (tests) and Pyodide (the shipped page). That matters here because
several long-standing requests on the upstream tracker
([`kelvinlawson/pykaraoke`](https://github.com/kelvinlawson/pykaraoke/issues))
were symptoms of the old architecture — pygame/pygst backends, wxPython
dialogs, a persistent SQLite song database of absolute file paths — rather
than missing features.

This page records, for each **open** upstream issue, whether and how
PyKaraoke-NG addresses it, and what is genuinely still missing. It is a
narrative companion to the [Specifications](specifications.md), which are the
authoritative statement of behaviour; where an issue is resolved, the relevant
spec is linked.

* Snapshot: the **18 open issues** on the upstream tracker on **2026-10-09**
  (opened 2011–2023). Issue titles and quoted text are taken from the tracker.
* This page makes no claim about the upstream repository itself, only about
  PyKaraoke-NG's behaviour as implemented here.

!!! note "How to read the status column"

    - **Solved** — the request is met, or the rewrite removes the failure the
      report describes.
    - **Partly** — the underlying need is served, but a specific part of the
      request is not implemented.
    - **Not implemented** — no equivalent behaviour exists yet. These are
      candidates for an OpenSpec change, not claims of parity.
    - **Moot** — the report describes a component (wxPython dialog, external
      MIDI synth, GP2X target, pygame backend) that no longer exists.

## Summary

| # | Upstream issue | Status |
|---|----------------|--------|
| [#1](https://github.com/kelvinlawson/pykaraoke/issues/1) | Save Personal Singer Playlists | Partly |
| [#2](https://github.com/kelvinlawson/pykaraoke/issues/2) | Pitch-shifting | Not implemented |
| [#3](https://github.com/kelvinlawson/pykaraoke/issues/3) | Lyrics Preview Window | Partly |
| [#4](https://github.com/kelvinlawson/pykaraoke/issues/4) | Tempo-Shifting | Not implemented |
| [#5](https://github.com/kelvinlawson/pykaraoke/issues/5) | Custom pattern for song structure filter | Solved |
| [#6](https://github.com/kelvinlawson/pykaraoke/issues/6) | Scan DIVX and XVID extensions | Solved |
| [#7](https://github.com/kelvinlawson/pykaraoke/issues/7) | Reallocate file links in database | Solved |
| [#8](https://github.com/kelvinlawson/pykaraoke/issues/8) | Backup and restore library | Solved |
| [#9](https://github.com/kelvinlawson/pykaraoke/issues/9) | KJ Features | Not implemented |
| [#10](https://github.com/kelvinlawson/pykaraoke/issues/10) | Unresponsive after a MIDI file without lyrics | Solved |
| [#11](https://github.com/kelvinlawson/pykaraoke/issues/11) | Log files that failed during a scan | Partly |
| [#12](https://github.com/kelvinlawson/pykaraoke/issues/12) | Kamikaze mode double performer prompt | Moot |
| [#13](https://github.com/kelvinlawson/pykaraoke/issues/13) | Scan exclusion filter | Solved |
| [#14](https://github.com/kelvinlawson/pykaraoke/issues/14) | Artist-Title parsing fails under certain circumstances | Solved |
| [#16](https://github.com/kelvinlawson/pykaraoke/issues/16) | Fails to play sound with no error message (MIDI) | Solved |
| [#18](https://github.com/kelvinlawson/pykaraoke/issues/18) | Renamed `libwxgtk-python` to `python-wxgtk2.8` | Moot |
| [#21](https://github.com/kelvinlawson/pykaraoke/issues/21) | GP2X still relevant? | Solved |
| [#22](https://github.com/kelvinlawson/pykaraoke/issues/22) | Installation on Ubuntu 22 | Solved |

Tally: 10 solved, 2 partly, 4 not implemented, 2 moot (18 total).

---

## #1 Save Personal Singer Playlists

**Reported** — "Allow singers to save personal playlists of their favourite
songs."

**In PyKaraoke-NG** — the show is driven by a first-class **queue**
(`SongQueue`) that supports add, indexed removal, move, clear, and
auto-advance, and that persists across restarts. What is missing is the
*personal, named, reusable* part: there is one queue (a running order for the
current show), not a set of saved playlists per singer, and no per-singer
identity.

**Evidence**

* `SongQueue` and queue persistence — `src/web/index.html`
  (`SongQueue`, `persist()`, restore from the `pykaraoke-ng:queue` key).
* Requirement "Persistence across restarts" —
  [ux-slim-sidebar](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md).
* Storage keys — [Configuration](configuration.md).

**Still open** — saved, named playlists; per-singer attribution; queue
history.

## #2 Pitch-shifting

**Reported** — the gstreamer-branch pitch shift "needs to be merged into
master", falling back to pygame when `pygst` is unavailable, disabling the
buttons when it is, and fixing Windows.

**In PyKaraoke-NG** — the *architectural* half of the report is gone: there is
no `pygst`, no pygame, and no GStreamer, so there are no pitch-shifting
buttons to hide when a backend is missing. The *feature* is not implemented:
nothing in the UI or engine changes pitch, and the audio elements are not
routed through any pitch node.

**Evidence**

* Zero dependencies and pure-stdlib engine — `pyproject.toml`
  ("The engine is pure stdlib … No pygame, numpy, or mutagen").
* Audio is a plain `<audio>`/`<video>` element or the Web Audio
  `MidiSynth` — [Architecture overview](../architecture/overview.md).
* No pitch/`playbackRate`/`detune` usage anywhere in `src/web/index.html`.

**Still open** — the feature itself. `HTMLMediaElement.preservesPitch` /
`playbackRate`, or an `AudioContext` detune node, are the mechanisms a change
would use, but neither is wired up.

## #3 Lyrics Preview Window

**Reported** — a second window previewing lyrics, without "break[ing] all
supported platforms" or introducing a wxPython dependency for
`pykaraoke_mini` platforms.

**In PyKaraoke-NG** — the singer-facing lyric display exists, but *inside the
same window*, sharing the stage area with the CD+G canvas and the video slot.
The platform concern is gone (no wxPython, no `pykaraoke_mini`). A **separate**
preview window is not implemented — the app is a single slim panel by design,
so a floating lyrics window would also need reconciling with the
slim-sidebar layout invariant.

**Evidence**

* Stage rendering (canvas / `#lyrics` / `#video-slot`) —
  [Architecture: web application](../architecture/web-app.md) and
  [Supported formats](formats.md).
* Duet-aware lyric presentation —
  [playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md)
  ("Duet presentation in the UI").
* Slim single-column layout is a binding invariant —
  [ux-slim-sidebar](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md).

**Still open** — a detachable/second lyric window.

## #4 Tempo-Shifting

**Reported** — "work-in-progress in gstreamer branch, but is not yet working",
to be disabled when `pygst` is unavailable.

**In PyKaraoke-NG** — not implemented as a user feature. Note the distinction:
the engine *parses* MIDI tempo changes and uses them to compute timings for
synthesis, but there is no control to speed up or slow down playback, and MIDI
synthesis has no rate parameter exposed.

**Evidence**

* MIDI tempo handling in parsing — `src/pykaraoke/midi.py`;
  [playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md)
  ("Tempo changes" scenario: events after a change are timed with the new
  tempo).
* No transport-rate control — [Configuration](configuration.md) lists every
  setting; none changes playback rate.

**Still open** — a tempo/rate control, and its interaction with lyric timing.

## #5 Custom pattern for song structure filter

**Reported** — a zip archive structured as `language/artist/song.kar` "does
not parse it properly"; the reporter supplied a `pykdb.py` patch and noted
that "fix[ing] it properly would require much more programming".

**In PyKaraoke-NG** — **solved.** The reported layout works. Archives are
scanned in-page (no extraction to disk); each member is parsed, and when the
member's filename yields no artist, the **immediate parent directory** is used
as the artist. Measured against the current parser:

```text
language/artist/song.kar           -> artist='artist'  title='song'
Language/Artist/Title.kar          -> artist='Artist'  title='Title'
Some Dir/Queen - Bohemian Rhapsody.kar -> artist='Queen' title='Bohemian Rhapsody'
```

Beyond the fixed legacy schemes (`file_name_type` `0`–`3`, now selectable in
the settings panel), the library accepts fully custom, user-supplied
`fnmatch` **include** and **exclude** patterns
(`include_patterns` / `exclude_patterns`) matched case-insensitively against
every file and zip-member basename — so any structure the user can express as
a glob can be filtered in or out of the scan.

**Evidence**

* `parse_zip_path()` and the "Archive members fall back to the directory as
  artist" requirement —
  [filename-parsing spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/filename-parsing/spec.md).
* Requirement "Include and exclude filename patterns" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* `file_name_type` and the pattern settings —
  [Configuration](configuration.md).

## #6 Scan DIVX and XVID Extensions

**Reported** — "When scanning for songs … it should be possible to search also
for divx and xvid extensions and not only avi."

**In PyKaraoke-NG** — **solved.** `.divx` and `.xvid` are first-class video
extensions and map to the same `mpg` kind as `.mpg`, `.mpeg`, and `.avi`.
Extension matching is case-insensitive, and the behaviour is specified and
tested.

**Evidence**

* `_KIND_BY_EXT` in `src/pykaraoke/database.py` maps `.mpg`, `.mpeg`, `.avi`,
  `.divx`, `.xvid` → `mpg`.
* Requirement "Supported song file kinds" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* Documented extension list — [Supported formats](formats.md).
* Measured: `a.divx -> mpg`, `a.xvid -> mpg`.

## #7 Reallocate file links in database

**Reported** — the old database stored media files by absolute path, so moving
`D:\Myfiles\…` to `C:\MyKaraoke\…` invalidated every entry; the request is to
"change root of file links in database".

**In PyKaraoke-NG** — **solved.** There is still no database of absolute
media paths to reallocate — the library is **derived** from the folders you
pick (`SongLibrary.scan()`), keyed by folder-relative path — but relocation
is now an explicit operation:

* **Replace-scan** (`scan(files, replace=True)`, or the **Replace library**
  button) clears previously scanned loose files and zip expansions before
  applying the new batch, leaving settings untouched. A move becomes: pick
  the new folder, click **Replace library** — no ghosts of the old root.
* **Prune** (`prune_songs(known_paths)`, exercised internally by replace)
  drops songs whose paths are absent from a caller-supplied on-disk path
  set; an empty set is a guarded no-op.

**Evidence**

* Requirements "Replace-scan clears prior contents" and "Prune stale songs
  by known path set" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* `SongLibrary.scan(replace=True)` / `prune_songs()` —
  `src/pykaraoke/database.py`; `scan_files(replace=)` / `prune_songs()` —
  `src/pykaraoke/webapp.py`.
* Relocate workflow — [User guide](../user-guide/index.md) ("Library
  Management").

## #8 Backup and restore library

**Reported** — "It should be possible to backup and restore the song database
… the list of artists and songs and the link to the media file … and not the
media files themselves."

**In PyKaraoke-NG** — **solved.** The library and settings serialise to a
single versioned, JSON-compatible payload and restore from it, and malformed
or unknown-version state is ignored rather than fatal. On top of that there
is now a full backup/share path:

* **Export** downloads the whole library (songs, pairing, folders, settings —
  never the media files themselves) as a self-describing envelope
  (`{"format": "pykaraoke-ng-library", "schema": 1, "library": {…}}`) named
  `pykaraoke-library.json`.
* **Import** validates the payload — envelope or bare library dict, recognised
  schema only — and atomically replaces the in-memory library on success. A
  corrupt or wrong-version file returns a structured error and leaves the
  existing library untouched; there is never a partial state.

**Evidence**

* Requirements "Library export envelope" and "Library import with validation
  and atomic swap" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* Requirements "Import and export API" —
  [web-engine-api spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/web-engine-api/spec.md).
* `SongLibrary.export_json()` / `import_json()` — `src/pykaraoke/database.py`;
  `KaraokeApp.export_json()` / `import_json()` — `src/pykaraoke/webapp.py`;
  Export/Import buttons — `src/web/index.html`.
* Share workflow — [User guide](../user-guide/index.md) ("Library
  Management").

## #9 KJ Features

**Reported** — "add a key change facility, make the time count down during
playback so we know how much time is left. Add a screen so the dj can see what
the singer is seeing and if possible add singer history which remembers
key/tempo change."

Four separate asks, all **not implemented**:

| Ask | Status in PyKaraoke-NG |
|-----|------------------------|
| Key change | Absent — same gap as [#2](#2-pitch-shifting) / [#4](#4-tempo-shifting). |
| Count down time remaining | The transport shows elapsed / total (`#time-current` / `#time-total`) and a progress slider, so remaining time is visible on the slider, but the readout counts **up** and there is no countdown mode. |
| Second screen mirroring the singer's view | Absent — single window, no second-screen output (see [#3](#3-lyrics-preview-window)). |
| Singer history remembering key/tempo | Absent — no history, and no key/tempo state to record. |

**Evidence**

* Transport requirements —
  [playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md)
  ("Transport control") and
  [ux-slim-sidebar](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md).
* Text output `time-current / time-total` — `src/web/index.html`.

## #10 Unresponsive after playing a MIDI file without lyrics

**Reported** — after a faulty MIDI file, PyKaraoke showed "Could not parse the
MIDI file" and "No lyrics in the track", then stayed stuck: it would not play
anything else and printed a traceback forever
(`AttributeError: midPlayer instance has no attribute 'useMidiTimer'`). The
reporter also suggested an optional validity check at scan time.

**In PyKaraoke-NG** — **solved: the failure mode cannot occur.** MIDI parsing
is a pure function, not a stateful player object, so there is no `midPlayer`
whose attribute can be missing after an error, and there is no idle loop that
keeps calling into a half-constructed player. Concretely:

* `parse_midi(bytes)` returns `None` for data that is not a usable MIDI/KAR
  file; the bridge turns that into `{"error": "could not parse MIDI file"}`.
* The UI plays every song inside a `try`/`catch`: a parse failure is reported
  in the status bar, that song stops, and the library, queue, and every other
  song remain usable.
* The queue survives, because it is persisted independently of playback.

The reporter's alternative suggestion — validating files during the scan — is
*not* implemented; the rewrite handles the failure at play time instead of
pre-screening the library.

**Evidence**

* `parse_midi()` and `KaraokeApp.parse_midi()` — `src/pykaraoke/midi.py`,
  `src/pykaraoke/webapp.py`.
* Requirement "MIDI parsing", including the invalid-data scenario —
  [web-engine-api spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/web-engine-api/spec.md).
* Requirement "MIDI/KAR parsing", including "Not a MIDI file" —
  [playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md).
* `playKar()` throwing on `parsed.error`, caught by `playSong()` —
  `src/web/index.html`.

## #11 Log files that failed during a scan

**Reported** — during a scan, files that "failed to unzip or parse" should be
logged to a file or a GUI window, ideally separated by reason (unsupported
compression, invalid/corrupt zip, name could not be parsed).

**In PyKaraoke-NG** — **partly.** The scan now records a structured,
per-file, per-reason report: unsupported extensions, filtered (pattern-excluded)
files, corrupt archives, unsupported compression, unreadable archives, and
filename parse failures each get their own category and path entry. The UI
shows a summary line under the library header (counts plus a few example
paths) with a dismiss control. What is *not* implemented is a persistent log
file — the report lives in memory for the session and is cleared on demand or
on reload.

**Evidence**

* Requirement "Scan reporting" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* `scan_report()` / `clear_scan_report()` —
  [Engine API](engine-api.md).
* `renderScanSummary()` — `src/web/index.html`.

**Still open** — an exportable/persisted log file.

## #12 Kamikaze mode double performer prompt

**Reported** — the "Kamikaze" button prompted for "Performer" twice and then
displayed the value from the first prompt as the filename.

**In PyKaraoke-NG** — **moot.** There is no Kamikaze/random-play button and no
performer-name prompt dialog anywhere in the application; adding a song is a
single keystroke on a highlighted result and the status bar echoes what was
queued. The dialog flow that produced the double prompt does not exist.

**Evidence**

* Requirement "Three-second add workflow" and the keyboard model —
  [ux-slim-sidebar spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md).
* `enqueue()` + `setStatus('Queued: …')` — `src/web/index.html`.

**Still open** — nothing equivalent to Kamikaze mode exists, so if that feature
is wanted it would be a new proposal rather than a fix.

## #13 Scan exclusion filter

**Reported** — "add the ability to exclude files matching certain patterns
from a scan", e.g. `_(Vocal)_`, `_(Gospel)_`, `_(Spanish)_`.

**In PyKaraoke-NG** — **solved.** Arbitrary filename-pattern exclusion is
implemented via the `exclude_patterns` (and `include_patterns`) settings:
lists of case-insensitive `fnmatch` patterns matched against each file and
zip-member basename. `_(Vocal)_` and friends work as expected, e.g.
`*_(vocal)_*` excludes `Song - Artist_(Vocal)_.cdg`. Exclude wins over
include; an empty include list means "everything". Both are editable in the
settings panel and filter the scan at the library level (filtered files are
counted in the scan report). The two older mechanisms remain as well:

* **Kind filters** — results can be filtered to CDG, KAR/MID, MPG, and LRC.
* **`exclude_non_matching`** — "Hide songs without artist": a parseability
  filter, not a pattern filter.

**Evidence**

* Requirement "Include and exclude filename patterns" —
  [song-library spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).
* `include_patterns` / `exclude_patterns` — [Configuration](configuration.md).
* Settings panel inputs and `parsePatternList()` — `src/web/index.html`.

## #14 Artist-Title parsing fails under certain circumstances

**Reported** — dashes break parsing for both spaced and legacy forms, e.g.
`CB30055-15 - Switchfoot - Stars.zip`, `SC3448-03 - All-American Rejects -
Dirty Little Secret.zip`, `CB5056-03-06 - Al Green - Let's Stay Together.zip`,
and `PHM - Pop/PHM0512/PHM0512-08 - Switchfoot - Stars.zip`. The reporter
proposed a new "DISC-TRACK - ARTIST - TITLE" mode in which spaces are
**required**, the last dash inside the disc-track part separates disc from
track, and the first ` - ` in the remainder separates artist from title.

**In PyKaraoke-NG** — **solved.** The reporter's requested mode is implemented
as `DISC_TRACK_SPACED` (`file_name_type` = `4`, selectable in the settings
panel as **Naming convention → Disc-Track - Artist - Title (spaced)**). It
requires the spaces, splits the prefix at its last hyphen into disc and
track, and splits the remainder at its first ` - ` into artist and title.
Measured with the spaced mode enabled:

```text
CB30055-15 - Switchfoot - Stars.cdg                -> disc='CB30055' track='15' artist='Switchfoot' title='Stars'
SC3448-03 - All-American Rejects - Dirty Little Secret.cdg
                                                   -> disc='SC3448' track='03' artist='All-American Rejects' title='Dirty Little Secret'
CB5056-03-06 - Al Green - Let's Stay Together.cdg  -> disc='CB5056-03' track='06' artist='Al Green' title="Let's Stay Together"
PHM - Pop/PHM0512/PHM0512-08 - Switchfoot - Stars.kar (zip member)
                                                   -> disc='PHM0512' track='08' artist='Switchfoot' title='Stars'
```

The earlier safety fixes remain in place: names are never dropped
(`exclude_non_matching` defaults to off, parse failures never abort a scan),
the parser never raises, directory dashes are ignored, inner dashes in the
title are preserved, and zipped libraries are parsed per *member* with the
parent directory able to supply the artist
(see [#5](#5-custom-pattern-for-song-structure-filter)).

One caveat remains for the *legacy unspaced* modes: a dash inside an artist
name (`SC3448-03-All-American Rejects-…` under `DISC_TRACK_ARTIST_TITLE`)
still mis-splits, because the legacy schemes have no reliable way to know
where the artist begins. The spaced mode sidesteps this by requiring the
` - ` separator.

**Evidence**

* Requirements "Disc-track spaced naming mode" and "Spaced disc-track
  fallback and setting value" —
  [filename-parsing spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/filename-parsing/spec.md).
* `FilenameParser._parse_disc_track_spaced()` —
  `src/pykaraoke/filename_parser.py`; tests in
  `tests/pykaraoke/test_filename_parser.py` (`TestDiscTrackSpaced`).
* Settings exposure (`file_name_type` = `4`) — [Configuration](configuration.md).

## #16 pykaraoke 7.5 fails to play sound with no error message

**Reported** — on Linux, MIDI files displayed lyrics correctly but produced no
sound and no error message, even with `timidity++` and sound patches installed.
The same MIDI files worked under `timidity` directly.

**In PyKaraoke-NG** — **solved by architecture.** MIDI/KAR is not handed to an
external synth: the engine parses the notes and the page **synthesises them
itself** with the Web Audio API, honouring the song's program changes and the
volume setting. There is no `timidity`/`mikmod`/`pygst` process or system
configuration that can silently fail to make sound, which was the report's
actual cause. A file that cannot be parsed now produces a visible status
message rather than silence.

One caveat, stated plainly: this removes the *reported* cause (a
missing/misconfigured external MIDI synthesiser). The rewrite still has no
positive confirmation that synthesis produced audible output, so a
valid-but-inaudible case (no OS audio device, blocked Web Audio) would
present as "playing with no sound" just as before.

**Evidence**

* "synthesizes the notes with the Web Audio API, scheduling them slightly ahead
  of the play head and honouring program changes and the current volume" —
  [Supported formats](formats.md).
* Requirement "MIDI synthesis" —
  [playback spec](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md).
* `MidiSynth` (Web Audio) — `src/web/index.html`.
* No external synth dependency — `pyproject.toml` (zero dependencies).

## #18 Renamed `libwxgtk-python` to `python-wxgtk2.8`

**Reported** — the packaging library was renamed; "Just update the README.md".

**In PyKaraoke-NG** — **moot.** There is no wxPython dependency anywhere, so
no wx package name appears in the install instructions to go stale. The engine
is pure stdlib and the UI is HTML/CSS/JS in the webview; the desktop app needs
`WebKit2GTK` on Linux, not wx.

**Evidence**

* `dependencies = []` and the "No pygame, numpy, or mutagen" note —
  `pyproject.toml`; requirements in
  [Installation](../getting-started/installation.md).
* Three-layer architecture with no wx — [Architecture overview](../architecture/overview.md).

!!! note "Scope"
    This resolves the request for PyKaraoke-NG only. The upstream
    `kelvinlawson/pykaraoke` README is a different repository.

## #21 GP2X still relevant?

**Reported** — during the port to GStreamer 1.0 / GTK3 / wxPython Phoenix,
"GP2X will probably break … wondering if it's still relevant to support this
platform or if the code could be removed?" The maintainer's answer on the
issue was that he was not against removing it *provided Windows and ideally
macOS were retained*.

**In PyKaraoke-NG** — **solved, in the direction the issue agreed on.** The
turnover targets are Windows, macOS, and (desktop) Linux, built by Tauri with
NSIS/DMG/deb installers, plus a browser build. There is no GP2X or
`pykaraoke_mini` target or code path.

**Evidence**

* Installer/platform table — [Installation](../getting-started/installation.md).
* Tauri bundle targets — `src/runtimes/tauri/src-tauri/tauri.conf.json`.
* No `gp2x` / `pykaraoke_mini` references in the project source or docs.

## #22 Installation on Ubuntu 22

**Reported** — "Is it compatible with Python 3?"; the documented apt packages
(`python-dev`, `python-pygam`, `libwxgtk-python`, `libsdl-dev`,
`python-mutagen`) do not exist on Ubuntu 22, and a later comment concluded the
project was "pretty much dead" for Python 3.

**In PyKaraoke-NG** — **solved.** PyKaraoke-NG is Python 3 only
(`requires-python >= 3.10`, classifiers for 3.10–3.13) with modern PEP 621
packaging, and the user-facing install path needs **no Python at all**: the
engine is compiled to WebAssembly inside the app, and Linux users install the
`.deb` (or run the browser build). None of the obsolete apt packages appear in
the instructions.

**Evidence**

* `requires-python = ">=3.10"`, 3.10–3.13 classifiers, `dependencies = []` —
  `pyproject.toml`.
* "Python is not required on the target machine", `.deb` installer, and
  Linux requirements (WebKit2GTK) —
  [Installation](../getting-started/installation.md).
* From-source path for developers —
  [Quick start](../getting-started/quickstart.md).

---

## Open gaps at a glance

None of these are hidden by the table above; they are the items worth turning
into OpenSpec changes:

| Gap | Issues |
|-----|--------|
| Pitch/key shifting and tempo/rate control | #2, #4, #9 |
| Saved, named playlists and per-singer history (including key/tempo memory) | #1, #9 |
| A second/presenter window mirroring the singer's view | #3, #9 |
| Countdown (time-remaining) readout | #9 |
| Scan reporting: per-file, per-reason failures and an exportable log | #11 |
| User-defined pattern exclusion (`_(Vocal)_`, …) | #13 |
| Spaced disc/track-aware naming mode; dashes inside legacy artist names | #14 |
| Library export/import as a file | #8 |
| Relocation ("change root") and removal of stale path entries | #7 |
| A user-visible control for `file_name_type` | #5, #14 |

To propose any of these, see the
[OpenSpec workflow](../contributing/openspec.md) — the same
propose → validate → implement → archive lifecycle the rest of the project
uses.

## Method and caveats

* Statuses were derived from the current source tree
  (`src/pykaraoke/`, `src/web/index.html`, `src/runtimes/tauri/`), the
  [specifications](specifications.md), and the published docs — not from the
  issue threads alone.
* The parser outputs quoted above were produced by running the shipped
  `FilenameParser` / `kind_for_name` on the exact filenames and extensions
  named in the issues (#6, #14, #5), against the current working tree.
* Issue texts are quoted from the upstream tracker snapshot of 2026-10-09.
  Upstream may close or change issues afterwards; this page covers only the
  open set as of that date.
* Not part of this page's scope, but worth knowing when comparing against the
  upstream project: `uv.lock` and `coverage.json` in this repository are
  **stale artifacts** from the pre-rewrite layout (they still name version
  0.7.5, `pygame`/`numpy`/`mutagen`, and a `src/pykaraoke/core/` package that
  no longer exists). They are not evidence of the current dependency set;
  `pyproject.toml` and the source tree are.

## See also

* [Specifications](specifications.md) — the capability index and how the site
  relates to the specs
* [Supported formats](formats.md) · [Configuration](configuration.md) ·
  [Engine API](engine-api.md)
* [OpenSpec workflow](../contributing/openspec.md)
* Upstream tracker:
  [kelvinlawson/pykaraoke/issues](https://github.com/kelvinlawson/pykaraoke/issues)
