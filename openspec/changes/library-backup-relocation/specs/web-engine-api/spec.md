# Delta for Web Engine API

> Proposed change: `library-backup-relocation`. Scan-report and pattern APIs
> are owned by `scan-diagnostics-and-filters`.

## ADDED Requirements

### Requirement: Replace-scan API

`scan_files()` SHALL accept a `replace` flag: when true it SHALL clear
previously scanned loose files and zip expansions before applying the
batch, and SHALL leave settings untouched. The flag SHALL default to
preserving the accumulated behaviour.

#### Scenario: Relocation via replace

- **WHEN** `scan_files(new_entries, replace=True)` is called
- **THEN** the returned song list contains only the new entries' songs

#### Scenario: Default remains additive

- **WHEN** `scan_files(entries)` is called without the flag
- **THEN** previously scanned songs are retained as before

### Requirement: Prune API

The webapp SHALL expose `prune_songs(known)` forwarding to the library's
prune operation, treating an empty known-set as a no-op.

#### Scenario: Prune from the page

- **WHEN** the page calls `prune_songs` with the current on-disk path set
- **THEN** songs with paths absent from that set are removed

#### Scenario: Empty set does nothing

- **WHEN** the page calls `prune_songs` with an empty set
- **THEN** the library is unchanged

### Requirement: Import and export API

`export_json()` SHALL return the envelope-wrapped library as a string, and
`import_json(payload)` SHALL validate the payload (envelope or bare library
dict, recognised schema) and return `{"ok": true}` on success or
`{"ok": false, "error": …}` with the previous library intact on failure.

#### Scenario: Round-trip through the page

- **WHEN** the page exports and immediately imports its own payload
- **THEN** the library is unchanged and the result is ok

#### Scenario: Corrupt payload

- **WHEN** `import_json("not json")` is called
- **THEN** the result is not-ok with an error string
- **AND** the existing library is unchanged
