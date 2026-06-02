# Build Audit

Date: 2026-06-02
Scope: Repository-wide engineering audit from a Windows host shell.

## Repository Structure Overview
- Core Python package: src/pykaraoke
- Desktop runtime: src/runtimes/tauri (frontend + Rust backend)
- Tests: tests/pykaraoke, tests/integration, tests/manual
- Deployment artifacts: deploy/docker, deploy/kubernetes, deploy/install
- Automation: scripts, .github/workflows
- Documentation: README.md, ARCHITECTURE.md, docs/*, specs/*

## Dependency Inventory
- Python runtime deps (pyproject): pygame, numpy, mutagen
- Optional Python deps: fastapi, uvicorn, pytest stack, selenium, mypy, ruff, mkdocs
- Build backend: hatchling
- Rust deps: managed by Cargo.toml under src/runtimes/tauri/src-tauri
- Node deps: runtime/frontend test deps under src/runtimes/tauri/src and src/runtimes/tauri/e2e

## Build Inventory
- Python package build: python -m build (validated successful)
- Editable install: pip install -e ".[dev,test,http]" (validated on Python 3.13)
- Tauri build path: tauri build --bundles ... (defined in CI, not executed locally)
- Docker build paths: multi-stage Dockerfile with backend, ui, test, tauri targets

## Runtime Inventory
- Python CLI entrypoints: pycdg, pykar, pympg
- HTTP backend mode: pykaraoke.core.backend --http
- Stdio backend mode: pykaraoke.core.backend --stdio
- Tauri desktop app: src/runtimes/tauri/src-tauri

## Configuration Inventory
- Primary config files: pyproject.toml, pytest.ini, sonar-project.properties
- Environment variables observed:
  - PYKARAOKE_API_HOST, PYKARAOKE_API_PORT, BACKEND_MODE
  - PYKARAOKE_DIR, PYKARAOKE_TEMP_DIR
  - PYKARAOKE_API_URL, SONGS_DIR, SELENIUM_URL, UI_URL
  - SONARQUBE_TOKEN, SONARQUBE_HOST_URL, TAURI_PRIVATE_KEY, TAURI_KEY_PASSWORD
- Config sources: env vars, CLI args, workflow secrets, docker-compose env blocks

## Technical Debt Inventory
- Ruff lint currently reports large existing style debt in tests (not fully remediated in this pass)
- Legacy packaging path (setup.py/distutils) coexists with modern pyproject build flow
- Some integration tests depend on external services but did not consistently self-skip before this remediation

## TODO/FIXME Inventory
- src/runtimes/tauri/e2e/steps/database-scan.steps.ts: TODO about pygame-unavailable environments
- deploy/docker/.dockerignore: literal "!TODO" marker

## Dead Code Inventory (Candidates)
- setup.py appears legacy relative to active hatchling build path
- Staged backend tree under src/runtimes/tauri/src-tauri/backend may contain generated/copy artifacts that can drift from src/pykaraoke

## Unused Asset Inventory (Heuristic)
- Potentially unreferenced files by filename scan:
  - assets/icons/note.ico
  - assets/icons/splash.xcf (likely source asset; may be intentionally retained)

## Risk Assessment
- HIGH: Local deployment/runtime validation blocked by missing Docker CLI in this environment
- MEDIUM: Security findings from bandit around pickle deserialization and broad default bind host
- MEDIUM: Integration and E2E confidence depends on containerized services not available in this local session
- LOW: Python package ecosystem vulnerability scan returned no known CVEs for third-party deps

## Fixes Implemented During Audit
- Added cross-platform Python environment handling and Docker Compose detection improvement in scripts/run-tests.sh
- Added build package to dev dependency sets in pyproject.toml
- Fixed manual backend mode tests to preserve environment on subprocess spawn (Windows-compatible)
- Hardened Selenium integration fixture to skip cleanly when Selenium host is unavailable
- Restored defensive Tauri API fallback symbols in src/runtimes/tauri/src/app.js to satisfy packaging regression contract

