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
interfaces  ──►  application  ──►  domain
     │                │
     └────►  infrastructure  ──►  domain
                      │
                      └────►  config
```

No layer may depend on a layer above it.  `config/` is a leaf dependency
imported by all layers.

## Tauri Integration

The Tauri runtime bundles the Python backend as a resource
(`src-tauri/backend/`).  The staging script (`scripts/stage-backend.js`)
copies **both** legacy and layered packages so that import paths resolve
correctly at runtime.  The Rust launcher (`src/main.rs`) searches for
`backend_api.py` first, then falls back to `backend.py`.
