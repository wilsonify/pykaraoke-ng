# Developer Guide

Set up the development environment, run tests, and contribute.

[← Home](index.md)

---

## Prerequisites

- Python 3.10+
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker (optional — for integration tests)
- Rust toolchain (optional — for Tauri development)

## Setup

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng

# With uv (recommended)
uv sync

# With pip
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Project Structure

```
src/pykaraoke/              # Core Python package
├── players/                # CDG, KAR, MPG players
├── core/                   # Backend, database, manager
└── config/                 # Constants, environment, version

src/runtimes/tauri/         # Tauri desktop app
├── src/                    # Frontend (HTML / CSS / JS)
└── src-tauri/              # Rust backend

tests/                      # Test suite
├── pykaraoke/              # Unit tests (mirrors src/)
├── integration/            # End-to-end tests
└── fixtures/               # Test data

specs/                      # Specifications and governance
├── constitution.md         # Engineering invariants
├── ux-design.md            # Slim sidebar UX spec
├── workflow.md             # Spec-driven development lifecycle
└── features/               # Per-feature spec directories
```

See [Repository Structure](architecture/structure.md) for the full tree.

---

## Tests

```bash
# All tests
./scripts/run-tests.sh

# pytest directly
uv run pytest tests/ -v

# Single file
uv run pytest tests/pykaraoke/core/test_filename_parser.py -v

# With coverage
uv run pytest tests/ --cov=. --cov-report=html
```

### Tauri tests

```bash
# Rust
cd src/runtimes/tauri/src-tauri && cargo test

# JavaScript
cd src/runtimes/tauri && node --test src/app.test.js src/index.test.js
```

### Integration tests (Docker)

```bash
./scripts/run-tests.sh --integration-only
```

See [Integration Testing](development/integration-testing.md) for full details.

---

## Code Quality

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix
uv run ruff format .         # format
```

SonarCloud runs on every PR. See [SonarQube Setup](development/sonarqube-setup.md).

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `core/backend.py` | Headless backend — stdio and HTTP modes |
| `core/database.py` | Song database, library scanning, settings |
| `core/filename_parser.py` | Artist–title extraction from filenames |
| `core/manager.py` | Playback coordination and queues |
| `players/cdg.py` | CD+G playback |
| `players/kar.py` | MIDI / KAR playback with lyrics |
| `players/mpg.py` | MPEG / AVI video playback |

---

## Tauri Development

### Linux prerequisites

```bash
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

cargo install tauri-cli --version "^1"
```

### Run

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri dev     # hot-reload
cargo tauri build   # production
```

---

## Docker Development

```bash
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .
docker compose -f deploy/docker/docker-compose.yml --profile dev up
```

---

## Contributing

### Governance

All contributions follow Spec-Driven Development. Read these first:

- [Project Constitution](../specs/constitution.md) — engineering invariants
- [Developer Workflow](../specs/workflow.md) — specify → clarify → plan → implement
- [UX Design Spec](../specs/ux-design.md) — slim sidebar design constraints

### Workflow

1. Create a feature branch: `NNN-short-description` (see [workflow](../specs/workflow.md)).
2. Write spec artifacts in `specs/features/NNN-*/`.
3. Implement via TDD: failing test → pass → refactor.
4. Lint: `uv run ruff check .`
5. Open a PR referencing the spec.

### Commit messages

```
feat: add support for OGG audio files
fix: resolve CDG timing issue on Windows
docs: update installation instructions
test: add tests for MIDI parsing
refactor: simplify player state management
```

### Code style

- PEP 8.
- Type hints on public interfaces.
- Docstrings on public functions.
- Tests for every new behaviour.
