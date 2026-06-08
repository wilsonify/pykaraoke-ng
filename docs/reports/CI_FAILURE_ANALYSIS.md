# CI Failure Analysis

## Failure 1: Python UI Layout Tests (5 tests)

**Workflow:** ci-cd.yml → unit-tests-python
**Error:** 5 assertion failures in `tests/pykaraoke/test_ui_layout.py`
**Status:** CONFIRMED (reproduced locally)

### Failing Tests

| Test | Expected | Actual | Root Cause |
|------|----------|--------|------------|
| `test_queue_before_progress_bar` | playlist < progress-slider | progress-slider at line 71, playlist at line 85 | HTML now has player (with progress) before queue, per spec |
| `test_queue_before_time_display` | playlist < time-current | Same ordering issue | Same cause |
| `test_clear_playlist_before_progress` | clear-playlist-btn < progress-slider | Same ordering issue | Same cause |
| `test_full_expected_ordering` | clear-> playlist -> progress -> time | Reversed order | Same cause |
| `test_tab_order_queue_before_playback` | playlist < play-btn | play-btn at line 60, playlist at line 85 | Same cause |

**Root Cause:** Python tests were written for the old layout (queue before player). The 002-slim-sidebar-layout spec mandates "Now Playing → Queue" order. The frontend tests enforce this. The Python tests need updating to match.

**Fix:** Update expected order in Python tests to: progress-bar elements BEFORE playlist elements.

---

## Failure 2: pytest: command not found

**Workflow:** ci-cd.yml → unit-tests-python, integration-tests, e2e-tests; sonarqube.yml
**Error:** `pytest: command not found` (exit 127)
**Status:** FIXED (uv run pytest)

**Root Cause:** Switching from `pip install -e` to `uv sync --locked` moved pytest into a uv-managed virtual environment not on system PATH.

**Fix Applied:** Prefixed all 5 pytest invocations with `uv run`.

---

## Failure 3: Frontend Sidebar Layout Tests (2 tests)

**Workflow:** ci-cd.yml → unit-tests-frontend
**Error:** 2 assertion failures in `index.test.js`
**Status:** FIXED

**Root Cause:** `index.html` had queue before player (wrong order per spec), and library controls were not wrapped in `<details>`.

**Fix Applied:** 
- Reordered DOM: player-section before playlist-section
- Wrapped library controls in `<details class="search-filters">`

---

## Failure 4: SonarQube Quality Gate Exit Code 3

**Workflow:** ci-cd.yml → sonarqube, sonarqube.yml → sonarqube
**Error:** `EXECUTION FAILURE` exit code 3 — Quality Gate FAILED
**Status:** PARTIALLY FIXED (sonarqube.yml has continue-on-error; ci-cd.yml still needs it)

**Root Cause:** SonarScanner CLI v8.1.0 checks Quality Gate internally and exits with code 3 when gate fails. The GitHub Actions scan step propagates this exit code, causing job failure.

**Fix Applied:** Added `continue-on-error: true` to sonarqube.yml scan step.
**Fix Needed:** Add same to ci-cd.yml scan step, so the separate QG check action can run.

---

## Failure 5: Tauri Build Fails on Linux/macOS

**Workflow:** ci-cd.yml → build (linux, macos)
**Error:** `stage-backend.js` cannot find Python — exits with code 1
**Status:** UNFIXED (needs cross-platform script)

**Root Cause:** `stage-backend.js` only searches for Windows-style venv paths (`Scripts/python.exe`) and uses `where python`. On Linux/macOS, Python is at `bin/python` and found via `which python`. The script then checks for `backend.exe` which only exists on Windows.

**Fix Needed:** 
- Add Linux/macOS venv paths (`bin/python`)
- Use `which python` as fallback on non-Windows
- Check for platform-appropriate binary name (`backend` or `backend.exe`)

---

## Failure 6: Tauri Resources Not Cross-Platform

**Workflow:** ci-cd.yml → build (all platforms)
**Error:** `tauri.conf.json` lists `backend/backend.exe` as a resource — won't match Linux binary (`backend/backend`)
**Status:** UNFIXED (low severity — `backend/**` glob will catch both)

**Root Cause:** Resource glob `backend/backend.exe` assumes Windows naming.

**Fix Needed:** No fix strictly needed since `backend/**` covers all files, but should be cleaned up for correctness.
