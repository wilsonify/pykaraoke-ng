# GitHub Actions Audit

## Workflow Inventory

### 1. `.github/workflows/ci-cd.yml` — CI/CD Pipeline

**Name:** CI/CD Pipeline
**Triggers:** push (main/master), pull_request (opened/synchronize/reopened), workflow_dispatch
**Concurrency:** Grouped by ref; cancels in-progress on PRs only

| Job | OS | Dependencies | Artifacts | Notes |
|-----|----|-------------|-----------|-------|
| `changes` | ubuntu-latest | — | (outputs) | dorny/paths-filter@v3.0.2 |
| `unit-tests-python` | ubuntu-latest | — | python-coverage (coverage.xml, pytest-junit.xml, htmlcov/) | Python 3.12, uv |
| `unit-tests-rust` | ubuntu-22.04 | changes (needs) | — | Conditional on Rust changes; dtolnay/rust-toolchain@stable, Swatinem/rust-cache@v2 |
| `unit-tests-frontend` | ubuntu-latest | — | — | Node.js 20, node --test |
| `spec-validation` | ubuntu-latest | — | — | specs/ci/validate-spec-completion.sh |
| `sonarqube` | ubuntu-latest | unit-tests-python, unit-tests-rust, unit-tests-frontend, spec-validation | — | sonarsource/sonarqube-scan-action@v8.1.0 + sonarqube-quality-gate-action@v1.2.0 |
| `integration-tests` | ubuntu-latest | sonarqube | integration-test-results | xvfb-run + chromium-browser |
| `build` | matrix (3) | integration-tests | tauri-{linux,windows,macos}-{arch} | Tauri v1.6.3 CLI |
| `e2e-tests` | matrix (3) | build | e2e-results-{platform} | pytest + Selenium |
| `bdd-e2e-tests` | ubuntu-latest | build | bdd-e2e-reports | docker-compose + Cucumber.js |
| `release` | ubuntu-latest | e2e-tests, bdd-e2e-tests | GitHub Release | main branch only |

**Required secrets:** SONAR_TOKEN, SONARQUBE_HOST_URL, TAURI_PRIVATE_KEY, TAURI_KEY_PASSWORD

**External actions:**
- actions/checkout@v4
- actions/setup-python@v5
- actions/cache@v4
- actions/upload-artifact@v4
- actions/download-artifact@v4
- dorny/paths-filter@de90cc6fb38fc0963ad72b210f1f284cd68cea36 (v3.0.2)
- dtolnay/rust-toolchain@631a55b12751854ce901bb631d5902ceb48146f7 (stable)
- Swatinem/rust-cache@779680da715d629ac1d338a641029a2f4372abb5 (v2)
- sonarsource/sonarqube-scan-action@7006c4492b2e0ee0f816d36501671557c97f5995 (v8.1.0)
- sonarsource/sonarqube-quality-gate-action@cf038b0e0cdecfa9e56c198bbb7d21d751d62c3b (v1.2.0)
- mathieudutour/github-tag-action@a22cf08638b34d5badda920f9daf6e72c477b07b (v6.2)
- softprops/action-gh-release@c062e08bd532815e2082a85e87e3ef29c3e6d191 (v2.0.8)

### 2. `.github/workflows/sonarqube.yml` — SonarQube Analysis (Manual)

**Name:** SonarQube Analysis (Manual)
**Triggers:** workflow_dispatch only

| Job | OS | Dependencies | Artifacts | Notes |
|-----|----|-------------|-----------|-------|
| `sonarqube` | ubuntu-latest | — | — | Standalone scan; continue-on-error on tests + scan + QG |

**External actions:** Same as ci-cd.yml sonarqube job

### 3. `.github/workflows/pages.yml` — Deploy Documentation

**Name:** Deploy Documentation
**Triggers:** push to main (docs/**), workflow_dispatch
**Concurrency:** "pages" group, no cancel

| Job | OS | Dependencies | Artifacts | Notes |
|-----|----|-------------|-----------|-------|
| `build` | ubuntu-latest | — | upload-pages-artifact | Ruby 3.2 + Jekyll |
| `deploy` | ubuntu-latest | build | — | Deploy to GitHub Pages |

**External actions:**
- ruby/setup-ruby@8d27f39a5e7ad39aebbcbd1324f7af020229645c (v1.287.0)
- actions/configure-pages@v4
- actions/jekyll-build-pages@v1
- actions/upload-pages-artifact@v3
- actions/deploy-pages@v4

### 4. `src/runtimes/tauri/e2e/ci/bdd-e2e.yml` — BDD E2E Snippet (documentation only)

**Status:** NOT an active workflow — it's a reusable snippet/specimen. The actual BDD job is in ci-cd.yml.
**Location:** Outside `.github/workflows/` — GitHub will not execute it.

## Issues Found

### Deprecated Actions
- None detected (all use pinned SHA or major version)

### Floating Action Versions
- `actions/jekyll-build-pages@v1` — v1.x is fine, but unpinned to a SHA

### Cross-Platform Issues
- `stage-backend.js` uses Windows-only `Scripts/python.exe` and `where python` — will fail on Linux/macOS builds
- `stage-backend.js` checks for `backend.exe` (Windows-only) after build
- `tauri.conf.json` resources list `backend/backend.exe` which doesn't exist on Linux/macOS

### Test Conflicts
- Frontend tests assert `player-section` before `playlist-section` (per spec)
- Python tests assert queue before progress bar (opposite of spec)
- Spec says: Search → Filters → Results → **Now Playing → Queue** → Status

### SonarQube Quality Gate
- SonarScanner v8.1.0 bundles QG check internally and exits with code 3 on failure
- ci-cd.yml scan step lacks `continue-on-error: true`, so QG failure blocks the separate QG check step from running

### Build Process
- `stage-backend.js` requires PyInstaller and searches for `python.exe` — no Linux/macOS fallback
- Linux build job will fail at `beforeBuildCommand` stage
- Backend bundling is only needed for Windows; Linux/macOS use system Python

### Workflow Gaps
- `workflow_dispatch` is present on all 3 active workflows ✓
- `concurrency` controls present on ci-cd.yml and pages.yml ✓
- No artifact retention policies set on individual uploads (uses action defaults)
- Release workflow collects `*.msi` but Tauri only produces NSIS (`.exe`) on Windows by default
