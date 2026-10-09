# Architecture Overview

[← Home](../index.md) · [Development](../contributing/index.md) · [Specifications](../reference/specifications.md)

---

## Design

PyKaraoke-NG is three thin layers and nothing else:

```
┌──────────────────────────────────────────────────────────────┐
│  Tauri desktop shell (Rust)                                  │
│    pick_folder · list_folder · read_file                     │
│    (everything a browser cannot do)                          │
└───────────────┬──────────────────────────────────────────────┘
                │ window.__TAURI__.core.invoke / convertFileSrc
┌───────────────▼──────────────────────────────────────────────┐
│  src/web/index.html — the whole application                  │
│    <style>            all CSS                                │
│    <script type=module>  UI, state, file access, playback    │
│    <script type=py>      bridge → window.pykaraoke_api       │
│    PyScript/Pyodide (vendored) + one engine .whl             │
└───────────────┬──────────────────────────────────────────────┘
                │ window.pykaraoke_api(name, ...args)
┌───────────────▼──────────────────────────────────────────────┐
│  src/pykaraoke — pure-stdlib Python engine                   │
│    cdg · midi · lrc · database · filename_parser · webapp    │
└──────────────────────────────────────────────────────────────┘
```

There is **no backend process, no server, no IPC protocol, and no
sidecar**. Python runs as WebAssembly *inside the page* (Pyodide), loaded
from a single wheel. The same engine modules run under CPython for the
test suite.

## Components

### Web application (`src/web/index.html`)

One self-contained file — UI, CSS, state, interaction, playback, and the
inline PyScript bridge. Vanilla JS, no framework, no bundler, no build
step. It owns:

| Concern | Implementation |
|---------|----------------|
| Layout / styling | Inline `<style>` |
| State (queue, settings, playback) | Plain JS object + `localStorage` |
| Folder access (browser fallback) | `<input webkitdirectory>` |
| Audio / video playback | `<audio>`, `<video>` |
| MIDI karaoke synthesis | Web Audio API (`MidiSynth`) |
| CD+G rendering | `<canvas>` from engine tile updates |
| Lyric highlighting | DOM + `requestAnimationFrame` |
| Persistence | `localStorage` (library JSON + queue ids) |

Everything pure in that script (queue, lyric grouping/highlighting,
note timeline, time formatting) is unit-tested: the vitest suite extracts
the inline module from `index.html` and imports it.

### Python engine (`src/pykaraoke`)

Pure stdlib, so it runs unchanged under CPython and Pyodide:

| Module | Purpose |
|--------|---------|
| `webapp.py` | JSON-friendly API the bridge dispatches to |
| `cdg.py` | CD+G packet decode → dirty-tile updates for the canvas |
| `midi.py` | MIDI/KAR parse → lyrics + note events for the synth |
| `lrc.py` | LRC + `.elrc` parse + duet part tags → timed lyric events |
| `database.py` | Song library, scanning, search, settings |
| `filename_parser.py` | "Artist - Title" extraction from filenames |

It is packaged as one wheel (`src/web/_wheel/*.whl`) that PyScript installs
at page load — no pip on the target machine, no Python interpreter
required.

### Tauri shell (`src/runtimes/tauri/src-tauri`)

Rust exists only for what the web platform cannot do:

| Command | Purpose |
|---------|---------|
| `pick_folder` | Native folder dialog (`rfd`) |
| `list_folder` | Recursively list a folder as flat entries |
| `read_file` | Read file bytes by absolute path (raw IPC → `ArrayBuffer`) |

That is the entire native surface: three commands, one file
(`src/lib.rs`). Playback, decoding, search and rendering all happen in
the webview. The same code runs in a plain browser using the
`webkitdirectory` file picker when `window.__TAURI__` is absent.

## JS ↔ Python boundary

Exactly one function crosses it:

```js
window.pykaraoke_api(name, ...args)   // defined by the inline <script type="py">
```

* Arguments are converted to plain Python with `to_py()`.
* Returns are Python objects; JS converts PyProxies with `toJs()`.
* `None` becomes `undefined`.

The dispatcher is intentionally untyped and total: the UI treats every
call as `try`/`catch`, so an engine error surfaces as a status message
rather than a dead window.

## Why these boundaries stay

| Boundary | Why it is necessary |
|----------|---------------------|
| Tauri ↔ webview | Native folder dialog and reading arbitrary files by path. `File System Access` / `webkitdirectory` cannot re-open a saved folder on restart. |
| JS ↔ Python | CD+G packet decoding, MIDI parsing and the library/search engine already exist as tested, pure-Python code. Porting them to JS would duplicate the logic; running Pyodide keeps one implementation and one test suite. |
| Everything else | None — there are no other processes, protocols, or layers. |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **One HTML file** | No build step, no module graph, no framework; the file *is* the app |
| **Tauri only for native gaps** | The webview already does audio, video, canvas, workers, storage |
| **Pyodide instead of a backend process** | Same code path in dev, tests, and the shipped app; nothing to spawn or supervise |
| **Single engine wheel** | One artifact, one version, no service split |
| **Vanilla JS + stdlib Python** | Zero frontend deps; zero Python deps |
| **Slim sidebar UI** | DJs need screen space for primary software (governed by the [project-governance](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/project-governance/spec.md) and [ux-slim-sidebar](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md) specs) |
