# 💻 Developer Guide

Set up your development environment and contribute to PyKaraoke-NG.

[← Back to Home](index.md)

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker (optional, for containerized development)

### Quick Setup with uv

```bash
# Clone the repository
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng

# Run the setup script
./scripts/setup-dev-env.sh

# Or manually with uv
uv venv
source .venv/bin/activate
uv sync
```

### Manual Setup with pip

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Project Structure

```
pykaraoke-ng/
├── src/
│   ├── pykaraoke/           # Main Python package
│   │   ├── core/            # Core player modules
│   │   ├── config/          # Configuration & constants
│   │   └── utils/           # Utility functions
│   └── runtimes/
│       ├── electron/        # Electron desktop app
│       └── tauri/           # Tauri desktop app
├── deploy/
│   ├── docker/              # Dockerfile & compose
│   └── kubernetes/          # K8s manifests
├── tests/                   # Test suite
├── scripts/                 # Helper scripts
├── docs/                    # Documentation (you are here)
├── pykaraoke.py             # Main GUI application entry
├── pycdg.py                 # CDG player
├── pykar.py                 # MIDI/KAR player
├── pympg.py                 # MPEG player
├── pykaraoke_mini.py        # Minimal player
└── pyproject.toml           # Project configuration
```

---

## Running Tests

### Run All Tests

```bash
# Using the test script
./scripts/run-tests.sh

# Or directly with pytest
uv run pytest tests/ -v

# With coverage report
uv run pytest tests/ --cov=. --cov-report=html
```

### Run Specific Tests

```bash
# Run a single test file
uv run pytest tests/test_pykversion.py -v

# Run tests matching a pattern
uv run pytest -k "test_cdg" -v

# Run with parallel execution
uv run pytest -n auto
```

### Test Coverage

```bash
uv run pytest --cov=. --cov-report=html
open htmlcov/index.html
```

---

## Code Quality

### Linting with Ruff

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Checking with mypy

```bash
uv run mypy *.py
```

### Pre-commit Hooks

```bash
uv pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## Architecture Overview

### Player Classes

All players inherit from a common base:

```
pykplayer.py (base)
├── pycdg.py    (CDG+audio)
├── pykar.py    (MIDI/KAR)
└── pympg.py    (MPEG video)
```

### Key Components

| Module | Purpose |
|--------|---------|
| `pykmanager.py` | Manages playback, queues, and settings |
| `pykdb.py` | SQLite database for song library |
| `pykenv.py` | Platform detection (Linux/Windows/macOS) |
| `pycdgAux.py` | CDG format parsing and rendering |

---

## Docker Development

### Build and Run

```bash
# Build the image
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .

# Run development container
docker compose -f deploy/docker/docker-compose.yml --profile dev up

# Run tests in container
docker compose -f deploy/docker/docker-compose.yml --profile test up
```

### Development Container

```bash
docker compose -f deploy/docker/docker-compose.yml run --rm dev bash

# Inside container
pytest tests/ -v
ruff check .
```

---

## Electron Desktop App

### Setup

```bash
cd src/runtimes/electron
npm install
```

### Development

```bash
npm start        # Development mode
npm run build    # Build for distribution
```

---

## Tauri Desktop App

Tauri provides a lightweight alternative to Electron using Rust and native webview.

### Prerequisites

1. **Install Rust** (if not already installed):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source $HOME/.cargo/env
   ```

2. **Install webkit2gtk** (Linux only):
   ```bash
   # Debian/Ubuntu (webkit2gtk 4.0)
   sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget file \
       libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

   # Debian/Ubuntu (webkit2gtk 4.1 - for newer systems)
   sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
       libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

   # Fedora
   sudo dnf install webkit2gtk4.0-devel openssl-devel curl wget file
   ```

3. **Install Tauri CLI** (version 1.x for webkit2gtk 4.0 compatibility):
   ```bash
   cargo install tauri-cli --version "^1"
   ```

### Setup Icons

The Tauri app requires icons in `src/runtimes/tauri/src-tauri/icons/`. If missing:

```bash
# Create icons directory
mkdir -p src/runtimes/tauri/src-tauri/icons

# Copy an icon (adjust source path as needed)
cp assets/icons/microphone.png src/runtimes/tauri/src-tauri/icons/icon.png
cp src/runtimes/tauri/src-tauri/icons/icon.png src/runtimes/tauri/src-tauri/icons/32x32.png
cp src/runtimes/tauri/src-tauri/icons/icon.png src/runtimes/tauri/src-tauri/icons/128x128.png
cp src/runtimes/tauri/src-tauri/icons/icon.png src/runtimes/tauri/src-tauri/icons/128x128@2x.png

# For Windows builds, also create .ico file
convert src/runtimes/tauri/src-tauri/icons/icon.png src/runtimes/tauri/src-tauri/icons/icon.ico
```

### Development

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri dev
```

### Build for Distribution

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri build
```

Built packages appear in `src/runtimes/tauri/src-tauri/target/release/bundle/`.

### Troubleshooting Tauri

**GBM buffer creation errors (GPU/driver issues):**
```bash
WEBKIT_DISABLE_COMPOSITING_MODE=1 cargo tauri dev
```

**Tauri v1 vs v2 compatibility:**
- Tauri v1 CLI requires `libwebkit2gtk-4.0-dev`
- Tauri v2 CLI requires `libwebkit2gtk-4.1-dev`
- Check your system: `pkg-config --exists webkit2gtk-4.0 && echo "4.0 available"`

---

## Contributing

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `./scripts/run-tests.sh`
5. Run linting: `uv run ruff check .`
6. Commit with clear messages
7. Push and create a Pull Request

### Commit Messages

Use conventional commit format:

```
feat: add support for OGG audio files
fix: resolve CDG timing issue on Windows
docs: update installation instructions
test: add tests for MIDI parsing
refactor: simplify player state management
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where practical
- Write docstrings for public functions
- Keep functions focused and small
- Add tests for new features

> **Questions?** Open an issue on GitHub or check existing discussions.
