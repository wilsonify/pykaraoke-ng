# Proposal: Lyrics timing resilience — accept the files people actually have

> Status: proposed — implemented by this change.
> Capabilities: `playback`, `ux-slim-sidebar`
> Related: `reliable-media-pairing` (this initiative) decides *which* songs
> exist; this change makes their lyrics play.

## Intent

Lyrics are half of what a karaoke player does, and the parser currently
rejects the most common real-world variations outright. Audited against the
engine and against the `.lrc`/`.elrc` pairs produced by the project's own
chord-vault pipeline:

1. **Timestamps without a fractional second kill the file.** `_LINE_RE`
   requires `[mm:ss.xx]`. Verified: `[00:12]Hello` → `parse_lrc` returns
   `None`, `[00:12:34]Hello` → `None`, `[100:12.00]…` → `None`. A file whose
   lines all use `[mm:ss]` produces no lyrics at all, so the song fails to
   play with "no timed lyrics found" — not a missing feature but a dead song.
2. **The ELRC dialect is only half supported.** A chord-vault `.elrc` repeats
   the whole line as a *line header* at the same timestamp as its first word
   (see `chord-vault/capo=0/Olivia Rodrigo/Drivers License/…elrc`). The merge
   handles that header, but a file whose `.lrc` carries no usable timing
   cannot be read at all, even though the `.elrc` describes every line.
3. **Nothing tells the user a line was dropped.** Malformed timestamps are
   skipped silently, so a lyric display that starts late looks like a bug in
   the player.
4. **The stage cannot be operated during a verse.** There is no click-to-seek
   on a lyric line, no visual distinction between the line just sung and the
   line coming up, and no way to make the words bigger for a singer standing
   back from the screen.

## Scope

In scope (`playback`):

* **Tolerant line timestamps**: `[mm:ss]`, `[mm:ss.xx]`, `[mm:ss:xx]`,
  `[m:ss]`, and minutes longer than two digits, in both `.lrc` and `.elrc`
  files, and in enhanced-LRC `<mm:ss.xx>` word tags.
* **Counted warnings**: a line that looks timed but cannot be parsed is
  skipped and reported as a warning with its line number and text, instead of
  disappearing silently. Clean files keep their exact current payload.
* **ELRC line-header inference**: when a `.lrc` yields no timed lines but a
  companion `.elrc` describes lines as header + per-word entries, the lyrics
  come from the `.elrc`.

In scope (`ux-slim-sidebar`):

* **Current/past/next lyrics**: the stage shows the line being sung, the line
  just sung (dimmed above), and the line coming up, distinguished by class.
* **Click a lyric line to seek** to its timestamp, when seeking is available.
* **Lyric size** setting (small / medium / large), persisted, applied to both
  LRC and MIDI lyrics.
* **Active line kept in view** as the window advances.

Out of scope:

* Full-screen or karaoke-CD style bouncing-ball lyric rendering; the panel
  stays a 300–450 px utility strip (deliberate difference from
  PerfectKaraokeEternal, which also renders a full-window lyric stage).
* Pitch/tempo/countdown (`playback-pitch-tempo-countdown`).
* Changing chord detection or the `.chrc` format.
* Transliteration, romaji, or right-to-left layout work.

## Approach

`lrc._TIMESTAMP` becomes one shared pattern used by line tags, `.elrc` entries
and enhanced word tags, with the fraction optional and `:` or `.` accepted as
the fraction separator. `_tag_ms()` treats a missing fraction as zero, so no
caller needs to know which form matched.

Warnings are data, not exceptions: `parse_lrc()` gains a `warnings` list
(omitted when empty, so existing payloads and tests are unchanged) and
`parse_elrc()` gains an optional `warnings` list that receives one entry per
line whose `.elrc` timings could not be matched. `webapp.parse_lrc()` merges
both lists into the payload it returns to the UI.

`parse_elrc_lines()` reads an `.elrc` on its own: an entry whose letters are
exactly the concatenation of the entries that follow it is a line header, and
its words are timed from those entries. This is the only shape the chord-vault
pipeline emits, and it is the same rule the merge already uses to recognise a
header, so there is one definition of "header" in the module.

On the UI side the lyric window is computed by a pure helper
(`lyricWindow(lines, ms)`) that returns the past/current/next indices and the
lit syllable count, so the three-line rule is unit-tested without a DOM. The
renderer builds the three rows once per line change and then only toggles
`lit` on the syllables that changed, which also removes the per-frame
`querySelectorAll` the current renderer performs sixty times a second.
