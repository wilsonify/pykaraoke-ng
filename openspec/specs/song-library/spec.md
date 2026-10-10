# Song Library Specification

## Purpose

The song library turns the flat file entries produced by the web folder
picker (and the bytes of any chosen `.zip` archives) into an in-memory,
JSON-serialisable collection of karaoke songs with derived artist/title
metadata, companion-audio pairing, search, and sorting. It runs unchanged
under CPython and Pyodide, performs no filesystem or network I/O, and is
persisted by the UI as JSON in browser storage.

> Source: `src/pykaraoke/database.py`; verified against
> `tests/pykaraoke/test_database.py` and the library sections of
> `docs/user-guide/index.md`.

## Requirements

### Requirement: Supported song file kinds

The library SHALL classify a file by its lowercased extension into a song
kind, or ignore it when the extension is not a supported karaoke format.

> Source: `kind_for_name()` / `_KIND_BY_EXT` in `src/pykaraoke/database.py`.

#### Scenario: Recognised extensions are classified

- **WHEN** a file name ends in `.cdg`
- **THEN** the kind is `cdg`
- **AND** `.kar` and `.mid` map to `kar`
- **AND** `.mpg`, `.mpeg`, `.avi`, `.divx`, and `.xvid` map to `mpg`
- **AND** `.lrc` and `.lcr` map to `lrc`

#### Scenario: Unsupported files are ignored

- **WHEN** a file name ends in an extension with no karaoke kind (for
  example `.mp3`, `.txt`, or no extension at all)
- **THEN** the classifier returns no kind
- **AND** the file is not added as a song

### Requirement: Scanning file entries

The library SHALL accept a batch of file entries of the shape
`{"name", "path", "size"}`, index them by their lowercased path, and rebuild
the song list from every entry seen so far. Re-scanning the same entry SHALL
not produce duplicates, and two files that share a basename in different
folders SHALL remain distinct songs.

> Source: `SongLibrary.scan()` and `_rebuild()` in `src/pykaraoke/database.py`.

#### Scenario: A batch adds songs with parsed metadata

- **WHEN** a batch containing `Queen - Bohemian Rhapsody.cdg` is scanned
- **THEN** the library contains one `cdg` song
- **AND** its artist is `Queen` and its title is `Bohemian Rhapsody`

#### Scenario: Repeated scans are idempotent

- **WHEN** the same file entries are scanned twice
- **THEN** the library contains each song exactly once

#### Scenario: Same basename, different folders

- **WHEN** `One/A - B.cdg` and `Two/A - B.cdg` are scanned
- **THEN** the library contains two distinct songs

#### Scenario: Unsupported entries are skipped

- **WHEN** a batch mixes `notes.txt` and `cover.jpg` with `Artist - Title.kar`
- **THEN** only the `.kar` file becomes a song

#### Scenario: Empty or missing input is a no-op

- **WHEN** the scan receives no entries
- **THEN** the library reports its current size and adds nothing

### Requirement: Metadata extraction from filenames

The library SHALL derive each song's artist, title, disc, and track from its
file name (or zip member name) using the filename parser selected by the
`file_name_type` setting. When the parser yields no title, the library SHALL
fall back to the file-name stem as the title. A parse failure SHALL NOT abort
the scan.

> Source: `_make_song()` and `_parse_name()` in `src/pykaraoke/database.py`;
> parsing rules are owned by the `filename-parsing` capability.

#### Scenario: Space-dash names populate artist and title

- **WHEN** a file named `Queen - Bohemian Rhapsody.cdg` is scanned
- **THEN** the artist is `Queen` and the title is `Bohemian Rhapsody`

#### Scenario: A name with no recognised separator yields a title only

- **WHEN** a file named `JustATitle.cdg` is scanned
- **THEN** the title is `JustATitle`
- **AND** the artist is empty

### Requirement: Optional exclusion of songs without an artist

When the `exclude_non_matching` setting is enabled, the library SHALL omit
every entry from which no artist could be extracted. When it is disabled, the
library SHALL keep those entries as title-only songs.

> Source: `_make_song()` and `Settings.exclude_non_matching` in
> `src/pykaraoke/database.py`.

#### Scenario: Excluding songs without an artist

- **WHEN** `exclude_non_matching` is enabled
- **AND** a file whose name has no artist (for example `JustATitle.cdg`) is scanned
- **THEN** the library contains no song for that file

#### Scenario: Keeping songs without an artist by default

- **WHEN** `exclude_non_matching` is at its default value
- **AND** `JustATitle.cdg` is scanned
- **THEN** the library contains a title-only song

### Requirement: Companion audio pairing

The library SHALL attach a companion audio file (`.mp3`, `.ogg`, or `.wav`)
to each top-level `.cdg` and `.lrc`/`.lcr` song. It SHALL prefer an exact
case-insensitive basename-stem match, and otherwise accept a normalised-stem
match that ignores leading track numbers and trailing `karaoke` /
`instrumental` suffixes. Songs inside a zip archive SHALL NOT be paired.

> Source: `pair_cdg_audio()`, `_normalize_stem()`, and `AUDIO_EXTENSIONS` in
> `src/pykaraoke/database.py`.

#### Scenario: Exact stem match

- **WHEN** `Queen - Bohemian Rhapsody.cdg` and
  `Queen - Bohemian Rhapsody.mp3` are scanned
- **THEN** the song's `audio_name` is `Queen - Bohemian Rhapsody.mp3`

#### Scenario: Normalised match ignores numbering and suffixes

- **WHEN** `01 - Inside Out.lrc` is scanned alongside
  `Inside Out - Karaoke.mp3`
- **THEN** the song's `audio_name` is `Inside Out - Karaoke.mp3`

#### Scenario: No companion file

- **WHEN** a `.cdg` song has no matching audio entry
- **THEN** its `audio_name` remains unset

### Requirement: Zip archive scanning

When the `look_inside_zips` setting is enabled, the library SHALL expand a zip
archive supplied as bytes into songs for each supported karaoke member, keying
each song by the archive name plus the member name and recording the archive
name. Member entries SHALL be deduplicated, and an unreadable archive SHALL be
reported as adding nothing rather than raising — and SHALL additionally be
recorded in the scan report with a distinguishing outcome
(`corrupt_archive`, `unsupported_compression`, or `unreadable`) so the caller
can tell the user why songs are missing.

> Source: `SongLibrary.scan_zip()` in `src/pykaraoke/database.py:277`.

#### Scenario: Supported members become songs

- **WHEN** a zip containing `Artist/Title.kar` and `readme.txt` is scanned
- **THEN** the library contains one `kar` song
- **AND** its `zip_name` is the archive name
- **AND** its artist is `Artist` and its title is `Title`

#### Scenario: Archive scanning is disabled

- **WHEN** `look_inside_zips` is disabled
- **THEN** scanning a zip archive adds no songs

#### Scenario: Unreadable archive

- **WHEN** bytes that are not a valid zip are scanned
- **THEN** the library adds no songs and does not raise
- **AND** the scan report records the archive path as `corrupt_archive`

#### Scenario: Unsupported compression

- **WHEN** a valid zip whose members use a compression method the runtime
  cannot read is scanned
- **THEN** the library adds no songs and does not raise
- **AND** the scan report records the archive path as
  `unsupported_compression`

### Requirement: Search

The library SHALL return the songs whose title, artist, or file name contains
every term of a whitespace-separated, case-insensitive query. An empty query
SHALL return no results, and the result set SHALL be capped by a caller-
supplied limit.

> Source: `SongLibrary.search()` in `src/pykaraoke/database.py`.

#### Scenario: Matching on title, artist, or file name

- **WHEN** the query `queen` is searched
- **THEN** every song whose artist contains `queen` is returned
- **AND** the match is case-insensitive

#### Scenario: All terms must match

- **WHEN** the query `queen champions` is searched
- **THEN** only songs whose combined title/artist/file text contains both terms are returned

#### Scenario: Empty query

- **WHEN** the query is empty or whitespace only
- **THEN** the result list is empty

#### Scenario: Result limit

- **WHEN** more matches exist than the requested limit
- **THEN** at most that many songs are returned

### Requirement: Sorting

The library SHALL order songs by `filename`, `title`, or `artist`. Title and
artist ordering SHALL ignore a leading article (`a`, `an`, `the`) and a
leading parenthesised block. An unrecognised sort mode SHALL fall back to
`filename`.

> Source: `SongLibrary.sort_by()` and `_strip_articles()` in
> `src/pykaraoke/database.py`.

#### Scenario: Title sort ignores articles

- **WHEN** songs are sorted by `title`
- **THEN** `The Beatles - Let It Be` orders under `Let It Be`

#### Scenario: Artist sort ignores articles

- **WHEN** songs are sorted by `artist`
- **THEN** `The Beatles` orders under `B`

#### Scenario: Unknown sort mode falls back

- **WHEN** an unrecognised sort mode is requested
- **THEN** the effective sort mode becomes `filename`

### Requirement: Settings defaults and round-trip

The library SHALL persist and losslessly restore the settings `folders`,
`cdg_zoom`, `derive_song_info`, `file_name_type`, `exclude_non_matching`,
`look_inside_zips`, `sort`, `volume`, `include_patterns`, and
`exclude_patterns`. It SHALL default `sort` to `filename`, `cdg_zoom` to
`int`, `volume` to `0.75`, and both pattern lists to empty.

> Source: `Settings` in `src/pykaraoke/database.py:127` (`to_dict` at
> `src/pykaraoke/database.py:141`, `from_dict` at
> `src/pykaraoke/database.py:156`).

#### Scenario: Defaults

- **WHEN** settings are created without arguments
- **THEN** `sort` is `filename`, `cdg_zoom` is `int`, and `volume` is `0.75`
- **AND** the folder list is empty, `derive_song_info` is enabled, the naming
  type is `ARTIST_TITLE`, `exclude_non_matching` is disabled, and
  `look_inside_zips` is enabled

#### Scenario: Settings survive a round-trip

- **WHEN** settings are serialised and restored
- **THEN** every field keeps its value

#### Scenario: Pattern settings round-trip

- **WHEN** `include_patterns` and `exclude_patterns` are set and the
  settings are serialised and restored
- **THEN** both lists are returned unchanged

> Note: `derive_song_info` and `file_name_type` are persisted by the library;
> only `file_name_type` is consulted during scanning. `derive_song_info` is a
> UI-facing toggle at present.

### Requirement: Naming convention is user-selectable

The settings panel SHALL expose `file_name_type` as a labelled control
offering every supported naming convention — including the spaced
disc-track mode — SHALL persist the selected value with the other settings,
SHALL apply it to the next library scan, and SHALL restore the selection
after a restart.

> Source: the `#setting-naming` control in `src/web/index.html` (settings
> panel), wired through `refreshSettings()` and the change listener that
> calls `set_settings({file_name_type})`. Verified by
> `tests/pykaraoke/test_webapp.py:128`
> (`test_file_name_type_accepts_spaced_disc_track`).

#### Scenario: Selecting the spaced disc-track mode

- **WHEN** the user selects the disc-track spaced convention in settings
- **THEN** `file_name_type` is persisted as `4`
- **AND** the next scan parses matching filenames with that convention

#### Scenario: Selection survives a restart

- **WHEN** a non-default convention is selected and the application is
  reloaded
- **THEN** the settings control shows the persisted convention

### Requirement: Include and exclude filename patterns

The library SHALL accept `include_patterns` and `exclude_patterns` settings as lists of case-insensitive `fnmatch` patterns matched against the file basename and each zip member's basename. A file SHALL be scanned when it matches the include list (or the include list is empty) and does not match the exclude list; exclude wins. Patterns SHALL round-trip through settings persistence, and an invalid pattern SHALL degrade to a literal match rather than raising.

> Source: `SongLibrary._name_allowed()` in `src/pykaraoke/database.py:241`
> and `_pattern_match()` in `src/pykaraoke/database.py:58`; applied in
> `scan()` (`src/pykaraoke/database.py:256`), `scan_zip()`
> (`src/pykaraoke/database.py:277`), and `_make_song()`
> (`src/pykaraoke/database.py:365`). Verified by
> `tests/pykaraoke/test_database.py:321` (`TestPatternFilters`).

#### Scenario: Exclude a vocal version

- **WHEN** `exclude_patterns` contains `*_(vocal)_*` and the tree contains
  `Song - Artist_(Vocal)_.cdg`
- **THEN** the library contains no song for that file
- **AND** the scan report counts it as `filtered`

#### Scenario: Include narrows the scan

- **WHEN** `include_patterns` is `["CB*.cdg"]` and the tree also contains
  `Artist - Other.cdg`
- **THEN** only the `CB…` file is scanned

#### Scenario: Exclude beats include

- **WHEN** a file matches both an include pattern and an exclude pattern
- **THEN** the file is filtered out

#### Scenario: Empty include means everything

- **WHEN** both pattern lists are empty
- **THEN** every supported file is scanned as before

#### Scenario: Patterns apply inside zips

- **WHEN** a zip member matches an exclude pattern
- **THEN** that member becomes no song while other members still do

### Requirement: Scan reporting

The library SHALL record a structured scan report — per-input outcome plus per-kind counts — covering `unsupported`, `filtered`, `corrupt_archive`, `unsupported_compression`, `unreadable`, and `parse_failure` (recorded when filename parsing raises, after which the file is kept as title-only instead of aborting the scan). The report SHALL be retrievable and clearable by the caller, SHALL survive independent of the song list until cleared, SHALL deduplicate repeated (category, path) pairs, and SHALL never influence which songs are added.

> Source: `SongLibrary._report()` in `src/pykaraoke/database.py:221`,
> `scan_report()` at `src/pykaraoke/database.py:229`,
> `clear_scan_report()` at `src/pykaraoke/database.py:236`, and the
> defensive parse catch in `_parse_name()` at
> `src/pykaraoke/database.py:389`. Categories are defined by
> `REPORT_CATEGORIES` in `src/pykaraoke/database.py:48`. Verified by
> `tests/pykaraoke/test_database.py:377` (`TestScanReport`).

#### Scenario: A mixed batch reports every category

- **WHEN** a scan batch mixes an unsupported file, a filtered file, and a
  parseable song
- **THEN** the report counts one `unsupported`, one `filtered`, and zero
  problems for the parseable song

#### Scenario: Report is clearable

- **WHEN** the caller clears the scan report
- **THEN** the next `scan_report()` is empty

#### Scenario: Reporting never aborts

- **WHEN** a corrupt archive is followed by a valid file in the same batch
- **THEN** the valid file still becomes a song

#### Scenario: A parse that raises is recorded, not fatal

- **WHEN** filename parsing raises for a file during a scan
- **THEN** the scan report counts one `parse_failure` for that path
- **AND** the file is still added as a title-only song

#### Scenario: Outcomes are not duplicated across rebuilds

- **WHEN** a later scan rebuilds the song list and re-visits an already
  reported path
- **THEN** the report gains no duplicate entry for that (category, path)

### Requirement: Zip songs survive rebuilds

Rebuilding the song list after settings changes SHALL preserve songs that came from zip archives using a cache of previously parsed members, so that a rebuild does not require re-reading archive bytes and does not silently drop zip songs. Restoring a persisted library SHALL rebuild the cache from the restored zip songs.

> Source: `SongLibrary._zip_cache` in `src/pykaraoke/database.py:211`,
> written by `scan_zip()` at `src/pykaraoke/database.py:331`, consumed by
> `_rebuild()` at `src/pykaraoke/database.py:359`, and repopulated by
> `SongLibrary.from_dict()` at `src/pykaraoke/database.py:502`. Verified by
> `tests/pykaraoke/test_database.py:444` (`TestZipMemberCache`).

#### Scenario: Rebuild keeps zip songs

- **WHEN** a zip has been scanned and a settings change triggers a rebuild
- **THEN** the zip's songs remain in the library with their metadata

#### Scenario: A later loose scan does not drop zip songs

- **WHEN** a loose-file scan runs after a zip has been scanned
- **THEN** the zip's songs are still present alongside the new loose songs

#### Scenario: Persistence restores the cache

- **WHEN** a library containing zip songs is serialised and restored, and a
  loose-file scan then runs
- **THEN** the restored zip songs are still present

### Requirement: Replace-scan clears prior contents

The library SHALL support a replace-scan that clears previously scanned
loose files and zip expansions before applying the new batch, while leaving
`Settings` untouched. The default (non-replace) scan SHALL remain additive
so existing callers keep their accumulated behaviour.

> Source: `SongLibrary.scan(files, replace=…)` in
> `src/pykaraoke/database.py:253` (replace clears `_files`, `_zip_cache`,
> and `songs` before the normal apply path). Verified by
> `tests/pykaraoke/test_database.py:476` (`TestReplaceScan`).

#### Scenario: Replace-scan relocates a library

- **WHEN** a replace-scan supplies the files under a new root
- **THEN** the library contains exactly the new root's songs
- **AND** no song from the previous root remains

#### Scenario: Settings survive a replace-scan

- **WHEN** a replace-scan runs with a non-default volume setting
- **THEN** the volume setting is unchanged afterwards

#### Scenario: Default scan stays additive

- **WHEN** a scan runs without the replace flag after an earlier scan
- **THEN** songs from both batches are present

### Requirement: Prune stale songs by known path set

The library SHALL provide a prune operation that removes loose and zip
songs whose paths are absent from a caller-supplied set of known paths.
Pruning with an empty known-set SHALL be a no-op so an accidental empty
call cannot wipe the library.

> Source: `SongLibrary.prune_songs()` in `src/pykaraoke/database.py:282`
> (prunes `_files`, `_zip_cache`, and `songs`; normalises separators and
> case). Verified by `tests/pykaraoke/test_database.py:506` (`TestPrune`).

#### Scenario: Prune removes stale paths

- **WHEN** prune is called with a known set lacking one previously scanned
  path
- **THEN** that song is removed and the rest remain

#### Scenario: Empty known-set is a no-op

- **WHEN** prune is called with an empty set
- **THEN** the library is unchanged

### Requirement: Library export envelope

The library SHALL export as a JSON string containing a versioned envelope
`{"format": …, "schema": 1, "library": …}` whose `library` value is the
library's own serialised dictionary, so an export is self-describing and
validatable on import.

> Source: `SongLibrary.export_json()` and the `EXPORT_FORMAT` /
> `EXPORT_SCHEMA` constants in `src/pykaraoke/database.py:548`. Verified by
> `tests/pykaraoke/test_database.py:540` (`TestExportImport`).

#### Scenario: Envelope shape

- **WHEN** the library is exported
- **THEN** the payload parses to an object with a `schema` of `1` and a
  `library` member equal to the serialised library

### Requirement: Library import with validation and atomic swap

The library SHALL import from a JSON string that is either the export
envelope or a bare serialised library dictionary. It SHALL validate the
payload and schema version before applying. A recognised, valid payload
SHALL atomically replace the in-memory library; malformed JSON, an
unrecognised schema, or an invalid library SHALL leave the existing library
unchanged and SHALL report a structured error rather than a partial state.

> Source: `SongLibrary.import_json()` in `src/pykaraoke/database.py:561`
> (validates envelope schema and library version, builds a fresh
> `SongLibrary` from the payload, then swaps state in one step). Verified by
> `tests/pykaraoke/test_database.py:540` (`TestExportImport`).

#### Scenario: Export/import round-trip

- **WHEN** a library is exported and imported into a fresh instance
- **THEN** songs, pairing, folders, and settings are identical

#### Scenario: Bare library dict is accepted

- **WHEN** an import payload is the bare serialised library without the
  envelope
- **THEN** the import succeeds as if the envelope were present

#### Scenario: Malformed JSON leaves state intact

- **WHEN** an import payload is not valid JSON
- **THEN** the existing library is unchanged
- **AND** the import reports an error

#### Scenario: Unrecognised schema is rejected cleanly

- **WHEN** an import payload declares a schema the library does not
  recognise
- **THEN** the existing library is unchanged
- **AND** the import reports an error

### Requirement: Library persistence

The library SHALL serialise to a versioned JSON-compatible dictionary and
restore from one, preserving the songs and settings. Data with an unrecognised
version SHALL restore as an empty library rather than raising.

> Source: `SongLibrary.to_dict()` and `SongLibrary.from_dict()` in
> `src/pykaraoke/database.py`.

#### Scenario: Round-trip preserves songs and settings

- **WHEN** a library with a paired CDG song, a folder list, and a volume of
  `0.5` is serialised and restored
- **THEN** the restored library has the same song, artist, title, companion
  audio, folders, and volume

#### Scenario: Unknown version

- **WHEN** data whose version is not the current version is restored
- **THEN** the library is empty and no error is raised

### Requirement: Deterministic, side-effect-free operation

The library SHALL derive its state only from the supplied file entries and zip
bytes — performing no filesystem, network, or environment access — and SHALL
produce identical songs and ordering for identical inputs.

> Source: `src/pykaraoke/database.py` (pure-stdlib, Pyodide-compatible).

#### Scenario: Identical inputs produce identical libraries

- **WHEN** the same entries are scanned into two fresh libraries with the same
  settings
- **THEN** both libraries contain the same songs in the same order
