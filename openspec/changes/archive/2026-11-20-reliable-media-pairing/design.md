# Design: Reliable media pairing

## Pairing resolution order

```
song: Pack2/A - Song.cdg
 1. (Pack2, "a - song")        exact stem, same folder   <- chosen
 2. (Pack2, "asong")           normalised stem, same folder
 3. ("a - song")               exact stem, any folder
 4. ("asong")                  normalised stem, any folder
```

Level 1 is the fix: it is the only level that can tell two packs apart. Levels
3 and 4 keep working libraries working — a library whose audio sits in a
subfolder (`Songs/Artist - Title.cdg` beside `Audio/Artist - Title.mp3`) paired
before this change and must keep pairing.

Within a level, candidates are sorted by path and the first is taken, so the
result is stable across scans, machines and dict ordering. A previous version
returned the first match in iteration order, which depended on scan order.

## Keeping the old contract

`audio_name` (the base name the UI displays) is retained and still written.
`audio_path` is added and is what the web layer now prefers:

```python
Song(..., audio_name="A - Song.mp3", audio_path="Pack2/A - Song.mp3")
```

`Song.from_dict()` treats `audio_path` as optional, so a library exported by an
older build loads unchanged and is re-paired on the next scan. No library
version bump: the change is additive and the persisted shape stays readable by
both builds.

## Why lyric files are classified during the rebuild

The decision needs three facts that only the rebuild has together: which files
exist in a folder, which of them is a CD+G, and which audio each lyric could
use. Doing it in `_rebuild()` keeps one pass and one source of truth; a second
pass over `self.songs` would have to re-read `_files` and could disagree with
the first.

## Why `.lrc` without audio is not listed

Two defensible behaviours exist: list it and fail on click (today), or omit it
and report it. The library exists to play songs; a row that cannot play costs
a search slot and produces an error the DJ has to dismiss mid-set. Because the
skip is reported (`missing_audio` + the file path), the user can fix the
library, so omitting loses no information. This is the one user-visible
behaviour change in this capability, and it is recorded in the spec delta.

## CD+G preference

The brief for the player requires CD+G to win when both a `.cdg` and an `.lrc`
exist: the operator expects the graphics they prepared. The lyric file is
therefore a companion of the CD+G song rather than a second performance. It is
reported as `duplicate_lyric` so the count of skipped files still adds up.

## Alternatives rejected

* **Pair only within the same folder (no fallback).** Cleaner rule, but it
  silently unpairs existing libraries that keep audio elsewhere, turning
  playable songs into failures — a regression the brief forbids.
* **Pair by folder-relative prefix of the `id`.** Equivalent for loose files,
  but songs inside archives have synthetic paths and would need special cases.
* **Drop `audio_name` in favour of `audio_path`.** The UI displays the base
  name and existing tests assert it; removing it is churn without benefit.
* **Report `missing_audio` as an error row in the UI.** The scan report already
  separates problems from ordinary skips; this is an ordinary skip.
