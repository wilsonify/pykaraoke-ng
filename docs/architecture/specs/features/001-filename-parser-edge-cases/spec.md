# Specification: Improved Filename Parsing for Artist/Title Extraction

> **Feature ID:** 001
> **Branch:** `001-filename-parser-edge-cases`
> **Status:** Draft
> **Author:** PyKaraoke-NG Contributors
> **Created:** 2026-02-22
> **Revised:** 2026-02-22 — Purged technology references; aligned with
>   `/speckit.specify` phase discipline.
>
> **Spec Kit command that produced this:**
> ```
> /speckit.specify Improve filename parsing for artist/title extraction
>                  with full edge-case handling
> ```

---

## Feature Title

Robust artist and title extraction from karaoke filenames across all naming
conventions, international character sets, and operating system environments.

---

## Problem Statement

Users curate karaoke libraries from dozens of sources. Each source uses a
different filename convention — some use spaced-dash separators (`" - "`),
others use plain dashes, others embed disc and track codes, and some rely on
directory structure to convey the artist name. When the system fails to extract
the correct artist or title, the song appears in the library with a blank
artist or a garbled title, making it impossible to search, sort, or browse
effectively.

Current parsing covers the most common patterns but **silently produces
incorrect results** for several real-world edge cases:

- Filenames with **artist names containing internal dashes** (e.g.,
  `AC-DC - Back In Black.cdg`) where the artist is split at the wrong dash.
- Filenames with **Unicode characters** (CJK, accented Latin, Cyrillic) that
  are corrupted, truncated, or normalised inconsistently across platforms.
- Filenames with **leading/trailing whitespace** or invisible Unicode
  whitespace that contaminates extracted fields.
- Filenames with **no separator at all** (just a bare title) that produce
  empty or undefined results.
- Filenames with **parenthetical suffixes** that should be part of the title
  (e.g., `(Live)`, `(Karaoke Version)`) but are dropped or mis-attributed.
- Filenames from **compressed archives** where the directory structure provides
  the artist context, but the system ignores it.
- Filenames using **typographic dash variants** — em-dash (U+2014), en-dash
  (U+2013), full-width hyphen-minus (U+FF0D), figure dash (U+2012) — instead
  of ASCII hyphens, which are not recognised as separators.

These failures are **silent**. The system returns plausible-looking but wrong
metadata and the user does not discover the error until they search by artist
and find nothing.

---

## User Impact

- **Karaoke hosts** will see correctly attributed songs in their library
  without having to manually rename files before import.
- **Search accuracy** improves — users can reliably find songs by artist name.
- **Sorting and grouping** by artist becomes trustworthy across the entire
  library.
- **Compressed-archive import** produces clean metadata without manual
  post-processing.
- **International users** (CJK, Cyrillic, accented-Latin locales) see their
  native characters preserved exactly — no garbling, no lossy transliteration.

---

## Desired Outcome

Given any filename that follows a recognisable karaoke naming convention, the
system extracts the correct **artist**, **title**, **disc identifier**, and
**track number** as structured metadata. When no convention is recognised, the
system returns the full filename stem as the title and leaves the artist empty.

**Invariants:**

- The parser **never crashes**, regardless of input.
- The parser **never returns garbled or partially-decoded text**.
- The parser **never silently discards characters** from artist or title.
- Results are **deterministic**: identical input always produces identical
  output, on every supported platform, with no dependence on locale settings.

---

## Architectural Constraints

> These constraints describe the **decision criteria** that shape any
> implementation of this feature. They are technology-agnostic and express
> the project's non-functional requirements.

### AC-1: Pure Computation, No Side Effects

Filename parsing is a **pure transformation**: string in → structured metadata
out. It must perform zero file I/O, zero network access, and zero disk access.
It must not read environment variables, locale settings, or system
configuration. This enables exhaustive testing, fearless parallelism, and
deterministic behaviour.

### AC-2: Strict Separation from User Interface

Filename parsing is **core logic**. It must contain no rendering, no display
code, no event handling, and no dependency on any user-interface subsystem. It
communicates only through its input/output contract: a string in, structured
metadata out.

### AC-3: Cross-Platform Determinism

The same input must produce **byte-identical output** on every supported
operating system (Linux, macOS, Windows). This requires:

- Normalising path separators before parsing (backslash and forward-slash
  equivalence).
- Normalising Unicode to a canonical composed form so that the same character
  encoded differently on different filesystems produces identical metadata.
- Not relying on OS-specific filename length limits, case-folding rules, or
  trailing-character stripping behaviour.

### AC-4: No Global Mutable State

The parser must hold no module-level mutable variables. All configuration
(such as the expected naming convention) is passed at construction time or
call time. Concurrent callers must never observe shared-state interference.

### AC-5: Minimal External Dependencies

The parsing operation should rely only on capabilities available in the
language's standard library. No third-party parsing libraries may be
introduced without a compelling justification evaluated during the planning
phase.

### AC-6: Strong Typing

All public interfaces of the parser must carry complete, verifiable type
declarations. The use of untyped or dynamically-typed escape hatches (such as
"any" types) is prohibited. Static analysis must be able to verify type
correctness without runtime execution.

### AC-7: Observability

The parser must emit structured, levelled log messages for diagnostic
scenarios. No output to standard streams. Log calls must carry sufficient
context to identify the input that triggered them without exposing sensitive
data.

---

## Supported Naming Conventions

The following filename patterns must be correctly recognised and parsed. For
each pattern the expected field extraction is shown.

| Pattern | Example | Artist | Title | Disc | Track |
|---------|---------|--------|-------|------|-------|
| Spaced-dash | `Artist - Title.ext` | Artist | Title | — | — |
| Spaced-dash, multi-segment title | `Artist - Title - Live.ext` | Artist | Title - Live | — | — |
| Parenthetical modifier | `Artist - Title (Remix).ext` | Artist | Title (Remix) | — | — |
| Disc-Track-Artist-Title | `SC1234-05-John Doe-My Song.ext` | John Doe | My Song | SC1234 | 05 |
| DiscTrack-Artist-Title | `SC123405-John Doe-My Song.ext` | John Doe | My Song | SC123405 | — |
| Disc-Artist-Title | `SC1234-John Doe-My Song.ext` | John Doe | My Song | SC1234 | — |
| Artist-Title (plain dash) | `John Doe-My Song.ext` | John Doe | My Song | — | — |
| Typographic dash variants | `Artist — Title.ext` | Artist | Title | — | — |
| Full-width separator | `Artist－Title.ext` | Artist | Title | — | — |
| Archive path with directory-as-artist | `Language/Artist/Title.ext` | Artist | Title | — | — |

---

## Scope

### In Scope

- All naming conventions listed in the table above.
- Recognition of Unicode typographic dash variants (em-dash, en-dash,
  full-width hyphen-minus, figure dash, small em-dash) as separator
  equivalents.
- Filenames with only a bare title and no separator.
- Filenames where parenthetical suffixes belong to the title.
- Improved recognition of artist names that contain internal dashes (AC-DC,
  Jay-Z, MC-Hammer, ZZ-Top).
- Compressed-archive member paths where the directory component provides the
  artist name when the filename alone has no separator.
- Graceful handling of empty strings, whitespace-only strings, and paths with
  no filename component.
- Normalisation of Unicode to a canonical composed form before parsing.
- Normalisation of full-width ASCII variant characters (U+FF01–U+FF5E) to
  their standard ASCII equivalents.
- Stripping of invisible or zero-width Unicode characters that would
  contaminate extracted fields.

### Out of Scope

- Embedded metadata tag reading (ID3, Vorbis comments, etc.). This capability
  exists elsewhere in the system and is not part of filename parsing.
- Automatic correction of misspelled artist names.
- Network-based metadata lookup or enrichment services.
- Any user-interface changes — this feature affects only the core parsing
  logic's correctness.

---

## Edge Cases

Each edge case below defines an input and the **required** output behaviour.

1. **Empty string input** → Return empty artist, empty title, empty disc,
   empty track.
2. **Whitespace-only filename** → Return empty structured result (same as
   empty string).
3. **No file extension** → Parse the entire input as the filename stem.
4. **Multiple extensions** (e.g., `song.cdg.bak`) → Strip only the final
   extension; the remaining stem (including earlier dots) is parsed normally.
5. **Directory-only path** (e.g., `/music/karaoke/`) → Return empty
   structured result.
6. **Unicode em-dash separator** (`Artist — Title.mp3`) → Recognised as a
   valid separator; extract artist and title identically to the spaced-dash
   pattern.
7. **Full-width dash** (`Artist－Title.mp3`) → Recognised as a valid
   separator.
8. **CJK characters in artist and title** → Preserved exactly, no character
   loss, no encoding corruption, no transliteration.
9. **Artist name with internal dashes** (`AC-DC`, `Jay-Z`) → Grouped
   correctly into the artist field; the title begins after the artist.
10. **Filename consisting entirely of dashes** (`----.mp3`) → Return the
    dash sequence as the title; artist is empty.
11. **Very long filenames** (>255 characters) → Parsed without truncation,
    without error, without excessive resource consumption.
12. **Path separators embedded in stem** (malformed archive entries) →
    Normalised; only the final path component is parsed.
13. **Trailing period in stem** (Windows filesystem artefact) → Stripped
    before parsing so it does not contaminate the title.
14. **Decomposed Unicode (NFD) vs composed (NFC)** → Both representations
    of the same character produce identical output.
15. **Full-width parentheses** `（）` → Normalised to ASCII equivalents `()`
    before parsing.
16. **Null byte embedded in filename** → The parser does not crash; it
    processes the content up to the null byte.

---

## Failure Modes

1. **Completely unrecognisable pattern** → The system returns the full
   filename stem as the title and leaves the artist empty. A diagnostic
   message is emitted at the lowest (trace/debug) severity level. No error
   is raised.
2. **Character encoding error** — the input contains byte sequences that
   cannot be decoded as valid text → The system returns an empty structured
   result and emits a diagnostic message at warning severity. No unhandled
   exception propagates.
3. **Null or absent input** — the caller passes a missing/null value instead
   of a string → The system raises a type error immediately. This is a
   programming defect in the caller and must fail fast, not silently return
   a default.

---

## Backward Compatibility

- The **input contract** (accept a filesystem path as a string, return
  structured metadata) does not change. All existing callers continue to
  work without modification.
- The **output structure** (four fields: artist, title, disc, track) does not
  change. No fields are added, removed, or renamed.
- The **configuration surface** (naming convention selector) does not change.
  No new configuration values are introduced.
- **Behavioural corrections:** Filenames that previously produced incorrect
  metadata (e.g., `AC-DC-Back In Black.cdg` returned artist `"AC"` instead
  of `"AC-DC"`) will now produce correct metadata. This is classified as a
  **bug fix**, not a breaking change, but must be documented in the release
  changelog.
- **Risk for existing users:** Users who built manual workarounds for
  incorrect parsing (e.g., renaming files to compensate) may see duplicate
  or changed entries if they re-scan their library. This is acceptable — the
  correct behaviour is now canonical — but should be noted in release
  documentation.

---

## Performance Expectations

- **Single-file parsing latency:** < 100 microseconds on commodity hardware.
  Filename parsing is a lightweight string transformation and must not become
  a bottleneck.
- **Bulk import throughput:** Parsing 10,000 filenames must complete in under
  1 second total. Libraries commonly contain this many files and import must
  feel instantaneous.
- **Memory:** The structured result for a single file is a small, fixed-size
  record (four string fields). Memory consumption must remain O(1) per parse
  call. Bulk import of 100,000 files must not cause excessive memory pressure.
- **No per-call overhead:** The parser must not perform pattern compilation,
  file I/O, configuration reads, or any other deferred initialisation on each
  invocation.

---

## Observability Expectations

- Unrecognised patterns are logged at **debug/trace** severity (not visible
  in production by default, available when troubleshooting).
- Encoding errors are logged at **warning** severity with enough context to
  identify the problematic filename without exposing full filesystem paths.
- Successfully parsed files are **not** logged individually (too noisy at
  scale).
- Aggregate statistics (files parsed, patterns matched, patterns unrecognised)
  should be available at **info** severity for bulk import operations.

---

## Acceptance Criteria

- [ ] All 16 edge cases above have dedicated, individually-identifiable
      passing tests.
- [ ] All 3 failure modes have dedicated passing tests.
- [ ] All naming conventions in the Supported Naming Conventions table have
      dedicated passing tests.
- [ ] Zero regressions: every test that passes today continues to pass.
- [ ] Branch-level test coverage for the parsing component ≥ 95%.
- [ ] All public interfaces carry complete, statically-verifiable type
      declarations.
- [ ] Static analysis reports zero new defects (bugs, vulnerabilities, or
      code smells).
- [ ] Bulk parsing of 10,000 filenames completes in < 1 second.
- [ ] Output is deterministic and byte-identical across Linux, macOS, and
      Windows for every test case.
- [ ] No new external dependencies are introduced.

---

## Open Questions

- Should full-width parentheses `（）` be normalised to ASCII `()`?
  **Tentative decision:** Yes, normalise for consistency. (Captured as edge
  case 15 above.)
- Should aggregate parse statistics be emitted automatically during bulk
  import, or only when the caller explicitly requests them?
  **Tentative decision:** Emit automatically at info severity; callers who
  want silence can configure log levels.
