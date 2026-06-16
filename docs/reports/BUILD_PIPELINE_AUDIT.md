# PyKaraoke NG — Build Pipeline Audit

**Date**: 2026-06-16  
**Audit Scope**: All build, packaging, CI/CD, and installer workflows  
**Status**: Migration complete — Rust-native engine replaces Python backend

---

## 1. Current Pipeline Architecture (Rust-Native)

```
Source (crates/pykaraoke-engine/)    Source (src/runtimes/tauri/)
        │                                      │
  cargo build — workspace              tauri build (cargo build)
        │                                      │
  pykaraoke-engine.dll        ┌────────┴────────┐
        │                     │                 │
        └─────────┬───────────┘    [stage-rust-backend.js]
                  │                 copies binary to resources/
                  │
          tauri build (cargo build + bundling)
                  │
       ┌──────────┼──────────┐
       │          │          │
    .deb        .exe       .dmg
    (Linux)   (Windows)   (macOS)
```

## 2. Files in the Build Pipeline

| File | Role | Status |
|------|------|--------|
| `pyproject.toml` | Python package metadata, deps, build config | **Keep** (Python lib still used for reference) |
| `setup.py` | Legacy distutils build (C extension) | **Archived** (not used) |
| `setup.cfg` | Legacy RPM build config | **Archived** (not used) |
| `MANIFEST.in` | Legacy sdist manifest | **Archived** (not used) |
| `backend.spec` | PyInstaller spec for backend.exe | **Removed** |
| `scripts/stage-backend.js` | PyInstaller build runner | **Removed** |
| `scripts/stage-rust-backend.js` | Rust engine staging script | **Active** |
| `src-tauri/build.rs` | Build script | **Simplified** — just `tauri_build::build()` |
| `src-tauri/tauri.conf.json` | Tauri app config | **Active** — resources: `resources/**` |
| `src-tauri/src/main.rs` | Tauri shell | **Active** — in-process Rust engine |
| `src-tauri/Cargo.toml` | Tauri Rust deps | **Active** — depends on `pykaraoke-engine` |
| `Cargo.toml` (workspace root) | Rust workspace | **Active** — engine member, Tauri excluded |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline | **Active** — Rust-native pipeline |
| `tests/validation/conftest.py` | Artifact validation | **Active** — Rust binary resolution |
| `tests/validation/test_artifact_backend.py` | Backend artifact tests | **Active** — Rust engine tests |
| `tests/validation/test_artifact_installer.py` | Installer content tests | **Active** — Rust binary validation |
| `tests/integration/test_tauri_packaging.py` | Packaging regression | **Active** — updated assertions |
| `deploy/install/windows/installer.nsi` | Legacy NSIS installer | **Archived** (Tauri generates NSIS) |
| `deploy/install/linux/*` | Legacy shell launchers | **Archived** |
| `deploy/install/gp2x/*` | Legacy GP2X scripts | **Archived** |

## 3. Python Backend Dependencies — Status

| Dependency | Used By | Status |
|------------|---------|--------|
| `pygame>=2.5.0` | Runtime engine, players | **Still needed** (Rust CDG decoder not production-ready) |
| `numpy>=1.24.0` | Audio processing | **Optional** (not used by Rust backend) |
| `mutagen>=1.47.0` | Metadata reading | **Optional** (not used by Rust backend) |
| `fastapi>=0.104.0` | HTTP API | **Optional** (not yet in Rust) |
| `uvicorn>=0.24.0` | HTTP server | **Optional** |
| PyInstaller | backend.exe build | **Removed** |
| SDL (C extension) | `_pycdgAux` | **Optional** |

## 4. CI/CD Cost Savings Realized

| Item | Before | After | Savings |
|------|--------|-------|---------|
| Python venv creation | ~30s per job | 0s | ~30s ✓ |
| PyInstaller build | ~120s per Windows build | 0s | ~120s ✓ |
| `uv sync` dependencies | ~45s per job | 0s for Rust jobs | ~45s ✓ |
| NumPy/pygame/mutagen download | ~60s per job | 0s | ~60s ✓ |
| `backend/_internal/` size | ~150 MB | 0 | ~150 MB ✓ |
| NSIS installer size | ~180 MB (with Python runtime) | ~30 MB (Rust binary) | ~150 MB ✓ |

## 5. Cleanup Completed

The following stale Python backend artifacts have been removed from the repository:

| Artifact | Removed |
|----------|---------|
| `backend.spec` | ✓ |
| `scripts/stage-backend.js` | ✓ |
| `src/runtimes/tauri/src-tauri/backend/` (directory + `backend.exe` + `_internal/`) | ✓ |
| `app.test.js` assertion for old script name | ✓ Fixed |
| `tauri-packaging.steps.ts` assertion for old script name | ✓ Fixed |
| `pytest.ini` marker description | ✓ Fixed |
| Documentation still referencing old pipeline | See `docs/` for remaining updates needed |
