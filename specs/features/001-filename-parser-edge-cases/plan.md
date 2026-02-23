# Technical Plan: Filename Parser Edge Cases

> **Feature ID:** 001
> **Branch:** `001-filename-parser-edge-cases`
> **Status:** Draft
> **Created:** 2026-02-22
>
> **Spec Kit command that produced this:**
> ```
> /speckit.plan 001-filename-parser-edge-cases
>   --language python
>   --typing strict
>   --testing pytest --parameterized
>   --strategy regex
>   --no-third-party
>   --coverage-target 95
> ```

---

## Feature Reference

→ [spec.md](spec.md) · [clarify.md](clarify.md)

## Implementation Language / Stack

- **Python 3.13+** — strict type annotations (`mypy --strict`).
- **stdlib only:** `re`, `os`, `unicodedata`, `dataclasses`, `enum`, `logging`.
- **No third-party parsing libraries** — regex-based strategy is sufficient
  and keeps the dependency tree clean.

## Architecture

```
src/pykaraoke/core/filename_parser.py   ← All changes here
tests/pykaraoke/core/test_filename_parser.py  ← Test file
```

The parser is a pure function layer in the **Core** module. It has no side
effects, no I/O, no state mutation, and no dependency on any other PyKaraoke
module. This isolation makes it ideal for exhaustive unit testing.

**Data flow:**
```
filepath (str)
  → os.path.basename()
  → os.path.splitext()
  → _normalize_stem()        # NEW: NFC + full-width ASCII + dash variants
  → _SPACE_DASH_RE match?
    ├─ YES → _parse_space_dash()
    └─ NO  → _parse_legacy()
  → ParsedSong
```

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pykaraoke/core/filename_parser.py` | Modify | Add `_normalize_stem()`, update dash regex, harden edge cases |
| `tests/pykaraoke/core/test_filename_parser.py` | Modify | Add parameterized edge-case tests, failure-mode tests |
| `tests/pykaraoke/core/test_filename_parser_bulk.py` | Create | Performance benchmark (10k filenames in <1s) |

## Key Design Decisions

1. **Single normalization pass before any parsing logic.**
   All Unicode normalization (NFC, full-width → ASCII, dash variants → ASCII
   dash) happens in one private function `_normalize_stem()`. This keeps the
   existing `_parse_space_dash()` and `_parse_legacy()` methods unchanged.

2. **Module-level compiled regex constants for all new patterns.**
   Avoids per-call compilation overhead. Pattern names follow the existing
   `_SPACE_DASH_RE` convention.

3. **`maxsplit=1` on the primary split.**
   The artist is always everything before the *first* recognized separator.
   The title is everything after. This preserves subtitles like "Live" and
   "(Remix)" that appear after secondary separators.

4. **No changes to `ParsedSong`, `FileNameType`, or public method signatures.**
   Full backward compatibility. The only behavioral change is *more correct*
   parsing of previously-mishandled filenames.

## Data Structures

No new data structures. Existing:

```python
@dataclass
class ParsedSong:
    artist: str = ""
    title: str = ""
    disc: str = ""
    track: str = ""
```

## Algorithm / Strategy

### New: `_normalize_stem(stem: str) -> str`

```
1. Apply unicodedata.normalize("NFC", stem)
2. Replace Unicode dash variants with ASCII hyphen:
   - U+2014 (em dash — )
   - U+2013 (en dash – )
   - U+FF0D (fullwidth hyphen-minus － )
   - U+2012 (figure dash ‒ )
   - U+FE58 (small em dash ﹘ )
3. Replace fullwidth ASCII characters (U+FF01–U+FF5E) with
   their ASCII equivalents (subtract 0xFEE0).
4. Strip leading/trailing whitespace.
5. Strip trailing dots (Windows normalization).
6. Return the normalized stem.
```

### Updated: `parse()` method

```
1. basename + splitext (existing)
2. Call _normalize_stem() on the stem          ← NEW
3. Handle empty/whitespace result → ParsedSong(title="")
4. Check for _SPACE_DASH_RE → _parse_space_dash()
5. Else → _parse_legacy()
```

### Regex Patterns (module-level constants)

```python
# Existing
_SPACE_DASH_RE = re.compile(r"\s+-\s+")

# New: matches em-dash, en-dash variants as separators
# (after normalization, these are already converted to ASCII,
#  so this constant is defensive only)
_UNICODE_DASH_RE = re.compile(r"[\u2012\u2013\u2014\uFF0D\uFE58]")
```

## Testing Strategy

- **Framework:** `pytest` with `pytest-cov`.
- **Approach:** Heavy use of `@pytest.mark.parametrize` for all edge cases.
- **Coverage target:** ≥ 95% branch coverage for `filename_parser.py`.
- **Performance test:** `test_filename_parser_bulk.py` generates 10,000
  filenames from templates and asserts total parse time < 1.0 second.

### Parameterized Test Matrix

```python
@pytest.mark.parametrize("filename, expected_artist, expected_title", [
    # Happy path
    ("Artist - Title.mp3", "Artist", "Title"),
    # Unicode em-dash
    ("Artist — Title.mp3", "Artist", "Title"),
    # Fullwidth dash
    ("Artist－Title.mp3", "Artist", "Title"),
    # Abbreviation artist
    ("AC-DC - Back In Black.cdg", "AC-DC", "Back In Black"),
    # Abbreviation in legacy mode
    ("AC-DC-Back In Black.cdg", "AC-DC", "Back In Black"),
    # Empty string
    ("", "", ""),
    # Whitespace only
    ("   ", "", ""),
    # No extension
    ("Artist - Title", "Artist", "Title"),
    # Multiple extensions
    ("Artist - Title.cdg.bak", "Artist", "Title.cdg"),  # strips last ext only
    # CJK characters
    ("初音ミク - 千本桜.mp3", "初音ミク", "千本桜"),
    # Path traversal in input (safety)
    ("../../etc/passwd", "", "../../etc/passwd"),  # basename strips path
    # Only dashes
    ("----.mp3", "", "----"),
    # Very long filename
    ("A" * 300 + " - " + "B" * 300 + ".mp3", "A" * 300, "B" * 300),
])
```

## Error Handling

| Condition | Response |
|-----------|----------|
| Empty/whitespace input | Return `ParsedSong(title="")` |
| `None` input | Raise `TypeError` (let Python's `os.path.basename` raise naturally) |
| Unrecognized pattern | Return `ParsedSong(title=stem)`, log `DEBUG` |
| `UnicodeDecodeError` | Catch, return `ParsedSong()`, log `WARNING` |

All errors are logged via `logger = logging.getLogger(__name__)`. No
exceptions are swallowed silently.

## Performance Considerations

- **Time complexity:** O(n) where n = length of filename string. Single-pass
  normalization + single regex search + one split. No backtracking risk.
- **Space complexity:** O(n) for the normalized stem copy.
- **Benchmark:** 10,000 parses in < 1 second (amortized < 100μs each).
  Measured with `time.perf_counter()` in the bulk test.
