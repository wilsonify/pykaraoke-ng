# Project Governance Specification

## Purpose

The binding engineering, quality, and process invariants that govern all
contributions to PyKaraoke-NG — audience and design posture, architecture
constraints, testing standards, continuous integration, versioning, and
dependency governance. Technology choices are derived from these constraints,
not the reverse. This capability is the canonical, migrated replacement for the
Spec Kit-era engineering constitution (v3.0.0, ratified 2026-02-28).

> Source: `specs/constitution.md` (historical Spec Kit constitution, v3.0.0) and
> `openspec/config.yaml`.

> Note: This specification states intended, binding policy. Where the current
> repository has not yet fully realised a rule, the requirement is marked
> SHOULD and the gap is called out in a `> Note:` line beneath it. Migrating the
> Spec Kit `NNN-feature-name` branch workflow to OpenSpec changes the mechanics
> of change governance (see the final requirement) while preserving its intent.

## Requirements

### Requirement: Primary persona governs design

The project MUST treat the live-event DJ as its primary persona and evaluate
every user-facing decision against that persona.

#### Scenario: Design decision review

- **WHEN** a proposed change alters a user-facing workflow or layout
- **THEN** the change is assessed against the working-DJ persona (real-time pressure, primary DJ software remaining visible, keyboard-dominant operation)
- **AND** the rationale is recorded in the change's proposal or design artifact

### Requirement: Professional utility panel posture

The product MUST be a compact, always-visible control strip rather than a
media-consumption application.

#### Scenario: Feature proposal conflicts with the posture

- **WHEN** a feature would make the app behave like a full-screen media player, a touch-first browser, or a wizard-driven tool
- **THEN** the feature requires explicit justification and maintainer approval before implementation
- **AND** the resulting behaviour MUST NOT compromise the slim-sidebar posture

### Requirement: Slim-sidebar UX invariants are binding

The ten slim-sidebar UX invariants (single vertical column, strict left
alignment of primary controls, slim window, no full-screen takeovers,
keyboard-first interaction, instant search, zero mode switching, compact
density, no screen dominance, dockable workflow) MUST hold, and a violation is
treated as a defect. The authoritative form of each invariant, with its
rationale, lives in `openspec/specs/ux-slim-sidebar/spec.md`.

#### Scenario: Primary control alignment

- **WHEN** a primary control (search, results, transport, queue) is laid out
- **THEN** it is left-aligned within the single vertical column

#### Scenario: Keyboard-only primary workflow

- **WHEN** a user performs search, queue, play, or skip
- **THEN** the action is achievable without a mouse

#### Scenario: Narrow window operation

- **WHEN** the window is 300–450 px wide
- **THEN** the application remains fully functional with no horizontal scrolling

> Note: The detailed, rationalised form of these invariants lives in
> `openspec/specs/ux-slim-sidebar/spec.md`, which is the authority for layout,
> dimensions, and prohibited interaction patterns.

### Requirement: Test-first development

Every behavioural change MUST follow the Red → Green → Refactor cycle, and no
production code may be added without a test that requires it.

#### Scenario: New behaviour is introduced

- **WHEN** a contributor adds or changes observable behaviour
- **THEN** a failing test exists first
- **AND** production code is added only to make that test pass
- **AND** refactoring happens only once all tests are green

### Requirement: Specification-driven development

Every non-trivial change MUST be described by OpenSpec artifacts before
implementation begins, and the change MUST be validated and archived through
the OpenSpec lifecycle.

#### Scenario: Starting a change

- **WHEN** a contributor begins a feature, refactor, or behaviour change
- **THEN** a change folder exists under `openspec/changes/` before implementation starts
- **AND** it captures intent and scope (proposal), requirements (delta specs), and technical approach and tasks (design, tasks)

#### Scenario: Completing a change

- **WHEN** the work is implemented and verified
- **THEN** `openspec validate` passes for the change
- **AND** the change is archived, merging any spec deltas into `openspec/specs/`

### Requirement: Desktop-first and offline-capable

Core functionality MUST run locally with no required external service, and
offline operation MUST be a first-class behaviour.

#### Scenario: No network available

- **WHEN** the application runs without network access
- **THEN** core playback, library scanning, search, and queueing still work
- **AND** behaviour is deterministic without cloud dependencies

### Requirement: Cross-platform determinism

The application MUST behave identically on Windows, macOS, and Linux, and
identical input MUST produce byte-identical output on every platform.

#### Scenario: Platform-specific assumptions

- **WHEN** code or build configuration handles path separators, line endings, locale defaults, or filename length limits
- **THEN** the assumption is abstracted behind a clean interface rather than hardcoded

#### Scenario: Cross-platform build configuration

- **WHEN** a build configuration file executes on all supported platforms
- **THEN** it contains no shell-specific syntax such as `bash -c`, `rm -rf`, `cp`, or `mkdir -p`
- **AND** cross-platform scripting (Python, Node.js, or Rust) is used instead

### Requirement: Strongly typed interfaces

All public interfaces MUST carry complete, statically verifiable type
declarations, and static analysis MUST be able to verify type correctness
without executing the code.

#### Scenario: Public interface declared

- **WHEN** a new public function, method, or data structure is introduced
- **THEN** it carries full type annotations
- **AND** an untyped or dynamically typed escape hatch is used only when explicitly justified and approved

> Note: Type annotations are required across the codebase; static enforcement is
> currently applied with `mypy` on selected modules rather than the whole tree.

### Requirement: Separation of concerns

Clear boundaries MUST exist between core logic, configuration, playback, and
the runtime shell, and layers MUST communicate only through well-defined
contracts.

#### Scenario: Core logic placement

- **WHEN** parsing, domain logic, validation, or data access is implemented
- **THEN** it lives in core modules with no user-interface logic

#### Scenario: User-interface logic placement

- **WHEN** rendering, event handling, or OS integration is implemented
- **THEN** it lives in the runtime shell with no domain logic

### Requirement: No global mutable state

Modules MUST NOT expose mutable module-level state; state MUST be injected via
parameters or encapsulated in instances.

#### Scenario: Shared state introduced

- **WHEN** a module needs to hold state
- **THEN** the state is encapsulated in an instance or passed in explicitly
- **AND** a singleton is used only with explicit justification and review approval

### Requirement: Structured observability

Production code MUST NOT write ad-hoc output to standard streams; runtime
diagnostics MUST use structured, levelled logging with contextual metadata.

#### Scenario: Diagnosing a failure

- **WHEN** a runtime failure occurs
- **THEN** a levelled log entry records enough context to diagnose the triggering condition without a debugger
- **AND** no unstructured print output is emitted from production code

### Requirement: Build-system determinism

Build configuration (CI workflows, Tauri configuration, build scripts) MUST be
treated as production code, and every build command MUST succeed on all three
supported CI platforms.

#### Scenario: Platform-specific build step

- **WHEN** a build step is only valid on one platform
- **THEN** it is guarded by an explicit condition such as `if: matrix.platform == 'linux'`

#### Scenario: Validating build configuration

- **WHEN** an integration test checks build configuration
- **THEN** it asserts the effect of the command (files staged, artifacts produced), not the literal command string
- **AND** the change is validated locally (`act`, `cargo check`, or equivalent) before it is pushed

#### Scenario: Relative path in build configuration

- **WHEN** a build command uses a relative path
- **THEN** the base directory (the actual working directory of the command) is documented
- **AND** changing path depth updates every reference

### Requirement: Static analysis and code quality gates

Linting and formatting checks MUST pass in CI, and unsafe or unchecked
operations MUST carry an explicit justification comment and review approval.

#### Scenario: Code quality check

- **WHEN** a pull request is opened
- **THEN** linting and formatting checks run and must pass
- **AND** public interfaces are typed and documented

### Requirement: Test coverage thresholds

Core-module coverage MUST be at least 90%, new code per change MUST be at
least 95%, and branch coverage MUST be measured (not only line coverage).

#### Scenario: Coverage evaluation

- **WHEN** a change is evaluated in CI
- **THEN** core coverage is at least 90% and new-code coverage is at least 95%
- **AND** branch coverage is reported

### Requirement: Test categories and edge-case discipline

Tests MUST be labelled by category (unit, integration, end-to-end, manual), and
every change MUST include tests for malformed input, boundary conditions,
cross-platform variance, and defined failure modes.

#### Scenario: Adding a behaviour

- **WHEN** a feature is implemented
- **THEN** it includes tests for its edge cases and failure modes
- **AND** parameterised tests are used in preference to duplicated test functions

### Requirement: Ordered CI pipeline with stage gating

Continuous integration MUST run in ordered stages — unit tests, static analysis
and quality gate, integration tests, platform build matrix, end-to-end
validation, then release — and each stage MUST gate the next.

#### Scenario: Stage ordering

- **WHEN** an earlier CI stage fails
- **THEN** later stages do not run
- **AND** the release stage runs only on the main branch after all prior stages pass

> Note: The current pipeline implements three parallel test legs (Python,
> frontend, Rust), OpenSpec validation, a SonarQube quality gate, a three-OS
> build matrix, and a main-only release. Integration and end-to-end stages are
> folded into these legs rather than run as separate stages.

### Requirement: Merge requirements

A pull request MUST NOT merge unless all tests pass on every supported
platform, the static-analysis quality gate passes with zero new defects, the
change's tasks and validation are complete, at least one maintainer approves,
and history is linear.

#### Scenario: Merge gate

- **WHEN** a pull request is proposed for merge
- **THEN** all required checks pass and the OpenSpec change is valid
- **AND** the branch history is linear (rebase only, no merge commits)
- **AND** at least one maintainer has approved

### Requirement: Change governance

Change work MUST be tracked in OpenSpec: a change folder under
`openspec/changes/` for proposed and in-progress work, promoted to
`openspec/changes/archive/` once complete, with enduring requirements living in
`openspec/specs/`.

#### Scenario: Proposing a change

- **WHEN** a contributor proposes a feature, refactor, or behaviour change
- **THEN** they create a change under `openspec/changes/` containing a proposal, delta specs (or a declared `skip_specs` for docs/tooling-only work), and design/tasks as appropriate

#### Scenario: Archiving a change

- **WHEN** a change is complete and validated
- **THEN** its tasks are fully checked and it is archived, moving to `openspec/changes/archive/` with a date prefix
- **AND** any spec deltas are merged into `openspec/specs/`

> Note: This replaces the Spec Kit `NNN-feature-name` branch naming and the
> `spec.md`/`clarify.md`/`plan.md`/`tasks.md`/`checklist.md` artifact set, which
> were enforced by CI. The underlying intent — a written specification reviewed
> before implementation — is unchanged.

### Requirement: Backward compatibility

Public interfaces (function signatures, CLI contracts, configuration schema,
data-storage schema, file-format expectations) MUST remain backward compatible
except across a major version increment.

#### Scenario: Removing a deprecated interface

- **WHEN** an interface is deprecated
- **THEN** it persists for at least one minor release, emitting a runtime warning with migration guidance
- **AND** its removal is treated as a breaking change

### Requirement: Semantic versioning and conventional commits

The project MUST follow Semantic Versioning 2.0.0, and all commit messages and
pull-request titles MUST use the Conventional Commits format.

#### Scenario: Version increment

- **WHEN** a release is prepared
- **THEN** a breaking change increments the major version, a new feature the minor version, and a bug fix or chore the patch version
- **AND** commit messages and PR titles follow Conventional Commits

### Requirement: Dependency governance

No external dependency SHALL be added without a written justification, an
evaluation of maintenance status and community health, a cross-platform
compatibility check, and a security review.

#### Scenario: Adding a dependency

- **WHEN** a change introduces a new dependency
- **THEN** the pull request records the justification and the maintenance, portability, and security assessment
- **AND** the dependency does not compromise determinism, portability, or offline operation

#### Scenario: Runtime dependency for the engine

- **WHEN** a dependency is proposed for the Python engine
- **THEN** it is rejected unless an approved proposal justifies leaving the pure-stdlib constraint

### Requirement: Governed amendment of this constitution

This governance specification MUST be amended only through a reviewed change
that states the rationale, receives maintainer approval, and passes all CI
checks.

#### Scenario: Amending governance

- **WHEN** a contributor proposes a change to governance
- **THEN** they submit a change that describes the amendment and its rationale
- **AND** it receives approval from all active maintainers and passes CI before it is archived into this spec
