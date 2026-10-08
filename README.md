# PyKaraoke-NG

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL-2.1](https://img.shields.io/badge/License-LGPL%202.1-green.svg)](https://opensource.org/licenses/LGPL-2.1)

A slim, keyboard-driven karaoke queue manager for working DJs, rebuilt
around the simplest architecture that works: **HTML/CSS/JS for the UI,
Python (via PyScript/Pyodide) for the engine, and Tauri only as a thin
desktop shell.**

There is no Python backend process, server, or sidecar — the same pure
Python engine that runs the test suite runs inside the browser as
WebAssembly.

## Supported Formats

| Format        | Extensions                     | Playback                       |
|---------------|--------------------------------|--------------------------------|
| CD+G          | `.cdg` + `.mp3`/`.ogg`/`.wav`  | `<audio>` + canvas rendering  |
| MIDI Karaoke  | `.kar`, `.mid`                 | WebAudio synthesizer + lyrics  |
| LRC lyrics    | `.lrc`, `.lcr` + audio         | `<audio>` + timed lyrics; optional `.elrc` word timing |
| MPEG Video    | `.mpg`, `.mpeg`, `.avi`        | `<video>`                      |

## Architecture

```
web/
  index.html              the entire app: UI + CSS + JS + PyScript bridge
  _assets/                vendored Pyodide + PyScript (generated)
  _wheel/                 pykaraoke engine wheel (generated)
src/pykaraoke/            pure-stdlib Python engine (CPython + Pyodide)
  webapp.py               the API the in-page bridge exposes
  cdg.py                  CD+G decoder (dirty tiles → canvas)
  midi.py                 MIDI/KAR parser (lyrics + notes → WebAudio)
  database.py             song library, search, settings
  filename_parser.py      "Artist - Title" name parsing
src/runtimes/tauri/       thin desktop shell (3 native commands)
tests/                    pytest (engine) + vitest (JS extracted from index.html)
```

`web/index.html` is one self-contained file: markup, `<style>`, the
vanilla-JS module (UI, file access, playback), and the inline
`<script type="py">` bridge — no framework, no bundler, no build step.

The engine is pure stdlib (no pygame, numpy, or mutagen) so the same
modules run under CPython for tests and under Pyodide in the browser.
It ships as a single `.whl` that PyScript installs at page load; there is
no second Python process, service, or backend.

## Quick Start

```bash
# 1. Python engine + tests
./scripts/setup-dev-env.sh          # create .venv, install dev deps
./scripts/run-tests.sh              # pytest + vitest

# 2. Run in a browser (dev / preview)
bash scripts/build-web.py           # wheel + vendored Pyodide/PyScript
python -m http.server 18000 --directory web
# open http://localhost:18000

# 3. Desktop app (Tauri)
cd src/runtimes/tauri
npm install
npm run tauri dev                   # serves web/ + opens the window
npm run tauri build                 # produces the installer
```

The desktop build embeds `web/` (including the vendored WASM runtime), so
the app works fully offline. The only native code is a folder dialog and
file reads (`src/runtimes/tauri/src-tauri/src/lib.rs`).

On Windows you need Visual Studio Build Tools (C++ workload + Windows SDK)
for the Tauri build.

## Documentation

| Audience | Guide |
|----------|-------|
| Users | [User Guide](docs/users.md) |
| Developers | [Developer Guide](docs/developers.md) |
| Architecture | [Overview](docs/architecture/overview.md) |
| Product spec | [Specs](specs/README.md) |

## License

LGPL-2.1-or-later (see [COPYING](COPYING)).