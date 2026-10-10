# Tasks: Singer management

## 1. Pure data model and tests (vitest)

- [ ] 1.1 Implement the `ShowState` class (singers, activeId, prefs,
      playlists, history) with injectable id/clock functions; tests for
      create/select/delete, duplicate-name rejection, and prefs set/apply.
- [ ] 1.2 Playlist methods (save-queue, load resolution against a supplied
      library list, delete); tests including skipped-missing-songs.
- [ ] 1.3 History methods (record, update-last, cap, clear, re-queue
      lookup); tests for cap eviction and mid-song update.
- [ ] 1.4 `serialize()`/`load()` round-trip plus malformed-JSON,
      non-object, and unknown-version fallbacks.

## 2. Page wiring (index.html)

- [ ] 2.1 Persist/restore `pykaraoke-ng:show` alongside the existing keys;
      warn in the status bar on corrupt data.
- [ ] 2.2 Singer row UI (select + inline add + delete) above the queue;
      selection applies prefs to the transport and current playback.
- [ ] 2.3 Hook key/tempo control changes to update the active singer's
      prefs; hook `playSong()` to record/update history entries.
- [ ] 2.4 Playlists section (save queue / load / delete) with status
      feedback for skipped songs.
- [ ] 2.5 History `<details>` section (list newest-first, re-queue,
      clear).

## 3. Verification

- [ ] 3.1 vitest green; pytest untouched/green.
- [ ] 3.2 Manual smoke: create singer, save playlist, restart, verify
      restore; history records plays with final key/tempo.
