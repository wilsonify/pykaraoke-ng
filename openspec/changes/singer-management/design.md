# Design: Singer management

## Data model (pure JS, `ShowState`)

```js
{
  v: 1,
  singers:      [{ id, name }],                    // stable ids, unique names
  activeId:     string | null,
  prefs:        { [singerId]: { semitones, tempo } },
  playlists:    [{ id, name, singerId|null, songIds: [string] }],
  history:      [{ id, singerId|null, singerName, songId, label,
                   at, semitones, tempo }],        // newest last, capped
}
```

History cap: 200 entries (oldest dropped). Playlist and singer names are
trimmed; empty names are rejected (method returns an error string the UI
shows in the status bar). Singer ids are `s-<counter>-<rand>` style —
deterministic in tests via an injectable id function.

## Storage

Key `pykaraoke-ng:show`, written after every mutation (same debounce-free
style as the queue's `persist()`). On load:

* not present → defaults;
* invalid JSON / not an object → defaults (status-bar warning);
* `v` missing or not 1 → defaults (forward-compat guard: an unknown newer
  version is not partially applied);
* fields coerced defensively (arrays checked, numbers clamped: semitones
  −12…+12, tempo 0.5…2.0).

The engine library payload (`pykaraoke-ng:state`) is untouched, so existing
installs upgrade with full compatibility.

## Interaction with playback

* Singer switch → key/tempo controls take that singer's stored prefs
  (or defaults 0/×1.0 when none) and the change applies to the current
  song immediately.
* Key/tempo change while a singer is active → prefs updated and persisted.
* `playSong()` with an active singer → one history entry recorded
  (`at` = epoch ms); if the DJ changes key/tempo during that song, the
  entry is updated in place so history reflects the final values.
* Playlists: "Save queue as playlist" names via an inline text input in the
  Playlists section; "Load" replaces the queue contents (after resolving
  ids against `library_songs`) and re-renders.

## UI placement (slim column, no modals)

* **Singer row** directly above the Queue section: a `<select>` of singers
  plus an inline "new singer" text input + Add button, and a forget
  (✕) control for the selected singer.
* **Playlists** section under the queue: list with load/delete buttons and
  the save-queue control.
* **History** as a collapsed `<details>` section: newest first, each row a
  song label with singer, key, tempo, and a re-queue button; a Clear
  control.
