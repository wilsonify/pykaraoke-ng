# PyKaraoke-NG

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL-2.1](https://img.shields.io/badge/License-LGPL%202.1-green.svg)](https://opensource.org/licenses/LGPL-2.1)
[![Tests](https://github.com/wilsonify/pykaraoke-ng/actions/workflows/test.yml/badge.svg)](https://github.com/wilsonify/pykaraoke-ng/actions)

A slim, keyboard-driven karaoke queue manager for working DJs.
Runs as a Tauri desktop panel or a containerised HTTP service.

## Supported Formats

| Format | Extensions |
|--------|------------|
| CD+G | `.cdg` + `.mp3` |
| MIDI Karaoke | `.kar`, `.mid` |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` |

## Quick Start

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
./scripts/setup-dev-env.sh   # create venv, install deps
./scripts/run-tests.sh       # verify everything works
```

### Tauri Desktop App

```bash
cd src/runtimes/tauri
npm install
npm run tauri dev
```

### Command-Line Players

```bash
pip install pykaraoke-ng
pycdg song.cdg
pykar song.kar
pympg song.mpg
```

### Docker

```bash
docker run -p 8080:8080 -e BACKEND_MODE=http pykaraoke-ng:backend
```

## Documentation

| Audience | Guide |
|----------|-------|
| Users | [User Guide](docs/users.md) — installation, controls, troubleshooting |
| Developers | [Developer Guide](docs/developers.md) — setup, testing, contributing |
| Administrators | [Admin Guide](docs/administrators.md) — Docker, Kubernetes, desktop builds |

See also: [Quick Start](docs/quickstart.md) ·
[Architecture](docs/architecture/overview.md) ·
[Backend Modes](docs/backend-modes.md)

## Project Structure

```
pykaraoke-ng/
├── src/pykaraoke/         # Core Python package
├── src/runtimes/tauri/    # Tauri desktop shell (vanilla JS + HTML + CSS)
├── tests/                 # Unit and integration tests
├── docs/                  # User, developer, and admin documentation
├── deploy/                # Docker, Kubernetes, installers
├── specs/                 # Design specs and project constitution
├── scripts/               # Build and development scripts
└── assets/                # Fonts and icons
```

## License

[LGPL-2.1-or-later](COPYING).
Originally created by Kelvin Lawson — see [legacy docs](docs/readme-legacy.txt).
