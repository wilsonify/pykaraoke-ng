# Build and Test Plan

## Repository Overview

- **Project**: pykaraoke-ng v0.7.5
- **Language**: Python 3.10+
- **Build System**: hatchling (pyproject.toml)
- **Test Framework**: pytest with coverage, xdist, selenium plugins
- **Additional Tooling**: ruff, mypy, pre-commit

## Build System

| Command | Description |
|---------|-------------|
| `pip install -e ".[dev,test]"` | Install package + dev/test dependencies |
| `python -m build` | Build sdist + wheel via hatchling |
| `ruff check .` | Run linting |
| `mypy src/` | Run type checking |

**Build targets**:
- **sdist**: `pykaraoke_ng-0.7.5.tar.gz`
- **wheel**: `pykaraoke_ng-0.7.5-py3-none-any.whl`
- **Tauri/Desktop**: Rust-based desktop app via Cargo + Tauri CLI (requires linux build deps)

## Test Framework

| Command | Description |
|---------|-------------|
| `pytest tests/` | Run all tests |
| `pytest tests/pykaraoke/` | Run unit tests only |
| `pytest tests/integration/` | Run integration/E2E tests |
| `pytest tests/manual/` | Run manual/integration tests |

### Test Categories

| Category | Count | Location |
|----------|-------|----------|
| Unit tests (core) | ~450 | `tests/pykaraoke/core/` |
| Unit tests (config) | ~20 | `tests/pykaraoke/config/` |
| Unit tests (players) | ~70 | `tests/pykaraoke/players/` |
| Settings tests | ~30 | `tests/pykaraoke/test_settings.py` |
| Integration/E2E | 3 files | `tests/integration/` |
| Manual/integration | 1 file | `tests/manual/` |

### Test Markers

- `integration` — integration tests requiring full environment
- `slow` — slow tests
- `requires_pygame` — tests needing pygame
- `e2e` — end-to-end tests

## Dependency Graph

```
             ┌─────────────────┐
             │  pytest          │
             │  pytest-cov      │
             │  pytest-xdist    │
             └────────┬────────┘
                      │ depends on
             ┌────────▼────────┐
             │  pykaraoke-ng   │
             │  (source code)  │
             │                 │
             │  pygame         │
             │  numpy          │
             │  mutagen        │
             └────────┬────────┘
                      │ optional
             ┌────────▼────────┐
             │  selenium        │  (E2E browser tests)
             │  fastapi+uvicorn │  (HTTP backend)
             └─────────────────┘
```

## Execution Order

1. Install dependencies (`pip install -e ".[dev,test]"`)
2. Build package (`python -m build`)
3. Run unit tests (`pytest tests/pykaraoke/`)
4. Run integration tests (`pytest tests/integration/`)
5. Run manual tests (`pytest tests/manual/`)
6. Run linter (`ruff check .`)
7. Run type checker (`mypy src/`)

## Identified Risks

1. **pygame build on Windows**: pygame 2.6.1 requires C compiler on Python 3.14; use pre-built wheel for Python 3.13
2. **Selenium tests**: require Selenium Grid or local ChromeDriver; skip gracefully when unavailable
3. **Tauri tests**: require Linux with webkit2gtk-4.0-dev; gated behind file-change detection in CI
4. **CI-only stages**: spec-validation, SonarQube, platform builds, release require GitHub Actions
5. **Windows encoding**: Unicode checkmark characters in test print statements cause UnicodeEncodeError on cp1252 console
