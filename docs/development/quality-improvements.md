# Code Quality Improvements

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

## Overview

The codebase has been modernized from Python 2 to Python 3, all critical security issues have been resolved, and continuous quality monitoring is in place via SonarCloud.

## Python 2 → 3 Migration

| Category | Count | Example |
|----------|-------|---------|
| Print statements | 65+ | `print "text"` → `print("text")` |
| Raise syntax | 9 | `raise Exception, msg` → `raise Exception(msg)` |
| Except syntax | 2 | `except E, e:` → `except E as e:` |
| Long integers | 6 | `0xFFFFFFFFL` → `0xFFFFFFFF` |
| Octal literals | 1 | `0666` → `0o666` |
| Type checks | 4 | `type(x) == unicode` → `isinstance(x, str)` |
| `types.StringType` | 2 | Replaced with `isinstance(x, bytes)` |
| `unicode()` calls | 4 | Replaced with `isinstance(x, bytes)` + `.decode()` |

## Security Fixes

| Issue | Severity | Fix |
|-------|----------|-----|
| Bare `except:` clauses (26) | Critical | Changed to `except Exception:` or specific types |
| `eval()` usage | Critical | Replaced with `ast.literal_eval()` |
| `shell=True` in subprocess | High | Removed; using `shlex.split()` + `shell=False` |
| Hardcoded `/tmp` paths (2) | High | Replaced with `tempfile.gettempdir()` |
| `assert` in production (4) | Medium | Replaced with `if ... raise` |
| Try-except-pass blocks (10) | High | Added specific exception types and comments |

## Code Quality Fixes

| Issue | Count | Fix |
|-------|-------|-----|
| `== None` / `!= None` | 52 | Changed to `is None` / `is not None` |
| `== True` / `== False` | 5 | Removed; using truthiness directly |
| Unused variables | 12 → 4 | Prefixed with `_` or removed |
| Missing format arguments | 7 | Fixed format strings |
| File resource leaks | 5 | Converted to `with` statements |
| Commented-out code | 3 | Removed dead blocks |

## Remaining Non-Critical Issues

These are accepted and tracked for future cleanup:

- **Import-star warnings** (F403/F405, ~182) — would require extensive refactoring
- **Old-style `%` formatting** (UP031, ~74) — stylistic, not a bug
- **Unused callback arguments** (ARG002, ~65) — required by event-handler signatures
- **Complex functions** (C901, ~31) — refactoring planned incrementally

## SonarCloud Integration

See [SonarQube Setup](sonarqube-setup.md) for configuration details.

- **Dashboard:** https://sonarcloud.io/project/overview?id=wilsonify_pykaraoke-ng
- **Runs on:** push to `master`/`main`/`develop` and all PRs
- **Quality gate:** no new critical/blocker issues, no new vulnerabilities
