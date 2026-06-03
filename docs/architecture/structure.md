# Repository Structure

[← Home](../index.md) · [Developer Guide](../developers.md)

---

# Architecture

PyKaraoke-NG follows a **layered architecture** that separates domain logic
from infrastructure concerns and provides clear entry points for external
consumers.

## Layers

```
src/pykaraoke/
├── config/          # Shared constants, environment detection, version info
├── domain/          # Pure logic and data structures (no I/O)
├── application/     # Orchestration and services
├── infrastructure/  # Database, players, native extensions
├── interfaces/      # Entry points used by Tauri / CLI / HTTP
├── core/            # Legacy location — compatibility wrappers
├── players/         # Legacy location — compatibility wrappers
└── native/          # Legacy location — C extension sources
```

### Config (`config/`)

Shared constants, platform detection, and version strings.  This layer is
imported by every other layer but depends on nothing inside `pykaraoke`.

### Domain (`domain/`)

Pure business logic and data structures with **no** infrastructure
dependencies.

| Module | Responsibility |
|--------|---------------|
| `domain/parsing/filename_parser.py` | Extracts artist / title / disc / track from filenames |
| `domain/performer.py` | Performer prompt dialog (wx-dependent) |
| `domain/song.py` | Song value object *(placeholder)* |
| `domain/queue.py` | Queue / playlist model *(placeholder)* |

### Application (`application/`)

Use-case orchestration that coordinates domain objects and infrastructure.

| Module | Responsibility |
|--------|---------------|
| `application/karaoke_manager.py` | Session management, playback coordination, settings |
| `application/playback_service.py` | Base player class shared by format-specific players |
| `application/library_service.py` | Library scanning & search *(placeholder)* |

### Infrastructure (`infrastructure/`)

Concrete adapters for persistence, format-specific playback, and native
extensions.

| Module | Responsibility |
|--------|---------------|
| `infrastructure/database/database.py` | SQLite song database, library scanning, settings |
| `infrastructure/players/cdg.py` | CD+G karaoke format player |
| `infrastructure/players/kar.py` | MIDI / KAR format player |
| `infrastructure/players/mpg.py` | MPEG / AVI video player |
| `infrastructure/players/cdg_aux.py` | CD+G auxiliary processing |
| `infrastructure/native/_cpuctrl.c` | GP2X CPU control (C extension) |
| `infrastructure/native/_pycdgAux.c` | CD+G pixel blitting (C extension) |

### Interfaces (`interfaces/`)

Entry points that external systems (Tauri, HTTP, CLI) use to drive the
karaoke engine.

| Module | Responsibility |
|--------|---------------|
| `interfaces/backend_api.py` | Headless JSON API — stdio and HTTP transports |

## Backward Compatibility

The original import paths continue to work.  Modules under `core/` and
`players/` still contain the canonical implementation; the new layered
modules **re-export** from those originals:

```python
# Both paths resolve to the same objects:
from pykaraoke.core.database import SongDB          # legacy
from pykaraoke.infrastructure.database.database import SongDB  # layered
```

In a future cleanup phase the implementation will be migrated into the
layered modules and the legacy paths will become thin compatibility
wrappers.

## Dependency Flow

```
config
infrastructure
domain
application
interfaces                                        
```

No layer may depend on a layer above it.  

`config/` is a leaf dependency imported by all layers.

## Tauri Integration

The Tauri desktop build uses PyInstaller (`backend.spec`) to compile the
Python backend into a standalone `backend.exe` (~12 MB).  The staging
script (`scripts/stage-backend.js`) runs PyInstaller and places the
result in `src-tauri/backend/`, which the Tauri resource glob
(`backend/**`) bundles into the installer.

The Rust launcher (`src/main.rs`) checks for `backend.exe` first
(production), then falls back to finding a Python interpreter (dev mode).


```
pykaraoke-ng/
├── src/
│   ├── pykaraoke/              # Core Python package
│   │   ├── players/            # Format-specific players
│   │   │   ├── cdg.py          #   CD+G player
│   │   │   ├── cdg_aux.py      #   CD+G rendering helpers
│   │   │   ├── kar.py          #   MIDI / KAR player
│   │   │   └── mpg.py          #   MPEG video player
│   │   ├── core/               # Business logic
│   │   │   ├── backend.py      #   Headless backend service (stdio + HTTP)
│   │   │   ├── database.py     #   Song database & library scanning
│   │   │   ├── filename_parser.py  # Artist–title extraction from filenames
│   │   │   ├── manager.py      #   Playback manager / coordinator
│   │   │   ├── performer_prompt.py # Performer queue UI
│   │   │   └── player.py       #   Base player class
│   │   ├── config/             # Configuration
│   │   │   ├── constants.py    #   Application constants
│   │   │   ├── environment.py  #   Platform detection
│   │   │   └── version.py      #   Version string
│   │   └── native/             # C extensions
│   │       ├── _cpuctrl.c
│   │       └── _pycdgAux.c
│   └── runtimes/
│       └── tauri/              # Tauri desktop app
│           ├── src/            #   Web frontend (HTML/CSS/JS)
│           └── src-tauri/      #   Rust backend
├── tests/
│   ├── pykaraoke/              # Unit tests (mirrors src/)
│   ├── integration/            # End-to-end tests
│   ├── manual/                 # Manual / environment-dependent tests
│   └── fixtures/               # Test data (UltraStar songs, etc.)
├── docs/                       # Documentation
│   ├── architecture/           # Design & structure
│   ├── development/            # Quality & tooling guides
│   └── issues/                 # Legacy issue tracker
├── deploy/
│   ├── docker/                 # Dockerfile & docker-compose.yml
│   ├── kubernetes/             # K8s manifests
│   └── install/                # Platform-specific install scripts
├── assets/
│   ├── fonts/                  # DejaVu fonts
│   └── icons/                  # App icons
├── scripts/                    # Dev & CI helper scripts
├── pyproject.toml              # Package metadata & dependencies
└── README.md                   # Project overview
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `core/backend.py` | Headless service — stdio and HTTP transports |
| `core/database.py` | SQLite song database, library scanning, settings |
| `core/filename_parser.py` | Extracts artist and title from filenames |
| `core/manager.py` | Coordinates playback, queues, and settings |
| `players/cdg.py` | CD+G format playback (with `cdg_aux.py`) |
| `players/kar.py` | MIDI / KAR playback with lyrics |
| `players/mpg.py` | MPEG / AVI video playback |
| `config/constants.py` | Shared constants and enums |
| `config/environment.py` | OS and platform detection |

## Imports

```python
from pykaraoke.players import cdg, kar, mpg
from pykaraoke.core import backend, database, manager
from pykaraoke.config import constants, version, environment
```
