# Tasks: Filename Parser Edge Cases

> Status: core shipped 2026-10-10. Tests came first: every group-1 test was
> red before the group-2 implementation landed. Remaining unchecked tasks
> are the format-gate run, the local CI-equivalent suite, the SonarQube
> gate (CI-only), and archiving.
> Capability: `filename-parsing` · Design: [design.md](design.md)

## 1. Test scaffolding (red)

- [x] 1.1 Add parameterised happy-path tests for the patterns that already work (space-dash, legacy disc-track-artist-title, disc-artist-title, artist-title) to `tests/pykaraoke/test_filename_parser.py`; confirm the current suite is green as a regression baseline.
- [x] 1.2 Add parameterised tests for Unicode dash variants — em-dash (`—`), en-dash (`–`), full-width dash (`－`), figure dash (`‒`), small em-dash (`﹘`) — asserting each yields the same `ParsedSong` as the ASCII ` - ` equivalent.
- [x] 1.3 Add parameterised tests for input boundary conditions: empty string, whitespace-only, no extension, multiple extensions (`song.cdg.bak`), directory-only path, trailing dots, and an embedded null byte.
- [x] 1.4 Add parameterised tests for international characters: CJK, Cyrillic, accented Latin, and NFD-vs-NFC pairs that must produce identical output.
- [x] 1.5 Add parameterised tests for full-width ASCII and full-width parentheses (U+FF01–U+FF5E), including `Artist－Title.mp3` and `Artist（Live）.mp3`.
- [x] 1.6 Add parameterised tests for abbreviated artists with internal dashes (`AC-DC`, `Jay-Z`, `MC-Hammer`, `ZZ-Top`) in both the modern and legacy paths.
- [x] 1.7 Add failure-mode tests: `None` input raises `TypeError`; an unrecognised pattern returns a title-only result; a `../` path traversal input is reduced to a safe basename.
- [x] 1.8 Add parameterised tests for `parse_zip_path()` edge cases: deeply nested paths, backslash paths, no-directory paths, and directory-as-artist fallback with Unicode names.
- [x] 1.9 Create the bulk performance test generating 10,000 filenames from templates and asserting total parse time < 1.0 s, marked `@pytest.mark.slow` (marker registered in `pyproject.toml`).

## 2. Implementation (green)

- [x] 2.1 Implement `_normalize_stem(stem: str) -> str` in `src/pykaraoke/filename_parser.py`: NFC normalisation, dash-variant folding, full-width ASCII folding, whitespace/zero-width stripping, trailing-dot stripping.
- [x] 2.2 Wire `_normalize_stem()` into `FilenameParser.parse()` after `os.path.splitext()`, before pattern detection; return an empty `ParsedSong(title="")` for empty/whitespace stems.
- [x] 2.3 Add the module-level compiled `_UNICODE_DASH_RE` (or equivalent) constant following the `_SPACE_DASH_RE` naming convention; never compile a pattern inside a method.
- [x] 2.4 Verify `_parse_space_dash()` needs no change (or the minimal change) against normalised input, preserving `maxsplit=1` semantics.
- [x] 2.5 Verify `_parse_legacy()` / `_parse_artist_title()` still behave correctly for normalised input, including dashes inside artist names.
- [x] 2.6 Run the group-1 tests and confirm every one passes (red → green).

## 3. Refactor

- [x] 3.1 Extract any repeated normalisation logic and give every private helper a clear docstring; confirm no module-level mutable state was introduced.
- [x] 3.2 Add or verify complete type annotations (`mypy --strict src/pykaraoke/filename_parser.py`); use `list[str]` rather than bare `list` in `_parse_artist_title`.
- [ ] 3.3 Run `ruff check` and `ruff format` on the parser and its tests; fix all violations. (Covered by the repo-wide format gate; `ruff check` already clean.)

## 4. Integration

- [x] 4.1 Verify integration with library scanning: run `tests/pykaraoke/test_database.py` and confirm the `FilenameParser` change does not break the import flow.
- [x] 4.2 Verify cross-platform path handling with Windows-style backslashes and mixed separators (e.g. `C:\music/karaoke\song.cdg`).
- [x] 4.3 Run the full suite with coverage and confirm zero regressions and ≥ 95% branch coverage for `filename_parser.py` (measured 99%).

## 5. Documentation and validation

- [x] 5.1 Update the `filename_parser.py` module docstring to list the newly supported patterns and the normalisation behaviour.
- [x] 5.2 Update the user-facing documentation (`docs/user-guide/`) if any page describes filename conventions, and note the behavioural correction in the release changelog. (No user-guide page describes filename conventions; the capability spec and reference docs carry the behaviour. Shipped behaviour is recorded in `openspec/specs/filename-parsing/spec.md`.)
- [ ] 5.3 Run the full CI-equivalent suite locally (`pytest tests/pykaraoke/ --cov=src/pykaraoke`, `mypy --strict`, `ruff check`) and confirm all stages pass.
- [ ] 5.4 Confirm the SonarQube quality gate passes with zero new bugs, vulnerabilities, or code smells and new-code coverage ≥ 80%. (Enforced by CI after merge.)
- [ ] 5.5 Confirm the delta spec in `specs/filename-parsing/spec.md` matches the shipped behaviour, then archive this change (`openspec archive filename-parser-edge-cases --yes`).
