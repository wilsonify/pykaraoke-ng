# PyKaraoke-NG

A slim, keyboard-driven karaoke queue manager for working DJs.
Linux, Windows, macOS.

---

**[User Guide](users.md)** · **[Developer Guide](developers.md)** · **[Admin Guide](administrators.md)** · **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## What It Is

PyKaraoke-NG is a desktop karaoke application designed to sit beside your
primary DJ software. It occupies a narrow strip of screen (300–450 px),
searches and queues songs via keyboard, and stays out of the way during
a live set.

It is a professional utility panel — not a full-screen media player.

## Quick Start

```bash
pip install pykaraoke-ng    # or: uv pip install pykaraoke-ng

pycdg song.cdg              # CD+G
pykar song.kar              # MIDI / KAR
pympg song.mpg              # video
```

For development setup, see the **[Quick Start Guide](quickstart.md)**.

## Supported Formats

| Format | Extensions | Description |
|--------|-----------|-------------|
| CD+G | `.cdg` + `.mp3` | Graphics + audio karaoke |
| MIDI Karaoke | `.kar`, `.mid` | MIDI with embedded lyrics |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Video karaoke |

## Documentation

### By Audience

- **[User Guide](users.md)** — Install, set up a song library, run karaoke
- **[Developer Guide](developers.md)** — Clone, test, contribute
- **[Admin Guide](administrators.md)** — Deploy via Docker, Kubernetes, or Tauri

### Architecture

- **[Overview](architecture/overview.md)** — System design and IPC protocol
- **[Repository Structure](architecture/structure.md)** — Project layout
- **[Backend Modes](backend-modes.md)** — stdio and HTTP API reference

### Development

- **[Integration Testing](development/integration-testing.md)** — Docker-based test orchestration
- **[SonarQube Setup](development/sonarqube-setup.md)** — CI quality scanning
- **[Code Quality History](development/quality-improvements.md)** — Python 3 migration log

### Reference

- **[UX Design Spec](../specs/ux-design.md)** — Slim sidebar design rationale
- **[Project Constitution](../specs/constitution.md)** — Engineering invariants
- **[Open Work](architecture/next-steps.md)** — Backlog and future features
- **[Legacy Issues](issues/README.md)** — Issues from the original PyKaraoke

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
