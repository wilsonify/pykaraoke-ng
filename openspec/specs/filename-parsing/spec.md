# Filename Parsing Specification

## Purpose

Define how PyKaraoke-NG turns a karaoke file path into structured song
metadata — artist, title, disc, and track — so the library can be searched,
sorted, and grouped by artist without the user renaming their files. The
parser is a pure, deterministic string transformation shared by the browser
and desktop builds.

> Source: `src/pykaraoke/filename_parser.py`; behaviour verified by
> `tests/pykaraoke/test_filename_parser.py`. Consumed by
> `src/pykaraoke/database.py` during library scans, configured through the
> `file_name_type` setting exposed by `src/pykaraoke/webapp.py`.

> Known limitation: only the ASCII space-dash-space separator (`" - "`) and
> plain ASCII hyphens are recognised. Unicode dash variants (em dash, en
> dash, full-width hyphen-minus, figure dash), full-width ASCII characters,
> and decomposed (NFD) Unicode are **not** normalised. Closing that gap is a
> proposed, not-yet-implemented change recorded in
> `openspec/changes/filename-parser-edge-cases/`.

## Requirements

### Requirement: Parsing is a pure, deterministic function

Filename parsing SHALL be a side-effect-free transformation from a path
string to a `ParsedSong` record. It SHALL perform no file, network, or
environment access and SHALL hold no module-level mutable state, so that
identical input produces byte-identical output on Windows, macOS, and Linux
regardless of locale.

#### Scenario: Identical input yields identical output

- **WHEN** the same filepath is parsed repeatedly, on any supported platform
- **THEN** the returned `ParsedSong` fields are identical each time

#### Scenario: Parsing performs no I/O

- **WHEN** a filepath is parsed for a file that does not exist on disk
- **THEN** parsing still succeeds and produces the same result as for a file that does exist

### Requirement: Only the final path component is parsed

The parser SHALL strip directory components before extraction, normalising
backslashes to forward slashes first, so that dashes appearing in directory
names never contaminate artist or title.

#### Scenario: Directory names containing dashes are ignored

- **WHEN** the path `/music/rock-band/best-of/Artist - Title.mp3` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title`

#### Scenario: Windows separators are handled on every platform

- **WHEN** the path `C:\my-music\rock-hits\Queen - Bohemian Rhapsody.cdg` is parsed
- **THEN** the artist is `Queen`
- **AND** the title is `Bohemian Rhapsody`

#### Scenario: A deep directory chain contributes nothing

- **WHEN** the path `/a-b/c-d/e-f/Artist - Title.cdg` is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title`

### Requirement: Only the final file extension is removed

The parser SHALL remove only the last extension from the basename, leaving
earlier dots in the stem intact.

#### Scenario: Multiple extensions keep the inner extension

- **WHEN** `Artist - Song.name.cdg` is parsed
- **THEN** the title is `Song.name`

#### Scenario: A path without an extension is parsed in full

- **WHEN** `Artist - Title` (no extension) is parsed
- **THEN** the artist is `Artist`
- **AND** the title is `Title`

### Requirement: Space-dash-space filenames split at the first separator

When the stem contains a separator of one-or-more whitespace, a hyphen, and
one-or-more whitespace, the parser SHALL split at the **first** such
separator only: the segment before it is the artist and everything after it —
including any further separators — is the title.

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

### Requirement: Legacy naming conventions are selected by configuration

When the stem contains no space-dash-space separator, the parser SHALL fall
back to the legacy convention named by the parser's `file_name_type`, one of
`DISC_TRACK_ARTIST_TITLE`, `DISCTRACK_ARTIST_TITLE`, `DISC_ARTIST_TITLE`, or
`ARTIST_TITLE` (the default). The convention is a persisted user setting, so
the same library can be re-parsed under a different scheme.

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

### Requirement: Artist-Title mode groups dashed abbreviations into the artist

In `ARTIST_TITLE` (the default) mode, when the first hyphen-separated segment
is a short all-caps abbreviation, the parser SHALL continue consuming
consecutive such segments as part of the artist so names such as `AC-DC`,
`MC-Hammer`, and `ZZ-Top` are attributed correctly. A segment qualifies when
it is at most three characters long, consists of case-bearable characters
that are all uppercase, and contains at least one letter.

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

### Requirement: Unrecognised input degrades to a title-only result

When a filename matches no recognised convention — including names with no
separator at all, and legacy names with fewer segments than the configured
convention requires — the parser SHALL return the full stem as the title and
leave artist, disc, and track empty. It SHALL emit a diagnostic message at
debug level and SHALL NOT raise.

#### Scenario: A bare title with no separator

- **WHEN** `JustATitle.mp3` is parsed
- **THEN** the title is `JustATitle`
- **AND** the artist is empty

#### Scenario: Too few segments for a legacy convention

- **WHEN** `OnePart.cdg` is parsed with `DISC_TRACK_ARTIST_TITLE`
- **THEN** the title is `OnePart`
- **AND** the artist is empty

#### Scenario: An unrecognised pattern is logged, not raised

- **WHEN** a stem matching no convention is parsed
- **THEN** no exception propagates
- **AND** a debug-level diagnostic naming the stem is emitted through the module logger

### Requirement: Empty and whitespace-only input yield an empty result

The parser SHALL return an empty `ParsedSong` (all four fields empty) for an
empty string or a whitespace-only path, and SHALL NOT raise for them. A
missing or non-string value is a caller defect and SHALL fail fast rather
than silently returning a default.

#### Scenario: Empty string

- **WHEN** the empty string is parsed
- **THEN** the artist and title are both empty

#### Scenario: Whitespace-only filename

- **WHEN** a filename containing only whitespace is parsed
- **THEN** the artist and title are both empty

#### Scenario: A null value fails fast

- **WHEN** a non-string value (such as null) is passed to the parser
- **THEN** a type error is raised immediately

### Requirement: Archive members fall back to the directory as artist

`parse_zip_path()` SHALL first attempt ordinary parsing of the archive member
path. When that yields no artist and the path has a parent directory, it
SHALL use the immediate parent directory name as the artist while keeping the
parsed filename stem as the title. It SHALL otherwise return the ordinary
parse result unchanged.

#### Scenario: Directory supplies the artist

- **WHEN** `Language/Artist/Title.kar` is parsed as an archive member
- **THEN** the artist is `Artist`
- **AND** the title is `Title`

#### Scenario: An in-filename artist wins over the directory

- **WHEN** `Some Dir/Queen - Bohemian Rhapsody.kar` is parsed as an archive member
- **THEN** the artist is `Queen`
- **AND** the title is `Bohemian Rhapsody`

> Note: the parser preserves characters as-is (for example `Björk - Jóga.cdg`
> round-trips unchanged) but does not perform Unicode normalisation. Its
> private helpers also use partially annotated containers (`_parse_artist_title`
> takes a bare `list`), which the project constitution's strong-typing
> requirement would have fully annotated; tightening that is part of the
> pending `filename-parser-edge-cases` change rather than current behaviour.
