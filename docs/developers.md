# Developer Guide

Set up, test, and contribute to PyKaraoke-NG.

[← Home](index.md)

---

## Prerequisites

- Python 3.10+, Git, uv (recommended) or pip
- Docker (optional — for integration tests)
- Rust toolchain (optional — for Tauri)
- PyInstaller (optional — for production builds)

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
└── config/                 # Constants, environment, version

src/runtimes/tauri/         # Tauri desktop app
├── src/                    # Frontend (HTML / CSS / JS)
├── src-tauri/              # Rust backend
├── scripts/stage-backend.js # Staging script (copies .py or runs PyInstaller)
└── backend.spec            # PyInstaller spec for standalone backend.exe

tests/                      # Test suite
├── pykaraoke/              # Unit tests (mirrors src/)
├── integration/            # End-to-end tests
└── fixtures/               # Test data

specs/                      # Governance & design specs
```

## Tests

```bash
# All tests
uv run pytest tests/ -v

# Single file
uv run pytest tests/pykaraoke/core/test_filename_parser.py -v

# Rust tests (Tauri)
cd src/runtimes/tauri/src-tauri && cargo test

# Frontend JS
cd src/runtimes/tauri && node --test src/app.test.js

# With coverage
uv run pytest tests/ --cov=. --cov-report=html
```

## Code Quality

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix
uv run ruff format .         # format
```

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
npx tauri build
```

The build runs `scripts/stage-backend.js` which uses PyInstaller to
compile the Python backend into a standalone `backend.exe` (~12 MB).
The output is at `src-tauri/target/release/bundle/`.

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

## Key Modules

| Module | Purpose |
|--------|---------|
| `core/backend.py` | Headless backend — stdio and HTTP modes |
| `core/database.py` | Song database, scanning, settings |
| `core/filename_parser.py` | Artist–title extraction from filenames |
| `core/manager.py` | Playback coordination and queues |
| `players/cdg.py` | CD+G playback |
| `players/kar.py` | MIDI / KAR playback with lyrics |
| `players/mpg.py` | MPEG / AVI video playback |

## Packaging Notes

- The **PyInstaller spec** (`backend.spec`) uses `onedir` mode for faster
  startup.  The `backend.exe` + `_internal/` directory go into
  `src-tauri/backend/` and are bundled by the Tauri resource glob.
- In **dev mode**, `main.rs` falls back to searching for a Python
  interpreter and running the backend script directly — no PyInstaller
  needed.
- The `build.rs` script creates a placeholder file so `cargo test`
  passes even when the staging script hasn't run yet.

## Contributing

1. Create a feature branch: `NNN-short-description`
2. Write spec artifacts in `specs/features/NNN-*/`
3. Implement via TDD: failing test → pass → refactor
4. Lint: `uv run ruff check .`
5. Open a PR

Read the [Project Constitution](../specs/constitution.md) and
[Developer Workflow](../specs/workflow.md) first.
