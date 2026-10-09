# OpenSpec workflow

PyKaraoke-NG is developed with **specification-driven development** using
[OpenSpec](https://github.com/Fission-AI/OpenSpec). Every behavioural change
starts as a proposal in `openspec/changes/`, is validated, is implemented
test-first, and is archived into the enduring specifications when it ships.

This page is the contributor guide. The system-level description of the
specification layout lives in [Specifications](../reference/specifications.md).

## Install the CLI

OpenSpec ships as a Node package and needs Node.js 20.19 or newer.

```bash
npm install --global @fission-ai/openspec@1.14.1   # pinned to the version CI uses
openspec --version
```

Contributors who prefer not to install globally can run the same commands with
`npx @fission-ai/openspec@1.14.1 <command>`.

## The two trees

| Tree | Meaning |
|------|---------|
| `openspec/specs/<capability>/spec.md` | How the product behaves **today** — the source of truth |
| `openspec/changes/<change-id>/` | A **proposal** in flight: proposal, design, tasks, delta specs |
| `openspec/changes/archive/YYYY-MM-DD-<change-id>/` | A **completed** change, kept for history |

A change's delta specs describe only what is *changing*, using four sections:

| Section | Effect when the change is archived |
|---------|-------------------------------------|
| `## ADDED Requirements` | Appended to the capability's main spec |
| `## MODIFIED Requirements` | Replaces the matching requirement in the main spec |
| `## REMOVED Requirements` | Deleted from the main spec |
| `## Purpose` | Seeds the Purpose of a brand-new capability |

Requirements use RFC 2119 keywords (`MUST`/`SHALL` for binding, `SHOULD` for
recommended, `MAY` for optional) and each requirement needs at least one
`#### Scenario:` written as `- **WHEN** … / - **THEN** …`.

## 1. Propose

Create a change folder and describe the intent before writing any code:

```bash
openspec new change my-feature      # scaffolds openspec/changes/my-feature/
```

Fill in:

* `proposal.md` — **why** this change exists, what is in and out of scope, and
  the approach in a few sentences.
* `specs/<capability>/spec.md` — the delta requirements and scenarios.
* `design.md` — the technical approach and decisions (optional for small
  changes).
* `tasks.md` — the ordered implementation checklist, tests first.

Ask the AI assistant to help with `/opsx:propose <what you want to build>`, and
keep `openspec/changes/<id>/` as the single place the plan lives.

## 2. Validate

```bash
openspec validate --all --strict    # every spec and change
openspec validate my-feature        # one change
openspec show my-feature --json     # inspect a change
openspec status                     # artifact progress for the active change
```

CI runs `openspec validate --all --strict` and `openspec validate --archived`
on every pull request, so a malformed spec or a stale archived change fails the
build. Fix the cause — do not disable the check.

## 3. Implement

Work the `tasks.md` checklist test-first (Red → Green → Refactor). Check items
off as they land. If the design changes while implementing, update `design.md`
and the delta specs rather than letting the plan drift from the code.

Requirements that describe behaviour the product does **not** have yet must stay
inside `openspec/changes/` — never in `openspec/specs/`.

## 4. Archive

When the change is implemented and merged:

```bash
openspec archive my-feature --yes   # merges the deltas, then moves the change
```

The command validates the change, merges its delta specs into
`openspec/specs/`, and moves the folder to
`openspec/changes/archive/YYYY-MM-DD-my-feature/`. A change that genuinely has
no spec deltas (tooling or docs work) declares `skip_specs: true` in its
`.openspec.yaml` so it can be archived without a delta.

```yaml
# openspec/changes/my-tooling-change/.openspec.yaml
schema: spec-driven
skip_specs: true
```

## Quick reference

| Action | Command |
|--------|---------|
| Scaffold a change | `openspec new change <id>` |
| List active changes | `openspec list` |
| List capabilities | `openspec list --specs` |
| Show a change or spec | `openspec show <id> [--type spec]` |
| Validate everything | `openspec validate --all --strict` |
| Validate the archive | `openspec validate --archived` |
| Archive | `openspec archive <id> --yes` |

## Migrating from Spec Kit

PyKaraoke-NG previously used a `specs/` tree managed by [Spec Kit](https://github.com/speckit/speckit).
That tree has been consolidated into OpenSpec: the enduring documents became
capability specs, the historical feature folders became change artifacts, and
the branch-name CI gate was replaced by `openspec validate`. See the migration
summary in
`openspec/changes/consolidate-docs-and-adopt-openspec/migration-summary.md`.
