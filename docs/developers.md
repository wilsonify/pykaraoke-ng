# Developer Guide

Set up, test, build, and contribute to PyKaraoke-NG.

[← Home](index.md)

---

## Prerequisites

- Python 3.10+, Git, uv (recommended) or pip
- Docker (optional — for integration tests)
- Rust toolchain (optional — for Tauri builds)
- PyInstaller (optional — for production builds)
- Node.js 20+ (optional — for Tauri frontend + CLI)

## Setup

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync                    # or: python -m venv .venv && pip install -e ".[dev]"
```

## Project Structure

```
src/pykaraoke/              # Core Python package
├── players/                # CDG, KAR, MPG players
├── core/                   # Backend, database, manager
├── config/                 # Constants, environment, version
├── interfaces/             # Entry points for Tauri / CLI / HTTP
└── native/                 # C extensions

src/runtimes/tauri/         # Tauri desktop app
├── src/                    # Frontend (HTML / CSS / JS)
├── src-tauri/              # Rust backend
├── scripts/stage-backend.js # Staging script (copies .py or runs PyInstaller)
├── backend.spec            # PyInstaller spec for standalone backend.exe
└── e2e/                    # BDD end-to-end tests (Cucumber.js)

tests/                      # Test suite
├── pykaraoke/              # Unit tests (mirrors src/)
├── integration/            # Docker-compose integration tests
├── validation/             # Artifact tests against built backend.exe
├── manual/                 # Environment-dependent tests
└── fixtures/               # Test data

specs/                      # Governance & design specs
```

## Tests

### Python unit tests

```bash
uv run pytest tests/ -v                         # all tests
uv run pytest tests/pykaraoke/ -v                # unit only
uv run pytest tests/validation/ -v               # artifact validation
uv run pytest tests/pykaraoke/core/test_filename_parser.py -v  # single file
uv run pytest tests/ --cov --cov-report=html     # with coverage
```

### Running against a built artifact

Set `PYKARAOKE_BACKEND_EXE` to validate a specific `backend.exe`:

```bash
export PYKARAOKE_BACKEND_EXE=src/runtimes/tauri/src-tauri/backend/backend.exe
uv run pytest tests/validation/test_artifact_backend.py -v
```

This launches the real PyInstaller-built binary as a subprocess and
tests it via stdin/stdout — no mocking.

### Integration tests (Docker)

```bash
cd deploy/docker
docker compose --profile integration run test-integration
```

See [Integration Testing](development/integration-testing.md) for details.

### BDD end-to-end tests (Cucumber.js)

```bash
cd src/runtimes/tauri/e2e
npm ci
npm run test:e2e:ci
```

### Cross-project tests

```bash
cd src/runtimes/tauri/src-tauri && cargo test   # Rust
cd src/runtimes/tauri && node --test src/app.test.js  # Frontend JS
```

## Code Quality

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix
uv run ruff format .         # format
```

SonarQube Cloud analyses every pull request and push to main.  The
pipeline blocks release if the quality gate fails.  Key rules:

- **Cognitive complexity ≤ 15** per function
- **Zero blocker/vulnerability** issues in production code
- **Coverage must not decrease** below the project baseline

## CI/CD Pipeline

The pipeline (`ci-cd.yml`) runs in stages:

```
unit-tests ─► sonarqube ─► integration-tests ─► build ─► e2e-tests ─► release
```

| Stage | What it does | Gating |
|-------|-------------|--------|
| `unit-tests-python` | Python unit tests + coverage | — |
| `unit-tests-rust` | `cargo test` (skipped if no Rust changes) | — |
| `unit-tests-frontend` | `node --test` | — |
| `spec-validation` | Enforces spec-driven development | — |
| `sonarqube` | Static analysis + quality gate | Blocks next stage on failure |
| `integration-tests` | Docker compose integration tests | Blocks build on failure |
| `build` | Platform matrix (Linux deb, Windows NSIS, macOS DMG) | — |
| `e2e-tests` | Per-platform E2E + artifact validation | Blocks release on failure |
| `bdd-e2e-tests` | Cucumber.js BDD suite in Docker | Blocks release on failure |
| `release` | Tags + GitHub Release on main branch push | Main branch only |

## Tauri Development

### Dev mode

```bash
cd src/runtimes/tauri
npx tauri dev
```

In dev mode the Rust backend searches for a local Python interpreter and
runs the backend script directly.  Edit the Python/JS source and refresh
the window to see changes.

### Production build

```bash
cd src/runtimes/tauri
python -m pip install pyinstaller
npm install -g @tauri-apps/cli@1
npx tauri build --bundles nsis   # Windows
npx tauri build --bundles dmg    # macOS
npx tauri build --bundles deb    # Linux
```

The `beforeBuildCommand` runs `scripts/stage-backend.js` which uses
PyInstaller to compile the Python backend into a standalone `backend.exe`
(~12 MB).  The Tauri resource glob bundles it into the installer.

Output directory: `src-tauri/target/release/bundle/`.

### Build the backend artifact standalone

```bash
cd src/runtimes/tauri
python -m PyInstaller backend.spec --distpath src-tauri --workpath build/pyinstaller-work --clean -y
```

The resulting `src-tauri/backend/backend.exe` can be run standalone or
tested with the validation suite.

### Validate the built artifact

```bash
export PYKARAOKE_BACKEND_EXE=src/runtimes/tauri/src-tauri/backend/backend.exe
pytest tests/validation/ -v -m artifact
```

16 smoke tests exercise the real binary: startup, settings, library scan,
playlist, volume, and error handling.

### Windows prerequisites

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools -e \
    --accept-source-agreements --accept-package-agreements \
    --override "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.Windows10SDK.19041"
npm install -g @tauri-apps/cli@1
```

Run from a Developer Command Prompt or initialize MSVC env:

```bat
"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
```

### Linux prerequisites

```bash
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
npm install -g @tauri-apps/cli@1
```

## Docker Development

```bash
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .
docker compose -f deploy/docker/docker-compose.yml --profile dev up
```

Available Docker Compose profiles:

| Profile | Services | Use case |
|---------|----------|----------|
| `dev` | UI + backend + app | Development with hot reload |
| `test` | test, test-all, test-all-coverage | Unit + integration tests |
| `integration` | backend-test, test-integration | Integration tests only |
| `e2e` | backend, ui, selenium | BDD end-to-end tests |

## Key Modules

| Module | Purpose |
|--------|---------|
| `interfaces/backend_api.py` | Entry point — re-exports `PyKaraokeBackend` |
| `core/backend.py` | Headless backend — stdio and HTTP modes |
| `core/database.py` | Song database, scanning, settings |
| `core/filename_parser.py` | Artist–title extraction from filenames |
| `core/manager.py` | Playback coordination and queues |
| `core/player.py` | Base `PykPlayer` class with `seek()`, `get_pos()`, state machine |
| `players/cdg.py` | CD+G playback (overrides `seek()` for audio restart + packet sync) |
| `players/kar.py` | MIDI / KAR playback with lyrics |
| `players/mpg.py` | MPEG / AVI video playback |

## Backend State & Poll Architecture

The backend maintains authoritative state in `PyKaraokeBackend`:

- `state` — `BackendState` enum (`IDLE`, `PLAYING`, `PAUSED`, `STOPPED`, etc.)
- `position_ms` / `duration_ms` — current playback position and total length
- `current_song` — the active `SongStruct` (persists across stop/play cycles)
- `current_player` — the active `PykPlayer` subclass instance (cleared on stop)

### State lifecycle invariants

| Event | `current_song` | `current_player` | `position_ms` | `state` |
|-------|---------------|-----------------|---------------|---------|
| Play starts | set | created | 0 | PLAYING |
| Pause | unchanged | unchanged | frozen | PAUSED |
| **Stop** | **preserved** | **cleared** | **reset to 0** | STOPPED |
| Seek | unchanged | unchanged | updated | unchanged |
| Song finishes | advanced | cleared | 0 | IDLE |

**Stop preserves `current_song`** so that pressing Play after Stop restarts
the same song from the beginning.  Early versions cleared `current_song`,
which caused Play to auto-play queue index 0 instead.

### Seek flow

```
Frontend: slider drag → change event → sendCommand('seek', { position_ms })
Backend:  _handle_seek → self.position_ms = pos → player.seek(pos)
          → _emit_state_change()
Player:   PykPlayer.seek() sets seek_pos_ms + adjusts play_start_time;
          subclass overrides restart audio at the given position
          (e.g. pygame.mixer.music.play(start=start_sec))
Poll:     get_pos() returns seek_pos_ms + elapsed for correct position
```

### Fast-forward / Rewind flow

```
Frontend: mousedown on ff-btn → sendCommand('fast_forward', { amount_seconds: 10 })
          hold repeats every 500 ms via setInterval
Backend:  _handle_fast_forward → new_pos = min(position_ms + 10s, duration_ms)
          → _handle_seek(new_pos)
```

FF/RW clamp to `[0, duration_ms]`.  When no song is loaded (`duration_ms = 0`),
the position clamps to 0 — expected behaviour.

### Position tracking

`position_ms` is the **authoritative** position used by the backend and
frontend display.  It is:
- **Set directly** by `_handle_seek` during a seek operation
- **Updated** by `poll()` → `player.get_pos()` every state read during PLAYING
- **Reset to 0** by `_handle_stop` and `_start_playback`

The backend's `position_ms` is NOT read back from the player after seek;
it is set to the target value, and subsequent `poll()` calls reconcile
it with `player.get_pos()`.

### Poll safety

`poll()` is called from `get_state()` on every state change emission and
state read.  It must **never raise** — `manager.poll()` is wrapped in
`try/except` so that player errors (e.g. `NameError` from missing imports
in `kar.py:do_stuff()`) do not corrupt the state snapshot.

See [Playback Controls Fix](issues/playback-controls-fixes.md) for the
consequences of an unhandled poll exception.

### Known gotchas

- `pygame.mixer.music.play(start=...)` does **not** seek MIDI files on
  all platforms (SDL_mixer limitation).  For KAR files:
  `PykPlayer.seek()` still sets `seek_pos_ms` correctly so the UI
  position display updates, but audio may start from the beginning.
- The same limitation applies to some MP3 codecs in pygame —
  `play(start=secs)` may be silently ignored on certain SDL_mixer builds.
- `STATE_CAPTURING` in `kar.py:do_stuff()` must be imported from
  `pykaraoke.config.constants`.  The short-circuit `or` in
  `if self.state == STATE_PLAYING or self.state == STATE_CAPTURING:`
  masked the bug during playback; it only surfaced on stop/pause.
  Always add `STATE_CAPTURING` to any import block that references
  player states.

## Packaging Notes

- The **PyInstaller spec** (`backend.spec`) uses `onedir` mode for faster
  startup.  The `backend.exe` + `_internal/` directory go into
  `src-tauri/backend/` and are bundled by the Tauri resource glob.
- Hidden imports required: `pygame`, `numpy`, `mutagen`,
  `pykaraoke.config.constants` (see `backend.spec:hiddenimports`).
- In **dev mode**, `main.rs` falls back to searching for a Python
  interpreter and running the backend script directly — no PyInstaller
  needed.
- The `build.rs` script creates a placeholder file so `cargo test`
  passes even when the staging script hasn't run yet.

## Spec-Driven Development

Features start as spec artifacts in `specs/features/NNN-*/`:

```
specs/features/NNN-description/
├── README.md           # Feature specification
├── scenario-*.md       # User scenarios
└── acceptance.md       # Acceptance criteria
```

CI enforces spec completion via `specs/ci/validate-spec-completion.sh`.
The pipeline:
1. Reads the branch name for the feature number
2. Checks that the spec directory exists and is well-formed
3. Fails the `spec-validation` job if specs are incomplete

## Contributing

1. Create a feature branch: `NNN-short-description`
2. Write spec artifacts in `specs/features/NNN-*/`
3. Implement via TDD: failing test → pass → refactor
4. Lint: `uv run ruff check .`
5. Run full test suite: `uv run pytest tests/ -v`
6. Open a PR

Read the [Project Constitution](../specs/constitution.md) and
[Developer Workflow](../specs/workflow.md) first.
