# Tasks: Library backup and relocation

## 1. Library (test-first, pytest)

- [x] 1.1 `scan(files, replace=True)` clears loose + zip-expanded contents,
      preserves `Settings`; non-replace stays additive.
- [x] 1.2 `prune_songs(known_paths)` removes loose and zip songs absent
      from the known set; empty set is a no-op.
- [x] 1.3 `to_dict()` envelope wrapper for export; `from_dict()` accepts
      bare dict; schema-version check helper.

## 2. Webapp API (pytest)

- [x] 2.1 `scan_files(..., replace=)` wiring; `prune_songs(known)`; both
      exercised through the public webapp surface.
- [x] 2.2 `export_json()` builds `{format, schema: 1, library}`;
      `import_json()` validates, accepts bare or enveloped payloads,
      atomically swaps on success and returns `{ok:false, error}` leaving
      state intact on malformed JSON, unrecognised schema, or invalid
      library.

## 3. UI wiring

- [x] 3.1 Library actions row: "Replace library" (rescans folders + known
      zips with `replace=True`), "Export" (downloads `pykaraoke-library.json`),
      "Import" (file picker → `import_json`), each with status feedback.

## 4. Verification and docs

- [x] 4.1 pytest + ruff + mypy green.
- [x] 4.2 Docs: `docs/reference/engine-api.md` (new API rows) and
      `docs/user-guide/index.md` (relocate / back up / share workflow).
