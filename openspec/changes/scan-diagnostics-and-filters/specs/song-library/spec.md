# Delta for Song Library

> Proposed change: `scan-diagnostics-and-filters`. Legacy issues: #5
> (pattern exclusion), #14 (silent zip failures). The `## MODIFIED`
> requirement extends zip scanning; everything else is new.

## MODIFIED Requirements

### Requirement: Zip archive scanning

When the `look_inside_zips` setting is enabled, the library SHALL expand a zip
archive supplied as bytes into songs for each supported karaoke member, keying
each song by the archive name plus the member name and recording the archive
name. Member entries SHALL be deduplicated, and an unreadable archive SHALL be
reported as adding nothing rather than raising — and SHALL additionally be
recorded in the scan report with a distinguishing outcome
(`corrupt_archive`, `unsupported_compression`, or `unreadable`) so the caller
can tell the user why songs are missing.

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

## ADDED Requirements

### Requirement: Include and exclude filename patterns

The library SHALL accept `include_patterns` and `exclude_patterns` settings as lists of case-insensitive `fnmatch` patterns matched against the file basename and each zip member's basename. A file SHALL be scanned when it matches the include list (or the include list is empty) and does not match the exclude list; exclude wins. Patterns SHALL round-trip through settings persistence, and an invalid pattern SHALL degrade to a literal match rather than raising.

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

The library SHALL record a structured scan report — per-input outcome plus
per-kind counts — covering `unsupported`, `filtered`, `corrupt_archive`,
`unsupported_compression`, `unreadable`, and `parse_failure` (a file kept as
title-only after a parse fallback). The report SHALL be retrievable and
clearable by the caller, SHALL survive independent of the song list until
cleared or reset by the next replace-scan, and SHALL never influence which
songs are added.

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

### Requirement: Zip songs survive rebuilds

Rebuilding the song list after settings changes SHALL preserve songs that
came from zip archives using a cache of previously parsed members, so that
a rebuild does not require re-reading archive bytes and does not silently
drop zip songs.

#### Scenario: Rebuild keeps zip songs

- **WHEN** a zip has been scanned and a settings change triggers a rebuild
- **THEN** the zip's songs remain in the library with their metadata

> Relocation behaviours (replace-scan, prune, export/import envelope) are
> specified by the separate `library-backup-relocation` change and are not
> repeated here.
