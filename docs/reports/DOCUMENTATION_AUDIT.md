# Documentation Audit

Audit date: 2026-06-16
Repository: pykaraoke-ng

## Methodology

Every Markdown file was read and evaluated against these criteria:
- **Audience**: Who should read this? (User, Developer, Administrator, All, Historical)
- **Accuracy**: Is the information still correct?
- **Actionability**: Does it help the reader do something?
- **Uniqueness**: Is the same material covered in another document?
- **Freshness**: Is it a one-time report, a permanent guide, or historical record?

---

## Root-Level

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `README.md` | All | **RETAIN** | Project entry point; links to audience-specific guides; accurate and actionable |

---

## `docs/` — Core Documentation

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `index.md` | All | **RETAIN** | Documentation home; cross-references all guides; maintains Jekyll integration |
| `users.md` | Users | **RETAIN** | Installation, playback controls, search, queue management, troubleshooting |
| `developers.md` | Developers | **RETAIN** | Setup, testing, Tauri dev/build, packaging, contributing |
| `administrators.md` | Administrators | **RETAIN** | Docker, Kubernetes, desktop builds, release process, configuration |
| `quickstart.md` | Developers | **RETAIN** | Minimal "get running" guide from a clone |
| `backend-modes.md` | Developers/Admin | **RETAIN** | stdio/HTTP protocol reference; unique API endpoint reference |
| `readme-legacy.txt` | Historical | **RETAIN** | Original PyKaraoke README by Kelvin Lawson; attribution/legal value |

---

## `docs/architecture/`

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `overview.md` | Developers | **RETAIN** | System design, component diagram, IPC protocol, state model |
| `structure.md` | Developers | **RETAIN** | Repository layout, module responsibilities, dependency flow |
| `next-steps.md` | Developers | **RETAIN** | Open work / backlog; useful for new contributors |
| `reorganization.md` | Developers | **RETAIN** | Historical record of 2026-01-31 repo restructuring; helps explain why files are where they are |

---

## `docs/development/`

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `integration-testing.md` | Developers | **RETAIN** | Active guide for running Docker-based integration tests |
| `sonarqube-setup.md` | Developers/Admin | **RETAIN** | Unique reference for SonarCloud secrets and configuration |
| `quality-improvements.md` | Developers | **RETAIN** | Catalog of Python 2→3 migration and security fixes; useful historical context |

---

## `docs/issues/` — Postmortems & Legacy Tracking

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `README.md` | Developers | **RETAIN** | Index of legacy issues; maps original issues to NG status |
| `legacy-issues.md` | Developers | **RETAIN** | Complete catalog of 18 original PyKaraoke issues; guides future development |
| `playback-controls-fixes.md` | Developers | **RETAIN** | Postmortem documenting state machine invariants, poll safety, click debounce; referenced by `developers.md` |
| `webkit-dmabuf-empty-window.md` | Developers/Admin | **RETAIN** | Postmortem of Linux blank-window bug; explains `WEBKIT_DISABLE_DMABUF_RENDERER`; referenced by `administrators.md` troubleshooting |
| `deb-buttons-not-working.md` | Developers | **RETAIN** | Postmortem covering Tauri resource bundling, PYTHONPATH, silent process death, IPC response channel |
| `fast-forward-rewind-not-working.md` | Developers | **RETAIN** | Postmortem/implementation doc for FF/RW feature; explains design decisions |

---

## `docs/reports/` — DELETE ALL (One-Time Investigation Reports)

| File | Verdict | Rationale |
|------|---------|-----------|
| `TEST_REPORT.md` | **DELETE** | Single test run (2026-06-02); no ongoing value |
| `SONAR_FIX_REPORT.md` | **DELETE** | One-time SonarCloud fix report (2026-06-16); fixes already applied |
| `SECURITY_REPORT.md` | **DELETE** | One-time security assessment; findings already fixed |
| `RELIABILITY_REPORT.md` | **DELETE** | One-time reliability audit; fixes already applied |
| `RELEASE_READINESS.md` | **DELETE** | One-time release readiness assessment |
| `GITHUB_ACTIONS_AUDIT.md` | **DELETE** | One-time CI audit; issues already fixed |
| `FINAL_CI_REPORT.md` | **DELETE** | One-time CI remediation report; fixes applied |
| `FINAL_BUILD_REPORT.md` | **DELETE** | One-time build report |
| `E2E_REPORT.md` | **DELETE** | One-time E2E validation report |
| `E2E_FAILURE_ANALYSIS.md` | **DELETE** | One-time failure analysis; fixes applied |
| `DOCUMENTATION_REPORT.md` | **DELETE** | Meta-report about documentation; self-referential |
| `DEPLOYMENT_REPORT.md` | **DELETE** | One-time deployment validation |
| `DEFECT_ANALYSIS.md` | **DELETE** | Defect postmortem; fixes already implemented; content subsumed by individual issue docs |
| `CI_FAILURE_ANALYSIS.md` | **DELETE** | One-time CI failure analysis; fixes applied |
| `CICD_REPORT.md` | **DELETE** | One-time CI/CD review |
| `BUILD_AUDIT.md` | **DELETE** | One-time build/discovery audit |
| `BUILD_AND_TEST_PLAN.md` | **DELETE** | One-time build plan; stale (references 0.7.5, 2026-06-02) |

---

## `docs/archive/` — DELETE ALL (Completed-Task Completion Reports)

| File | Verdict | Rationale |
|------|---------|-----------|
| `SCRIPT_UNIFICATION_COMPLETE.md` | **DELETE** | Task completion report; script already unified; content subsumed by `docs/development/integration-testing.md` |
| `INTEGRATION_TESTS_SETUP.md` | **DELETE** | Task completion report; content subsumed by `docs/development/integration-testing.md` |
| `INTEGRATION_TESTS_QUICK_REF.md` | **DELETE** | Obsolete quick-reference; `docker test-docker.sh` no longer exists |
| `IMPLEMENTATION_COMPLETE.md` | **DELETE** | Triple duplicate of INTEGRATION_TESTS_SETUP.md content |
| `DOCKER_INTEGRATION_ARCHITECTURE.md` | **DELETE** | Architecture diagrams for integration setup; no ongoing value |

---

## `specs/` — Specification Documents

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `README.md` | Developers | **RETAIN** | Spec kit directory index |
| `constitution.md` | Developers | **RETAIN** | Project governance, invariants, standards; authoritative |
| `ux-design.md` | Developers/Design | **RETAIN** | UX design spec for slim sidebar; governance for UI decisions |
| `workflow.md` | Developers | **RETAIN** | Spec-driven development workflow guide |
| `build-system-invariants.md` | Developers | **RETAIN** | Hard-won CI/build lessons; cross-platform rules |
| `features/001-filename-parser-edge-cases/*` | Developers | **RETAIN** | Active feature spec (5 files) |
| `features/002-slim-sidebar-layout/*` | Developers | **RETAIN** | Active feature spec (5 files) |
| `templates/*` | Developers | **RETAIN** | Spec kit templates (4 files) |
| `archive/.gitkeep` | — | **RETAIN** | Placeholder for empty directory |

---

## Co-located READMEs

| File | Audience | Verdict | Rationale |
|------|----------|---------|-----------|
| `src/runtimes/tauri/README.md` | Developers | **RETAIN** | Tauri-specific architecture and build info; co-located with code |
| `src/runtimes/tauri/e2e/README.md` | Developers | **RETAIN** | E2E BDD test setup; co-located with test code |
| `scripts/README.md` | Developers | **RETAIN** | Scripts reference; co-located with scripts |
| `scripts/troubleshooting-tests.md` | Developers | **RETAIN** | Test troubleshooting guide; co-located |

---

## Summary

| Action | Count |
|--------|-------|
| **RETAIN** | 39 files |
| **DELETE** | 22 files |
