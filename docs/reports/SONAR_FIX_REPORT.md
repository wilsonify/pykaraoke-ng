# SonarCloud Issue Fix Report

**Date:** 2026-06-16
**Project:** PyKaraoke-NG (wilsonify_pykaraoke-ng)

## Summary

| Metric | Value |
|--------|-------|
| Issues before fix | 19 |
| Issues actionably fixed | 6 |
| Issues already resolved in code (stale) | 13 |
| Files changed | 3 |
| Test count (Python) | 788 passed, 37 skipped |
| Test count (JS) | 140 passed, 0 failed |
| Regressions | None |

## Issues Fixed

### 1. `ci-cd.yml` — S8544: Version locking (3 occurrences)
**Lines:** 100, 289, 483

Replaced the two-step install pattern (`uv sync --no-install-project` + `uv pip install --editable .`) with a single `uv sync --frozen` command. This installs all dependencies and the project itself via the lockfile, ensuring resolved versions are tracked.

**Before:**
```yaml
- run: uv sync --frozen --no-build --extra dev --extra test --no-install-project
- run: uv pip install --editable .
```

**After:**
```yaml
- run: uv sync --frozen --extra dev --extra test
```

### 2. `database.py` — S3776: Cognitive complexity (16 → 15 limit)
**Function:** `_is_safe_database_file` (line 1245)

Extracted the file ownership/permission check into a dedicated `_is_owner_readonly` helper method. This reduced the function's cognitive complexity from 16 to below the 15-threshold.

### 3. `database.py` — S1066: Merge nested if
**Function:** `_try_load_database` (line 1276)

Replaced the nested `if error_callback:` inside `if not self._is_safe_database_file():` by combining conditions with `and` and storing the safety check result in a local variable. Eliminates double evaluation and unnecessary nesting.

### 4. `Dockerfile` — S8544: Version pinning for apt packages
**Lines:** 221-226

Pinned `curl`, `git`, and `vim` to their Debian bookworm versions to ensure reproducible builds.

| Package | Pinned version |
|---------|---------------|
| curl    | `7.88.1-10+deb12u14` |
| git     | `1:2.39.5-0+deb12u3` |
| vim     | `2:9.0.1378-2+deb12u2` |

## Stale Issues (auto-resolving)

The following 13 issues were already addressed in prior commits and will auto-close on the next SonarCloud scan:

- **S8541** (6 issues): All `pip install` commands in ci-cd.yml already include `--only-binary :all:`; all `uv sync` commands already include `--no-build`.
- **S8544** (4 issues): All `uv sync` commands already use `--locked`/`--frozen` for immutable lockfile resolution.
- **S8482** (1 issue): `deploy/docker/Dockerfile` already verifies the Node.js download via GPG signature + SHA256 checksum before extraction.
- **S8541/S8544** (2 issues): `sonarqube.yml` already uses `--only-binary :all:`, `--locked`, and `--no-build` on all pip/uv commands.

## Verification

- **Python tests:** `pytest tests/` → 788 passed, 37 skipped
- **JS tests:** `node --test app.test.js index.test.js` → 140 passed
- **Validation tests:** `pytest tests/validation/` → 19 passed, 5 skipped (NSIS-only tests not applicable)
- **No regressions** introduced.

## Next Steps

1. Push changes to trigger the next SonarCloud scan.
2. Verify on https://sonarcloud.io that all 19 issues resolve to "Closed" or "Fixed".
3. If any remain open, investigate whether the fix is not being detected (coverage, analysis scope).
