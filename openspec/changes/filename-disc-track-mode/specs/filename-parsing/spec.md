# Delta for Filename Parsing

> Proposed change: `filename-disc-track-mode`. The `## MODIFIED` requirement
> gains the new mode in its enumeration; the `## ADDED` requirement defines
> the mode's algorithm. Legacy issue: kelvinlawson/pykaraoke#14.

## MODIFIED Requirements

### Requirement: Legacy naming conventions are selected by configuration

When the stem contains no space-dash-space separator, the parser SHALL fall
back to the legacy convention named by the parser's `file_name_type`, one of
`DISC_TRACK_ARTIST_TITLE`, `DISCTRACK_ARTIST_TITLE`, `DISC_ARTIST_TITLE`,
`ARTIST_TITLE` (the default), or — when the stem does contain spaced
separators — the spaced convention `DISC_TRACK_SPACED`. The convention is a
persisted user setting, so the same library can be re-parsed under a
different scheme.

#### Scenario: Disc-Track-Artist-Title

- **WHEN** `SC1234-05-John Doe-My Song.cdg` is parsed with `DISC_TRACK_ARTIST_TITLE`
- **THEN** the disc is `SC1234`, the track is `05`, the artist is `John Doe`, and the title is `My Song`

#### Scenario: DiscTrack-Artist-Title

- **WHEN** `SC123405-John Doe-My Song.cdg` is parsed with `DISCTRACK_ARTIST_TITLE`
- **THEN** the disc is `SC123405`, the artist is `John Doe`, and the title is `My Song`

#### Scenario: Disc-Artist-Title

- **WHEN** `SC1234-John Doe-My Song.cdg` is parsed with `DISC_ARTIST_TITLE`
- **THEN** the disc is `SC1234`, the artist is `John Doe`, and the title is `My Song`

#### Scenario: Legacy modes tolerate extra dashes in the title

- **WHEN** `SC1234-05-Artist-Title-With-Dashes.cdg` is parsed with `DISC_TRACK_ARTIST_TITLE`
- **THEN** the disc is `SC1234`, the track is `05`, the artist is `Artist`, and the title is `Title-With-Dashes`

#### Scenario: An unknown numeric convention falls back to the default

- **WHEN** `file_name_type` holds a value outside the known conventions
- **THEN** parsing behaves as `ARTIST_TITLE`

## ADDED Requirements

### Requirement: Disc-track spaced naming mode

When `file_name_type` is `DISC_TRACK_SPACED`, the parser SHALL recognise stems of the form `DISC-TRACK - ARTIST - TITLE` in which the spaces around the separating dashes are required: it SHALL split the stem at the first space-dash-space separator, treat the prefix as a disc-track part separated into disc and track at the last hyphen inside the prefix, and split the remainder at its first space-dash-space separator into artist and title.

#### Scenario: Issue #14 example parses correctly

- **WHEN** `CB30055-15 - Switchfoot - Stars.cdg` is parsed with
  `DISC_TRACK_SPACED`
- **THEN** the disc is `CB30055`, the track is `15`, the artist is
  `Switchfoot`, and the title is `Stars`

#### Scenario: The last hyphen in the prefix separates disc from track

- **WHEN** `CB5056-03-06 - Al Green - Let's Stay Together.cdg` is parsed
  with `DISC_TRACK_SPACED`
- **THEN** the disc is `CB5056-03` and the track is `06`

#### Scenario: Dashes inside the artist name are preserved

- **WHEN** `SC3448-03 - All-American Rejects - Dirty Little Secret.cdg` is
  parsed with `DISC_TRACK_SPACED`
- **THEN** the artist is `All-American Rejects`
- **AND** the title is `Dirty Little Secret`

#### Scenario: Extra separators stay in the title

- **WHEN** `SC1-01 - Artist - Title - Radio Edit.cdg` is parsed with
  `DISC_TRACK_SPACED`
- **THEN** the title is `Title - Radio Edit`

#### Scenario: A plain space-dash name still parses

- **WHEN** `Artist - Title.cdg` is parsed with `DISC_TRACK_SPACED`
- **THEN** the artist is `Artist` and the title is `Title`
- **AND** no disc or track is produced

#### Scenario: Zip members use the same mode

- **WHEN** `PHM - Pop/PHM0512/PHM0512-08 - Switchfoot - Stars.kar` is
  parsed with `DISC_TRACK_SPACED` via the zip-member entry point
- **THEN** the disc is `PHM0512`, the track is `08`, the artist is
  `Switchfoot`, and the title is `Stars`

### Requirement: Spaced disc-track fallback and setting value

When the stem has no spaced separator, or the disc-track prefix has no hyphen, `DISC_TRACK_SPACED` SHALL fall back to ordinary space-dash and best-effort legacy parsing rather than mis-attributing the artist. The mode SHALL apply to zip member paths and be accepted as the integer value `4` by the `file_name_type` setting.

#### Scenario: An unspaced stem degrades to best-effort parsing

- **WHEN** `CB30055-15-Switchfoot-Stars.cdg` is parsed with
  `DISC_TRACK_SPACED`
- **THEN** no disc-track result is forced from the spaced convention
- **AND** the parse degrades to the ordinary best-effort result rather
  than mis-attributing the artist

#### Scenario: A prefix with no hyphen falls back

- **WHEN** `Something - Artist - Title.cdg` is parsed with
  `DISC_TRACK_SPACED`
- **THEN** no disc or track is produced from the prefix
- **AND** the result follows the ordinary space-dash parse
