# Task Breakdown Template

> **Command:** `/speckit.tasks`
> **Purpose:** Break the plan into atomic, ordered implementation tasks.
> **Input:** Completed `plan.md`.
> **Rule:** First task is always a failing test. Last tasks are always
>           documentation, CI validation, and Sonar validation.

---

## Feature Reference

_[Link to `plan.md` or feature name]_

## Tasks

### Phase 1: Test Scaffolding

- [ ] **T01** — Write failing unit tests for the core happy path
- [ ] **T02** — Write failing unit tests for all edge cases (parameterized)
- [ ] **T03** — Write failing unit tests for error/failure modes

### Phase 2: Implementation

- [ ] **T04** — Implement core logic to pass happy-path tests
- [ ] **T05** — Implement edge-case handling to pass all parameterized tests
- [ ] **T06** — Implement error handling to pass failure-mode tests

### Phase 3: Refactor

- [ ] **T07** — Refactor for clarity, DRY, and adherence to constitution
- [ ] **T08** — Add/verify full type annotations (`mypy --strict`)
- [ ] **T09** — Run ruff and fix any lint violations

### Phase 4: Integration

- [ ] **T10** — Write integration tests verifying end-to-end behavior
- [ ] **T11** — Verify cross-platform compatibility (path handling, etc.)

### Phase 4b: Build / Packaging _(if applicable)_

- [ ] **T12** — Verify build commands are cross-platform (no bare `bash`/`cp`/`rm`)
- [ ] **T13** — Validate relative paths resolve correctly from the actual CWD
- [ ] **T14** — Run `act -j build --matrix platform:linux` locally and confirm success
- [ ] **T15** — Confirm integration tests validate **effects**, not command strings
- [ ] **T16** — If CI workflow changed, dry-run with `act -n` on all modified jobs

### Phase 5: Documentation & Validation

- [ ] **T17** — Update module/function docstrings
- [ ] **T18** — Update user-facing documentation if needed
- [ ] **T19** — Run full CI pipeline and confirm all stages pass
- [ ] **T20** — Verify SonarQube quality gate passes (0 new issues)
- [ ] **T21** — Complete `/speckit.checklist` — all items green

## Estimated Effort

_[S/M/L per phase, or story points]_
