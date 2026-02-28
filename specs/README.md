# Spec Kit — PyKaraoke-NG

This directory contains all Spec-Driven Development artifacts managed by
[Spec Kit](https://github.com/speckit/speckit).

## Directory Structure

```
specs/
├── constitution.md          # Project constitution (governance + invariants)
├── ux-design.md             # UX design spec (DJ utility panel, slim sidebar)
├── build-system-invariants.md # Build-system rules and postmortem log
├── workflow.md              # Developer workflow guide (Spec Kit lifecycle)
├── templates/
│   ├── feature-spec.md      # Template for /speckit.specify
│   ├── clarification.md     # Template for /speckit.clarify
│   ├── technical-plan.md    # Template for /speckit.plan
│   └── task-breakdown.md    # Template for /speckit.tasks
├── features/
│   ├── 001-filename-parser-edge-cases/
│   │   ├── spec.md
│   │   ├── clarify.md
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   └── checklist.md
│   └── 002-slim-sidebar-layout/
│       ├── spec.md          # Slim sidebar feature specification
│       ├── clarify.md       # Clarification (risks, cross-platform, compat)
│       ├── plan.md          # Technical plan (DOM, CSS, Tauri config)
│       ├── tasks.md         # Phased task breakdown
│       └── checklist.md     # Completion checklist
├── archive/                 # Completed and merged specs
└── README.md                # This file
```

## Workflow Summary

1. **Branch** — `git checkout -b NNN-feature-name`
2. **Specify** — `/speckit.specify` → write `specs/features/NNN-feature-name/spec.md`
3. **Clarify** — `/speckit.clarify` → write `specs/features/NNN-feature-name/clarify.md`
4. **Plan** — `/speckit.plan` → write `specs/features/NNN-feature-name/plan.md`
5. **Tasks** — `/speckit.tasks` → write `specs/features/NNN-feature-name/tasks.md`
6. **Implement** — TDD: failing test → green → refactor
7. **Checklist** — `/speckit.checklist` → write `specs/features/NNN-feature-name/checklist.md`
8. **CI** — All gates must pass before merge
9. **Archive** — After merge, move to `specs/archive/`

## Branch Naming Convention

All feature branches **must** follow the format:

```
NNN-short-description
```

Where `NNN` is a zero-padded three-digit sequential number (e.g., `001`, `042`, `100`).

Examples:
- `001-filename-parser-edge-cases`
- `002-structured-logging`
- `003-playlist-management`
