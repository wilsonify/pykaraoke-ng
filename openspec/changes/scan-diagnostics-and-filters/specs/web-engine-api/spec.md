# Delta for Web Engine API

> Proposed change: `scan-diagnostics-and-filters`. The Python engine surface
> grows by the report, pattern settings, replace/prune, and the
> export/import envelope.

## ADDED Requirements

### Requirement: Scan report API

The webapp SHALL expose `scan_report()` returning the library's structured
report as JSON (outcomes plus counts) and `clear_scan_report()` resetting
it. Both SHALL be callable from the browser page without side effects on
playback or the song list.

#### Scenario: Report after a mixed scan

- **WHEN** the page scans a batch containing a corrupt archive
- **THEN** `scan_report()` includes a `corrupt_archive` entry and its count

#### Scenario: Clearing

- **WHEN** the page calls `clear_scan_report()`
- **THEN** the next `scan_report()` shows empty outcomes and zero counts

### Requirement: Pattern settings API

`set_settings()` SHALL accept and persist `include_patterns` and
`exclude_patterns` lists, and a subsequent scan SHALL apply them. The keys
SHALL round-trip through `get_settings()`.

#### Scenario: Setting patterns

- **WHEN** `set_settings({"exclude_patterns": ["*_(vocal)_*"]})` is
  called
- **THEN** a subsequent scan filters matching files

#### Scenario: Patterns round-trip

- **WHEN** patterns are set and settings are read back
- **THEN** both lists are returned unchanged

> Replace-scan, prune, and import/export APIs are specified by the separate
> `library-backup-relocation` change and are not repeated here.
