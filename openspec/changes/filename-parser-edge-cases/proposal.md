# Proposal: Filename Parser Edge Cases

> Status: core shipped 2026-10-10 (NFC composition, Unicode-dash and
> full-width folding, field hygiene incl. trailing dots / zero-width /
> embedded null, and the `TypeError` contract for non-string input), with
> tests and the matching capability-spec requirements merged into
> `openspec/specs/filename-parsing/spec.md`. Remaining tasks are the
> unchecked boxes in [tasks.md](tasks.md).
> Migrated from Spec Kit feature `specs/features/001-filename-parser-edge-cases/`
> (2026-02-22). Capability: `filename-parsing`

## Intent

Users curate karaoke libraries from dozens of sources, and each source uses a
different filename convention. When the parser extracts the wrong artist or
title, the song is still imported — but with blank or garbled metadata — so
the user only discovers the error later, when a search by artist returns
nothing.

The current parser handles the common patterns but **silently mis-parses**
several real-world cases:

- Artists whose names contain internal dashes (`AC-DC - Back In Black.cdg`)
  are split at the wrong dash.
- CJK, Cyrillic, and accented-Latin characters are corrupted or normalised
  inconsistently across platforms.
- Typographic dash variants (em-dash, en-dash, full-width hyphen-minus,
  figure dash) are not recognised as separators at all.
- Leading/trailing whitespace, invisible Unicode whitespace, full-width ASCII
  characters, and trailing dots contaminate the extracted fields.
- Archive members that rely on the directory component for the artist name
  are not handled when the filename itself has no separator.

Because the failure is silent, the user cannot tell correct metadata from
incorrect metadata. This change makes extraction deterministic and complete
for the conventions karaoke libraries actually use.

## Scope

In scope:

- Recognition of Unicode typographic dash variants (em-dash, en-dash,
  full-width hyphen-minus, figure dash, small em-dash) as separator
  equivalents.
- Normalisation of the stem to a canonical composed Unicode form (NFC) so
  macOS (NFD) and Linux/Windows (NFC) produce identical results.
- Normalisation of full-width ASCII variants (U+FF01–U+FF5E) to their ASCII
  equivalents, including full-width parentheses.
- Stripping of leading/trailing whitespace, invisible/zero-width characters,
  and Windows trailing dots before parsing.
- Filenames consisting of a bare title with no separator.
- Parenthetical suffixes (`(Live)`, `(Remix)`, `(Karaoke Version)`) preserved
  as part of the title.
- Improved grouping of artist names with internal dashes (`AC-DC`, `Jay-Z`,
  `MC-Hammer`, `ZZ-Top`).
- Archive member paths where the parent directory supplies the artist name.
- Graceful handling of empty strings, whitespace-only strings, directory-only
  paths, very long filenames, and embedded null bytes without crashing.

Out of scope:

- Embedded metadata tag reading (ID3, Vorbis comments). This exists elsewhere
  in the system and is not part of filename parsing.
- Automatic correction of misspelled artist names.
- Network-based metadata lookup or enrichment services.
- Any user-interface change. This change affects only the correctness of the
  core parsing logic.
- Unicode homoglyph/lookalike detection. Characters are preserved as-is.

## Approach

Add a single normalisation pass, `_normalize_stem()`, applied to the filename
stem after `os.path.splitext()` and before any pattern detection. The pass
applies NFC normalisation, folds Unicode dash variants to the ASCII hyphen,
folds full-width ASCII to plain ASCII, and strips whitespace and Windows
trailing dots. The existing `_parse_space_dash()` and `_parse_legacy()` /
`_parse_artist_title()` strategies then run unchanged against the normalised
stem.

No new dependencies (stdlib `unicodedata` plus the existing `re`/`os`), no
change to the public API (`FilenameParser.parse`, `parse_zip_path`,
`ParsedSong`, `FileNameType`), and no new configuration values. All new
patterns are module-level compiled constants so no per-call compilation is
introduced.
