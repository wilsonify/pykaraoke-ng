# Supported formats

PyKaraoke-NG recognises four karaoke formats. Each one is identified by its
file extension when a library folder is scanned, and each drives a different
playback path: CD+G renders to a canvas, MIDI Karaoke is synthesized with the
Web Audio API, LRC shows timed lyrics over an audio track, and MPEG video
plays in a native video element.

The authoritative behaviour is the
[Playback specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md).

## At a glance

| Format | Extensions | Kind | Audio source |
|--------|-----------|------|--------------|
| CD+G | `.cdg` | `cdg` | Separate `.mp3` / `.ogg` / `.wav` file, matched by name |
| MIDI Karaoke | `.kar`, `.mid` | `kar` | Built-in MIDI synthesis (no separate file) |
| LRC lyrics | `.lrc`, `.lcr` | `lrc` | Separate `.mp3` / `.ogg` / `.wav` file, matched by name |
| MPEG video | `.mpg`, `.mpeg`, `.avi`, `.divx`, `.xvid` | `mpg` | Embedded audio track |

Extension matching is case-insensitive. Anything the scan does not recognise
is simply ignored, so the scan never fails on unrelated files in the folder.

## CD+G (`.cdg`)

CD+G files carry graphics only; the audio lives in a sibling file. The decoder
reads the stream as fixed 24-byte packets at 300 packets per second, decodes
them into a 300×216 framebuffer, and returns only the tiles that changed so the
canvas repaints incrementally. Seeking rewinds and fast-forwards through the
packets to redraw the frame.

Because a `.cdg` has no audio of its own, it **must** be paired with a
companion audio file — see [Pairing companion audio](#pairing-companion-audio).

## MIDI Karaoke (`.kar`, `.mid`)

MIDI Karaoke files embed the lyrics and the backing music in one file, so no
companion audio is required. The player parses the header, tracks, lyric
events, note events, program changes, and tempo changes, then:

- groups syllables into display lines using the line breaks in the file, and
  repairs runs where the words are not separated by inserting spaces;
- synthesizes the notes with the Web Audio API, scheduling them slightly ahead
  of the play head and honouring program changes and the current volume.

!!! note "No duet parts"
    MIDI/KAR has no way to express which singer performs a line, so it never
    carries [duet part tags](#duet-parts). Those lyrics stay plain solo lyrics.

## LRC lyrics (`.lrc`, `.lcr`)

An LRC file is a text file of timed lyric lines, played over a companion audio
file. The parser understands:

| Syntax | Meaning |
|--------|---------|
| `[mm:ss.xx]lyric text` | A lyric line at that time |
| `[mm:ss]lyric text` | The same, without a fractional second (read as `.00`) |
| `[mm:ss:xx]lyric text` | The same, with `:` introducing the fraction |
| `[mmm:ss.xxx]lyric text` | Minutes may run to three digits on long compilations |
| `[mm:ss.xx][mm:ss.xx]text` | Several leading timestamps repeat the same text |
| `[key:value]` | Metadata, e.g. `[ti:Title]`, `[ar:Artist]` |
| `[offset:±ms]` | A global adjustment; a positive offset makes lyrics appear sooner |
| `[length:mm:ss]` | Song duration, used when present instead of the last timestamp |
| `<mm:ss.xx>` inside a line | Word-level timing (enhanced LRC) |

Example:

```lrc
[ti:My Song]
[ar:Some Artist]
[offset:0]

[00:01.00]Here is the first line
[00:05.00]And here is the second
```

### Word timing with `.elrc`

An optional companion `.elrc` file adds word-level timing on top of the line
timestamps. PyKaraoke-NG matches words on letters alone, so punctuation,
spacing, and case may differ between the `.lrc` and the `.elrc`; every word of
a line is always kept, and if nothing matches it falls back to the plain line
timings. A missing or unusable `.elrc` is not an error.

The `.elrc` merges with the LRC, so keep it beside the `.lrc` (and add the
words to the same musical timing). Both files are matched in the song's own
folder first, so two folders may hold the same base name.

### `.elrc` line headers

The `.elrc` dialect written by the chord-vault pipeline repeats each line as a
*header* at the same timestamp as its first word, followed by one entry per
word:

```elrc
[00:11.560]I got my license last week   ← header: the line
[00:11.560] I
[00:12.440] got
[00:13.320] my
[00:14.720] license
[00:15.320] last
[00:15.740] week
```

A header is recognised only when the words after it spell it letter for
letter. If the `.lrc` has no usable timestamps at all, the player builds the
lyric lines from these headers instead of giving up; a `.lrc` that does have
timed lines always takes precedence, and the `.elrc` only adds word timing.

### When a lyric line cannot be read

A line whose timestamp is malformed (`[00:6x.00]…`) is skipped, and the status
bar says how many lines were dropped. The rest of the file still plays. If a
`.elrc` word timing cannot be matched to any word of its line, that is
reported too rather than shifting the remaining words.

### Duet parts

An LRC file can record which singer performs each line. The part tag goes
immediately after the timestamp and uses generic part ids — never gendered:
`a` and `b` for the two singers, `ab` for a line they sing together. `[ba]` is
accepted as a synonym of `[ab]`, and tags are case-insensitive.

Optional `[pa:Name]` and `[pb:Name]` metadata name the two singers.

```lrc
[pa:Alice]                ← optional singer names
[pb:Bob]

[00:01.00][a]I will sing the first line
[00:05.00][b]Then I will answer back
[00:09.00][ab]Together we hold the note
[00:13.00]An untagged line stays solo
```

Tagged lines are coloured by singer — blue for **A**, green for **B**, violet
for a **shared** line — with a small chip in front naming the singer (`Alice`,
`Bob`, `Alice + Bob`, or `A`, `B`, `A+B` when the song does not name them).

A song with no `[pa:]`/`[pb:]` names and no line tags behaves exactly like a
plain solo LRC file.

## MPEG video (`.mpg`, `.mpeg`, `.avi`, `.divx`, `.xvid`)

MPEG video files carry their own audio track and play in a native `<video>`
element. When the video ends the player advances to the next queued song, as
for any other format.

!!! warning "Video inside a zip archive"
    A video stored inside a `.zip` archive cannot be played. Selecting one
    shows an error message rather than attempting playback.

## Pairing companion audio

CD+G and LRC songs are paired with an audio file in the same scan:

1. **The song's own folder first** — exact stem (ignoring case), then a
   normalised stem that ignores track-number prefixes and `karaoke` /
   `instrumental` suffixes. Two packs that both contain `A - Song.cdg` and
   `A - Song.mp3` therefore keep their own audio.
2. **Anywhere else second** — the same two matches, for libraries whose audio
   lives in a separate folder (e.g. `Songs/A - B.cdg` with `Audio/A - B.mp3`).
   Where several files match, the alphabetically first path wins, so repeated
   scans pair the same way.

Only `.mp3`, `.ogg`, and `.wav` files are used as companion audio. Pairing is
skipped for songs inside a zip archive.

### One performance per folder and stem

A folder holding `B - Tune.cdg`, `B - Tune.lrc`, and `B - Tune.mp3` describes
**one** performance, and CD+G wins: the stage renders the graphics. The lyric
file is recorded in the scan report as a duplicate lyric rather than listed as
a second song.

A `.lrc`/`.lcr` with no companion audio anywhere is **not** listed as a song —
it could never play — and is reported in the scan details so you can add the
missing audio file. `.lrc` and `.lcr` of the same stem also collapse to one
song (`.lrc` wins).

## Zip archives

Karaoke files can be scanned from `.zip` archives when **Look inside .zip
files** is enabled in [settings](configuration.md). Members are indexed like
ordinary files, with the archive name recorded on the entry. Companion audio
pairing does not apply to zip members.

## Song library layout

Organize files so CDG and LRC tracks have a matching audio file in the same
folder:

```text
~/Karaoke/
├── Artist Name/
│   ├── Song Title.cdg
│   ├── Song Title.mp3          ← audio companion for the .cdg
│   ├── Song Title.lrc          ← optional: CD+G wins, this is a companion
│   └── Another Song.kar        ← self-contained (MIDI synthesis)
└── Another Artist/
    ├── Great Song.mpg          ← self-contained (embedded audio)
    ├── Great Song.lrc
    ├── Great Song.elrc         ← optional word timing for the .lrc
    └── Great Song.mp3          ← audio companion for the .lrc
```

## See also

- [User guide](../user-guide/index.md) — setting up a library and running a show
- [Configuration](configuration.md) — sort order, CDG zoom, zip scanning
- [Playback specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md)
