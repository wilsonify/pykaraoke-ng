# Design: Consolidate Documentation and Adopt OpenSpec

## Technical Approach

### Specifications: Spec Kit → OpenSpec

`openspec init` creates `openspec/{specs,changes,config.yaml}`. Enduring
documents become capability specs; historical feature folders become change
artifacts. Nothing is deleted without being represented somewhere.

| Source (`specs/`) | Destination | Rationale |
|-------------------|-------------|-----------|
| `constitution.md` | `openspec/specs/project-governance/spec.md` | Binding engineering/UX/CI rules → governance requirements |
| `ux-design.md` | `openspec/specs/ux-slim-sidebar/spec.md` | The design contract for the UI |
| `build-system-invariants.md` | `openspec/specs/build-system/spec.md` (with a `Historical incidents` appendix) | Cross-platform build rules and postmortems |
| `features/001-filename-parser-edge-cases/` | `openspec/changes/filename-parser-edge-cases/` (**active**) | Specified but **not implemented** — must not live in `openspec/specs/` |
| `features/002-slim-sidebar-layout/` | `openspec/changes/archive/2026-02-28-slim-sidebar-layout/` (**archived**) | Implemented and shipped |
| `workflow.md` | Superseded by `docs/contributing/openspec.md` | The Spec Kit lifecycle no longer applies |
| `templates/`, `features/.next-id`, `ci/new-feature.sh` | Removed | OpenSpec supplies scaffolding (`openspec new change`) and validation |
| `ci/validate-spec-completion.sh`, `ci/Validate-SpecCompletion.ps1` | Removed | Replaced by `openspec validate` in CI |
| `README.md` | Superseded by `openspec/README.md` + `docs/reference/specifications.md` | — |

New, evidence-based capability specs were added for behaviour that previously
had no specification but is tested and shipped: `filename-parsing`,
`song-library`, `playback`, and `web-engine-api`. These describe only behaviour
that exists in the code; each carries a `> Source:` traceability line.

### Documentation: Jekyll → MkDocs Material

The existing `docs/_config.yml` used `jekyll-theme-slate`, which required a
Ruby toolchain to preview and offered no search. MkDocs Material is a better
fit for a Python project:

- one Python dependency (`mkdocs-material`), installed via the new `docs`
  extra in `pyproject.toml`;
- built-in search, navigation, and a dark/light palette to match the app;
- `mkdocs build --strict` turns broken internal links and missing nav entries
  into build failures, which CI can rely on;
- `site_url` handles the `/pykaraoke-ng/` project-site base path for both
  GitHub Pages and local preview.

The `docs/` tree is regrouped into `getting-started/`, `user-guide/`,
`architecture/`, `reference/`, and `contributing/`. Existing pages are moved
rather than rewritten so their content and history are preserved; new pages
fill the gaps the requirements called out (installation, formats,
configuration, engine API, specifications, OpenSpec workflow, build system).

OpenSpec artifacts stay out of the published site: they are working documents.
The site links to the capability specs on GitHub instead.

### Deployment

`.github/workflows/docs.yml` builds the site with a pinned
`mkdocs-material==9.6.14` and deploys it with `actions/configure-pages`,
`actions/upload-pages-artifact`, and `actions/deploy-pages`. It runs on pushes
to the default branch when docs, site config, the specification tree, or the
workflow change, and on manual dispatch. Deployment permissions are limited to
`pages: write` and `id-token: write`, and no secrets are introduced.

## Architecture Decisions

### Decision: keep OpenSpec artifacts out of the published site

OpenSpec's `changes/` tree is deliberately working material. Publishing it
would expose half-finished proposals as if they were product documentation.
The site therefore links to the stable `openspec/specs/` capabilities only.

### Decision: record historical features as OpenSpec changes, not specs

Feature 001 was specified but never implemented; representing it in
`openspec/specs/` would claim behaviour the code does not have. It stays an
active change. Feature 002 shipped, so it is archived and its requirements are
folded into the `ux-slim-sidebar` capability.

### Decision: `skip_specs` for this migration

This change alters documentation and tooling only, so it declares
`skip_specs: true` rather than fabricating deltas against the capability specs
it introduces.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Historical requirements silently dropped in the conversion | Medium | High | Preserve source folders as change artifacts and diff the spec content against the originals |
| Specs describe aspirational behaviour as current | Medium | High | Every spec is grounded in code/tests and flags known divergences with `> Note:` lines |
| Stale links to `specs/` or moved docs | Medium | Medium | `mkdocs build --strict` for the site; a repository-wide reference sweep for the rest |
| Page is only complete after the manual Pages setting | High | Low | Document the `Settings → Pages → Source: GitHub Actions` step |

## Manual repository setting

GitHub Pages must be switched to the Actions source once:

**Settings → Pages → Build and deployment → Source = "GitHub Actions".**

Until that is done the deployment job has no Pages site to publish to. This
cannot be automated from a workflow.
