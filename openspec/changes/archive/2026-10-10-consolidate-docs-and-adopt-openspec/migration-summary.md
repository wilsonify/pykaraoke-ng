# Documentation Migration Summary

This change consolidated `specs/` and `docs/` into one documentation system:
OpenSpec for specifications, MkDocs Material for the published site.

## Major moves

| Before | After |
|--------|-------|
| `specs/constitution.md` | `openspec/specs/project-governance/spec.md` |
| `specs/ux-design.md` | `openspec/specs/ux-slim-sidebar/spec.md` |
| `specs/build-system-invariants.md` | `openspec/specs/build-system/spec.md` (+ historical-incidents appendix) |
| `specs/features/001-filename-parser-edge-cases/` | `openspec/changes/filename-parser-edge-cases/` (active) |
| `specs/features/002-slim-sidebar-layout/` | `openspec/changes/archive/2026-02-28-slim-sidebar-layout/` (archived) |
| `docs/users.md` | `docs/user-guide/index.md` |
| `docs/developers.md` | `docs/contributing/index.md` |
| `docs/quickstart.md` | `docs/getting-started/quickstart.md` |
| `docs/_config.yml` (Jekyll) | `mkdocs.yml` (MkDocs Material) |
| `specs/ci/validate-spec-completion.sh` + `.ps1`, `specs/ci/new-feature.sh` | `openspec validate` in CI; `openspec new change` for scaffolding |
| `specs/workflow.md`, `specs/README.md`, `specs/templates/`, `specs/features/.next-id` | Superseded by `docs/contributing/openspec.md` and `openspec/README.md` |

New pages that fill documented gaps: `docs/getting-started/installation.md`,
`docs/reference/formats.md`, `docs/reference/configuration.md`,
`docs/reference/engine-api.md`, `docs/reference/specifications.md`,
`docs/architecture/web-app.md`, `docs/architecture/engine.md`,
`docs/contributing/build-system.md`.

## Duplicates and contradictions resolved

* **Two overlapping spec trees.** `docs/` and `specs/` both described the
  architecture and workflow; the workflow text in `docs/developers.md`
  described a `specs/features/NNN-*` process the code had left behind. The
  developer guide now points at the OpenSpec workflow and the specs own the
  requirements.
* **Stale file paths.** The Spec Kit feature plans referenced
  `src/pykaraoke/core/filename_parser.py`, `src/runtimes/tauri/src/index.html`,
  `styles.css`, and `app.js` — none of which exist. The migrated change
  artifacts use the real paths (`src/pykaraoke/filename_parser.py`,
  `src/web/index.html`) and record the divergence.
* **A malformed user-guide table.** The "Supported formats" table in the user
  guide had a stray MPEG row stranded after the duet section; it is repaired.
* **A user-guide/implementation contradiction.** The user guide said the Stop
  button keeps the song loaded and that rewind/fast-forward step 10 seconds;
  the shipped code clears the current song on Stop and steps 5 seconds. The
  guide now matches the implementation. (Recorded as a `> Note:` in the
  `playback` spec.)
* **Spec Kit templates and ID counter.** Removed; OpenSpec provides scaffolding
  and validation, so a hand-maintained `.next-id` and shell scaffolding scripts
  were dead weight.

## Preserved historical content

* The **feature 001 proposal** is preserved in full as an active OpenSpec
  change (proposal, design, tasks, and delta specs), including its open
  questions and risk table. It was specified but never implemented, so it is
  explicitly **not** represented as current behaviour.
* The **feature 002 work** is preserved as an archived change with its task
  history marked complete, alongside a record of what actually shipped.
* The **constitution** is preserved as the `project-governance` capability,
  including the UX invariants, coverage thresholds, and merge requirements.
* **Build-system postmortems** are preserved as a `Historical incidents`
  appendix on the `build-system` spec.
* The `openspec/changes/archive/2026-02-28-slim-sidebar-layout` folder keeps
  the original date prefix so its chronology is obvious.

## Unresolved issues

* **GitHub Pages must be enabled manually** (`Settings → Pages → Build and
  deployment → Source: GitHub Actions`). Deployment cannot be verified from the
  repository alone, so the workflow is provided but not claimed to be live.
* **Feature 001 remains unimplemented.** The `filename-parser-edge-cases`
  change is active; its delta specs must be reconciled with
  `openspec/specs/filename-parsing/spec.md` at archive time (`openspec archive`
  performs the merge and will refuse a delta that drops a scenario).
* **Implementation divergences recorded, not fixed.** The `ux-slim-sidebar`
  spec notes that Now Playing is not sticky, that virtual scrolling, drag
  reorder, and opt-in wide mode are not implemented, and that queue reorder is
  limited. These are documented as `> Note:` lines rather than changed, since
  this migration makes no product changes.
* **A workspace-level `../openspec/` directory exists** outside this repository
  (in the parent `music/` checkout) and describes an older architecture. It is
  not part of this repository and was left untouched; it should be reconciled
  separately if that workspace keeps using it.
