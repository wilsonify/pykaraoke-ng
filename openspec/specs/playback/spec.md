# Playback Specification

## Purpose

How PyKaraoke-NG turns a supported karaoke file into audio, video, and timed
lyrics inside the page: CD+G packet decoding onto a canvas, MIDI/KAR lyric and
note parsing for a Web Audio synthesizer, LRC lyric parsing with optional
word-level `.elrc` timing and duet part tags, and MPEG video via a native
`<video>` element.

> Source: `src/pykaraoke/cdg.py`, `src/pykaraoke/midi.py`, `src/pykaraoke/lrc.py`,
> `src/pykaraoke/webapp.py`, `src/web/index.html`

## Requirements

### Requirement: Media format coverage

The player SHALL play CD+G (`.cdg` with a companion audio file), MIDI Karaoke
(`.kar`, `.mid`), LRC lyrics (`.lrc`, `.lcr` with a companion audio file and an
optional `.elrc`), and MPEG video (`.mpg`, `.mpeg`, `.avi`).

#### Scenario: Format drives the playback path

- **WHEN** a song of one of the supported kinds is played
- **THEN** the player selects the matching decoder (CD+G canvas, MIDI synth, LRC lyrics over audio, or video element)
- **AND** an unsupported kind is rejected with a status message rather than a crash

### Requirement: CD+G packet decoding

The CD+G decoder SHALL read the stream as fixed 24-byte packets, act only on
packets whose first byte carries the CD+G command code, and ignore unknown
instructions and truncated trailing packets without raising.

#### Scenario: Unknown instruction is ignored

- **WHEN** a packet carries an instruction the decoder does not implement
- **THEN** the framebuffer is unchanged and decoding continues with the next packet

#### Scenario: Truncated final packet

- **WHEN** the stream ends with fewer than 24 bytes remaining
- **THEN** the partial packet is not processed and no error is raised

### Requirement: CD+G timing

The decoder SHALL map a media timestamp to a packet index at 300 packets per
second of audio.

#### Scenario: Timestamp to packet index

- **WHEN** the player asks for the packet index for a given number of milliseconds
- **THEN** the index is the timestamp scaled by 300 packets per second

### Requirement: CD+G framebuffer and visible area

The decoder SHALL maintain a 300×216 framebuffer of palette indices and expose
the centred 288×192 visible area, divided into a 6×4 grid of 48×48 tiles.

#### Scenario: Visible area geometry

- **WHEN** the decoder is initialised
- **THEN** the visible area is 288×192 pixels inset by 6 pixels horizontally and 12 pixels vertically
- **AND** it is divided into 24 tiles of 48×48 pixels

### Requirement: Incremental dirty-tile updates

The decoder SHALL report only the tiles that changed since the previous update,
along with the current border colour, and SHALL report nothing when no tile is
dirty.

#### Scenario: Only changed tiles are returned

- **WHEN** a tile block touches a single tile after the previous update was consumed
- **THEN** the next update returns that tile and the dirty mask is cleared

#### Scenario: Clean decoder

- **WHEN** the decoder is advanced with no new content dirtying the screen
- **THEN** the update reports no changes

#### Scenario: First frame

- **WHEN** a freshly created decoder is updated before any packet is processed
- **THEN** all 24 tiles are reported so the canvas can be painted blank

### Requirement: CD+G rendering instructions

The decoder SHALL apply the CD+G memory preset, border preset, tile block, tile
block XOR, scroll preset, scroll copy, colour-table load, and transparent-colour
instructions, including the scroll offsets that shift later tiles.

#### Scenario: Memory preset clears the screen

- **WHEN** a memory-preset instruction is decoded
- **THEN** every pixel takes the preset colour index and the whole screen is marked dirty

#### Scenario: Tile block draws its 12×6 bitmap

- **WHEN** a tile block instruction is decoded at a position
- **THEN** its 12 rows of 6 pixels are written with the two colour indices before the tile is reported

#### Scenario: XOR tile block inverts

- **WHEN** a tile block XOR instruction is decoded over existing pixels
- **THEN** each set bit inverts the pixel using the second colour index

#### Scenario: Scroll shifts content

- **WHEN** a scroll instruction shifts the screen by a whole number of pixels
- **THEN** the content moves accordingly and the whole screen is marked dirty

#### Scenario: Colour table load repaints

- **WHEN** a colour-table load instruction is decoded
- **THEN** the palette entries are updated and the whole screen is marked dirty so it is re-rendered under the new colours

#### Scenario: Border colour is exposed

- **WHEN** a border preset has been decoded
- **THEN** the reported border colour is the palette entry it set
- **AND** before any border preset the border colour is absent

### Requirement: Seeking a CD+G stream

The decoder SHALL support seeking to a timestamp by rewinding, decoding forward
to the packet for that time, and marking the whole screen dirty.

#### Scenario: Seek redraws the frame

- **WHEN** the player seeks a CD+G to an earlier time
- **THEN** the decoder rewinds, fast-forwards to that packet, and reports all tiles so the canvas is fully redrawn

### Requirement: MIDI/KAR parsing

The parser SHALL accept a Standard MIDI File with a header chunk and one or
more track chunks and produce timed lyric events, timed note events, per-channel
program changes, tempo changes, and a duration, or report failure for input that
is not a usable karaoke MIDI file.

#### Scenario: Valid karaoke MIDI file

- **WHEN** a `.kar`/`.mid` file with lyric events is parsed
- **THEN** the result exposes lyrics, notes, programs, tempo, and a duration

#### Scenario: Not a MIDI file

- **WHEN** the data does not begin with a MIDI header chunk
- **THEN** parsing reports failure instead of raising

#### Scenario: No lyrics present

- **WHEN** the file parses but contains no usable lyric events
- **THEN** parsing reports failure rather than returning an empty song

### Requirement: MIDI lyric selection and timing

The parser SHALL select the richest available lyric set, preferring a track
marked as the words track, and SHALL convert click positions to milliseconds by
applying every tempo change in turn, holding the last tempo indefinitely.

#### Scenario: Words track wins

- **WHEN** one track is marked as the words track and holds lyrics
- **THEN** its lyrics are chosen even when another track also contains text

#### Scenario: Tempo changes

- **WHEN** the file changes tempo partway through
- **THEN** events after the change are timed using the new tempo

### Requirement: MIDI lyric lines and spacing

The parser SHALL group lyric syllables into display lines using the line breaks
in the file and SHALL repair runs where words are not separated by inserting
spaces when the proportion of gaps is very low.

#### Scenario: Line breaks split lyrics

- **WHEN** the file marks a line break between syllables
- **THEN** the syllables are placed on separate display lines

#### Scenario: Run-together words

- **WHEN** nearly none of the syllables in a file carry surrounding spaces
- **THEN** spaces are inserted between the words of each line, honouring an existing trailing hyphen as a syllable split

### Requirement: MIDI note events

The parser SHALL pair note-on and note-off events per channel and note into
note events with a start time, velocity, and duration, treating a note-on with
zero velocity as a note-off and giving an unmatched note-on a short default
duration.

#### Scenario: Note-on and note-off pair

- **WHEN** a note-on is followed by a matching note-off
- **THEN** a note event starts at the note-on time and lasts until the note-off time

#### Scenario: Unmatched note-on

- **WHEN** a note-on has no matching note-off
- **THEN** it is given a short default duration so it is still audible

### Requirement: MIDI/KAR has no duet parts

The player SHALL NOT expose duet part information for MIDI/KAR lyrics, because
that format has no way to express it.

#### Scenario: KAR playback

- **WHEN** a `.kar`/`.mid` song is played
- **THEN** its lyric lines carry no part tag and no singer chip is shown

### Requirement: LRC parsing

The parser SHALL parse LRC text into timed lyric events, reading `[mm:ss.xx]`
timestamps, `[key:value]` metadata tags, multiple leading timestamps on one line,
and a global `[offset:±ms]` adjustment that makes lyrics appear sooner; it SHALL
report a duration from the `length` tag when present, otherwise from the last
timestamp, and SHALL report failure for text with no usable timed lyrics.

#### Scenario: Timed line

- **WHEN** a line begins with an `[mm:ss.xx]` timestamp
- **THEN** one lyric event is produced at that time with the remaining text

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

### Requirement: Enhanced LRC word timing

The parser SHALL support word-level `<mm:ss.xx>` tags inside a line, giving the
text before the first tag the line's time and each tag the time of the word that
follows it, and SHALL leave an unrecognised angle-bracket token as literal text.

#### Scenario: Word tags split a line

- **WHEN** a line contains word timestamps
- **THEN** each word segment is emitted with its own time in file order

#### Scenario: Malformed word tag

- **WHEN** an angle-bracket token is not a valid word timestamp
- **THEN** it stays part of the line text and the line keeps its line-level timing

### Requirement: Companion `.elrc` word timing

The player SHALL merge word-level timing from a companion `.elrc` file into the
parsed lyrics, matching on letters alone so punctuation, spacing, and case may
differ between the files. It SHALL keep every word of a line, with untimed
words inheriting a neighbour's time and times never running backwards, SHALL
apply the song's offset to the `.elrc` times so both stay aligned, and SHALL
fall back to the plain line timings when no word could be matched.

#### Scenario: Words align to their line

- **WHEN** a companion `.elrc` times the words of a line
- **THEN** those words are emitted with the `.elrc` times in that line

#### Scenario: Unmatched word is kept

- **WHEN** the `.elrc` never mentions one of a line's words
- **THEN** that word still appears in the line and its time does not run backwards

#### Scenario: Stray entry

- **WHEN** an `.elrc` entry does not continue the next letters of the line
- **THEN** it is skipped and the remaining words still align correctly

#### Scenario: Nothing matched

- **WHEN** no `.elrc` word can be matched to the lyrics
- **THEN** the player keeps the original line-level lyric timings

### Requirement: Duet part tags in LRC

The parser SHALL read an optional duet part tag that immediately follows a
line's timestamps, accepting `a`, `b`, and `ab` (with `ba` normalised to `ab`
and all tags case-insensitive); a tag must follow timestamps to be recognised,
and the part SHALL apply to every syllable of the line, including all words of
an enhanced line and all repetitions of a repeated timestamp.

#### Scenario: Part per line

- **WHEN** consecutive lines are tagged `a`, `b`, `ab`, and untagged
- **THEN** each tagged line carries its part and the untagged line carries none

#### Scenario: Shared-line synonym

- **WHEN** a line is tagged `ba`
- **THEN** it is treated as the shared part `ab`

#### Scenario: Unknown bracket tag

- **WHEN** a bracket group after the timestamps is not a recognised part id
- **THEN** it is stripped like any other bracket group and no part is set

#### Scenario: Part covers every word

- **WHEN** a tagged line also carries word-level timing
- **THEN** every word syllable of that line carries the same part

### Requirement: Solo songs keep their payload

The parser SHALL omit duet keys entirely for a song with no part tags and no
singer names, so solo songs produce exactly the previous lyric payload.

#### Scenario: Solo payload shape

- **WHEN** a song has no part tags and no `[pa:]`/`[pb:]` metadata
- **THEN** no lyric event carries a part and the result exposes no singer-name map

### Requirement: Duet singer names

The parser SHALL expose the two optional singer names declared by `[pa:Name]`
and `[pb:Name]`, including only the names actually provided, and SHALL omit the
map when neither is named.

#### Scenario: Both singers named

- **WHEN** the song declares both singer names
- **THEN** the result exposes a map from the part ids `a` and `b` to those names

#### Scenario: One or no singers named

- **WHEN** only one name is provided, or none
- **THEN** only that name is exposed, or no map at all

### Requirement: Duet presentation in the UI

The player SHALL visually distinguish duet lines by their part and SHALL show a
small chip naming the singer for each tagged line, using the declared singer
name when available and the generic `A`, `B`, or `A+B` label otherwise.

#### Scenario: Named singers

- **WHEN** a tagged line belongs to a song that names its singers
- **THEN** its chip shows the singer's name, and a shared line shows both names joined

#### Scenario: Unnamed singers

- **WHEN** a tagged line belongs to a song that names no singers
- **THEN** its chip shows the generic part label

### Requirement: MPEG video playback

The player SHALL play MPEG video files through a native video element and
advance to the next queued song when the video ends; a video stored inside a zip
archive SHALL NOT be played and SHALL report an error message instead.

#### Scenario: Video ends

- **WHEN** an MPEG video reaches its end
- **THEN** the player advances as it does when any song ends

#### Scenario: Video inside a zip

- **WHEN** the selected MPEG video lives inside a zip archive
- **THEN** playback is refused with a status message

### Requirement: Transport control

The player SHALL support play and pause, seeking to a position, and moving to
the next song, and SHALL advance automatically to the next queued song when the
current song ends, stopping and reporting that the queue has finished when
nothing is queued.

#### Scenario: Play/pause toggle

- **WHEN** the play control is used while a song is paused
- **THEN** playback resumes, and using it again pauses playback

#### Scenario: Seek

- **WHEN** the player seeks to a position
- **THEN** the active audio, synthesizer, video, or CD+G decoder moves to that position and the displayed lyrics refresh

#### Scenario: Auto-advance

- **WHEN** the current song ends and the queue holds another song
- **THEN** that next song starts automatically

#### Scenario: Queue finished

- **WHEN** the current song ends and the queue is empty
- **THEN** playback stops and the status reports that the queue has finished

#### Scenario: Stop

- **WHEN** the stop control is used
- **THEN** playback ends, the active player is released, and the position display resets to the start

> Note: `docs/user-guide/index.md` states that Stop keeps the current song
> loaded so Play can restart it, and that the rewind/forward buttons move by
> 10 seconds. The implementation does neither: the stop control clears the
> current song, and the rewind/forward buttons move by 5 seconds
> (`seekTo(state.songClock ± 5000)`). This specification records the
> implemented behaviour; the user guide needs reconciling.

### Requirement: MIDI synthesis

The player SHALL synthesize MIDI/KAR note events with the Web Audio API,
scheduling notes shortly ahead of the play head, honouring per-channel program
changes and the current volume, and supporting start, pause, resume, seek, and
stop.

#### Scenario: Notes are scheduled ahead of the play head

- **WHEN** a KAR song is playing
- **THEN** upcoming note events are scheduled a short look-ahead in advance

#### Scenario: Volume

- **WHEN** the volume setting changes during KAR playback
- **THEN** the synthesizer output gain follows it

#### Scenario: Synthesizer ends

- **WHEN** the synthesizer passes the song duration
- **THEN** the end-of-song handling runs as for any other format
