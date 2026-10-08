# Developer Guide

Set up, test, build, and contribute to PyKaraoke-NG.

[← Home](index.md)

---

## Prerequisites

- Python 3.10+ and `uv` (or pip)
- Node.js 20+ (Tauri CLI)
- Rust stable toolchain (Tauri shell only)
- Platform build tools for Tauri (see [Tauri prerequisites](#tauri-prerequisites))

There is no frontend toolchain: no bundler, no framework, no `npm run build`
step for the app itself.

## Setup

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
./scripts/setup-dev-env.sh          # .venv + editable install + dev deps
uv sync                              # or: uv sync --extra dev
```

## Project Structure

```
web/
  index.html              the app: markup + <style> + <script type="module">
                           + <script type="py"> bridge   (one file, no build)
  _assets/                vendored Pyodide + PyScript   (generated)
  _wheel/                 pykaraoke engine wheel        (generated)

src/pykaraoke/            pure-stdlib engine (runs on CPython and Pyodide)
  webapp.py               JSON-friendly API exposed to the page
  cdg.py                  CD+G packet decoding
  midi.py                 MIDI/KAR parsing
  lrc.py                  LRC / .elrc word-timing parsing
  database.py             library scan, search, settings
  filename_parser.py      "Artist - Title" extraction

src/runtimes/tauri/       desktop shell
  package.json            local Tauri CLI + beforeDev/beforeBuild commands
  src-tauri/              Rust: pick_folder, list_folder, read_file

tests/
  pykaraoke/              pytest (engine)
  web/                    vitest on the JS extracted from web/index.html
  fixtures/               karaoke + LRC samples

scripts/                  setup, test runner, web build/serve helpers
specs/                    constitution, workflow, feature specs (CI-enforced)
docs/                     this documentation
```

## Tests

### Python

```bash
uv run pytest tests/pykaraoke/ -v              # unit tests
uv run pytest tests/pykaraoke/ --cov --cov-report=html
uv run pytest tests/pykaraoke/test_cdg.py -v   # single file
```

### Frontend (JS extracted from `web/index.html`)

```bash
cd tests/web
npm ci
npm test
```

The loader (`tests/web/load-app.mjs`) pulls the inline module out of
`web/index.html`, so tests always run against the real shipped script —
no `app.js` to keep in sync.

### Rust

```bash
cd src/runtimes/tauri/src-tauri
cargo test
```

### Everything

```bash
./scripts/run-tests.sh          # pytest + vitest
```

## Code Quality

```bash
uv run ruff check .             # lint
uv run ruff check . --fix       # auto-fix
uv run ruff format .            # format
```

SonarQube Cloud analyses every pull request and push to main.  The
pipeline blocks release if the quality gate fails.  Key rules:

- **Cognitive complexity ≤ 15** per function
- **Zero blocker/vulnerability** issues in production code
- **Coverage must not decrease** below the project baseline

## CI/CD Pipeline

`ci-cd.yml` runs in stages:

```
python tests ─┐
rust tests   ─┼─► sonarqube ─► build (linux/windows/macos) ─► release
frontend tests─┘
spec-validation ─┘
```

| Stage | What it does | Gating |
|-------|-------------|--------|
| `unit-tests-python` | `pytest` + coverage upload | — |
| `unit-tests-rust` | `cargo test` (skipped when no Rust files changed) | — |
| `unit-tests-frontend` | `npm test` in `tests/web` | — |
| `spec-validation` | Enforces spec-driven development | — |
| `sonarqube` | Static analysis + quality gate | Blocks build on failure |
| `build` | Platform matrix: deb / NSIS / DMG via `npx tauri build` | — |
| `release` | Tag + GitHub Release with built installers | main branch pushes only |

Pull requests never reach `release`.

## Working on `web/index.html`

The whole application lives in that file. Three sections, top to bottom:

1. **`<style>`** — all CSS.
2. **`<script type="module">`** — vanilla JS: state, rendering, file
   access, playback, canvas, lyrics. Pure functions here are covered by
   `tests/web`.
3. **`<script type="py">`** — the PyScript bridge. It defines
   `window.pykaraoke_api(name, ...args)`, which dispatches into
   `pykaraoke.webapp`, plus `runPython`-based helpers for decoding
   (CD+G packets, MIDI, LRC).

The JS engine-neutral pieces are `CDGAnimator`, `MidiSynth`,
`LrcHighlighter`, `queue` helpers and `formatTime`.

### Editing rules

- Keep the file self-contained. No external CSS/JS files, no build step.
- Never add a dependency to the front end.
- Changes that touch extracted logic must keep `tests/web` green.
- Engine work happens in `src/pykaraoke` and must stay **stdlib-only** so
  it runs under Pyodide.

## Tauri Development

### Dev mode

```bash
cd src/runtimes/tauri
npm ci
npx tauri dev
```

`beforeDevCommand` starts `python ../../../scripts/serve-web.py 18000`,
which serves `web/` (including `_assets/` and `_wheel/`) on
`http://localhost:18000`, and the window loads that URL. Edit
`web/index.html` and reload the window.

### Production build

```bash
cd src/runtimes/tauri
npx tauri build --bundles nsis   # Windows
npx tauri build --bundles dmg    # macOS
npx tauri build --bundles deb    # Linux
```

`beforeBuildCommand` runs `python ../../../scripts/build-web.py`, which
rebuilds the engine wheel and vendors the Pyodide/PyScript runtime into
`web/`. Tauri then embeds `web/` as the app's frontend. Output:
`src-tauri/target/release/bundle/`.

### The three native commands

| Command | Rust | Purpose |
|---------|------|---------|
| `pick_folder` | `rfd` dialog | Choose a library folder |
| `list_folder` | `walkdir` | Flat `{name, rel_path, size}` entries |
| `read_file` | `std::fs` | Raw bytes over IPC → `ArrayBuffer` |

If you change them, update the Rust unit tests in `src/runtimes/tauri/src-tauri`
(`cargo test`) and the fallback path in `web/index.html`
(`window.__TAURI__` detection).

### Tauri prerequisites

**Windows**

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools -e `
  --accept-source-agreements --accept-package-agreements `
  --override "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.Windows10SDK.19041"
```

**Linux (Debian/Ubuntu)**

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

**macOS** — Xcode Command Line Tools (`xcode-select --install`).

## Spec-Driven Development

Features start as spec artifacts in `specs/features/NNN-*/`:

```
specs/features/NNN-description/
├── README.md           # Feature specification
├── scenario-*.md       # User scenarios
└── acceptance.md       # Acceptance criteria
```

CI enforces spec completion via `specs/ci/validate-spec-completion.sh`:
the branch name determines the feature number, and the `spec-validation`
job fails if the spec directory is missing or malformed.

## Contributing

1. Create a feature branch: `NNN-short-description`
2. Write spec artifacts in `specs/features/NNN-*/`
3. Implement via TDD: failing test → pass → refactor
4. Lint: `uv run ruff check .`
5. Run the suite: `./scripts/run-tests.sh`
6. Open a PR

Read the [Project Constitution](../specs/constitution.md) and
[Developer Workflow](../specs/workflow.md) first.
