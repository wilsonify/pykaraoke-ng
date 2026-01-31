# Quick Start Guide - After Reorganization

[← Back to Home](index.md)

---

## For Developers

### Setting Up Your Environment

1. **Clone the repository**:
```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
```

2. **Set PYTHONPATH** (required for development):
```bash
# Add to your ~/.bashrc or ~/.zshrc:
export PYTHONPATH="/path/to/pykaraoke-ng/src:$PYTHONPATH"

# Or set it temporarily in your shell:
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
```

3. **Install dependencies**:
```bash
# Using uv (recommended):
uv sync

# Or using pip:
pip install -e .
```

### Running the Application

**Legacy wxPython GUI**:
```bash
python -m pykaraoke.legacy.pykaraoke
```

**Minimal GUI**:
```bash
python -m pykaraoke.legacy.pykaraoke_mini
```

**Specific Players**:
```bash
# CD+G player
python -m pykaraoke.players.cdg yourfile.cdg

# MIDI/KAR player
python -m pykaraoke.players.kar yourfile.kar

# MPEG player
python -m pykaraoke.players.mpg yourfile.mpg
```

**Backend Service** (for Tauri/Electron):
```bash
python -m pykaraoke.core.backend
```

### Running Tests

```bash
# All tests
PYTHONPATH=src pytest tests/

# Specific test suite
PYTHONPATH=src pytest tests/pykaraoke/config/
PYTHONPATH=src pytest tests/pykaraoke/players/

# With coverage
PYTHONPATH=src pytest tests/ --cov=pykaraoke --cov-report=html
```

### Building

**Python Package**:
```bash
python -m build
```

**Docker Image**:
```bash
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng .
```

**Electron App**:
```bash
cd src/runtimes/electron
npm install
npm run build
```

**Tauri App**:
```bash
cd src/runtimes/tauri
cargo build --release
```

### Development Workflow

1. **Make changes** in `src/pykaraoke/`
2. **Run tests**: `PYTHONPATH=src pytest tests/`
3. **Check linting**: `ruff check src/`
4. **Format code**: `ruff format src/`
5. **Commit** your changes

### Importing in Your Code

```python
# Players
from pykaraoke.players import cdg, kar, mpg

# Core components
from pykaraoke.core import backend, database, manager, player

# Configuration
from pykaraoke.config import constants, version, environment

# Legacy
from pykaraoke.legacy import pykaraoke, pykaraoke_mini
```

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'pykaraoke'`
**Solution**: Set PYTHONPATH to include src directory:
```bash
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
```

**Issue**: Tests fail with import errors
**Solution**: Run pytest with PYTHONPATH:
```bash
PYTHONPATH=src pytest tests/
```

**Issue**: Can't find assets (fonts, icons)
**Solution**: Assets are now in `assets/fonts/` and `assets/icons/`

## For CI/CD

Update your CI scripts to set PYTHONPATH:

```yaml
# GitHub Actions example
env:
  PYTHONPATH: ${{ github.workspace }}/src

# Or in steps:
- name: Run tests
  run: |
    export PYTHONPATH="${GITHUB_WORKSPACE}/src:$PYTHONPATH"
    pytest tests/
```

## Directory Reference

```
src/pykaraoke/          # Main package
├── players/            # Player implementations
├── core/               # Core business logic
├── config/             # Configuration
├── legacy/             # Legacy wxPython code
└── native/             # C extensions

src/runtimes/           # Runtime implementations
├── electron/           # Electron app
└── tauri/              # Tauri app

tests/                  # Test suite
├── pykaraoke/         # Unit tests
└── integration/        # Integration tests

deploy/                 # Deployment files
├── docker/            # Docker configs
├── kubernetes/        # K8s manifests
└── install/           # Install scripts

assets/                 # Static assets
├── fonts/             # Font files
└── icons/             # Icon files

docs/                   # Documentation
├── architecture/      # Architecture docs
└── development/       # Dev guides
```

## More Information

- **STRUCTURE.md**: Detailed structure documentation
- **REORGANIZATION_PLAN.md**: Planning document with rationale
- **REORGANIZATION_SUMMARY.md**: Summary of changes
- **docs/architecture/**: Architecture documentation
- **docs/development/**: Development guides
