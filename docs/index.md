# 🎤 PyKaraoke-NG

A free, open-source karaoke player for Linux, Windows, and macOS

---

**[User Guide](users.md)** | **[Developer Guide](developers.md)** | **[Admin Guide](administrators.md)** | **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## Features

| 🎵 Multiple Formats | 📚 Song Database | 🖥️ Cross-Platform | 🚀 Desktop Apps |
|---------------------|------------------|-------------------|-----------------|
| CDG+MP3, MIDI/KAR, MPEG video | Automatically catalog and search | Linux, Windows, macOS | Electron & Tauri |

## Quick Start

```bash
# Install with pip
pip install pykaraoke-ng

# Or using uv (recommended)
uv pip install pykaraoke-ng

# Run the GUI
pykaraoke

# Play a specific file
pycdg song.cdg
pykar song.kar
pympg song.mpg
```

For detailed setup after cloning, see the **[Quick Start Guide](quickstart.md)**.

## Supported Formats

| Format | Extension | Player | Description |
|--------|-----------|--------|-------------|
| CD+G | .cdg + .mp3 | pycdg | Standard karaoke format with graphics |
| MIDI Karaoke | .kar, .mid | pykar | MIDI files with embedded lyrics |
| MPEG Video | .mpg, .mpeg, .avi | pympg | Video karaoke files |

## Documentation

### By Audience

- **[User Guide](users.md)** - Install and use PyKaraoke-NG
- **[Developer Guide](developers.md)** - Set up development environment and contribute
- **[Admin Guide](administrators.md)** - Deploy with Docker, Kubernetes, Electron, or Tauri
- **[Quick Start](quickstart.md)** - Fast setup after cloning the repository

### Architecture

- **[Overview](architecture/overview.md)** - System architecture and design
- **[Repository Structure](architecture/structure.md)** - Project organization
- **[Migration Guide](architecture/migration-guide.md)** - Migrating from legacy code
- **[Reorganization Plan](architecture/reorganization-plan.md)** - Repository reorganization details
- **[Reorganization Summary](architecture/reorganization-summary.md)** - Summary of changes made
- **[Reorganization Complete](architecture/reorganization-complete.md)** - Final reorganization status

### Development

- **[SonarQube Setup](development/sonarqube-setup.md)** - Code quality scanning setup
- **[Quality Improvements](development/quality-improvements.md)** - Code quality fixes
- **[SonarQube Fixes](development/sonarqube-fixes.md)** - Resolved SonarQube issues
- **[SonarCloud HIGH Issues Fixed](development/sonarcloud-high-issues-fixed.md)** - Security fixes
- **[87 Issues Fixed](development/sonarqube-87-issues-fixed.md)** - Bulk issue resolution
- **[PR Summary](development/pr-summary.md)** - Tauri migration implementation details
- **[TODO](development/todo.txt)** - Planned features and improvements

### Historical

- **[Changelog](changelog.txt)** - Historical version changes
- **[Legacy README](readme-legacy.txt)** - Original project documentation

## License

PyKaraoke-NG is licensed under [LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

