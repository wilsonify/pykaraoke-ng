# Proposal: Reliable media pairing — one song per performance

> Status: proposed — implemented by this change.
> Capabilities: `song-library`
> Related: `scan-diagnostics-and-filters` (archived) added the scan report this
> change extends; `lyrics-timing-resilience` (this initiative) fixes the lyrics
> side of the same songs.

## Intent

A karaoke library is a pile of files that only make sense when they are paired.
The scanner currently decides that pairing by base name alone, in any folder,
which produces three user-visible failures found while auditing the engine:

1. **Wrong audio, silently.** With two packs that both contain
   `A - Song.cdg` and `A - Song.mp3`, both songs are paired with the *first*
   audio file found, so playing the second pack plays the first pack's audio.
   Verified: `Pack2/A - Song.cdg -> audio_name A - Song.mp3` (Pack 1's file).
2. **Duplicate performances.** A folder holding `B - Tune.cdg`, `B - Tune.lrc`
   and `B - Tune.mp3` lists *two* playable songs for one performance. The brief
   for the player is explicit that CD+G wins when both exist.
3. **Unplayable rows.** An `.lrc` whose audio is missing stays in the library
   and fails on click with "no audio file found for this LRC" — a row that can
   never work, occupying a slot in a search result during a live set.

The scan summary compounds this: `SongLibrary.scan()` returns the library size
as `added`, so rescanning an unchanged library announces every song as newly
added (verified: `{'added': 2, 'total': 2}` on an identical second scan).

## Scope

In scope:

* **Same-folder pairing.** A companion audio file (`.mp3`, `.ogg`, `.wav`) is
  resolved in the song's own folder first, exact stem before normalised stem,
  and only then anywhere else in the library (deterministic, path-ordered).
* **Explicit audio path.** `Song` carries the paired file's path
  (`audio_path`) as well as its display name, so the browser and Tauri layers
  no longer have to re-derive a path from a base name.
* **CD+G wins.** When a `.cdg` and a `.lrc`/`.lcr` share a folder and stem, the
  CD+G is the song; the lyric file is not listed separately and is reported as
  `duplicate_lyric`.
* **Lyrics without audio are reported, not listed.** An `.lrc`/`.lcr` with no
  companion audio is left out of the playable library and recorded as
  `missing_audio` with a suggested fix.
* **Honest counts.** `scan()` reports how many songs the scan actually added,
  and the existing `total`.
* **Per-member zip tolerance.** One unreadable member no longer costs the whole
  archive's other songs.

Out of scope:

* Playing songs that live inside a ZIP archive (unchanged; they are still
  listed and still report a named failure on play).
* Showing `.lrc` lyrics on top of CD+G playback (a new playback mode, not a
  pairing decision; CD+G keeps the canvas).
* MIDI/KAR, MPEG discovery rules (`kar`/`mpg` songs carry their own media).
* Filename parsing, search ranking, and the queue.

## Approach

`SongLibrary._rebuild()` builds both the song list and a directory-keyed audio
index once, then pairs every song from that index. Resolution order is
same-folder exact stem, same-folder normalised stem, any-folder exact stem,
any-folder normalised stem, each level choosing the alphabetically first path
so two runs over the same library always agree. Pairing is re-applied after
`prune_songs()`, so a deleted folder cannot leave a song pointing at a file
that is gone.

Lyric entries are classified in the same pass: a lyric that is shadowed by a
CD+G of the same folder and stem is a companion (`duplicate_lyric`), and a
lyric with no audio at all is a skip (`missing_audio`). Both go to the
existing scan report, so nothing is dropped without a trace — the categories
are ordinary scan outcomes, not errors.

`scan()` snapshots the song ids before rebuilding and reports the difference as
`added`, which keeps the existing `{added, total}` shape the web UI already
reads.
