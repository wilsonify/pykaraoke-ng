# 💻 Developer Guide

Set up your development environment and contribute to PyKaraoke-NG.

[← Back to Home](index.md)

---

## Prerequisites

- Python 3.10+
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker (optional)
- Rust toolchain (optional, for Tauri development)

## Setup

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng

# Quick setup with uv
uv sync

# Or with pip
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Project Structure

```
src/pykaraoke/              # Core Python package
├── players/                # CDG, KAR, MPG players
├── core/                   # Backend, database, manager, player
├── config/                 # Constants, environment, version
└── native/                 # C extensions

src/runtimes/tauri/         # Tauri desktop app
├── src/                    # Web frontend (HTML/CSS/JS)
└── src-tauri/              # Rust backend

tests/                      # Test suite
├── pykaraoke/              # Unit tests (mirrors src/)
├── integration/            # End-to-end tests
└── fixtures/               # Test data
```

See [Repository Structure](architecture/structure.md) for the full breakdown.

---

## Running Tests

```bash
# All tests
./scripts/run-tests.sh

# Directly with pytest
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/pykaraoke/core/test_filename_parser.py -v

# With coverage
uv run pytest tests/ --cov=. --cov-report=html
```

### Tauri Tests

```bash
# Rust unit tests
cd src/runtimes/tauri/src-tauri && cargo test

# JavaScript tests
cd src/runtimes/tauri && node --test src/app.test.js src/index.test.js
```

---

## Code Quality

```bash
# Lint
uv run ruff check .

# Auto-fix
uv run ruff check . --fix

# Format
uv run ruff format .
```

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `core/backend.py` | Headless backend — stdio and HTTP modes |
| `core/database.py` | Song database, library scanning, settings |
| `core/filename_parser.py` | Artist–title extraction from filenames |
| `core/manager.py` | Playback coordination and queues |
| `players/cdg.py` | CD+G format playback |
| `players/kar.py` | MIDI / KAR playback with lyrics |
| `players/mpg.py` | MPEG / AVI video playback |

---

## Docker Development

```bash
# Build and run
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .

# Development container
docker compose -f deploy/docker/docker-compose.yml --profile dev up

# Run tests in container
docker compose -f deploy/docker/docker-compose.yml --profile test up
```

---

## Tauri Development

### Prerequisites (Linux)

```bash
# Debian/Ubuntu
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Install Tauri CLI v1
cargo install tauri-cli --version "^1"
```

### Development

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri dev     # hot-reload development
cargo tauri build   # production build
```

---

## Contributing

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and run tests: `./scripts/run-tests.sh`
4. Lint: `uv run ruff check .`
5. Commit with clear messages and open a PR

### Commit Messages

```
feat: add support for OGG audio files
fix: resolve CDG timing issue on Windows
docs: update installation instructions
test: add tests for MIDI parsing
refactor: simplify player state management
```

### Code Style

- Follow PEP 8
- Use type hints where practical
- Write docstrings for public functions
- Add tests for new features

---

## Additional Resources

- [Architecture Overview](architecture/overview.md) — system design
- [Backend Modes](backend-modes.md) — stdio and HTTP API reference
- [Quality Improvements](development/quality-improvements.md) — code quality history
- [SonarQube Setup](development/sonarqube-setup.md) — CI quality scanning
