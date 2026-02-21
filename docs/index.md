# 🎤 PyKaraoke-NG

A free, open-source karaoke player for Linux, Windows, and macOS.

---

**[User Guide](users.md)** · **[Developer Guide](developers.md)** · **[Admin Guide](administrators.md)** · **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## Features

| 🎵 Multiple Formats | 📚 Song Database | 🖥️ Cross-Platform | 🚀 Desktop App |
|---------------------|------------------|-------------------|----------------|
| CDG+MP3, MIDI/KAR, MPEG video | Automatically catalog and search | Linux, Windows, macOS | Tauri (Rust + web UI) |

## Quick Start

```bash
# Install
uv pip install pykaraoke-ng   # or: pip install pykaraoke-ng

# Play files directly
pycdg song.cdg
pykar song.kar
pympg song.mpg
```

For development setup, see the **[Quick Start Guide](quickstart.md)**.

## Supported Formats

| Format | Extensions | Player | Description |
|--------|-----------|--------|-------------|
| CD+G | `.cdg` + `.mp3` | pycdg | Standard karaoke with graphics |
| MIDI Karaoke | `.kar`, `.mid` | pykar | MIDI with embedded lyrics |
| MPEG Video | `.mpg`, `.mpeg`, `.avi`, `.divx`, `.xvid` | pympg | Video karaoke |

## Documentation

### Guides

- **[User Guide](users.md)** — Install and use PyKaraoke-NG
- **[Developer Guide](developers.md)** — Set up development and contribute
- **[Admin Guide](administrators.md)** — Deploy with Docker, Kubernetes, or Tauri
- **[Quick Start](quickstart.md)** — Fast setup after cloning

### Architecture

- **[Overview](architecture/overview.md)** — System design and communication protocol
- **[Repository Structure](architecture/structure.md)** — Project layout and key modules
- **[Next Steps](architecture/next-steps.md)** — Open work and future features
- **[Reorganization](architecture/reorganization.md)** — Historical record of the repo restructuring

### Reference

- **[Backend Modes](backend-modes.md)** — stdio and HTTP API documentation
- **[SonarQube Setup](development/sonarqube-setup.md)** — Code quality scanning
- **[Quality Improvements](development/quality-improvements.md)** — Python 3 migration and security fixes
- **[Legacy Issues](issues/README.md)** — Issues from the original PyKaraoke project

### Historical

- **[Changelog](changelog.txt)** — Version history (pre-NG)
- **[Legacy README](readme-legacy.txt)** — Original project documentation

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
