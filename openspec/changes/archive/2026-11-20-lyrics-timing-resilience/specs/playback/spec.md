# Delta for Playback

> Change: `lyrics-timing-resilience`. `## MODIFIED Requirements` replaces the
> requirement of the same name in `openspec/specs/playback/spec.md`;
> `## ADDED Requirements` is new.

## MODIFIED Requirements

### Requirement: LRC parsing

The parser SHALL parse LRC text into timed lyric events, reading line
timestamps whose minutes are one to three digits, whose seconds are one or two
digits, and whose fractional part is optional and written after `.` or `:` with
one to three digits (`[mm:ss]`, `[mm:ss.xx]`, `[mm:ss:xx]`, `[m:ss]`,
`[mmm:ss.xxx]`). It SHALL read `[key:value]` metadata tags, multiple leading
timestamps on one line, and a global `[offset:±ms]` adjustment that makes lyrics
appear sooner; it SHALL report a duration from the `length` tag when present,
otherwise from the last timestamp, and SHALL report failure for text with no
usable timed lyrics. Every accepted form SHALL be accepted in `.elrc` files and
in enhanced-LRC word tags as well.

#### Scenario: Timed line

- **WHEN** a line begins with an `[mm:ss.xx]` timestamp
- **THEN** one lyric event is produced at that time with the remaining text

#### Scenario: Timestamp without a fraction

- **WHEN** every line begins with `[mm:ss]` and no fractional part
- **THEN** each line produces one lyric event at that whole second
- **AND** parsing succeeds rather than reporting failure

#### Scenario: Colon fractional separator

- **WHEN** a line begins with `[mm:ss:ff]`
- **THEN** the fractional part is read as hundredths of a second

#### Scenario: Long songs

- **WHEN** a line's minute field has three digits
- **THEN** the timestamp is read as that many minutes

#### Scenario: Repeated timestamp

- **WHEN** a line carries several leading timestamps
- **THEN** the same text is emitted once per timestamp

#### Scenario: Offset shifts every timestamp

- **WHEN** the song declares a positive offset
- **THEN** every lyric time is reduced by that offset and clamped so it never becomes negative

#### Scenario: Duration source

- **WHEN** the song declares a `length` metadata tag
- **THEN** the reported duration comes from that tag, otherwise from the last lyric timestamp

#### Scenario: Unusable text

- **WHEN** the input is empty or contains no line with a timestamp and text
- **THEN** parsing reports failure

## ADDED Requirements

### Requirement: Lyric parse warnings

When a line looks like a timed lyric but its timestamp cannot be parsed, the
parser SHALL skip that line and report a warning naming the line number and its
text, instead of failing the file or dropping it silently. A `.elrc` entry that
matches no word SHALL be counted per line in the same list. A file with nothing
to report SHALL keep a payload without the warnings key.

> Source: `parse_lrc()` and `parse_elrc(..., warnings=…)` in
> `src/pykaraoke/lrc.py`; surfaced by `KaraokeApp.parse_lrc()`.

#### Scenario: A malformed line is skipped and reported

- **WHEN** a file contains `[00:6x.00]Non-digit seconds` among valid lines
- **THEN** the valid lines are returned
- **AND** the payload carries one warning for that line number and text

#### Scenario: Clean files carry no warnings key

- **WHEN** every line parses
- **THEN** the payload has no warnings key

#### Scenario: Unmatched word timings are counted

- **WHEN** a `.elrc` entry matches no word of its line
- **THEN** the merged payload reports an `unmatched-elrc` warning for that line

### Requirement: ELRC line-header inference

When the `.lrc` yields no timed lines but a companion `.elrc` describes them as
a line header plus its per-word entries, the parser SHALL build the lines from
the `.elrc`: the header supplies the text and time, the following entries the
word timings. A `.lrc` with timed lines SHALL always win.

> Source: `parse_elrc_lines()` in `src/pykaraoke/lrc.py`; dialect produced by
> the chord-vault pipeline.

#### Scenario: Lines come from the header entries

- **WHEN** a `.lrc` has no timestamps and its `.elrc` holds
  `[00:11.560]I got my license` followed by `[00:11.560]I`, `[00:12.440]got`, …
- **THEN** the payload contains that line at 11.560 s with word-level syllables

#### Scenario: Only a real header starts a line

- **WHEN** an `.elrc` entry's letters are not spelled by the entries after it
- **THEN** that entry is its own line with no word timing
- **AND** the entries after it are read as further lines

#### Scenario: A usable LRC is never overridden

- **WHEN** the `.lrc` already yields timed lines
- **THEN** the `.elrc` only adds word timing to those lines
- **AND** no line is inferred from the `.elrc`
