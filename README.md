# 🎤 PyKaraoke-NG


[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL-2.1](https://img.shields.io/badge/License-LGPL%202.1-green.svg)](https://opensource.org/licenses/LGPL-2.1)
[![Tests](https://github.com/wilsonify/pykaraoke-ng/actions/workflows/test.yml/badge.svg)](https://github.com/wilsonify/pykaraoke-ng/actions)

A free, open-source karaoke player for Linux, Windows, and macOS.

## Features

- 🎵 **Multiple Formats**: CDG+MP3, MIDI/KAR, MPEG video karaoke files
- 📚 **Song Database**: Automatically catalog and search your library
- 🖥️ **Cross-Platform**: Linux, Windows, macOS support
- 🚀 **Desktop Apps**: Modern Electron and Tauri runtimes

## Quick Start

```bash
# Install from GitHub Releases
pip install https://github.com/wilsonify/pykaraoke-ng/releases/latest/download/pykaraoke_ng-0.0.0-py3-none-any.whl

# Or install from GitHub Packages
pip install pykaraoke-ng --index-url https://ghcr.io/wilsonify/pykaraoke-ng

# Or install from source (recommended for development)
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
pip install -e .

# Run the GUI
pykaraoke

# Play specific files
pycdg song.cdg
pykar song.kar
pympg song.mpg
```

## Documentation

| Audience | Guide |
|----------|-------|
| 👤 **Users** | [User Guide](docs/users.md) - Installation, usage, troubleshooting |
| 💻 **Developers** | [Developer Guide](docs/developers.md) - Development setup, testing, contributing |
| 🔧 **Administrators** | [Admin Guide](docs/administrators.md) - Docker, Kubernetes, desktop deployment |

### Additional Documentation

- [Quick Start Guide](docs/quickstart.md) - Fast setup after cloning
- [Architecture Overview](docs/architecture/overview.md) - System design and architecture
- [Repository Structure](docs/architecture/structure.md) - Project organization
- [Migration Guide](docs/architecture/migration-guide.md) - Guide for migrating from legacy code

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CD+G | `.cdg` + `.mp3` | Standard karaoke format with graphics |
| MIDI Karaoke | `.kar`, `.mid` | MIDI files with embedded lyrics |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Video karaoke files |

## Project Structure

```
pykaraoke-ng/
├── src/
│   ├── pykaraoke/         # Core Python package
│   └── runtimes/          # Desktop apps (Electron, Tauri)
├── tests/                  # Test suite
├── docs/                   # Documentation
├── deploy/                 # Docker, Kubernetes, installers
├── assets/                 # Fonts, icons
└── scripts/                # Build and dev scripts
```

See [Repository Structure](docs/architecture/structure.md) for details.

## Development

```bash
# Clone and setup
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
./scripts/setup-dev-env.sh

# Run tests
./scripts/run-tests.sh

# Code quality
uv run ruff check .
uv run ruff format .
```

**Having trouble with tests?** See [Test Troubleshooting Guide](scripts/troubleshooting-tests.md).

See [Developer Guide](docs/developers.md) for complete setup instructions.

## License

PyKaraoke-NG is licensed under [LGPL-2.1-or-later](COPYING).

Originally created by Kelvin Lawson. See [legacy documentation](docs/readme-legacy.txt) for historical information.
