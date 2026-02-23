# Task Breakdown: Filename Parser Edge Cases

> **Feature ID:** 001
> **Branch:** `001-filename-parser-edge-cases`
> **Status:** Draft
> **Created:** 2026-02-22
>
> **Spec Kit command that produced this:**
> ```
> /speckit.tasks 001-filename-parser-edge-cases
> ```

---

## Feature Reference

→ [spec.md](spec.md) · [clarify.md](clarify.md) · [plan.md](plan.md)

---

## Phase 1: Test Scaffolding (Red)

> _Write all tests FIRST. Every test must FAIL before any production code changes._

- [ ] **T01** — Add parameterized happy-path tests for existing patterns
  - File: `tests/pykaraoke/core/test_filename_parser.py`
  - Cover: space-dash, legacy disc-track-artist-title, artist-title
  - Assert: existing tests still pass (regression baseline)

- [ ] **T02** — Add parameterized edge-case tests for Unicode dash variants
  - Cases: em-dash (`—`), en-dash (`–`), fullwidth dash (`－`), figure dash (`‒`)
  - Each must produce the same `ParsedSong` as the ASCII ` - ` equivalent

- [ ] **T03** — Add parameterized edge-case tests for input boundary conditions
  - Cases: empty string, whitespace-only, no extension, multiple extensions,
    directory-only path, trailing dots, null bytes in filename

- [ ] **T04** — Add parameterized edge-case tests for international characters
  - Cases: CJK (日本語), Cyrillic (Кириллица), accented Latin (café),
    NFD vs NFC decomposed forms

- [ ] **T05** — Add parameterized edge-case tests for abbreviation artists
  - Cases: `AC-DC`, `Jay-Z`, `MC-Hammer`, `ZZ-Top`, artist with single-letter
    segments

- [ ] **T06** — Add failure-mode tests
  - Cases: `None` input → `TypeError`, unrecognized pattern → title-only,
    path traversal → safe basename extraction

- [ ] **T07** — Add parameterized tests for `parse_zip_path()` edge cases
  - Cases: deeply nested paths, backslash paths, paths with no directory,
    directory-as-artist fallback with Unicode

- [ ] **T08** — Create `test_filename_parser_bulk.py` performance benchmark
  - File: `tests/pykaraoke/core/test_filename_parser_bulk.py`
  - Generate 10,000 filenames from templates
  - Assert total parse time < 1.0 second
  - Mark with `@pytest.mark.slow`

---

## Phase 2: Implementation (Green)

> _Make each failing test pass. Minimal code only._

- [ ] **T09** — Implement `_normalize_stem()` private function
  - NFC normalization via `unicodedata.normalize`
  - Unicode dash variant → ASCII hyphen replacement
  - Fullwidth ASCII → standard ASCII conversion
  - Trailing dot stripping
  - Whitespace stripping

- [ ] **T10** — Wire `_normalize_stem()` into `FilenameParser.parse()`
  - Call after `os.path.splitext()`, before pattern detection
  - Handle empty/whitespace result → `ParsedSong(title="")`

- [ ] **T11** — Update `_parse_space_dash()` if needed for normalized input
  - Verify behavior with normalized stems
  - Should require zero or minimal changes

- [ ] **T12** — Update `_parse_legacy()` / `_parse_artist_title()` if needed
  - Verify abbreviation heuristic still works on normalized input
  - Ensure dashes in artist names (AC-DC) are handled correctly

- [ ] **T13** — Verify all Phase 1 tests now pass
  - Run: `pytest tests/pykaraoke/core/test_filename_parser.py -v`
  - Run: `pytest tests/pykaraoke/core/test_filename_parser_bulk.py -v -m slow`

---

## Phase 3: Refactor

> _All tests green. Now clean up._

- [ ] **T14** — Refactor for clarity and DRY
  - Extract any repeated normalisation logic
  - Ensure all private helpers have clear docstrings
  - Verify no global mutable state (constitution §4.1)

- [ ] **T15** — Add/verify full type annotations
  - Run: `mypy --strict src/pykaraoke/core/filename_parser.py`
  - Fix any issues (return types, parameter types, variable types)
  - Ensure `list[str]` not `list` in `_parse_artist_title` signature

- [ ] **T16** — Run ruff and fix lint violations
  - Run: `ruff check src/pykaraoke/core/filename_parser.py`
  - Run: `ruff format src/pykaraoke/core/filename_parser.py`

---

## Phase 4: Integration

- [ ] **T17** — Verify integration with database scanning
  - Run: `pytest tests/pykaraoke/core/test_database.py -v`
  - Ensure `FilenameParser` changes don't break database import flow

- [ ] **T18** — Verify cross-platform path handling
  - Test with Windows-style backslash paths in parameterized tests
  - Test with mixed separators (`C:\music/karaoke\song.cdg`)

- [ ] **T19** — Run full test suite
  - Run: `pytest tests/ -v --cov=src/pykaraoke --cov-report=term-missing`
  - Confirm zero regressions
  - Confirm coverage ≥ 95% for `filename_parser.py`

---

## Phase 5: Documentation & Validation

- [ ] **T20** — Update module docstring in `filename_parser.py`
  - Add newly supported patterns to the docstring header
  - Document the normalization behavior

- [ ] **T21** — Update `docs/` if parser behavior is user-facing
  - Check if any user documentation references filename conventions
  - Update as needed

- [ ] **T22** — Run full CI pipeline locally
  - Run: `pytest tests/pykaraoke/ --cov=src/pykaraoke --cov-report=xml --junitxml=pytest-junit.xml -v`
  - Run: `mypy --strict src/pykaraoke/core/filename_parser.py`
  - Run: `ruff check src/pykaraoke/`

- [ ] **T23** — Verify SonarQube quality gate
  - Push to feature branch
  - Confirm: 0 new bugs, 0 new vulnerabilities, 0 new code smells
  - Confirm: new code coverage ≥ 80%

- [ ] **T24** — Complete spec checklist
  - Run: `/speckit.checklist 001-filename-parser-edge-cases`
  - All items must be ✅ before PR is opened

---

## Estimated Effort

| Phase | Effort | Notes |
|-------|--------|-------|
| Phase 1: Test Scaffolding | Medium | ~2 hours — many parameterized cases |
| Phase 2: Implementation | Small | ~1 hour — `_normalize_stem()` is straightforward |
| Phase 3: Refactor | Small | ~30 min — types + lint |
| Phase 4: Integration | Small | ~30 min — mostly running existing tests |
| Phase 5: Validation | Small | ~30 min — CI + Sonar |
| **Total** | **Medium** | **~4.5 hours** |
