# Delta for Filename Parsing

> Change: `filename-parser-edge-cases`. **Core shipped 2026-10-10** — the
> behaviour described under `## MODIFIED Requirements` and the first three
> `## ADDED Requirements` (Canonical Unicode Normalisation, Full-Width ASCII
> Folding, Field Hygiene) is now live and recorded in the capability spec as
> the requirement "Stems are Unicode-normalised and hygienic". The remaining
> ADDED requirements below either already existed under other names (Bare
> Title, Parenthetical Title, Archive Directory) or restate existing
> guarantees (Determinism and Safety); at archive time this delta must be
> reconciled against `openspec/specs/filename-parsing/spec.md` rather than
> merged blindly (task 5.5).

## MODIFIED Requirements

### Requirement: Space-dash-space filenames split at the first separator

The parser SHALL split a filename at the first spaced-dash separator and treat
everything before it as the artist and everything after it as the title.
After this change the separator SHALL match Unicode dash variants
(em-dash, en-dash, figure dash, small em-dash, full-width hyphen-minus) in
addition to the ASCII hyphen.

(Previously: only the ASCII `" - "` sequence was recognised as a separator.)

#### Scenario: A simple space-dash-space filename

- **WHEN** `John Doe - My Song.mp3` is parsed
- **THEN** the artist is `John Doe`
- **AND** the title is `My Song`

#### Scenario: Subtitles and parentheticals stay in the title

- **WHEN** `Artist - Title (Remix).cdg` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title (Remix)`
- **WHEN** `Artist - Title - Live.mp3` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title - Live`

#### Scenario: Surrounding whitespace is trimmed

- **WHEN** `  Artist   -   Title  .mp3` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title`

#### Scenario: Inner dashes in the title are preserved

- **WHEN** `Artist - A-B-C Song.cdg` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `A-B-C Song`

#### Scenario: Disc and track remain empty for modern filenames

- **WHEN** `Artist - Title.mp3` is parsed
- **THEN** the disc field is empty
- **AND** the track field is empty

#### Scenario: ASCII separator

- **WHEN** the filename is `Artist - Title.mp3`
- **THEN** the artist is `Artist` and the title is `Title`

#### Scenario: Unicode em-dash separator

- **WHEN** the filename is `Artist — Title.mp3`
- **THEN** the artist is `Artist` and the title is `Title`

#### Scenario: Only the first separator divides the fields

- **WHEN** the filename is `Artist - Title - Live.mp3`
- **THEN** the artist is `Artist` and the title is `Title - Live`

### Requirement: Artist-Title mode groups dashed abbreviations into the artist

The parser SHALL group consecutive short all-uppercase components that make up
an artist name containing internal dashes, so that the artist is not split at
the wrong dash. After this change the grouping SHALL operate on the normalised
stem so it behaves identically for ASCII and Unicode dash variants.

(Previously: grouping ran on the raw stem and only recognised ASCII dashes.)

#### Scenario: A dashed abbreviation stays together

- **WHEN** `AC-DC-Back In Black.cdg` is parsed with `ARTIST_TITLE`
- **THEN** the artist is `AC-DC`
- **AND** the title is `Back In Black`

#### Scenario: A normal two-segment filename splits at the first hyphen

- **WHEN** `Queen-Bohemian Rhapsody.kar` is parsed with `ARTIST_TITLE`
- **THEN** the artist is `Queen`
- **AND** the title is `Bohemian Rhapsody`

#### Scenario: Extra hyphens in the title are kept

- **WHEN** `Artist-Title-Extra.cdg` is parsed with `ARTIST_TITLE`
- **THEN** the artist is `Artist`
- **AND** the title is `Title-Extra`

#### Scenario: Space-dash artist with internal dash

- **WHEN** the filename is `AC-DC - Back In Black.cdg`
- **THEN** the artist is `AC-DC` and the title is `Back In Black`

#### Scenario: Legacy artist with internal dash

- **WHEN** the filename is `AC-DC-Back In Black.cdg` and the legacy
  artist-title convention is selected
- **THEN** the artist is `AC-DC` and the title is `Back In Black`

## ADDED Requirements

### Requirement: Canonical Unicode Normalisation

The parser SHALL normalise the filename stem to Unicode NFC before parsing, so
that the same visible filename produces identical artist and title output
regardless of the composition form stored by the file system.

#### Scenario: Decomposed and composed forms agree

- **WHEN** the same filename is presented once in NFD (decomposed) and once in
  NFC (composed)
- **THEN** both produce byte-identical artist and title values

#### Scenario: CJK characters are preserved

- **WHEN** the filename is `初音ミク - 千本桜.mp3`
- **THEN** the artist is `初音ミク` and the title is `千本桜`, with no
  character loss, transliteration, or corruption

### Requirement: Full-Width ASCII Folding

The parser SHALL fold full-width ASCII variant characters (U+FF01–U+FF5E) to
their standard ASCII equivalents, including full-width parentheses and the
full-width hyphen-minus, before parsing.

#### Scenario: Full-width dash as separator

- **WHEN** the filename is `Artist－Title.mp3`
- **THEN** the artist is `Artist` and the title is `Title`

#### Scenario: Full-width parentheses in the title

- **WHEN** the filename is `Artist - Title（Live）.mp3`
- **THEN** the title is `Title(Live)`

### Requirement: Field Hygiene

The parser SHALL strip leading and trailing whitespace, invisible or
zero-width characters, and trailing dots from the stem before extracting
fields, so that they do not contaminate the artist or title.

#### Scenario: Surrounding whitespace is removed

- **WHEN** the filename is `  Artist   -   Title  .mp3`
- **THEN** the artist is `Artist` and the title is `Title`

#### Scenario: Windows trailing dot is removed

- **WHEN** the stem ends with one or more dots
- **THEN** the trailing dots are removed before the fields are extracted

#### Scenario: Embedded null byte does not crash the parser

- **WHEN** the filename contains an embedded null byte (`\x00`)
- **THEN** the parser returns a result without raising, processing the content
  up to the null byte

### Requirement: Bare Title Without Separator

The parser SHALL return the whole normalised stem as the title, with an empty
artist, when no recognised separator is present.

#### Scenario: No separator at all

- **WHEN** the filename is `JustATitle.mp3`
- **THEN** the title is `JustATitle` and the artist is empty

#### Scenario: Filename made only of dashes

- **WHEN** the filename is `----.mp3`
- **THEN** the title is `----` and the artist is empty

#### Scenario: Empty or whitespace-only input

- **WHEN** the input is an empty string or contains only whitespace
- **THEN** artist, title, disc, and track are all empty and no error is raised

### Requirement: Parenthetical Title Preservation

The parser SHALL preserve a parenthetical suffix as part of the title rather
than dropping it or attributing it to the artist.

#### Scenario: Remix suffix

- **WHEN** the filename is `Artist - Title (Remix).cdg`
- **THEN** the artist is `Artist` and the title is `Title (Remix)`

#### Scenario: Karaoke-version suffix

- **WHEN** the filename is `Artist - Title (Karaoke Version).cdg`
- **THEN** the title is `Title (Karaoke Version)`

### Requirement: Archive Directory as Artist

For archive member paths, the parser SHALL use the immediate parent directory
component as the artist when the filename component alone yields no artist.

#### Scenario: Directory provides the artist

- **WHEN** the member path is `Language/Artist/Title.kar`
- **THEN** the artist is `Artist` and the title is `Title`

#### Scenario: Filename separator wins over the directory

- **WHEN** the member path is `Some Dir/Queen - Bohemian Rhapsody.kar`
- **THEN** the artist is `Queen` and the title is `Bohemian Rhapsody`

### Requirement: Determinism and Safety

Filename parsing SHALL be a pure, offline transformation: it SHALL perform no
file or network access and read no locale or environment settings, SHALL never
raise for plausible filename input except a type error for a non-string
argument, and SHALL introduce no new third-party dependency.

#### Scenario: Path traversal is not resolved

- **WHEN** the input is `../../etc/passwd`
- **THEN** the parser reduces it to a safe basename and never resolves or
  follows the path

#### Scenario: Non-string input fails fast

- **WHEN** the caller passes `None` instead of a string
- **THEN** the parser raises a type error rather than silently returning an
  empty result
