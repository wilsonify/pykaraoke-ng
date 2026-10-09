# Configuration

PyKaraoke-NG has no configuration file. Settings live in the in-memory
`Settings` object of the Python engine and are persisted by the UI as JSON in
browser (or desktop webview) local storage. The one piece of native
configuration is the Tauri desktop window.

[← Home](../index.md) · [User guide](../user-guide/index.md) · [Specifications](specifications.md)

---

## Application settings

Every setting is defined by `Settings` in
`src/pykaraoke/database.py`. The table lists the wire key (the name used in the
JSON that crosses the JavaScript ↔ Python boundary), the control that exposes
it, its type, its default, and its effect.

| Setting | Exposed in | Type | Default | Effect |
|---------|-----------|------|---------|--------|
| `sort` | Settings panel — **Sort library by** | `filename` \| `title` \| `artist` | `filename` | Library/song-list ordering. `title` and `artist` sorts ignore a leading article (`a`, `an`, `the`) and any leading parenthesised block. An unknown value falls back to `filename`. |
| `cdg_zoom` | Settings panel — **CDG zoom** | `quick` \| `int` \| `full` \| `soft` | `int` | Zoom level applied to the CD+G rendering stage: Quick (0.75×), Normal (1×), Large (1.5×), Full (2×). |
| `look_inside_zips` | Settings panel — **Look inside .zip files** | boolean | `true` | When enabled, scanning a `.zip` archive expands its supported karaoke members into songs. When disabled, archives are skipped. |
| `exclude_non_matching` | Settings panel — **Hide songs without artist** | boolean | `false` | When enabled, entries from which no artist can be parsed are omitted from the library. When disabled (the default) they are kept as title-only songs. |
| `derive_song_info` | Settings panel — **Derive song info from filename** | boolean | `true` | UI-facing toggle. See the note below. |
| `volume` | Volume slider (transport controls) | float `0.0`–`1.0` | `0.75` | Playback volume applied to audio, video, and MIDI synthesis. |
| `folders` | No separate control — updated as folders are added | list of strings | `[]` | The scan sources recorded by the library. |
| `file_name_type` | Not exposed in the settings panel | integer `0`–`3` | `3` (`ARTIST_TITLE`) | The legacy filename naming convention used when a file has no `" - "` separator: `DISC_TRACK_ARTIST_TITLE` (0), `DISCTRACK_ARTIST_TITLE` (1), `DISC_ARTIST_TITLE` (2), `ARTIST_TITLE` (3). |

!!! note "Two settings deserve a caveat"

    - **`derive_song_info`** is persisted and round-tripped, but the library
      does not consult it during scanning today — only `file_name_type` selects
      the parser. It is a UI-facing toggle at present.
    - **`file_name_type`** is persisted and *is* used by the scanner, but it has
      no control in the settings panel yet, so it keeps its `ARTIST_TITLE`
      default unless set programmatically. The authoritative behaviour is in the
      [song-library specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md).

`cdg_zoom` also accepts `none` at the model level, but that value is not
offered by the settings panel.

### Where settings live

* The settings panel is opened with the gear icon (⚙) in the header. It is an
  inline, collapsible panel — never a modal — to keep the slim-sidebar workflow
  intact.
* Changing a control calls the engine's `set_settings`, which applies **only
  recognised keys** and ignores anything else. `sort` re-sorts the library
  immediately; `volume` is applied to whatever is currently playing.
* The UI persists state in local storage under the keys
  `pykaraoke-ng:state` (the library **and** settings, serialised by the
  engine's `to_json`) and `pykaraoke-ng:queue` (the queued song ids). State is
  restored through `from_json` on startup.
* Because storage is per-origin webview storage, clearing site data resets the
  library and settings.

To reset everything, clear the application's stored data (browser site data,
or the desktop webview's storage), remove the folders, and scan again.

## Desktop window

The desktop window is configured in
`src/runtimes/tauri/src-tauri/tauri.conf.json`:

```json
{
  "app": {
    "withGlobalTauri": true,
    "windows": [
      {
        "title": "PyKaraoke NG",
        "width": 380,
        "height": 800,
        "minWidth": 300,
        "maxWidth": 450,
        "minHeight": 500,
        "resizable": true,
        "center": true
      }
    ]
  }
}
```

* The window opens at **380 × 800** and can be resized horizontally between
  **300 px and 450 px**, to a minimum height of **500 px**.
* The slim bounds are a design invariant, not a preference: PyKaraoke-NG is a
  utility panel docked beside the DJ's primary software. The app's CSS also
  enforces `max-width: 450px`, so the layout stays slim even if a window
  manager ignores the size hints. See the
  [ux-slim-sidebar specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md)
  and [project-governance specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/project-governance/spec.md).

The same file's `build` block wires the Tauri hooks that build and serve the
web assets; those commands and their path rules are documented on the
[Build system](../contributing/build-system.md) page.

## Related

* [User guide](../user-guide/index.md) — using the settings panel
* [Supported formats](formats.md) — the file kinds the library recognises
* [Architecture overview](../architecture/overview.md) — how settings flow between the UI and engine
* [Specifications](specifications.md) — the capability index
