# Delta for Song Library

> Change: `reliable-media-pairing`. `## MODIFIED Requirements` replaces the
> requirement of the same name in `openspec/specs/song-library/spec.md`;
> `## ADDED Requirements` is new.

## MODIFIED Requirements

### Requirement: Companion audio pairing

The library SHALL attach a companion audio file (`.mp3`, `.ogg`, `.wav`) to
each top-level `.cdg`, `.lrc`, and `.lcr` song, recording its base name
(`audio_name`) and path (`audio_path`). Resolution SHALL try the same folder
with an exact stem, then a normalised stem, then any folder with an exact stem,
then any folder with a normalised stem, choosing the alphabetically first path
at each level so repeated scans agree. Songs inside a zip SHALL NOT be paired.

> Source: `_audio_index()`, `_pair_song()`, `_normalize_stem()`, and
> `AUDIO_EXTENSIONS` in `src/pykaraoke/database.py`; verified by
> `TestCompanionPairing`.

#### Scenario: Exact stem match

- **WHEN** `Queen - Bohemian Rhapsody.cdg` and
  `Queen - Bohemian Rhapsody.mp3` are scanned
- **THEN** the song's `audio_name` is `Queen - Bohemian Rhapsody.mp3`
- **AND** its `audio_path` is that file's path

#### Scenario: Normalised match ignores numbering and suffixes

- **WHEN** `01 - Inside Out.lrc` is scanned alongside
  `Inside Out - Karaoke.mp3`
- **THEN** the song's `audio_name` is `Inside Out - Karaoke.mp3`

#### Scenario: Same base name in two folders pairs within each folder

- **WHEN** `Pack1/A - Song.cdg` with `Pack1/A - Song.mp3`, and
  `Pack2/A - Song.cdg` with `Pack2/A - Song.mp3`, are scanned together
- **THEN** each song's `audio_path` is the audio file in its own folder

#### Scenario: No companion file

- **WHEN** a `.cdg` song has no matching audio entry anywhere in the library
- **THEN** its `audio_name` and `audio_path` remain unset

#### Scenario: Audio in another folder still pairs

- **WHEN** `Songs/A - B.cdg` is scanned with `Audio/A - B.mp3`
- **THEN** the song is paired with `Audio/A - B.mp3`

### Requirement: Scan reporting

The library SHALL record a structured scan report — per-input outcome plus
per-kind counts — covering `unsupported`, `filtered`, `corrupt_archive`,
`unsupported_compression`, `unreadable`, `parse_failure`, `duplicate_lyric`,
and `missing_audio`. The report SHALL be retrievable and clearable by the
caller and SHALL never influence which songs are added, except where another
requirement in this capability defines a song as unplayable.

> Source: `SongLibrary._report()`, `scan_report()`, `REPORT_CATEGORIES`, and
> `clear_scan_report()` in `src/pykaraoke/database.py`; verified by
> `TestScanReport`.

#### Scenario: A mixed batch reports every category

- **WHEN** a scan batch mixes an unsupported file, a filtered file, and a
  parseable song
- **THEN** the report counts one `unsupported`, one `filtered`, and zero
  problems for the parseable song

#### Scenario: Unreadable archive outcomes are distinguished

- **WHEN** bytes that are not a valid zip are scanned
- **THEN** the library adds no songs and does not raise
- **AND** the scan report records the archive path as `corrupt_archive`

#### Scenario: Unsupported compression is distinguished

- **WHEN** a valid zip whose members use a compression method the runtime
  cannot read is scanned
- **THEN** the library adds no songs and does not raise
- **AND** the scan report records the archive path as
  `unsupported_compression`

#### Scenario: One unreadable member is reported on its own

- **WHEN** a zip's first member is readable and a later member cannot be read
- **THEN** the readable members still become songs
- **AND** the report records `name!member` as `unreadable`

#### Scenario: Reporting never aborts

- **WHEN** a corrupt archive is followed by a valid file in the same batch
- **THEN** the valid file still becomes a song

#### Scenario: A parse that raises is recorded, not fatal

- **WHEN** filename parsing raises for a file during a scan
- **THEN** the scan report counts one `parse_failure` for that path
- **AND** the file is still added as a title-only song

### Requirement: Scanning file entries

The library SHALL accept a batch of file entries of the shape
`{"name", "path", "size"}`, index them by their lowercased path, and rebuild
the song list from every entry seen so far. Re-scanning the same entry SHALL
not produce duplicates, and two files that share a basename in different
folders SHALL remain distinct songs. The result SHALL report `added` as the
number of songs this scan introduced (zero for an unchanged library) and
`total` as the library size afterwards.

> Source: `SongLibrary.scan()` and `_rebuild()` in `src/pykaraoke/database.py`.

#### Scenario: A batch adds songs with parsed metadata

- **WHEN** a batch containing `Queen - Bohemian Rhapsody.cdg` is scanned
- **THEN** the library contains one `cdg` song
- **AND** its artist is `Queen` and its title is `Bohemian Rhapsody`
- **AND** `added` is 1

#### Scenario: Repeated scans are idempotent

- **WHEN** the same file entries are scanned twice
- **THEN** the library contains each song exactly once
- **AND** the second scan reports `added` of 0

#### Scenario: Same basename, different folders

- **WHEN** `One/A - B.cdg` and `Two/A - B.cdg` are scanned
- **THEN** the library contains two distinct songs

#### Scenario: Unsupported entries are skipped

- **WHEN** a batch mixes `notes.txt` and `cover.jpg` with `Artist - Title.kar`
- **THEN** only the `.kar` file becomes a song

#### Scenario: Empty or missing input is a no-op

- **WHEN** the scan receives no entries
- **THEN** the library reports its current size and adds nothing

## ADDED Requirements

### Requirement: CD+G wins over a lyric file of the same stem

When a `.cdg` and a `.lrc` or `.lcr` share a folder and stem, the library SHALL
provide one song — the CD+G — and SHALL NOT list the lyric file as a separate
playable song. The lyric file SHALL be recorded in the scan report as
`duplicate_lyric`, so a scan's outcomes still account for every input.

> Source: `_rebuild()` lyric classification in `src/pykaraoke/database.py`;
> verified by `TestLyricClassification`.

#### Scenario: CD+G and LRC of one performance are one song

- **WHEN** `B - Tune.cdg`, `B - Tune.lrc`, and `B - Tune.mp3` are scanned
- **THEN** the library contains exactly one song
- **AND** its kind is `cdg`
- **AND** the report counts one `duplicate_lyric` for `B - Tune.lrc`

#### Scenario: A duplicated lyric extension is reported, not listed twice

- **WHEN** `B - Tune.lrc` and `B - Tune.lcr` are scanned with one audio file
- **THEN** one `lrc` song is listed
- **AND** the report counts one `duplicate_lyric`

### Requirement: Lyrics without audio are reported instead of listed

A `.lrc` or `.lcr` file that has no companion audio anywhere in the library
SHALL NOT become a song, because it can never be played. It SHALL be recorded
in the scan report as `missing_audio` under its path, so the operator can add
the audio file. A lyric file shadowed by a CD+G SHALL be reported as
`duplicate_lyric` instead, never as `missing_audio`.

> Source: `_rebuild()` lyric classification in `src/pykaraoke/database.py`;
> verified by `TestLyricClassification`.

#### Scenario: Unpaired lyrics are not listed

- **WHEN** `Orphan - Song.lrc` is scanned with no audio file beside it
- **THEN** the library contains no song for it
- **AND** the report counts one `missing_audio` for `Orphan - Song.lrc`

#### Scenario: Adding the audio file makes the song appear

- **WHEN** `Orphan - Song.mp3` is scanned afterwards
- **THEN** the library contains one `lrc` song for the pair
