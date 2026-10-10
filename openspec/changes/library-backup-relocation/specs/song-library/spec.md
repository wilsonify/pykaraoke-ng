# Delta for Song Library

> Proposed change: `library-backup-relocation`. Patterns, scan reporting,
> and the zip-member cache are owned by `scan-diagnostics-and-filters` and
> are not repeated here.

## ADDED Requirements

### Requirement: Replace-scan clears prior contents

The library SHALL support a replace-scan that clears previously scanned
loose files and zip expansions before applying the new batch, while leaving
`Settings` untouched. The default (non-replace) scan SHALL remain additive
so existing callers keep their accumulated behaviour.

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
