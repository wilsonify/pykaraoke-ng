# Proposal: Library backup and relocation

> Status: proposed — not implemented.
> Capabilities: `song-library`, `web-engine-api`
> Legacy issues: kelvinlawson/pykaraoke#7 (reallocate file links) and
> #8 (backup and restore library), plus the standing operational need to
> move a library to a new drive or hand a collection to another machine.

## Intent

A karaoke library outlives any one machine or folder. Today the library can
only *accumulate*: scanning a new root adds to the old one, renames leave
stale entries behind, and there is no way to hand a colleague (or a fresh
install) an already-scanned collection. That makes three everyday KJ
operations fragile or impossible:

1. **Relocate** — the collection moves to a new drive, USB stick, or folder
   layout and the app must re-point without carrying ghosts of the old root.
2. **Prune** — files were deleted or renamed on disk and the in-memory list
   should drop what is no longer present.
3. **Back up / share** — export the whole scanned library (songs, pairing,
   folders, settings) to a file and import it elsewhere, atomically and
   with validation, never half-applying a bad payload.

This change adds exactly those three, on top of the pure-stdlib
`SongLibrary` and its webapp wrapper. It is deliberately separated from
`scan-diagnostics-and-filters` (patterns and the scan report) so each
proposal stays coherent.

## Scope

In scope:

* **Replace-scan.** `SongLibrary.scan(files, replace=True)` and the webapp
  `scan_files(..., replace=True)` clear previously scanned loose files and
  zip expansions before applying the new batch. Settings are untouched. The
  default remains additive so existing callers are unaffected.
* **Prune.** `prune_songs(known_paths)` removes loose and zip songs whose
  paths are absent from the caller's known set. An empty known-set is a
  no-op guard so an accidental empty call cannot wipe the library.
* **Export envelope.** `export_json()` wraps `to_dict()` in
  `{"format": …, "schema": 1, "library": …}` and returns it as a string.
* **Import with validation.** `import_json(payload)` parses the string,
  accepts the envelope or a bare library dict, validates structure and
  schema version, and on success replaces the in-memory library
  atomically. On any failure it returns `{"ok": false, "error": …}` and
  leaves the previous library byte-for-byte intact — never a partial state.
* **UI wiring.** A "Replace library" control that rescans the configured
  folders and known zips with `replace=True`, plus "Export"/"Import" file
  controls wired to the two API calls with status feedback.
* Pytest coverage for replace, prune, envelope round-trip, bare-dict
  import, malformed/unknown-schema import, and settings preservation.

Out of scope:

* Watching folders, automatic re-scans, or sync services.
* Versioned migration *between* schema versions (import recognises only the
  current schema and rejects others cleanly; a future change can add
  migrations).
* Backing up the singer store (`pykaraoke-ng:show`), which is
  presentation-layer state, not library data.

## Approach

Replace is implemented in `SongLibrary.scan` by clearing the loose-file
index and the zip-expansion results (but not `Settings`) before the normal
apply path, so every downstream behaviour — pairing, sorting, search — is
untouched. Prune filters both the loose index and the zip-derived songs by
the known-path set and rebuilds. Export/import are thin wrappers over the
existing `to_dict()`/`from_dict()`: the envelope carries a `schema` integer
that `import_json` checks against the current value before delegating, and
the swap is a single reference assignment after `from_dict` has fully
succeeded, so a raising `from_dict` cannot leave a half-built library.
