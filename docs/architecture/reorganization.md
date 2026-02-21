# Repository Reorganization (Completed)

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

> **Note:** This is a historical record. The reorganization described below was completed on 2026-01-31.

## Summary

The repository was restructured from a flat layout (13+ Python modules at root) into a proper Python package under `src/pykaraoke/`. This one-time migration moved 88 files, updated 100+ import statements, and produced the current layout.

## Before → After

| Before | After |
|--------|-------|
| `pycdg.py` (root) | `src/pykaraoke/players/cdg.py` |
| `pykar.py` (root) | `src/pykaraoke/players/kar.py` |
| `pympg.py` (root) | `src/pykaraoke/players/mpg.py` |
| `pykbackend.py` (root) | `src/pykaraoke/core/backend.py` |
| `pykdb.py` (root) | `src/pykaraoke/core/database.py` |
| `pykmanager.py` (root) | `src/pykaraoke/core/manager.py` |
| `pykplayer.py` (root) | `src/pykaraoke/core/player.py` |
| `pykconstants.py` (root) | `src/pykaraoke/config/constants.py` |
| `pykenv.py` (root) | `src/pykaraoke/config/environment.py` |
| `pykversion.py` (root) | `src/pykaraoke/config/version.py` |
| `electron/` | `src/runtimes/electron/` |
| `tauri-app/` | `src/runtimes/tauri/` |
| `fonts/`, `icons/` | `assets/fonts/`, `assets/icons/` |
| `k8s/` | `deploy/kubernetes/` |
| `Dockerfile` (root) | `deploy/docker/Dockerfile` |

## Import Changes

```python
# Old
import pycdg
import pykdb

# New
from pykaraoke.players import cdg
from pykaraoke.core import database
```

## Key Decisions

- **`src/` layout** — follows modern Python packaging conventions
- **`src/runtimes/`** — isolates Electron and Tauri as interchangeable wrappers
- **`deploy/`** — groups Docker, Kubernetes, and install scripts together
- **`assets/`** — shared fonts and icons used by multiple runtimes
- **Git history preserved** via `git mv`
