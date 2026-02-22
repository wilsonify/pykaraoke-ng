# Clarification: Filename Parser Edge Cases

> **Feature ID:** 001
> **Branch:** `001-filename-parser-edge-cases`
> **Status:** Draft
> **Created:** 2026-02-22
>
> **Spec Kit command that produced this:**
> ```
> /speckit.clarify 001-filename-parser-edge-cases
>   --focus security,performance,cross-platform,backward-compatibility
> ```

---

## Feature Reference

→ [spec.md](spec.md)

## Security Considerations

- **Path traversal:** Filenames from ZIP archives may contain `../` sequences.
  The parser must **never** resolve or follow path traversal — it operates
  purely on string content after `os.path.basename()`. This is already the
  case, but a dedicated test must assert it.
- **ReDoS (Regular Expression Denial of Service):** The regex
  `\s+-\s+` is safe (no nested quantifiers). Any new regex patterns
  introduced must be reviewed for catastrophic backtracking. Prefer anchored
  or atomic patterns.
- **Unicode homoglyph attacks:** A malicious filename could use lookalike
  characters (e.g., Cyrillic "А" vs Latin "A"). The parser does **not** need
  to detect homoglyphs — that is out of scope. It must simply preserve
  characters as-is.
- **Null bytes:** Filenames containing `\x00` must not crash the parser.
  Return the stem up to the null byte as the title.

## Performance Considerations

- **Latency budget:** Parsing a single filename must complete in < 100μs on
  commodity hardware. The current regex-based approach easily meets this.
- **Bulk import:** Libraries can contain 10,000+ files. The parser must
  handle bulk invocation without per-call overhead (no file I/O, no network,
  no disk access inside the parser).
- **Regex compilation:** The `_SPACE_DASH_RE` pattern is already compiled at
  module level. Any new patterns must also be module-level compiled constants
  — never compiled inside a method.
- **Memory:** `ParsedSong` is a dataclass with four string fields. No
  concern about memory pressure even at 100k instances.

## Cross-Platform Considerations

- **Windows path separators:** Filenames may arrive with backslashes. The
  existing `filepath.replace("\\", "/")` normalisation must remain and be
  tested explicitly on all platforms.
- **Windows trailing dots:** Windows silently strips trailing dots from
  filenames (e.g., `song..mp3` → `song.mp3`). The parser should handle
  stems with trailing dots gracefully.
- **macOS NFD normalization:** macOS HFS+ decomposes Unicode filenames (NFD).
  A filename stored as `é` (U+00E9) on Linux may appear as `e` + `́`
  (U+0065 + U+0301) on macOS. The parser must produce identical `ParsedSong`
  output for both forms. **Decision:** Apply `unicodedata.normalize("NFC", ...)`
  on the stem before parsing.
- **Case sensitivity:** The parser must not alter case. Artist "AC-DC" must
  remain "AC-DC", not "Ac-Dc".
- **Linux long filenames:** ext4 supports 255 bytes, not 255 characters.
  Multi-byte UTF-8 names can have fewer characters. The parser must not
  assume a character limit.

## Backward Compatibility

- **Public API:** `FilenameParser.parse(filepath) -> ParsedSong` — the
  signature does **not** change. This is fully backward compatible.
- **`ParsedSong` dataclass:** No fields added or removed. Backward
  compatible.
- **`FileNameType` enum:** No values added or removed. Backward compatible.
- **Behavioral change:** Some filenames that previously parsed incorrectly
  (e.g., `AC-DC-Back In Black.cdg` returned `artist="AC"`) will now return
  `artist="AC-DC"`. This is a **bug fix**, not a breaking change, but must
  be documented in the changelog.
- **`parse_zip_path`:** No signature change. Internal behavior may improve
  for edge cases — this is additive, not breaking.
- **Risk:** Users who have built workarounds for incorrect parsing (e.g.,
  manual renames) may see duplicate entries if they re-scan. This is
  acceptable — the correct behavior is now canonical.

## Dependency Impact

- **No new dependencies.** All parsing uses `re`, `os`, `dataclasses`,
  `unicodedata` — all stdlib.
- `mutagen` is not involved (metadata tag reading is out of scope).

## Ambiguities Identified

1. **Should full-width parentheses be normalized?**
   → **Resolution:** Yes. Apply a normalisation pass that converts full-width
   ASCII variants (U+FF01–U+FF5E) to their ASCII equivalents before parsing.

2. **What about filenames with multiple space-dash-space separators?**
   → **Resolution:** Already handled — `_SPACE_DASH_RE.split(stem, maxsplit=1)`
   splits only on the first occurrence. Everything after is the title. This is
   correct and intentional.

3. **Should the abbreviation heuristic be configurable?**
   → **Resolution:** No. Keep the current `_is_abbreviation_part()` heuristic
   as-is. It works for the known cases (AC-DC, ZZ-Top, MC-Hammer). If a user
   reports a false positive/negative, we'll address it as a follow-up.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regex change breaks existing passing tests | Medium | High | Run full existing test suite first; add regression tests before changing |
| NFC normalization changes output for existing filenames | Low | Medium | Only apply to stem; test with known NFD/NFC pairs |
| Performance regression from added normalization steps | Low | Low | Benchmark before/after with 10k filename corpus |
| Unicode edge case not covered by tests | Medium | Low | Use hypothesis property-based testing for fuzzing |

## Decisions Made

- **Decision:** Use `unicodedata.normalize("NFC")` on stems.
  **Rationale:** Ensures consistent output across macOS/Linux/Windows.

- **Decision:** No new third-party dependencies.
  **Rationale:** stdlib `re` + `unicodedata` is sufficient. Constitution
  requires justification for any new dependency.

- **Decision:** Treat em-dash and en-dash as equivalent to " - " separator.
  **Rationale:** Real-world karaoke files from Asian markets commonly use
  these characters. Users should not need to rename files.
