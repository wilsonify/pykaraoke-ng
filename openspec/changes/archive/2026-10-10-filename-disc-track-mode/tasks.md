# Tasks: Disc-track spaced naming mode

## 1. Parser (test-first)

- [x] 1.1 Add `FileNameType.DISC_TRACK_SPACED = 4` and route space-dash
      stems through `_parse_disc_track_spaced()` when selected; pytest
      cases: issue #14 examples (CB30055-15, SC3448-03 dashed artist,
      CB5056-03-06 multi-dash prefix), title-with-extra-separators,
      plain `Artist - Title` fallback, unspaced stem fallback, zip member
      path, empty/whitespace input, modes 0–3 non-regression.

## 2. Settings exposure

- [x] 2.1 Confirm `set_settings("file_name_type", 4)` round-trips through
      `webapp.py` (pytest) and clamps/rejects out-of-range values
      consistently with existing settings handling.
- [x] 2.2 Settings panel: labelled select for the naming convention
      (0–4 with human-readable labels), persisted and restored.

## 3. Verification and docs

- [x] 3.1 Full pytest + ruff + mypy green.
- [x] 3.2 Update `docs/reference/configuration.md` (`file_name_type` row:
      0–4, new label) and the issue #14 section in
      `docs/reference/original-pykaraoke-issues.md` (spaced mode now
      implemented; keep the unspaced-ambiguity caveat).
