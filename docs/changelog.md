# Changelog

User-visible changes, newest first. The authoritative contract for behaviour is
`openspec/specs/`; this page records when it changed and why.

## Unreleased

### Media pairing

- **Audio is paired in the song's own folder first.** Two packs that both
  contain `A - Song.cdg` and `A - Song.mp3` now keep their own audio instead of
  both using the first file found.
- **Songs carry the paired audio path** (`audio_path`), alongside the base name
  the UI displays. Libraries exported by earlier builds still load and are
  re-paired on the next scan.
- **CD+G wins over a lyric file of the same stem.** `B - Tune.cdg` +
  `B - Tune.lrc` is one performance, not two rows.
- **A `.lrc` with no companion audio is no longer listed.** It could never
  play; it is reported in the scan details as *missing audio* with the file
  path, and appears as soon as its audio file is scanned.
- **Scan summaries count additions.** Re-scanning an unchanged library reports
  0 added songs instead of repeating the library size.
- **One unreadable ZIP member no longer costs the archive's other songs**, and
  archive failures are classified as corrupt, unsupported compression, or
  unreadable instead of one catch-all.

### Lyrics

- **Timestamps without a fractional second are accepted**: `[mm:ss]`,
  `[mm:ss.xx]`, `[mm:ss:xx]`, and three-digit minutes, in `.lrc` files, `.elrc`
  files, and enhanced-LRC `<mm:ss.xx>` word tags. A file written entirely in
  whole seconds used to produce no lyrics at all and fail to play.
- **Skipped lyric lines are reported.** A line whose timestamp cannot be parsed
  is skipped and counted in the status bar; unmatched `.elrc` word timings are
  counted too. Clean files are unchanged.
- **`.elrc` line headers can stand alone.** When a `.lrc` has no usable
  timestamps, the lyric lines are built from the chord-vault-style `.elrc`
  headers (`[mm:ss]line` followed by one entry per word).

### Lyrics display

- **Three-line window**: the line just sung (dimmed), the current line (with
  syllable highlighting), and the upcoming line.
- **Click a lyric line to seek** to its timestamp, when the song can be seeked.
- **Lyric size setting** (small / medium / large) for LRC and MIDI lyrics,
  persisted between sessions.
- Lyric rendering updates only the syllables that changed, instead of rebuilding
  the row and re-querying the DOM every animation frame.

### Playback reliability

- **Rapid song switching can no longer leave two sources playing.** Every
  playback attempt carries a token; anything that finishes loading after it has
  been superseded stops itself instead of taking over.
- **The queue advances once per song.** An `ended` event fires at most once per
  attempt, including from a superseded media element.
- **Stopping releases resources**: media object URLs are revoked, the audio
  element is unloaded, and the transport position resets (Rewind after Stop no
  longer seeks the next song to the previous one's time).
- **MIDI playback ends reliably.** The synthesizer waits for its audio context
  to start before setting its clock, ends once at the end of the timeline even
  without a declared duration, and cannot fire `ended` after Stop.
- **A CD+G stream that stops decoding says so once**, instead of logging every
  frame and leaving a frozen stage unexplained. A stream the decoder survives
  but that never paints anything (damaged or empty) now says so once too,
  rather than leaving a blank stage with no explanation.

### Desktop shell

- Folder listing tolerates a symlink loop and unreadable subfolders: the folder
  is walked once, and an unreadable subfolder contributes nothing while its
  siblings still appear.
