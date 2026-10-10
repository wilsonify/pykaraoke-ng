# Proposal: Scan diagnostics and include/exclude patterns

> Status: proposed — not implemented.
> Capabilities: `song-library`, `web-engine-api`
> Legacy issues: kelvinlawson/pykaraoke#5 (custom pattern exclusion), part
> of #14 (zip archives must never silently swallow songs).

## Intent

Two related library-trust problems:

1. **Silent exclusion.** A KJ with `_(Vocal)_` versions, disc-swap files, or
   OS droppings in the tree has no way to keep them out short of renaming;
   issue #5 asked for pattern-based hiding.
2. **Silent failure.** When a zip is corrupt, uses unsupported compression,
   or a file is unreadable, the library just *adds nothing* for that input
   and the operator has no idea songs are missing.

These share one code path (`SongLibrary.scan`/`_rebuild` and the webapp
scan wrappers), so they ship as one change. Library relocation (replace
scans, pruning, export/import) is a separate change —
`library-backup-relocation` — and is not duplicated here.

## Scope

In scope:

* **Include/exclude filename patterns** (`fnmatch`-style, case-insensitive)
  in `Settings`, applied to loose file entries *and* zip member names:
  exclude wins; an empty include list means "all". Patterns match the
  basename (or member basename) — e.g. `*_(Vocal)_*`. Persisted and
  round-tripped; invalid patterns are treated as literal text rather than
  raising.
* **Scan reporting.** Every scan path records per-input outcomes in a
  structured report: `unsupported` (no karaoke kind — the common case, not
  an error), `filtered` (excluded by pattern or `exclude_non_matching`),
  `corrupt_archive`, `unsupported_compression`, `unreadable`,
  `parse_failure` (fell back to title-only), plus per-scan counts. The
  webapp exposes `scan_report()` / `clear_scan_report()`; the UI surfaces a
  compact summary with the first few problem paths. Nothing in the report
  aborts a scan.
* **Zip-member cache.** `scan_zip` records parsed members so a later full
  rebuild (triggered by settings changes) keeps zip songs without
  re-reading archives; rebuild takes an explicit path to this cache.
* Pytest coverage for all of the above; vitest only if the settings UI
  gains pure helpers (expected: none).

Out of scope:

* Replace-scan, prune, and export/import — owned by
  `library-backup-relocation`.
* UI pattern pickers beyond text inputs; watching folders; automatic
  re-scans on a timer.

## Approach

`SongLibrary` gains: `settings.include_patterns` / `exclude_patterns`
(lists), `_name_allowed(name)` predicate, `_report(kind, path)` appending to
an in-memory list with counts, `scan_report()` / `clear_scan_report()`, and
a `_zip_member_cache: dict[lowercased_zip_path, list[dict]]` written by
`scan_zip` and consulted by `_rebuild()` when the archive bytes are no
longer available. Zip expansion distinguishes `zipfile.BadZipFile`
(corrupt) from `NotImplementedError`/`LargeZipFile`-style unsupported
compression and `KeyError` on encrypted members (unreadable) into separate
report kinds. The webapp wraps the report accessors one-for-one and accepts
the two pattern keys in `set_settings`.
