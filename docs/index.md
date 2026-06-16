# PyKaraoke-NG

A slim, keyboard-driven karaoke queue manager for working DJs.
Linux, Windows, macOS.

---

**[User Guide](users.md)** · **[Developer Guide](developers.md)** · **[Admin Guide](administrators.md)** · **[Quick Start](quickstart.md)** · **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## What It Is

PyKaraoke-NG is a desktop karaoke application that sits beside your DJ
software. It occupies a narrow strip of screen (300–450 px), searches
and queues songs via keyboard, and stays out of the way during a live set.

**A professional utility panel — not a full-screen media player.**

Two deployment options:
- **Desktop app** — Tauri native window with a bundled Python backend.
  Pre-built installers for Windows (NSIS + MSI), macOS (DMG), Linux (AppImage/deb).
- **Headless backend** — Python service over stdio or HTTP. Run it directly,
  in Docker, or in Kubernetes. Drive it with any frontend.

## Supported Formats

| Format | Extensions | Audio |
|--------|-----------|-------|
| CD+G | `.cdg` + `.mp3`/`.wav`/`.ogg` | Separate audio file required |
| MIDI Karaoke | `.kar`, `.mid` | Built-in MIDI synthesis |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Embedded audio track |

## Quick Start

```bash
# Download a pre-built installer from GitHub Releases and run it.
# Or build from source:
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync
uv run pytest tests/ -v                     # run tests
uv run python -m pykaraoke.core.backend --http  # HTTP API on :8080
```

Full setup instructions: [Quick Start](quickstart.md).

## Documentation

### By Audience

| Guide | For |
|-------|-----|
| **[User Guide](users.md)** | Installing the desktop app, setting up a song library, running a show |
| **[Developer Guide](developers.md)** | Cloning, testing, building, contributing |
| **[Admin Guide](administrators.md)** | Docker, Kubernetes, CI/CD, production Tauri builds |

### Architecture

| Document | What it covers |
|----------|---------------|
| [Architecture Overview](architecture/overview.md) | System design, IPC protocol, state model |
| [Repository Structure](architecture/structure.md) | Project layout, module responsibilities |
| [Backend Modes](backend-modes.md) | stdio and HTTP API reference |
| [UX Design Spec](../specs/ux-design.md) | Slim sidebar design rationale |

### Development

| Document | What it covers |
|----------|---------------|
| [Quick Start](quickstart.md) | Running from a clone in under a minute |
| [Integration Testing](development/integration-testing.md) | Docker-based test orchestration |
| [SonarQube Setup](development/sonarqube-setup.md) | CI quality scanning |
| [Code Quality History](development/quality-improvements.md) | Python 3 migration log |

### Reference

- [Project Constitution](../specs/constitution.md) — Engineering invariants
- [Open Work](architecture/next-steps.md) — Backlog and future features
- [Legacy Issues](issues/README.md) — Issues from the original PyKaraoke

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
