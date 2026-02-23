# Spec Kit — PyKaraoke-NG

This directory contains all Spec-Driven Development artifacts managed by
[Spec Kit](https://github.com/speckit/speckit).

## Directory Structure

```
specs/
├── constitution.md          # Project constitution (governance + invariants)
├── templates/
│   ├── feature-spec.md      # Template for /speckit.specify
│   ├── clarification.md     # Template for /speckit.clarify
│   ├── technical-plan.md    # Template for /speckit.plan
│   └── task-breakdown.md    # Template for /speckit.tasks
├── features/
│   └── NNN-feature-name/    # One directory per feature branch
│       ├── spec.md          # Feature specification
│       ├── clarify.md       # Clarification notes
│       ├── plan.md          # Technical plan
│       ├── tasks.md         # Task breakdown
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
