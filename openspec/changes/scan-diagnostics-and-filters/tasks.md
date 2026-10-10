# Tasks: Scan diagnostics and patterns

## 1. Library (test-first, pytest)

- [ ] 1.1 `Settings.include_patterns` / `exclude_patterns` + round-trip;
      `_name_allowed()` predicate (case-insensitive fnmatch, exclude wins,
      empty include = all, invalid pattern = literal).
- [ ] 1.2 Scan report: `_report()` collector, `scan_report()`,
      `clear_scan_report()`; categories `unsupported`, `filtered`,
      `corrupt_archive`, `unsupported_compression`, `unreadable`,
      `parse_failure` with counts; reporting never aborts a scan.
- [ ] 1.3 Zip path: distinguish corrupt vs unsupported-compression vs
      unreadable members into report kinds; member cache written by
      `scan_zip` and consulted by `_rebuild()` so zip songs survive
      settings-triggered rebuilds.

## 2. Webapp API (pytest)

- [ ] 2.1 `scan_report()` / `clear_scan_report()`; `set_settings` accepts
      the two pattern keys and they round-trip through `get_settings`.

## 3. UI wiring

- [ ] 3.1 Settings: include/exclude pattern text inputs (comma/newline
      separated) persisted through `set_settings`.
- [ ] 3.2 Scan summary line under the library header: counts per category,
      first few problem paths, dismiss/clear control.

## 4. Verification

- [ ] 4.1 pytest + ruff + mypy green; vitest untouched/green.
- [ ] 4.2 Docs: `docs/reference/configuration.md` pattern rows;
      `docs/reference/engine-api.md` new API rows; issue #5 section in
      `docs/reference/original-pykaraoke-issues.md`.
