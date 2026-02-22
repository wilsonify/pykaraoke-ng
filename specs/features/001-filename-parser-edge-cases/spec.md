# Specification: Improved Filename Parsing for Artist/Title Extraction

> **Feature ID:** 001
> **Branch:** `001-filename-parser-edge-cases`
> **Status:** Draft
> **Author:** PyKaraoke-NG Contributors
> **Created:** 2026-02-22
>
> **Spec Kit command that produced this:**
> ```
> /speckit.specify Improve filename parsing for artist/title extraction
>                  with full edge-case handling
> ```

---

## Feature Title

Robust artist/title extraction from karaoke filenames across all naming
conventions and international character sets.

## Problem Statement

Users curate karaoke libraries from dozens of sources. Each source uses a
different filename convention — some use " - " separators, others use plain
dashes, others embed disc/track codes, and some rely on directory structure.
When the parser fails to extract the correct artist or title, the song appears
in the library with a blank artist or a garbled title, making it impossible to
search, sort, or browse effectively.

Current parsing covers the most common patterns but silently produces incorrect
results for several real-world edge cases:

- Filenames with **multiple consecutive dashes** (e.g., `AC-DC - Back In Black.cdg`).
- Filenames with **Unicode characters** (e.g., CJK, accented Latin, Cyrillic).
- Filenames with **leading/trailing whitespace** or invisible Unicode whitespace.
- Filenames with **no separator at all** (just a bare title).
- Filenames with **parenthetical suffixes** that should be part of the title
  (e.g., `(Live)`, `(Karaoke Version)`).
- Filenames from **ZIP archives** where the directory structure provides artist
  context.
- Filenames using **full-width dashes** (U+FF0D) or **em-dashes** (U+2014)
  instead of ASCII hyphens.

## User Impact

- **Karaoke hosts** will see correctly attributed songs in their library without
  manual renaming.
- **Search accuracy** improves — users can find songs by artist name reliably.
- **Sorting and grouping** by artist becomes trustworthy.
- **Import from ZIP** produces clean metadata without manual post-processing.

## Desired Outcome

Given any filename that follows a recognizable karaoke naming convention, the
parser returns a `ParsedSong` with the correct `artist`, `title`, `disc`, and
`track` fields. When no convention is recognized, the parser returns the entire
stem as the `title` and leaves `artist` empty — never crashes, never returns
garbage.

## Scope

### In Scope

- All patterns currently documented in `FilenameParser` docstring.
- New pattern: Unicode dash variants (em-dash, en-dash, full-width dash).
- New pattern: filenames with only a bare title (no separator).
- New pattern: filenames where parenthetical suffixes belong to the title.
- Improved handling of artist names containing dashes (AC-DC, Jay-Z, etc.).
- ZIP archive path parsing with directory-as-artist fallback.
- Graceful handling of empty strings, whitespace-only strings, and paths with
  no filename component.
- Normalisation of invisible/zero-width Unicode characters.

### Out of Scope

- ID3/metadata tag reading (handled by `mutagen` elsewhere).
- Automatic correction of misspelled artist names.
- Network-based metadata lookup (MusicBrainz, etc.).
- GUI changes — this is purely backend parsing logic.

## Edge Cases

1. **Empty string input** → Return `ParsedSong(title="")`.
2. **Whitespace-only filename** → Return `ParsedSong(title="")`.
3. **No extension** → Parse the full string as the stem.
4. **Multiple extensions** (e.g., `song.cdg.bak`) → Strip only the last extension.
5. **Directory-only path** (e.g., `/music/karaoke/`) → Return empty `ParsedSong`.
6. **Unicode em-dash separator** (`Artist — Title.mp3`) → Treat as " - " equivalent.
7. **Full-width dash** (`Artist－Title.mp3`) → Treat as dash separator.
8. **CJK characters in artist/title** → Preserve exactly, no mojibake.
9. **Artist name with internal dashes** (`AC-DC`, `Jay-Z`) → Group into artist field.
10. **Filename with only dashes** (`----.mp3`) → Return as title.
11. **Very long filenames** (>255 characters) → Parse without truncation or crash.
12. **Path separators in stem** (from malformed ZIP entries) → Normalise and extract basename.
13. **Trailing period in stem** (Windows edge case) → Strip before parsing.

## Failure Modes

1. **Completely unrecognizable pattern** → Return full stem as `title`, empty `artist`. Log at `DEBUG` level.
2. **OS path encoding error** → Catch `UnicodeDecodeError`, return empty `ParsedSong`, log at `WARNING`.
3. **None input** → Raise `TypeError` (caller bug — fail fast).

## Acceptance Criteria

- [ ] All 13 edge cases above have passing parameterized tests.
- [ ] All 3 failure modes have passing tests.
- [ ] Existing tests continue to pass (zero regressions).
- [ ] Unit test coverage for `filename_parser.py` ≥ 95%.
- [ ] mypy strict mode passes with no errors.
- [ ] SonarQube reports zero new issues.
- [ ] Parsing 10,000 filenames completes in < 1 second.

## Open Questions

- Should full-width parentheses `（）` be normalised to ASCII `()`?
  **Tentative decision:** Yes, normalise for consistency.
