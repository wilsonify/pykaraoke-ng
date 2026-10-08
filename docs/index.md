# PyKaraoke-NG

A slim, keyboard-driven karaoke queue manager for working DJs.
Linux, Windows, macOS.

---

**[User Guide](users.md)** · **[Developer Guide](developers.md)** · **[Quick Start](quickstart.md)** · **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## What It Is

PyKaraoke-NG is a desktop karaoke application that sits beside your DJ
software. It occupies a narrow strip of screen (300–450 px), searches
and queues songs via keyboard, and stays out of the way during a live set.

**A professional utility panel — not a full-screen media player.**

Two ways to run it:
- **Desktop app** — Tauri native window embedding `web/index.html`.
  Pre-built installers for Windows (NSIS), macOS (DMG), Linux (deb).
- **Browser** — serve `web/` and open it; folder picking uses the
  directory file input. Same page, same engine.

Both execute the pure-Python engine as WebAssembly (Pyodide) inside the
page — there is no backend process, service, or API server.

## Supported Formats

| Format | Extensions | Audio |
|--------|-----------|-------|
| CD+G | `.cdg` + `.mp3`/`.wav`/`.ogg` | Separate audio file required |
| MIDI Karaoke | `.kar`, `.mid` | Built-in MIDI synthesis |
| LRC lyrics | `.lrc`, `.lcr` + audio | Separate audio file; optional `.elrc` word timing and duet part tags |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Embedded audio track |

## Quick Start

```bash
# Download a pre-built installer from GitHub Releases and run it.
# Or build from source:
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
./scripts/setup-dev-env.sh
./scripts/run-tests.sh
```

Full setup instructions: [Quick Start](quickstart.md).

## Documentation

### By Audience

| Guide | For |
|-------|-----|
| **[User Guide](users.md)** | Installing the desktop app, setting up a song library, running a show |
| **[Developer Guide](developers.md)** | Cloning, testing, building, contributing |

### Architecture

| Document | What it covers |
|----------|---------------|
| [Architecture Overview](architecture/overview.md) | Layers, JS↔Python boundary, Tauri surface |
| [UX Design Spec](../specs/ux-design.md) | Slim sidebar design rationale |

### Development

| Document | What it covers |
|----------|---------------|
| [Quick Start](quickstart.md) | Running from a clone in under a minute |

### Reference

- [Project Constitution](../specs/constitution.md) — Engineering invariants

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
