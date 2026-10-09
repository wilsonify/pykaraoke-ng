# Design: Filename Parser Edge Cases

> Status: proposed — not implemented. Technical plan migrated from Spec Kit
> feature `specs/features/001-filename-parser-edge-cases/plan.md`, with the
> module paths corrected to the current repository layout.

## Technical Approach

All changes live in the pure core parsing layer:

```
src/pykaraoke/filename_parser.py        ← all production changes
tests/pykaraoke/test_filename_parser.py ← edge-case and failure-mode tests
tests/pykaraoke/test_filename_parser_bulk.py ← performance benchmark (new)
```

> Path correction: the original plan referenced `src/pykaraoke/core/…` and
> `tests/pykaraoke/core/…`. The package was later flattened; the parser is now
> `src/pykaraoke/filename_parser.py` and its tests are
> `tests/pykaraoke/test_filename_parser.py`. The proposed test file
> `tests/pykaraoke/test_filename_parser_bulk.py` does not exist yet.

Data flow after the change:

```
filepath (str)
  → os.path.basename(filepath.replace("\\", "/"))   # existing: path + separators
  → os.path.splitext()                              # existing: strip last extension
  → _normalize_stem()                               # NEW: NFC + dashes + full-width + strip
  → _SPACE_DASH_RE.search()?
      ├─ YES → _parse_space_dash()
      └─ NO  → _parse_legacy() → _parse_artist_title()
  → ParsedSong
```

`_normalize_stem()` performs, in order:

1. `unicodedata.normalize("NFC", stem)`.
2. Replace Unicode dash variants with the ASCII hyphen: U+2012 (figure dash),
   U+2013 (en dash), U+2014 (em dash), U+FF0D (full-width hyphen-minus),
   U+FE58 (small em dash).
3. Replace full-width ASCII characters U+FF01–U+FF5E with their ASCII
   equivalents (subtract 0xFEE0), which also folds full-width parentheses.
4. Strip leading/trailing whitespace and invisible/zero-width characters.
5. Strip trailing dots (Windows filesystem artefact).
6. Return the normalised stem.

The existing split strategies are then re-used unchanged: the primary split
remains `_SPACE_DASH_RE.split(stem, maxsplit=1)` so only the first separator
divides artist from title and later segments (subtitles, parentheticals) stay
in the title. The abbreviation heuristic in `_parse_artist_title()` is kept
as-is.

New module-level constants follow the existing `_SPACE_DASH_RE` convention:

```python
_SPACE_DASH_RE = re.compile(r"\s+-\s+")                     # existing
_UNICODE_DASH_RE = re.compile(r"[\u2012\u2013\u2014\uFF0D\uFE58]")  # defensive
```

## Architecture Decisions

### Decision: One normalisation pass, not per-branch clean-up

All Unicode and whitespace normalisation happens in a single private function
called once from `parse()`. This keeps `_parse_space_dash()` and
`_parse_legacy()` untouched, so the change cannot regress the patterns that
already work and the new behaviour is testable in isolation.

### Decision: NFC (composed) normalisation

macOS decomposes filenames (NFD) while Linux and Windows compose them (NFC).
Normalising to NFC before parsing makes the same visible filename produce
byte-identical `ParsedSong` output on every platform. Applied to the stem
only, never to the full path.

### Decision: Fold dash variants to ASCII rather than extend the regex

Folding each variant to `-` in the normalisation pass means the existing
`_SPACE_DASH_RE` (and the legacy `str.split("-")`) keep working for every
variant, and the parsed `artist`/`title` never contain a stray em-dash that
would break downstream search and sorting.

### Decision: No new dependencies, no public API change

`unicodedata` is stdlib. `ParsedSong`, `FileNameType`,
`FilenameParser.parse()`, and `parse_zip_path()` keep their current
signatures and fields, so every existing caller (notably
`src/pykaraoke/database.py`) works unchanged. The only behavioural difference
is more-correct parsing of previously mishandled filenames, which is
classified as a bug fix, not a breaking change.

### Decision: Keep the abbreviation heuristic non-configurable

`_is_abbreviation_part()` stays a fixed heuristic for the known cases
(`AC-DC`, `ZZ-Top`, `MC-Hammer`). Making it configurable is deferred until a
real false positive/negative is reported.

### Decision: Pure computation, offline

Parsing performs no I/O, no network access, and no environment/locale reads.
This keeps it exhaustively testable and avoids locale-dependent behaviour, in
line with the project governance invariants.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A regex change breaks existing passing tests | Medium | High | Run the full existing test suite first; add regression tests before changing production code |
| NFC normalisation changes output for filenames that already parsed correctly | Low | Medium | Apply to the stem only; test with known NFD/NFC pairs and assert equality |
| Added normalisation steps regress performance | Low | Low | Keep all patterns module-level compiled; benchmark with a 10,000-filename corpus |
| An unanticipated Unicode edge case is missed | Medium | Low | Add parameterised cases for every documented variant; consider property-based fuzzing |
| New separators mis-split an artist whose name legitimately contains a dash | Medium | Medium | `maxsplit=1` keeps the first separator authoritative; add `AC-DC`/`Jay-Z` regression cases |
| Windows trailing-dot stripping removes a legitimately dot-terminated title | Low | Low | Only strip trailing dots from the stem's end, never interior dots |

## Open Questions

- Should full-width parentheses `（）` be normalised to ASCII `()`?
  **Tentative decision:** Yes — fold all U+FF01–U+FF5E to ASCII in the same
  pass. (Captured as edge case 15 in the original spec.)
- Should aggregate parse statistics (files parsed, patterns matched,
  patterns unrecognised) be emitted automatically during bulk import, or only
  on request? **Tentative decision:** emit at info severity automatically;
  callers can raise the log level to silence it.
- How should the parser behave when a filename has multiple ` - ` separators
  and the artist itself contains one (e.g. `Artist - Name - Title`)?
  **Tentative decision:** current behaviour (first separator splits) is
  correct and intentional; a follow-up will only change it if a real-world
  counter-example appears.
- Which failures should be logged versus raised? **Tentative decision:**
  unrecognisable patterns log at debug and return a title-only result;
  encoding errors log at warning and return an empty result; a `None` input
  raises `TypeError` (caller defect — fail fast).
