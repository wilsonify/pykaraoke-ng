# Installation

PyKaraoke-NG ships as a desktop application for Windows, macOS, and Linux.
There is nothing to configure on the machine you install it on — the Python
engine is compiled to WebAssembly and runs inside the app, so **Python is not
required** on the target machine.

[← Home](../index.md) · [User guide](../user-guide/index.md)

---

## Pre-built installers

Download the installer for your platform from
[GitHub Releases](https://github.com/wilsonify/pykaraoke-ng/releases):

| Platform | Format | File |
|----------|--------|------|
| Windows | NSIS installer | `PyKaraoke NG_<version>_x64-setup.exe` |
| macOS | DMG | `PyKaraoke NG_<version>_x64.dmg` |
| Linux | deb | `pykaraoke-ng_<version>_amd64.deb` |

Run the installer (or open the DMG and drag the app to Applications) and
launch **PyKaraoke NG**. A narrow sidebar window opens.

!!! tip "Installer unavailable or fails?"
    Try the other format in Releases, or
    [build from source](quickstart.md). The packaged desktop app embeds the
    whole web runtime, so it works fully offline.

## Requirements

- A sound card and speakers
- Karaoke files to play — CD+G, MIDI Karaoke (`.kar`/`.mid`), LRC lyrics, or
  MPEG video (see [Supported formats](../reference/formats.md))
- Windows 10+, macOS 12+, or a Linux distribution with WebKit2GTK
- No Python on the target machine

## First run

1. **Add your songs** — click **Add Folder**, choose your karaoke directory,
   then click **Scan Library**. Matching `.cdg`/`.lrc` audio companions are
   picked up automatically.
2. **Search** — type in the search bar; results filter as you type.
3. **Queue** — press `↓` to highlight a song, then `Enter` to add it.
4. **Play** — click ▶ **Play** or press `Space`.

The full walkthrough is in the [user guide](../user-guide/index.md).

## Running in a browser instead

You can also run the app as a web page — the same page and the same engine.
Serve the `src/web/` directory (after building the web assets once) and open
it; folder selection falls back to the browser's directory file input instead
of a native dialog.

```bash
bash src/scripts/build-web.py                  # build the wheel + vendor Pyodide/PyScript
python -m http.server 18000 --directory src/web
# open http://localhost:18000
```

See the [quick start](quickstart.md) for the full from-source setup.

## Where to get karaoke files

Respect copyright laws in your jurisdiction.

- **Create your own** — CDG creator software plus royalty-free music
- **Public domain** — classical and traditional songs
- **Licensed services** — some vendors sell downloadable CDG packs
- **MIDI** — many `.kar` files are freely available online

---

**Next:** [User guide](../user-guide/index.md) ·
[Supported formats](../reference/formats.md) ·
[Configuration](../reference/configuration.md)
