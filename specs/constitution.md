# PyKaraoke-NG — Project Constitution

> **Version:** 3.0.0
> **Ratified:** 2026-02-28
> **Governance scope:** All contributions to `wilsonify/pykaraoke-ng`.

---

## 1. Purpose

PyKaraoke-NG is a cross-platform desktop karaoke application.

This constitution defines the engineering invariants that govern architecture,
quality, testing, specification workflow, continuous integration, and release
management for the project.

Technology choices are derived from these constraints — not the reverse.

---

## 2. Target Audience and Design Posture

### 2.1 Primary Persona — The Working DJ

The primary user of PyKaraoke-NG is a **live-event DJ** who runs karaoke as
part of a broader DJ set. This persona has governed design decisions since the
original PyKaraoke, which DJs used for over 10 years.

**Defining characteristics:**

- Operates under real-time pressure during live gigs.
- Runs primary DJ software (e.g., Audacious, VirtualDJ, Mixxx) alongside
  PyKaraoke-NG on a single laptop screen.
- Needs to search, queue, and manage karaoke requests without interrupting
  audio playback in the primary DJ application.
- Cannot afford UI friction, mode switching, or screen-dominating layouts.
- Values speed and efficiency over visual polish.

### 2.2 Design Posture — DJ Utility Panel

PyKaraoke-NG is a **professional utility panel**, not a media consumption app.

| PyKaraoke-NG IS                         | PyKaraoke-NG IS NOT                      |
|-----------------------------------------|------------------------------------------|
| A slim sidebar docked beside DJ tools   | A full-screen media player               |
| A keyboard-driven queue manager         | A touch-first browsing experience        |
| A fast search-and-queue workflow        | A visual showcase or content hub         |
| A compact, always-visible control strip | A modal-heavy wizard interface           |
| Optimized for 300–450 px window width  | Designed to consume 80–90% of screen     |

This posture is **constitutional** — every UI decision must be evaluated
against it. Features that violate this posture require explicit justification
and maintainer approval before implementation.

### 2.3 UX Invariants

The following UX constraints have the same governance weight as architectural
constraints (§3):

1. **Single vertical column layout.** All primary controls stack top → bottom.
2. **Strict left alignment.** No center-aligned or right-aligned primary
   controls.
3. **Slim default window.** Window defaults to 300–450 px width. The app must
   remain fully functional at this width.
4. **No full-screen takeovers.** No modal dialogs, splash screens, or
   overlays that block the entire window.
5. **Keyboard-first interaction.** Every primary action (search, queue, play,
   skip) must be achievable without a mouse.
6. **Instant search.** Search must filter incrementally as the user types.
   No "Submit" button required.
7. **Zero mode switching.** The user must never leave the main view to
   accomplish a primary task (search, queue, play).
8. **Compact visual density.** Typography, padding, and spacing must
   prioritize information density over whitespace aesthetics.
9. **No screen dominance.** The application must not expand to fill available
   screen width unless the user explicitly toggles a wide mode.
10. **Dockable workflow.** The interface must function correctly when the OS
    window is snapped/tiled to the left edge of the screen.

Violations of these invariants are treated as defects.

---

## 3. Development Methodology

### 3.1 Test-First Development

Every behavioural change follows the **Red → Green → Refactor** cycle:

- Every new behaviour begins with a **failing test**.
- Production code exists only to make a failing test pass.
- Refactoring occurs only when all tests are green.
- No code ships without corresponding test coverage.

This is policy, not preference.

### 3.2 Specification-Driven Development

Every feature begins with a written specification before any code is written.

**Required lifecycle:**

1. **Specify** — define WHAT and WHY (no implementation details).
2. **Clarify** — resolve ambiguities, surface risks.
3. **Plan** — define HOW (technology decisions live here).
4. **Tasks** — break the plan into ordered, atomic work items.
5. **Implement** — TDD: failing test → pass → refactor.
6. **Checklist** — verify all criteria before merge.

No implementation may begin before specification artefacts exist.

---

## 4. Architectural Constraints

### 4.1 Desktop-First, Offline-Capable

- The application runs locally. No external service is required for core
  functionality.
- Offline operation is a first-class requirement.
- Behaviour must be deterministic without cloud dependencies.

### 4.2 Cross-Platform Determinism

- The application must behave identically on Windows, macOS, and Linux.
- Platform differences must be abstracted behind clean interfaces.
- Hardcoded platform assumptions (path separators, line endings, locale
  defaults, filename length limits) are prohibited.
- Identical input must produce byte-identical output on every platform.
- **Build tooling and CI commands are subject to the same constraint.**
  Shell-specific syntax (`bash -c`, `rm -rf`, `cp`, `mkdir -p`) must
  not appear in build configuration files that execute on all platforms.
  Use cross-platform scripting (Node.js, Python, or Rust build scripts)
  instead.

### 4.3 Strongly Typed Interfaces

- All public interfaces must carry complete, statically verifiable type
  declarations.
- Untyped or dynamically typed escape hatches are prohibited unless
  explicitly justified and approved.
- Static analysis must verify type correctness without runtime execution.

### 4.4 Separation of Concerns

Clear boundaries must exist between the following layers:

| Layer | Responsibility |
|-------|---------------|
| **Core** | Parsing, domain logic, validation, data access |
| **Configuration** | Settings, environment, constants |
| **Playback** | Format-specific audio/video engines |
| **Runtime Shell** | UI, OS integration, platform bindings |

Rules:

- No user-interface logic inside core modules.
- No domain logic inside user-interface modules.
- Layers communicate only through well-defined contracts (APIs, messages,
  or function signatures).

### 4.5 No Global Mutable State

- No module-level mutable variables.
- All state must be injected via parameters or encapsulated in instances.
- Singleton patterns require explicit justification and review approval.

### 4.6 Structured Observability

- No ad-hoc output to standard streams in production code.
- All runtime diagnostics must use structured, levelled logging.
- Log entries must carry contextual metadata sufficient to diagnose the
  triggering condition.
- Failure states must be observable without requiring a debugger.

### 4.7 Build-System Determinism

- Build configuration changes (CI workflows, Tauri config, Dockerfiles,
  Cargo build scripts) are treated as production code.  They require the
  same specification, review, and test discipline as application code.
- Every build command must succeed on **all three CI platforms** (Linux,
  Windows, macOS).  Platform-specific steps require explicit conditional
  guards (e.g. `if: matrix.platform == 'linux'`).
- Relative paths in build configuration must be documented with their
  base directory.  Path depth changes require updating all references.
- Integration tests that validate build configuration must verify the
  **effect** of a command (files staged, artifacts produced), not the
  **literal text** of the command string.  Brittle string-matching
  assertions against build commands are prohibited.
- Build-system changes must be validated locally (`act`, `cargo check`,
  or equivalent) before being pushed.

---

## 5. Static Analysis and Code Quality

Implementation languages may evolve. The following invariants hold regardless:

- **Strong typing** enforced via static analysis tooling.
- **Linting and formatting** checks must pass in CI.
- **Unsafe or unchecked operations** require an explicit justification
  comment and review approval.
- **All public interfaces** must be fully typed and documented.

---

## 6. Testing Standards

### 6.1 Coverage Thresholds

- Core module coverage ≥ **90%** (enforced in CI).
- New code per feature ≥ **95%**.
- Branch coverage is required (not just line coverage).

### 6.2 Test Categories

| Category | Purpose |
|----------|---------|
| **Unit** | Pure logic — no I/O, no side effects |
| **Integration** | Filesystem, services, cross-module interactions |
| **End-to-End** | Built-artefact validation on target platforms |
| **Manual** | Exploratory or diagnostic verification |

All tests must be labelled with their category.

### 6.3 Edge-Case Discipline

Every feature must include tests for:

- Malformed and unexpected input.
- Boundary conditions.
- Cross-platform variance.
- Defined failure modes.

Parameterised tests are preferred over duplicated test functions.

---

## 7. Continuous Integration

### 7.1 Pipeline Stages (ordered)

1. Unit tests (all languages, parallel).
2. Static analysis and quality gate.
3. Integration tests.
4. Platform build matrix (all supported operating systems).
5. End-to-end validation (per-platform artefacts).
6. Release (main branch only, after all prior stages pass).

Each stage gates the next. No stage may run until its predecessor succeeds.

### 7.2 Merge Requirements

A pull request may not merge unless **all** of the following are satisfied:

- All tests pass on every supported platform.
- Static-analysis quality gate passes (zero new defects).
- Specification checklist is complete (all items checked).
- Branch name matches the required `NNN-feature-name` format.
- At least one maintainer has approved.
- History is linear (rebase only — no merge commits).

---

## 8. Backward Compatibility

Public interfaces include: function signatures, CLI contracts,
configuration schema, data-storage schema, and file-format expectations.

- **Breaking changes** require a major version increment.
- **Deprecations** must persist for at least one minor release before
  removal.
- Deprecated interfaces must emit a runtime warning with migration
  guidance.
- Removing a deprecated interface is a breaking change.

---

## 9. Versioning

The project follows [Semantic Versioning 2.0.0](https://semver.org/):

| Change type | Version bump |
|-------------|-------------|
| Breaking change | Major |
| New feature | Minor |
| Bug fix / chore | Patch |

Conventional Commit format is mandatory for all commit messages and PR titles.

---

## 10. Dependency Governance

No external dependency may be added without:

- A written justification in the pull request.
- Evaluation of maintenance status and community health.
- Verification of cross-platform compatibility.
- Security review.

Dependencies must not compromise determinism, portability, or offline
operation.

---

## 11. Feature Branch Governance

### 11.1 Naming Convention

```
NNN-short-kebab-case-description
```

`NNN` is a zero-padded, sequentially assigned three-digit identifier.

### 11.2 Required Artefacts

**Before implementation begins:**

- `spec.md` — Specification (WHAT and WHY).
- `clarify.md` — Clarification (risks and ambiguities resolved).
- `plan.md` — Technical plan (HOW).
- `tasks.md` — Task breakdown (ordered implementation steps).

**Before merge:**

- `checklist.md` — Completion checklist (every item checked).

Missing artefacts block merge.

---

## 12. Amendments

This constitution may be amended by a pull request that:

1. Describes the proposed change and its rationale.
2. Receives approval from **all** active maintainers.
3. Passes all CI checks.

Amendment PR titles must begin with `constitution:`.