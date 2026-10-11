# Tauri desktop QA — 2026-10-11

Full QA pass over the PyKaraoke NG Tauri desktop shell: gates, a release build,
and an automated functional pass driving the **real desktop window** through
WebView2's DevTools Protocol (not a browser stand-in). Two functional defects and
one resource leak were found and fixed; one functional gap is documented.

Version under test: `0.8.0` (exe, MSI and NSIS bundles rebuilt during this pass).

## What was tested

| Layer | Command | Result |
|---|---|---|
| Engine unit tests | `.venv313/Scripts/python.exe -m pytest tests -q` | 358 passed (357 before; one regression test added) |
| Python lint/format | `ruff check .`, `ruff format --check .` | clean (17 files) |
| Frontend tests | `cd tests/web && npx vitest run` | 40 passed |
| Asset build | `.venv313/Scripts/python.exe src/scripts/build-web.py` | wheel rebuilt, vendored assets verified by checksum, every asset referenced by `index.html` present |
| Desktop build | `cd src/runtimes/tauri && npx tauri build` | exit 0 — `pykaraoke-ng.exe` plus `PyKaraoke NG_0.8.0_x64_en-US.msi` and `-setup.exe`; `beforeBuildCommand` hook ran `build-web.py` correctly |
| Desktop runtime | WebView2 CDP harness, 50 checks | 50/50 on the rebuilt exe |
| Restart persistence | relaunch + CDP | 5/5 — library, queue, folders/zoom/volume restored |
| Browser fallback | `serve-web.py` + Chromium | page, engine, `webkitdirectory` picker, browser-mode messages; all assets 200 with `Cache-Control: no-store`, no console errors |

Runtime coverage: native `list_folder`/`read_file` IPC (recursive walk, unicode
and nested paths, raw `ArrayBuffer` bytes matching disk, error strings for a
file-as-directory, a missing directory and a missing file); library scan;
corrupt-archive and unsupported-file reporting; search (including non-ASCII) and
kind filters; queue and its persistence; KAR playback (3348 notes, lyrics,
transport, pause/seek/stop, WebAudio running without an autoplay block); LRC with
its `.elrc` companion (duet part chips, syllable lighting); CDG canvas rendering;
zoom and volume settings; decoder/audio cleanup after stop.

## Findings

### 1. CDG animation froze after the first update — fixed (engine, high)

`CdgDecoder.process_until()` compared a **packet index** with `packet_pos`, which
is a **byte offset** (`_next_packet` advances it by 24). The first call set
`packet_pos` to hundreds or thousands of bytes, so every later call
(`packet_index <= packet_pos`) returned immediately: the decoder processed
roughly the first 0.3 s of a CDG stream and then never advanced, while the audio
kept playing.

Evidence: on the real desktop app, the CDG canvas showed the memory-preset blue
frame at 1.5 s and still at 4.1 s with **0** white pixels from tile blocks that
the same decoder reproduces (3528 visible white pixels when a single
`process_until(3000)` call is used). A simulation of the old method against the
new regression test reports `{'red': True, 'white': False}`, i.e. later tiles are
never reported.

Fix: reconcile the units in `process_until` (`src/pykaraoke/cdg.py`); a shared
`PACKET_SIZE` constant now replaces the bare `24`. Regression test:
`test_incremental_updates_reach_later_packets` drives the decoder the way the UI
does (20 ms steps) and asserts a later tile block is still reported.

### 2. Changing the CDG zoom did nothing until a rescan — fixed (frontend, low)

The settings panel sends `updateSettings({ cdg_zoom })`, but `updateSettings`
only called `applyZoom()` for a `zoom` key that nothing ever sends, and it never
copied the new value into `state.settings.zoom`. The engine stored the new zoom
and the select showed it, but the canvas kept its old size until some other
action triggered `refreshSettings()`.

Fix: mirror `cdg_zoom` into the local settings and repaint immediately, in
`src/web/src/app.js`. Verified in the desktop app: selecting
"Full (2×)" now resizes the canvas to 576×384 immediately.

### 3. `cdg_open` ran before the audio check — fixed (frontend, low)

`playCdg()` opened the decoder and only then looked for the audio file, so every
failed CDG play left a decoder in the engine for the rest of the session. Audio
resolution now happens first; the check asserts `state.cdgKey === null` after a
failed play.

### 4. A `.cdg` inside a `.zip` can be listed but never played — not fixed (gap)

Scanned zip members appear in the library and are correctly typed as `cdg`, but
`resolveAudioPath()` only looks at on-disk paths (and the file the *engine* reads
through `read_zip_member`). Playing one fails with
`Playback error: no audio file found for this CDG`. The failure is graceful (clear
status message, decoder released, no exception leaking into the console as an
uncaught error), so it is a limitation rather than a crash. Closing it needs a
blob URL built from the zip member's audio bytes.

### 5. Minor observations

- The border-preset colour never reaches the screen: `drawCdgUpdate()` fills the
  canvas with `update.border` and then blits the full visible frame over it. The
  6 px / 12 px border ring is outside the 288×192 area the UI renders, so this is
  expected, just wasted work.
- After a failed play the stage keeps the previous song's frame while the
  transport resets, and "Now Playing" shows the song that failed.

## Test environment

Windows, WebView2 runtime 154.0.4258.62, Rust/Cargo 1.99.0, Node 24.15.0,
Python 3.13.1 (`.venv313`). Songs were a purpose-built library in `%TEMP%`
(a generated 6 s CDG with a known colour table and timed tile blocks, a KAR from
`tests/fixtures`, the duet and word-timing LRC/ELRC pairs, unicode filenames, a
nested folder, a zip holding a CDG + audio, a corrupt zip and an unsupported
file). The app was driven via `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222`.

## QA session side effects (disclosure)

The QA harness clears `localStorage` to start from a clean slate and backs up the
previous value first. Re-running the harness overwrote that backup with QA data,
so the app's original persisted state (a 128,376 character library JSON for
`C:\Users\toman\repos\music\chord-vault\Tom-and-the-Back-Roads` plus one queued
song) was lost from the live profile. It was rebuilt from the folder recovered out
of the WebView2 leveldb (272 songs, regenerated state 128,377 characters — the
same library) and the queued *Closing Time* entry was restored. Anything edited in
the settings panel before that point (volume, zoom, sort, naming convention,
include/exclude patterns) is back to defaults.

## How to reproduce

```bash
# gates
.venv313/Scripts/python.exe -m pytest tests -q
.venv313/Scripts/python.exe -m ruff check .
(cd tests/web && npx vitest run)

# build + run with a debugging port for automation
(cd src/runtimes/tauri && npx tauri build)
cd src/runtimes/tauri/src-tauri/target/release
WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222 ./pykaraoke-ng.exe
```

## Residual risk

- No automated test drives the desktop window in CI; this pass was manual +
  harness-driven, so the harness itself is not yet a checked-in artifact.
- The CDG decoder fix changes an internal invariant (`packet_pos` stays a byte
  offset); the new test covers the incremental path, but a seek-and-play mix
  (rapid next/previous between CDG songs) was only exercised incidentally.
- Zip-contained audio remains unsupported, so zipped CDG/MPG songs cannot play.
