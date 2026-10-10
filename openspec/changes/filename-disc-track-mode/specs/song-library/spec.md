# Delta for Song Library

> Proposed change: `filename-disc-track-mode`. The library itself already
> persists `file_name_type` generically; this delta makes the new mode
> user-visible and reachable.

## ADDED Requirements

### Requirement: Naming convention is user-selectable

The settings panel SHALL expose `file_name_type` as a labelled control
offering every supported naming convention — including the spaced
disc-track mode — SHALL persist the selected value with the other settings,
SHALL apply it to the next library scan, and SHALL restore the selection
after a restart.

#### Scenario: Selecting the spaced disc-track mode

- **WHEN** the user selects the disc-track spaced convention in settings
- **THEN** `file_name_type` is persisted as `4`
- **AND** the next scan parses matching filenames with that convention

#### Scenario: Selection survives a restart

- **WHEN** a non-default convention is selected and the application is
  reloaded
- **THEN** the settings control shows the persisted convention
