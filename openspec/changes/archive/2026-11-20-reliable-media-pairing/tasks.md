# Tasks: Reliable media pairing

## 1. Spec delta

- [x] 1.1 Add `duplicate_lyric` and `missing_audio` to the scan-report
      categories and to the scan-report requirement.
- [x] 1.2 Restate companion pairing: same-folder preference, deterministic
      fallback, `audio_path`, and no pairing inside archives.
- [x] 1.3 Add requirements for CD+G preference and for unpaired lyrics.

## 2. Engine (`src/pykaraoke/database.py`)

- [x] 2.1 `Song.audio_path` (optional in `from_dict`, present in `to_dict`).
- [x] 2.2 `_audio_index()` — same-folder and global, exact and normalised,
      path-sorted; built once per rebuild.
- [x] 2.3 `_pair_song()` — the four-level resolution order; re-applied by
      `prune_songs()`.
- [x] 2.4 `_rebuild()` classifies lyric entries: shadowed by a CD+G
      (`duplicate_lyric`), duplicate lyric of the same stem
      (`duplicate_lyric`), or unpaired (`missing_audio`).
- [x] 2.5 `scan()` reports the number of songs actually added.
- [x] 2.6 Zip scanning probes each member and skips only the unreadable one.
- [x] 2.7 `_open_archive()` distinguishes corrupt, unsupported-compression and
      unreadable archives instead of collapsing every failure.

## 3. Boundary (`src/pykaraoke/webapp.py`)

- [x] 3.1 `scan_files()`/`library_songs()` expose `audio_path` unchanged from
      the song payload (no new method needed).
- [x] 3.2 Scan payload keeps `{added, total}` semantics.

## 4. Regression tests (`tests/pykaraoke/test_database.py`)

- [x] 4.1 Two packs with the same base name pair their own audio.
- [x] 4.2 Same-folder exact beats a global exact match.
- [x] 4.3 Cross-folder fallback still pairs (existing test kept).
- [x] 4.4 CD+G shadows the lyric of the same stem, reported once.
- [x] 4.5 Lyric without audio is not listed and is reported.
- [x] 4.6 `.lrc`/`.lcr` duplicates of one stem yield one lyric song.
- [x] 4.7 `added` counts only new songs.
- [x] 4.8 `audio_path` round-trips and old JSON without it still loads.
- [x] 4.9 Prune re-pairs the songs that remain.
- [x] 4.10 One unreadable zip member does not lose its neighbours.

## 5. Documentation

- [x] 5.1 `docs/reference/formats.md` pairing rules and CD+G preference.
- [x] 5.2 `docs/reference/engine-api.md` scan categories and `audio_path`.
- [x] 5.3 `docs/architecture/engine.md` scan/pairing pipeline.
- [x] 5.4 User guide: what a skipped lyric file means and how to fix it.

## 6. Verification

- [x] 6.1 `python -m pytest -q` — whole suite green.
- [x] 6.2 `python -m ruff check src tests` and `mypy src/pykaraoke`.
- [x] 6.3 `openspec validate --all --strict`.
