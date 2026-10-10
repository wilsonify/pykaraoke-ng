# Specifications

PyKaraoke-NG uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) as its
specification-driven development system. The specifications are kept separate
from this website: they are the machine- and contributor-facing source of
truth, while the pages here are the user-facing narrative.

## Where the specifications live

```
openspec/
├── config.yaml          # project context for the OpenSpec workflow
├── specs/               # enduring capabilities — how the product behaves
└── changes/             # proposed, in-progress, and archived changes
    ├── <change-id>/     # an active proposal (proposal, design, tasks, deltas)
    └── archive/         # completed changes, kept for history
```

* **`openspec/specs/`** describes how the product behaves **today**. Each
  capability is a directory containing a `spec.md` built from requirements and
  concrete scenarios.
* **`openspec/changes/`** holds proposed behaviour. A change carries a
  proposal, an optional design, a task list, and *delta* specs that state what
  it adds, modifies, or removes. When a change ships it is archived, its deltas
  merge into `openspec/specs/`, and the change moves to `changes/archive/` with
  a date prefix.

Contributors propose and archive changes with the `openspec` CLI. See the
[OpenSpec workflow](../contributing/openspec.md) for the exact commands.

## Capability index

| Capability | Spec | Covers |
|------------|------|--------|
| Project governance | [project-governance](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/project-governance/spec.md) | The binding engineering, UX, testing, CI, and release invariants |
| Slim sidebar UX | [ux-slim-sidebar](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/ux-slim-sidebar/spec.md) | Layout, dimensions, keyboard model, density, prohibited patterns |
| Playback | [playback](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/playback/spec.md) | CD+G, MIDI/KAR, LRC/`.elrc`, duet parts, transport |
| Filename parsing | [filename-parsing](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/filename-parsing/spec.md) | Artist/title/disc/track extraction from filenames |
| Song library | [song-library](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/song-library/spec.md) | Scanning, companion audio, zip support, search, sort, settings |
| Web engine API | [web-engine-api](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/web-engine-api/spec.md) | The `window.pykaraoke_api` JavaScript ↔ Python contract |
| Build system | [build-system](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/build-system/spec.md) | Cross-platform build/packaging rules and path invariants |

## How this site relates to the specs

This documentation explains *how to use and work on* PyKaraoke-NG. The specs
state *what the product must do* in a form a test can be written against. They
are linked, not duplicated:

| Website page | Related specification |
|--------------|----------------------|
| [Architecture overview](../architecture/overview.md) | web-engine-api, playback, build-system |
| [User guide](../user-guide/index.md) | ux-slim-sidebar, playback, song-library |
| [Configuration](../reference/configuration.md) | song-library |
| [Engine API](../reference/engine-api.md) | web-engine-api |
| [Build system](../contributing/build-system.md) | build-system |
| [Contributing](../contributing/index.md) | project-governance |
| [Original PyKaraoke issue coverage](original-pykaraoke-issues.md) | song-library, filename-parsing, playback, web-engine-api |

Internal change-management artifacts (the contents of `openspec/changes/`) are
intentionally **not** published here — they are working documents. Completed
changes are preserved under `openspec/changes/archive/` in the repository.
