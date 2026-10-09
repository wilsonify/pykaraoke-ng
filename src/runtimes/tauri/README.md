# PyKaraoke NG — Tauri desktop shell

This directory is deliberately tiny. The entire application lives in
[`src/web/`](../../web/) (HTML/CSS/JS + PyScript/Pyodide). Rust adds only the
three native capabilities a browser cannot provide:

| Command        | Purpose                                        |
|----------------|------------------------------------------------|
| `pick_folder`  | Native folder picker (via `rfd`)               |
| `list_folder`  | Recursively list a folder as flat file entries |
| `read_file`    | Read a file's bytes (raw IPC → `ArrayBuffer`)  |

The frontend detects the Tauri runtime (`window.__TAURI__.core`) and falls
back to a browser folder picker (`webkitdirectory`) when running plain.

## Building

```bash
# From the repo root: install the CLI and build the wheel/runtime assets
cd src/runtimes/tauri
npm ci
npm run tauri build        # or: npx tauri build
```

`tauri.conf.json` runs `npm run build` (→ `python ../../scripts/build-web.py`)
before building, so the wheel and vendored Pyodide/PyScript assets are
recreated automatically. Output lands in `src-tauri/target/release/`.

## Developing

```bash
cd src/runtimes/tauri
npm ci
npx tauri dev
```

`beforeDevCommand` runs `python ../../scripts/serve-web.py 18000`, so the
window loads `http://localhost:18000` — the same URL you can open in a plain
browser with the browser folder picker. Reload the window after editing
`src/web/index.html`.