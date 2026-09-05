# PyKaraoke NG — Tauri desktop shell

This directory is deliberately tiny. The entire application lives in
[`web/`](../../web/) (HTML/CSS/JS + PyScript/Pyodide). Rust adds only the
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
npm install
npm run tauri build        # or: npx tauri build
```

`tauri.conf.json` runs `npm --prefix .. run build` (→ `scripts/build-web.py`)
before building, so the wheel and vendored Pyodide/PyScript assets are
recreated automatically. Output lands in `src-tauri/target/release/`.

## Developing

Serve `web/` on port 18000 (`python -m http.server 18000 --directory web`)
and open `http://localhost:18000` — the same code runs in a plain browser
with the browser file picker. `tauri dev` points at that same URL.