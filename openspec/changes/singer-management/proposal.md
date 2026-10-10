# Proposal: Singer management — playlists, history, and per-singer preferences

> Status: proposed — not implemented.
> Capability: `singer-management` (new)
> Legacy issues: kelvinlawson/pykaraoke#1 (save personal singer playlists),
> #9 (singer history remembering key/tempo change).

## Intent

PyKaraoke-NG has one anonymous queue. A KJ running a room full of singers
needs identity: who is singing, what songs they asked for (a reusable,
named playlist), what they sang tonight (history), and what key/tempo they
sing in (per-singer preferences). Legacy issues #1 and #9 asked for exactly
this and the rewrite shipped only the anonymous queue.

## Scope

In scope:

* Named singers: create, select, delete; the active singer is remembered
  across restarts.
* Per-singer key and tempo defaults: selected when the singer becomes
  active, updated when the DJ adjusts the controls while that singer is
  active, applied to playback.
* Named playlists: save the current queue as a named playlist (attributed
  to the active singer or to no singer), load a playlist into the queue,
  delete a playlist. Loading resolves song ids against the current library
  and skips entries whose songs no longer exist.
* Singer history: every played song is recorded with the singer, the song
  label, the key offset and tempo in effect, and a timestamp; the list is
  capped, shown in the panel, clearable, and entries can be re-queued.
* Persistence: one versioned browser-storage key with corrupt/unknown data
  degrading to defaults, never a crash or silent partial state.
* Deterministic unit tests for the pure data model (vitest).

Out of scope:

* Synchronising singers across machines or backing them up inside the
  library export (the export change owns library files; the singer store is
  presentation-layer state like the queue).
* Per-song history statistics (sets, rotation order) beyond the recorded
  key/tempo.
* Modal dialogs for any of the above (the slim-sidebar no-modal invariant
  holds; creation uses inline inputs).

## Approach

A pure, exported `ShowState` class owns singers, the active singer,
per-singer preferences, playlists, and history, with a versioned
`serialize()`/`load()` pair (format `{v: 1, …}`) persisted by the page under
`pykaraoke-ng:show` next to the existing library/queue keys. All mutations
that the UI performs are small methods on this class, so the vitest suite
covers behaviour without a DOM. The transport key/tempo controls read/write
the active singer's preferences through two small hooks in the page wiring;
`playSong()` attributes a history entry to the active singer and updates its
key/tempo if the DJ changes them mid-song.
