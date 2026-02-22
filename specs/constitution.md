# PyKaraoke-NG — Project Constitution

> **Version:** 1.0.0
> **Ratified:** 2026-02-22
> **Governance scope:** All code contributed to `wilsonify/pykaraoke-ng`.

---

## 1. Purpose

PyKaraoke-NG is a modern, cross-platform karaoke desktop application built on
a **Tauri** (Rust + Web UI) frontend and a **Python** backend. This
constitution defines the non-negotiable engineering invariants that every
contributor, every pull request, and every CI pipeline run must uphold.

---

## 2. Development Methodology

### 2.1 Test-First Development (TDD) — Mandatory

- **Every** behavioral change begins with a **failing test**.
- Production code exists only to make a failing test pass.
- Refactoring happens only when all tests are green.
- The Red → Green → Refactor cycle is not optional — it is policy.

### 2.2 Spec-Driven Development

- Every feature begins with a written specification (`/speckit.specify`).
- No implementation may start without a completed spec, clarification, and
  technical plan.
- Feature branches must contain their spec artifacts in
  `specs/features/NNN-feature-name/`.

---

## 3. Language and Type Safety

### 3.1 Python

- **Minimum version:** Python 3.13+.
- **Full type annotations** on every public function, method, class, and
  module-level variable. `Any` is forbidden except in explicitly justified
  legacy-interop layers.
- **mypy strict mode** must pass (`--strict` flag, no untyped defs).
- **Ruff** enforces style and lint rules defined in `pyproject.toml`.

### 3.2 Rust (Tauri backend)

- Rust `stable` channel, latest release.
- `#[deny(clippy::all, clippy::pedantic)]` in CI.
- `cargo fmt --check` must pass.
- No `unsafe` without a `// SAFETY:` comment and review approval.

### 3.3 Frontend (Web UI)

- Vanilla JS/HTML/CSS — no framework churn.
- All frontend test files run under `node --test`.

---

## 4. Architectural Invariants

### 4.1 No Global Mutable State

- No module-level mutable variables.
- All state must be encapsulated in classes or passed via function parameters.
- Singletons require explicit justification and review approval.

### 4.2 No GUI Logic in Backend Modules

- `src/pykaraoke/` contains **zero** GUI/rendering/display code.
- All presentation lives in `src/runtimes/tauri/`.
- The backend communicates with frontends only via well-defined APIs (HTTP,
  IPC, CLI).

### 4.3 Separation of Concerns

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **Core** | Parsing, database, playlist, file I/O | `src/pykaraoke/core/` |
| **Config** | Settings, environment, constants | `src/pykaraoke/config/` |
| **Players** | Format-specific playback engines | `src/pykaraoke/players/` |
| **Native** | Platform-specific C extensions | `src/pykaraoke/native/` |
| **Runtime** | Tauri shell, web UI | `src/runtimes/tauri/` |

### 4.4 No Legacy wxPython

- wxPython is **permanently removed**. No imports, no conditional imports, no
  compatibility shims.

### 4.5 Cross-Platform Compatibility

- All file paths must use `pathlib.Path` or `os.path` — never hardcoded
  separators.
- All filename handling must normalise `\\` → `/` before parsing.
- Tests must pass on Linux, macOS, and Windows (CI matrix).

---

## 5. Structured Logging

- All logging uses Python `logging` module with structured context.
- **No** `print()` statements in production code.
- Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` — used correctly.
- Every module defines `logger = logging.getLogger(__name__)` at the top.

---

## 6. Testing Requirements

### 6.1 Coverage

- **Unit test coverage ≥ 90%** for `src/pykaraoke/` (enforced in CI).
- **Per-feature coverage ≥ 95%** for new code in each PR.
- `pytest-cov` with branch coverage enabled.

### 6.2 Test Organization

| Path | Scope |
|------|-------|
| `tests/pykaraoke/` | Unit tests (fast, no I/O) |
| `tests/integration/` | Integration tests (services, filesystem) |
| `tests/manual/` | Manual verification scripts |

### 6.3 Test Markers

All tests must carry an appropriate pytest marker:
`slow`, `requires_pygame`, `requires_display`, `integration`, `e2e`.

### 6.4 Parameterized Tests

- Edge cases must be tested via `@pytest.mark.parametrize`, not copy-pasted
  test functions.

---

## 7. CI/CD Pipeline

### 7.1 Pipeline Stages (in order)

1. **Unit Tests** — Python + Rust + Frontend (parallel)
2. **SonarQube Analysis** — static analysis + quality gate
3. **Integration Tests**
4. **Platform Build Matrix** — Linux, Windows, macOS
5. **End-to-End Tests** — per-platform artifact validation
6. **Release** — semantic version tag + GitHub Release (main only)

### 7.2 Merge Requirements

A pull request **may not merge** unless ALL of the following are true:

- [ ] All unit tests pass on all platforms.
- [ ] SonarQube quality gate passes (no new bugs, no new vulnerabilities,
      no new code smells, coverage ≥ threshold).
- [ ] Integration tests pass.
- [ ] Spec checklist (`/speckit.checklist`) is complete.
- [ ] At least one approving review from a maintainer.
- [ ] Branch name matches `NNN-feature-name` format.
- [ ] No merge commits — rebase only.

### 7.3 SonarQube Quality Gate

- **Zero** new bugs.
- **Zero** new vulnerabilities.
- **Zero** new security hotspots (unreviewed).
- New code coverage ≥ 80%.
- Duplication on new code ≤ 3%.

---

## 8. Versioning and Releases

### 8.1 Semantic Versioning

- Strictly follows [SemVer 2.0.0](https://semver.org/).
- `BREAKING CHANGE` / `feat!:` → major bump.
- `feat:` → minor bump.
- `fix:` / `chore:` / others → patch bump.

### 8.2 Backward Compatibility

- **Public API** (function signatures, CLI arguments, config file format,
  database schema) changes require a **deprecation period of at least one
  minor release**.
- Deprecated APIs must emit a `DeprecationWarning` with a migration message.
- Removing a deprecated API is a **breaking change** → major version bump.

### 8.3 Changelog

- Auto-generated from conventional commit messages.
- Every PR title must follow
  [Conventional Commits](https://www.conventionalcommits.org/).

---

## 9. Dependencies

- **No third-party library** may be added without explicit justification in
  the PR description.
- Runtime dependencies must be cross-platform and maintained.
- Current approved runtime dependencies:
  - `pygame>=2.5.0`
  - `numpy>=1.24.0`
  - `mutagen>=1.47.0`
  - `fastapi>=0.104.0` (optional, HTTP backend)
  - `uvicorn>=0.24.0` (optional, HTTP backend)

---

## 10. Feature Branch Governance

### 10.1 Naming

```
NNN-short-kebab-case-description
```

Sequential three-digit prefix. The counter is tracked in
`specs/features/.next-id`.

### 10.2 Required Artifacts

Before any code is written, the feature branch must contain:

1. `specs/features/NNN-name/spec.md` — Specification
2. `specs/features/NNN-name/clarify.md` — Clarification
3. `specs/features/NNN-name/plan.md` — Technical plan
4. `specs/features/NNN-name/tasks.md` — Task breakdown

Before merge:

5. `specs/features/NNN-name/checklist.md` — Completion checklist (all items ✅)

---

## 11. Amendments

This constitution may be amended by a pull request that:

1. Clearly describes the proposed change and rationale.
2. Receives approval from **all** active maintainers.
3. Passes all CI checks.

The amendment PR title must begin with `constitution:`.
