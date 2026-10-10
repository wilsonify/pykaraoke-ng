# Proposal: Consolidate Documentation and Adopt OpenSpec

## Intent

The repository carried two overlapping documentation trees with no clear
division of labour: `specs/` (a Spec Kit workflow: a constitution, a UX design
document, build-system invariants, a workflow guide, templates, shell CI
scripts, and two feature folders) and `docs/` (user, developer, quick-start,
and architecture pages published as a bare Jekyll site). Neither tree was
complete on its own — the landing page linked into `specs/`, the developer
guide described a `specs/features/NNN-*` process that the code had outgrown,
and the Spec Kit feature folders referenced file paths that no longer exist
(`src/pykaraoke/core/…`, `src/runtimes/tauri/src/index.html`).

The goal is one coherent documentation system: contributor-facing
specifications in a supported, tool-validated framework, and user-facing
documentation published as a real website.

## Scope

In scope:

- Migrate every Spec Kit artifact into OpenSpec artifacts under `openspec/`.
- Establish `openspec/specs/` as the canonical home for enduring requirements
  and `openspec/changes/` for proposed, in-progress, and completed changes.
- Consolidate `docs/` into a navigable site with search, install a static-site
  generator, and publish it to GitHub Pages from CI.
- Replace the removal of the Spec Kit branch-name CI gate with OpenSpec
  validation.
- Update every reference to the old layout across the repository.

Out of scope:

- Behaviour changes to the product. No engine, UI, or packaging code changes.
- Implementing the proposed filename-parser edge-case work (it remains an
  active change).
- Repo settings that cannot be automated (enabling GitHub Pages is documented,
  not scripted).

## Approach

Adopt OpenSpec at the repository root with `openspec init`, model each enduring
concern as a capability spec, and preserve the two historical feature folders
as change artifacts (the implemented one archived, the unimplemented one
active). Publish the consolidated `docs/` with MkDocs Material, which is the
natural static-site generator for a Python project, and deploy it with the
official GitHub Pages actions.
