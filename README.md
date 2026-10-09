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
| LRC lyrics    | `.lrc`, `.lcr` + audio         | `<audio>` + timed lyrics; optional `.elrc` word timing, duet parts |
| MPEG Video    | `.mpg`, `.mpeg`, `.avi`        | `<video>`                      |

## Architecture

```
src/web/
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

`src/web/index.html` is one self-contained file: markup, `<style>`, the
vanilla-JS module (UI, file access, playback), and the inline
`<script type="py">` bridge — no framework, no bundler, no build step.

The engine is pure stdlib (no pygame, numpy, or mutagen) so the same
modules run under CPython for tests and under Pyodide in the browser.
It ships as a single `.whl` that PyScript installs at page load; there is
no second Python process, service, or backend.

## Quick Start

```bash
# 1. Python engine + tests
./src/scripts/setup-dev-env.sh          # create .venv, install dev deps
./src/scripts/run-tests.sh              # pytest + vitest

# 2. Run in a browser (dev / preview)
bash src/scripts/build-web.py           # wheel + vendored Pyodide/PyScript
python -m http.server 18000 --directory src/web
# open http://localhost:18000

# 3. Desktop app (Tauri)
cd src/runtimes/tauri
npm install
npm run tauri dev                   # serves src/web/ + opens the window
npm run tauri build                 # produces the installer
```

The desktop build embeds `src/web/` (including the vendored WASM runtime), so
the app works fully offline. The only native code is a folder dialog and
file reads (`src/runtimes/tauri/src-tauri/src/lib.rs`).

On Windows you need Visual Studio Build Tools (C++ workload + Windows SDK)
for the Tauri build.

## Documentation

The documentation is built with MkDocs Material and deployed to GitHub Pages
at `https://wilsonify.github.io/pykaraoke-ng/` by
[`.github/workflows/docs.yml`](.github/workflows/docs.yml). (Publishing that
site requires the one-time repository setting **Settings → Pages → Build and
deployment → Source = "GitHub Actions"**.)

| Audience | Guide |
|----------|-------|
| Users | [User guide](docs/user-guide/index.md) |
| Install / build | [Quick start](docs/getting-started/quickstart.md) |
| Developers | [Development](docs/contributing/index.md) |
| Architecture | [Overview](docs/architecture/overview.md) |
| Specifications | [Specifications](docs/reference/specifications.md) |

Build and preview the site locally:

```bash
python -m pip install -e ".[docs]"
mkdocs serve            # http://127.0.0.1:8000
mkdocs build --strict   # one-off build into site/ (git-ignored)
```

## Specifications

PyKaraoke-NG uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for
specification-driven development. Enduring requirements live in
`openspec/specs/`; proposed, in-progress, and completed changes live in
`openspec/changes/`.

```bash
npm install --global @fission-ai/openspec@1.14.1
openspec new change my-feature     # scaffold a change
openspec validate --all --strict   # validate specs and changes
```

The full lifecycle (propose → validate → implement → archive) is documented in
[docs/contributing/openspec.md](docs/contributing/openspec.md).

## License

LGPL-2.1-or-later (see [COPYING](COPYING)).