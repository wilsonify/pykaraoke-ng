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
├── pykaraoke.py       # Main GUI application
├── pycdg.py           # CDG player
├── pykar.py           # MIDI/KAR player
├── pympg.py           # MPEG player
├── pykaraoke_mini.py  # Minimal player
├── pykmanager.py      # Song manager/database
├── pykdb.py           # Database operations
├── pykenv.py          # Environment detection
├── pykversion.py      # Version information
├── pykconstants.py    # Shared constants
├── pykplayer.py       # Base player class
├── pycdgAux.py        # CDG helper functions
├── tests/             # Test suite
├── scripts/           # Helper scripts
├── electron/          # Desktop app (Electron)
├── k8s/               # Kubernetes manifests
├── docs/              # Documentation (you are here)
└── pyproject.toml     # Project configuration
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
docker build -t pykaraoke-ng .

# Run development container
docker compose --profile dev up

# Run tests in container
docker compose --profile test up
```

### Development Container

```bash
docker compose run --rm dev bash

# Inside container
pytest tests/ -v
ruff check .
```

---

## Electron Desktop App

### Setup

```bash
cd electron
npm install
```

### Development

```bash
npm start        # Development mode
npm run build    # Build for distribution
```

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
