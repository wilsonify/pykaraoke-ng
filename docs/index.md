# PyKaraoke-NG

A slim, keyboard-driven karaoke queue manager for working DJs.
Linux, Windows, macOS.

---

**[User Guide](users.md)** · **[Developer Guide](developers.md)** · **[Admin Guide](administrators.md)** · **[Tester Guide](quickstart.md#validation-tests)** · **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## What It Is

PyKaraoke-NG is a desktop karaoke application designed to sit beside your
primary DJ software. It occupies a narrow strip of screen (300–450 px),
searches and queues songs via keyboard, and stays out of the way during
a live set.

It is a professional utility panel — not a full-screen media player.

Two deployment options:
- **Desktop app** — Tauri-based native window with a bundled Python backend.
  Pre-built installers for Windows (NSIS), macOS (DMG), Linux (AppImage/deb).
- **Headless backend** — Python service via stdio or HTTP. Run it directly,
  in Docker, or in Kubernetes. Drive it with any frontend.

## Quick Start (Users)

```bash
# Install pre-built desktop app from GitHub Releases, or:
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync
uv run python -m pykaraoke.core.backend --http   # HTTP API on :8080
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

- **[User Guide](users.md)** — Install the desktop app, set up a song library, run a show
- **[Developer Guide](developers.md)** — Clone, test, build, contribute
- **[Admin Guide](administrators.md)** — Deploy via Docker, Kubernetes, or Tauri desktop builds

### Architecture

- **[Overview](architecture/overview.md)** — System design and IPC protocol
- **[Repository Structure](architecture/structure.md)** — Project layout
- **[Backend Modes](backend-modes.md)** — stdio and HTTP API reference

### Development

- **[Quick Start](quickstart.md)** — Get running from a clone in under a minute
- **[Integration Testing](development/integration-testing.md)** — Docker-based test orchestration
- **[SonarQube Setup](development/sonarqube-setup.md)** — CI quality scanning
- **[Code Quality History](development/quality-improvements.md)** — Python 3 migration log

### Reference

- **[UX Design Spec](../specs/ux-design.md)** — Slim sidebar design rationale
- **[Project Constitution](../specs/constitution.md)** — Engineering invariants
- **[Open Work](architecture/next-steps.md)** — Backlog and future features
- **[Legacy Issues](issues/README.md)** — Issues from the original PyKaraoke

### Reports

- **[Build Audit](reports/BUILD_AUDIT.md)** — Repository build/discovery audit
- **[Test Report](reports/TEST_REPORT.md)** — Full test execution outcomes
- **[Deployment Report](reports/DEPLOYMENT_REPORT.md)** — Deployment artifact validation
- **[CI/CD Report](reports/CICD_REPORT.md)** — Workflow and automation review
- **[Security Report](reports/SECURITY_REPORT.md)** — Security findings and remediation guidance
- **[Reliability Report](reports/RELIABILITY_REPORT.md)** — Resilience fixes and remaining risks
- **[Documentation Report](reports/DOCUMENTATION_REPORT.md)** — Docs accuracy and gaps
- **[E2E Report](reports/E2E_REPORT.md)** — End-to-end validation status
- **[Release Readiness](reports/RELEASE_READINESS.md)** — Release risk assessment

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
