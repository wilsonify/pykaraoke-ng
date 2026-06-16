# Documentation Cleanup Plan

## Goal

Reduce documentation from ~61 Markdown files to an authoritative core of ~39 files.
Every remaining document serves a clear audience and purpose. No file is kept
"just in case."

## Target Structure (after cleanup)

```
docs/
├── index.md                         # Documentation home
├── users.md                         # User guide
├── developers.md                    # Developer guide
├── administrators.md                # Admin guide
├── quickstart.md                    # Quick start
├── backend-modes.md                 # Backend protocol reference
├── readme-legacy.txt                # Original project attribution
├── architecture/
│   ├── overview.md                  # System architecture
│   ├── structure.md                 # Repository structure
│   ├── next-steps.md                # Open work / backlog
│   └── reorganization.md            # Historical restructuring record
├── development/
│   ├── integration-testing.md       # Docker integration testing
│   ├── sonarqube-setup.md           # SonarCloud configuration
│   └── quality-improvements.md      # Python 3 migration history
├── issues/
│   ├── README.md                    # Legacy issues index
│   ├── legacy-issues.md             # Original PyKaraoke issue catalog
│   ├── playback-controls-fixes.md   # Postmortem: state machine/poll bugs
│   ├── webkit-dmabuf-empty-window.md# Postmortem: Linux blank window
│   ├── deb-buttons-not-working.md   # Postmortem: Tauri resource bundling
│   └── fast-forward-rewind-not-working.md  # Postmortem: FF/RW implementation
├── reports/                         # DELETED entirely
├── archive/                         # DELETED entirely
├── _config.yml                      # Jekyll config (retained)
```

## Phase 1: Delete One-Time Reports

Delete entire `docs/reports/` directory (17 files). These are one-time investigation
reports with no ongoing value. All fixes described in them have been applied.
The developer guide already documents the current CI/CD pipeline, security
posture, and test practices.

Delete entire `docs/archive/` directory (5 files). These are task-completion
reports for work that has long been finished. The authoritative integration
testing documentation is `docs/development/integration-testing.md`.

## Phase 2: Delete Individual Stale Files

None — all remaining files outside `reports/` and `archive/` serve an active
purpose.

## Phase 3: Consolidate References (no text merging needed)

No text consolidation is required because:
- The three audience guides (`users.md`, `developers.md`, `administrators.md`)
  are already well-structured with unique content.
- The issue postmortems are self-contained and cross-referenced by the guides.
- The spec documents are governed by the spec-driven development process.

## Phase 4: Update `docs/index.md`

Remove the "Reports" section table from `docs/index.md` since those reports
no longer exist. The index should only link to authoritative, maintained
documents.

## Phase 5: Update `README.md`

No changes needed — the root README only links to the three audience guides
and `quickstart.md`, all of which are retained.

## Files to Delete

| # | File | Reason |
|---|------|--------|
| 1 | `docs/reports/TEST_REPORT.md` | One-time test run, 2026-06-02 |
| 2 | `docs/reports/SONAR_FIX_REPORT.md` | One-time Sonar fix report |
| 3 | `docs/reports/SECURITY_REPORT.md` | One-time security assessment |
| 4 | `docs/reports/RELIABILITY_REPORT.md` | One-time reliability audit |
| 5 | `docs/reports/RELEASE_READINESS.md` | One-time release assessment |
| 6 | `docs/reports/GITHUB_ACTIONS_AUDIT.md` | One-time CI audit |
| 7 | `docs/reports/FINAL_CI_REPORT.md` | One-time CI report |
| 8 | `docs/reports/FINAL_BUILD_REPORT.md` | One-time build report |
| 9 | `docs/reports/E2E_REPORT.md` | One-time E2E validation |
| 10 | `docs/reports/E2E_FAILURE_ANALYSIS.md` | One-time failure analysis |
| 11 | `docs/reports/DOCUMENTATION_REPORT.md` | Meta-report, stale |
| 12 | `docs/reports/DEPLOYMENT_REPORT.md` | One-time deployment validation |
| 13 | `docs/reports/DEFECT_ANALYSIS.md` | Subsumed by issue postmortems |
| 14 | `docs/reports/CI_FAILURE_ANALYSIS.md` | One-time CI analysis |
| 15 | `docs/reports/CICD_REPORT.md` | One-time CI/CD review |
| 16 | `docs/reports/BUILD_AUDIT.md` | One-time build audit |
| 17 | `docs/reports/BUILD_AND_TEST_PLAN.md` | One-time plan, stale |
| 18 | `docs/archive/SCRIPT_UNIFICATION_COMPLETE.md` | Task completion report |
| 19 | `docs/archive/INTEGRATION_TESTS_SETUP.md` | Task completion report |
| 20 | `docs/archive/INTEGRATION_TESTS_QUICK_REF.md` | Obsolete quick reference |
| 21 | `docs/archive/IMPLEMENTATION_COMPLETE.md` | Triple duplicate of #19/#20 |
| 22 | `docs/archive/DOCKER_INTEGRATION_ARCHITECTURE.md` | Obsolete architecture diagrams |

**Total: 22 files deleted, 0 files created (aside from audit/plan docs)**

## Post-Cleanup Verification

1. `docs/index.md` no longer references deleted reports
2. All cross-references in remaining docs point to valid files
3. `README.md` links still resolve
4. No dangling symlinks or broken navigation
