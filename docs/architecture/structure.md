# Repository Structure

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

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
