# Spec Kit — Developer Workflow Guide

> **Audience:** All PyKaraoke-NG contributors
> **Governance:** [constitution.md](constitution.md)
> **Version:** 1.0.0

---

## Overview

PyKaraoke-NG uses **Spec-Driven Development** via Spec Kit. Every feature,
bug fix, or significant refactor follows a structured workflow that ensures
clarity, traceability, and quality before code is written.

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  /speckit.   │   │  /speckit.   │   │  /speckit.   │   │  /speckit.   │
│   specify    │──▶│   clarify    │──▶│    plan      │──▶│   tasks      │
│  (WHAT/WHY)  │   │  (RISKS)     │   │  (HOW)       │   │  (STEPS)     │
└─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘
                                                              │
                                                              ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   RELEASE    │   │  /speckit.   │   │     CI       │   │    TDD       │
│  (merge to   │◀──│  checklist   │◀──│  (all gates  │◀──│ Red → Green  │
│   main)      │   │  (VERIFY)    │   │   pass)      │   │  → Refactor  │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Step 0: Initialize a Feature Branch

### Using the helper script (recommended)

```bash
# Linux / macOS
./specs/ci/new-feature.sh "improve filename parser edge cases"

# This creates:
#   Branch: 001-filename-parser-edge-cases
#   Directory: specs/features/001-filename-parser-edge-cases/
#   Files: spec.md, clarify.md, plan.md, tasks.md, checklist.md (from templates)
```

### Manual creation

```bash
# 1. Check the next available ID
cat specs/features/.next-id   # e.g., outputs "2"

# 2. Create branch
git checkout -b 002-structured-logging

# 3. Scaffold directory
mkdir -p specs/features/002-structured-logging
cp specs/templates/feature-spec.md   specs/features/002-structured-logging/spec.md
cp specs/templates/clarification.md  specs/features/002-structured-logging/clarify.md
cp specs/templates/technical-plan.md specs/features/002-structured-logging/plan.md
cp specs/templates/task-breakdown.md specs/features/002-structured-logging/tasks.md

# 4. Increment the counter
echo 3 > specs/features/.next-id
```

### Branch naming convention

```
NNN-short-kebab-case-description
 │
 └── Zero-padded 3-digit sequential number
```

**Enforced in CI.** Branches that don't match this pattern will fail the
spec-validation gate on pull requests.

---

## Step 1: Specify — `/speckit.specify`

**Write** `specs/features/NNN-name/spec.md`

Focus exclusively on **WHAT** and **WHY**:

- What problem does this solve?
- Who is affected?
- What is the desired outcome?
- What edge cases exist?
- What failure modes are possible?
- What are the acceptance criteria?

**Rules:**
- ❌ Do NOT mention technology, libraries, or implementation.
- ❌ Do NOT describe HOW to solve the problem.
- ✅ Write from the user's perspective.
- ✅ Be specific about edge cases and failure modes.

### Example command

```
/speckit.specify Improve filename parsing for artist/title extraction
                 with full edge-case handling
```

→ See [001-filename-parser-edge-cases/spec.md](features/001-filename-parser-edge-cases/spec.md) for a complete example.

---

## Step 2: Clarify — `/speckit.clarify`

**Write** `specs/features/NNN-name/clarify.md`

Surface cross-cutting concerns:

- **Security** — Input validation, injection, path traversal
- **Performance** — Latency budgets, bulk operations
- **Cross-platform** — Filesystem differences, path handling
- **Backward compatibility** — API changes, migration needs
- **Dependencies** — New libraries needed?
- **Ambiguities** — Anything unclear in the spec?
- **Risks** — What could go wrong?

### Example command

```
/speckit.clarify 001-filename-parser-edge-cases
  --focus security,performance,cross-platform,backward-compatibility
```

→ See [001-filename-parser-edge-cases/clarify.md](features/001-filename-parser-edge-cases/clarify.md)

---

## Step 3: Plan — `/speckit.plan`

**Write** `specs/features/NNN-name/plan.md`

NOW specify the technical approach:

- Language and stack
- Architecture and data flow
- Files to create/modify
- Data structures
- Algorithm/strategy
- Testing strategy and coverage target
- Error handling approach

### Example command

```
/speckit.plan 001-filename-parser-edge-cases
  --language python
  --typing strict
  --testing pytest --parameterized
  --strategy regex
  --no-third-party
  --coverage-target 95
```

→ See [001-filename-parser-edge-cases/plan.md](features/001-filename-parser-edge-cases/plan.md)

---

## Step 4: Tasks — `/speckit.tasks`

**Write** `specs/features/NNN-name/tasks.md`

Break the plan into atomic, ordered tasks:

1. **Phase 1: Test Scaffolding (Red)** — Write ALL failing tests first
2. **Phase 2: Implementation (Green)** — Minimal code to pass tests
3. **Phase 3: Refactor** — Clean up, types, lint
4. **Phase 4: Integration** — Cross-module and cross-platform verification
5. **Phase 5: Documentation & Validation** — Docs, CI, Sonar, checklist

### Example command

```
/speckit.tasks 001-filename-parser-edge-cases
```

→ See [001-filename-parser-edge-cases/tasks.md](features/001-filename-parser-edge-cases/tasks.md)

---

## Step 5: Implement (TDD)

Follow the task list strictly:

```bash
# Start with failing tests
pytest tests/pykaraoke/core/test_filename_parser.py -v
# → RED: tests fail

# Write minimal implementation
# → GREEN: tests pass

# Refactor
mypy --strict src/pykaraoke/core/filename_parser.py
ruff check src/pykaraoke/core/filename_parser.py
ruff format src/pykaraoke/core/filename_parser.py
```

**Constitutional requirement:** No production code exists without a failing
test that motivated it.

---

## Step 6: Validate — `/speckit.checklist`

**Write** `specs/features/NNN-name/checklist.md`

Check every item:

```markdown
- [x] All spec artifacts reviewed
- [x] All tasks completed
- [x] All tests pass
- [x] mypy --strict passes
- [x] ruff check passes
- [x] CI pipeline passes
- [x] SonarQube quality gate passes
- [x] Build matrix passes on all platforms (linux, windows, macos)
- [x] No shell-specific commands in cross-platform build config
- [x] Integration tests validate effects, not literal command strings
- [x] Code reviewed and approved
```

**CI enforces this.** The `spec-validation` job parses the checklist and
blocks merge if any item is unchecked.

### Example command

```
/speckit.checklist 001-filename-parser-edge-cases
```

→ See [001-filename-parser-edge-cases/checklist.md](features/001-filename-parser-edge-cases/checklist.md)

---

## Step 7: Open Pull Request

```bash
git push -u origin 001-filename-parser-edge-cases
# Open PR on GitHub
```

PR description should reference the spec:

```markdown
## Spec Reference
- Spec: specs/features/001-filename-parser-edge-cases/spec.md
- Plan: specs/features/001-filename-parser-edge-cases/plan.md

## Summary
[Brief description of changes]

## Checklist
All items in specs/features/001-filename-parser-edge-cases/checklist.md are ✅
```

### CI Pipeline on PR

```
spec-validation ──┐
unit-tests-python ─┼─► sonarqube ─► integration-tests ─► build ─► e2e-tests
unit-tests-rust   ─┤
unit-tests-frontend┘
```

ALL jobs must pass. The `spec-validation` job:
1. Checks branch name matches `NNN-feature-name`
2. Verifies all 5 spec artifacts exist
3. Parses `checklist.md` — all items must be `[x]`

---

## Step 8: After Merge — Archive

After the PR merges to `main`:

```bash
# On main branch
git checkout main
git pull
mv specs/features/001-filename-parser-edge-cases/ specs/archive/
git add specs/archive/001-filename-parser-edge-cases/
git commit -m "chore(specs): archive 001-filename-parser-edge-cases"
git push
```

---

## Preventing Bypass

### GitHub Branch Protection Rules (recommended)

Configure on GitHub → Settings → Branches → `main`:

1. **Require pull request reviews before merging** — 1 approval minimum
2. **Require status checks to pass before merging:**
   - `Spec Kit Validation`
   - `Unit Tests / Python`
   - `Unit Tests / Rust`
   - `Unit Tests / Frontend`
   - `SonarQube Analysis`
   - `Integration Tests`
3. **Require branches to be up to date before merging**
4. **Require linear history** (no merge commits)
5. **Do not allow bypassing the above settings** (even for admins)

### Pre-push Git Hook (optional local enforcement)

Add to `.git/hooks/pre-push`:

```bash
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    ./specs/ci/validate-spec-completion.sh "$BRANCH" || exit 1
fi
```

---

## Quick Reference

| Action | Command | Output |
|--------|---------|--------|
| New feature | `./specs/ci/new-feature.sh "description"` | Branch + scaffold |
| Specify | `/speckit.specify` | `spec.md` |
| Clarify | `/speckit.clarify` | `clarify.md` |
| Plan | `/speckit.plan` | `plan.md` |
| Tasks | `/speckit.tasks` | `tasks.md` |
| Checklist | `/speckit.checklist` | `checklist.md` |
| Validate | `./specs/ci/validate-spec-completion.sh` | Pass/fail |
| Archive | `mv specs/features/NNN-*/ specs/archive/` | — |
