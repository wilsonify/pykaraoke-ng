# Tasks

## 1. Audit

- [x] 1.1 Inventory `specs/` and `docs/`, including nested files, links, and config
- [x] 1.2 Identify authoritative content, duplicates, stale paths, and contradictions
- [x] 1.3 Determine implementation status of feature 001 (not implemented) and 002 (shipped)

## 2. Adopt OpenSpec

- [x] 2.1 Run `openspec init` and record project context in `openspec/config.yaml`
- [x] 2.2 Migrate `constitution.md` into `openspec/specs/project-governance/spec.md`
- [x] 2.3 Migrate `ux-design.md` into `openspec/specs/ux-slim-sidebar/spec.md`
- [x] 2.4 Migrate `build-system-invariants.md` into `openspec/specs/build-system/spec.md`
- [x] 2.5 Add evidence-based specs for `filename-parsing`, `song-library`, `playback`, and `web-engine-api`
- [x] 2.6 Migrate feature 001 to the active change `filename-parser-edge-cases`
- [x] 2.7 Archive feature 002 as `changes/archive/2026-02-28-slim-sidebar-layout`
- [x] 2.8 Record this migration as an OpenSpec change (`skip_specs: true`)
- [x] 2.9 Validate with `openspec validate --all --strict` and `openspec validate --archived`

## 3. Documentation site

- [x] 3.1 Choose MkDocs Material and add the `docs` dependency group to `pyproject.toml`
- [x] 3.2 Add `mkdocs.yml` with the published navigation and search
- [x] 3.3 Regroup `docs/` into getting-started, user-guide, architecture, reference, and contributing
- [x] 3.4 Add installation, formats, configuration, engine API, specifications, OpenSpec workflow, and build-system pages
- [x] 3.5 Build locally with `mkdocs build --strict` and fix link/nav errors
- [x] 3.6 Gitignore the generated `site/` output

## 4. CI and deployment

- [x] 4.1 Add `.github/workflows/docs.yml` using the official Pages actions
- [x] 4.2 Replace the Spec Kit `spec-validation` job with OpenSpec validation in `ci-cd.yml`
- [x] 4.3 Keep the existing `sonarqube` job gated on the new validation job
- [x] 4.4 Document the manual `Settings → Pages → Source: GitHub Actions` step

## 5. References and cleanup

- [x] 5.1 Update `README.md` (documentation links and OpenSpec workflow)
- [x] 5.2 Repoint `pyproject.toml` Documentation URL and fix in-repo references
- [x] 5.3 Remove the legacy `specs/` tree from version control
- [x] 5.4 Write the migration summary
- [ ] 5.5 Archive this change after the pull request merges (`openspec archive consolidate-docs-and-adopt-openspec --yes`)
