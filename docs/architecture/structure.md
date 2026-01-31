# PyKaraoke-NG - Repository Structure

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

This document explains the reorganized repository structure.

## Directory Structure

```
pykaraoke-ng/
├── src/                    # All application source code
│   ├── pykaraoke/         # Core Python package (installable)
│   │   ├── players/       # Format-specific players (CDG, KAR, MPG)
│   │   ├── core/          # Core business logic
│   │   ├── config/        # Configuration and environment
│   │   ├── legacy/        # Legacy wxPython implementations
│   │   └── native/        # C extensions
│   └── runtimes/          # Runtime-specific implementations
│       ├── electron/      # Electron desktop runtime
│       └── tauri/         # Tauri desktop runtime
├── tests/                  # Test suite
│   ├── pykaraoke/         # Tests for core package
│   └── integration/       # Integration tests
├── docs/                   # Documentation
│   ├── architecture/      # Architecture documentation
│   └── development/       # Development guides
├── deploy/                 # Deployment configurations
│   ├── docker/            # Docker files
│   ├── kubernetes/        # Kubernetes manifests
│   └── install/           # Installation packages
├── assets/                 # Shared assets
│   ├── fonts/             # Font files
│   └── icons/             # Icon files
├── scripts/                # Build and development scripts
└── [config files]          # Root-level configuration only
```

## Python Package Structure

The core Python code is now organized as a proper package under `src/pykaraoke/`:

- **players/**: Format-specific player implementations
  - `cdg.py` - CD+G player
  - `kar.py` - MIDI/KAR player
  - `mpg.py` - MPEG player
  - `cdg_aux.py` - CD+G auxiliary functions

- **core/**: Core business logic
  - `backend.py` - Headless backend service
  - `player.py` - Playback engine
  - `manager.py` - Manager/coordinator
  - `database.py` - Database & library management
  - `performer_prompt.py` - Performer interface

- **config/**: Configuration modules
  - `constants.py` - Application constants
  - `environment.py` - Environment detection
  - `version.py` - Version information

- **legacy/**: Legacy wxPython implementations
  - `pykaraoke.py` - Original GUI
  - `pykaraoke_mini.py` - Lightweight variant

- **native/**: C extensions for performance
  - `_cpuctrl.c`
  - `_pycdgAux.c`

## Runtime Implementations

Both Electron and Tauri runtimes are now under `src/runtimes/`:

### Electron Runtime (`src/runtimes/electron/`)
- Desktop application using Electron framework
- Wraps Python backend via subprocess
- Web-based UI

### Tauri Runtime (`src/runtimes/tauri/`)
- Desktop application using Tauri framework
- Wraps Python backend via subprocess
- Rust native layer with web UI

## Running the Application

### Development Mode

Set PYTHONPATH to include the src directory:

```bash
export PYTHONPATH=/path/to/pykaraoke-ng:$PYTHONPATH
```

Then run the desired component:

```bash
# Run the backend service
python -m pykaraoke.core.backend

# Run legacy GUI
python -m pykaraoke.legacy.pykaraoke

# Run a specific player
python -m pykaraoke.players.cdg somefile.cdg
```

### Installed Mode

After installation via pip, the package is importable:

```python
from pykaraoke.players import cdg
from pykaraoke.core import backend
from pykaraoke.config import version
```

## Testing

Tests are organized to mirror the source structure:

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/pykaraoke/players/
pytest tests/pykaraoke/core/
pytest tests/integration/
```

## Building

```bash
# Build the Python package
python -m build

# Build Docker image
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .

# Build Electron app
cd src/runtimes/electron
npm install
npm run build

# Build Tauri app
cd src/runtimes/tauri
cargo build
```

## Benefits of New Structure

1. **Clear Separation**: Core logic separated from runtime implementations
2. **Proper Python Package**: Follows Python packaging best practices
3. **Scalable**: Easy to add new players, runtimes, or features
4. **Maintainable**: Related code is grouped logically
5. **Testable**: Tests mirror source structure
6. **Cross-Platform**: Multiple runtimes supported equally
7. **Professional**: Standard structure familiar to developers

## Migration Notes

- Import paths have changed: `import pycdg` → `from pykaraoke.players import cdg`
- Entry points updated in `pyproject.toml`
- CI/CD and deployment configs updated
- All absolute paths updated in configuration files

See `REORGANIZATION_PLAN.md` for detailed migration information.
