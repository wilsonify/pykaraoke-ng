# PyKaraoke-NG

A slim, keyboard-driven karaoke queue manager for working DJs — Windows,
macOS, and Linux.

PyKaraoke-NG is a desktop karaoke application that sits beside your DJ
software. It occupies a narrow strip of screen (300–450 px), searches and
queues songs from the keyboard, and stays out of the way during a live set.
It is a **professional utility panel, not a full-screen media player**.

Two ways to run it:

- **Desktop app** — a Tauri window embedding the single-page app, with
  pre-built installers for Windows (NSIS), macOS (DMG), and Linux (deb).
- **Browser** — serve the app directory and open it; folder picking falls back
  to the directory file input. Same page, same engine.

Both run the pure-Python engine as WebAssembly (Pyodide) inside the page.
There is no backend process, service, or API server.

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting started**

    ---

    Install a pre-built app, or build and run from a clone in under a minute.

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)
    · [Quick start](getting-started/quickstart.md)

-   :material-account-music:{ .lg .middle } **User guide**

    ---

    Set up a song library, run a show, and use the keyboard shortcuts.

    [:octicons-arrow-right-24: User guide](user-guide/index.md)

-   :material-sitemap:{ .lg .middle } **Architecture**

    ---

    The three thin layers, the JavaScript ↔ Python boundary, and the engine.

    [:octicons-arrow-right-24: Overview](architecture/overview.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Supported formats, configuration, the engine API, and the specifications.

    [:octicons-arrow-right-24: Reference](reference/specifications.md)

-   :material-source-pull:{ .lg .middle } **Contributing**

    ---

    Tests, builds, and the OpenSpec specification-driven workflow.

    [:octicons-arrow-right-24: Contributing](contributing/index.md)

</div>

## Supported formats

| Format | Extensions | Audio |
|--------|-----------|-------|
| CD+G | `.cdg` + `.mp3`/`.wav`/`.ogg` | Separate audio file required |
| MIDI Karaoke | `.kar`, `.mid` | Built-in MIDI synthesis |
| LRC lyrics | `.lrc`, `.lcr` + audio | Separate audio file; optional `.elrc` word timing and duet part tags |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Embedded audio track |

See [Supported formats](reference/formats.md) for the details of each.

## Specifications

Behaviour is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec).
The enduring specifications live under `openspec/specs/` and proposed work
lives under `openspec/changes/`. See
[Specifications](reference/specifications.md) for the capability index and the
[OpenSpec workflow](contributing/openspec.md) for how to propose a change.

## License

[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html).
