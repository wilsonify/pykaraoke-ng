# Buttons Do Nothing in Packaged .deb Build

| Field | Value |
|-------|-------|
| **Reported** | 2026-02-26 |
| **Affected version** | v0.0.5 / 0.7.5 (.deb) |
| **Platform** | Debian/Ubuntu amd64, Tauri 1.8 |
| **Status** | Fixed |

---

## Symptom

After installing `py-karaoke-ng_0.7.5_amd64.deb` via `sudo dpkg -i`,
the application window launches correctly and the UI renders, but three
buttons are completely non-functional:

- **Add Folder** — clicking produces no visible effect
- **Scan Library** — clicking produces no visible effect
- **Settings** — clicking produces no visible effect

There are no errors in the UI and no errors in the terminal.

## Root Cause

Five interrelated bugs combined to make the buttons non-functional:

### 1. Settings button had no event listener

`app.js` wired click handlers for every button in `setupEventListeners()`
**except** the Settings button (`#settings-btn`).  The button element
existed in `index.html` and had a visible label, but clicking it did
nothing because no handler was attached.

### 2. Add Folder used `alert()` instead of a native dialog

The `handleAddFolder()` method contained only:

```js
alert('Folder picker not implemented yet. This would open a native folder selection dialog.');
```

In a Tauri WebView, `alert()` may be suppressed or invisible depending on
the platform and security settings.  Even when visible, it didn't actually
add a folder.  The proper fix is to use Tauri's native dialog API
(`window.__TAURI__.dialog.open`), but this required changes to both the
Tauri allowlist and the Cargo feature flags.

### 3. `send_command` always returned a placeholder response

The Rust `send_command` function wrote commands to the Python backend's
stdin but **never read the response from stdout**.  It always returned a
hardcoded placeholder:

```rust
Ok(CommandResponse {
    status: "ok".to_string(),
    message: Some("Command sent".to_string()),
    data: None,    // ← always null
})
```

This meant every command the frontend sent (scan_library, search_songs,
get_state, etc.) appeared to succeed but returned `data: null`.  The
frontend checked `response.data` for results and, finding nothing,
silently did nothing.

### 4. Flat resource bundling destroyed the Python package structure

`tauri.conf.json` listed individual Python files as resources:

```json
"resources": [
    "../../../../src/pykaraoke/core/backend.py",
    "../../../../src/pykaraoke/core/__init__.py",
    "../../../../src/pykaraoke/config/__init__.py",
    "../../../../src/pykaraoke/__init__.py",
    ...
]
```

Tauri v1 bundles individual-path resources into a **flat directory**.
This means three separate `__init__.py` files (from `pykaraoke/`,
`pykaraoke/core/`, and `pykaraoke/config/`) all collided — only the
last one survived.  The Python package structure was destroyed, so
`from pykaraoke.config.constants import ...` failed on import, and the
backend process died immediately after spawn.

### 5. Missing PYTHONPATH for the spawned Python process

Even if the files had been structured correctly, the `python3` child
process was spawned without a `PYTHONPATH` environment variable.  The
bundled Python files lived under a `backend/` resource directory, not in
any location on Python's default module search path.  Without
`PYTHONPATH=.../backend`, Python could not resolve `from pykaraoke...`
imports.

## Fix

### A. Wire the Settings button (`app.js`)

Added a click handler for `#settings-btn` in `setupEventListeners()` that
opens a settings modal.  Added `handleShowSettings()`,
`handleCloseSettings()`, and `handleSaveSettings()` methods that
communicate with the backend via `get_settings` / `update_settings`
commands.

### B. Settings modal UI (`index.html`, `styles.css`)

Added a `<div id="settings-modal">` overlay with controls for fullscreen
toggle and CDG zoom mode, plus Save/Cancel buttons.  Added corresponding
CSS for the modal overlay, content panel, and form elements.

### C. Native folder picker (`app.js`, `tauri.conf.json`, `Cargo.toml`)

Replaced `alert()` in `handleAddFolder()` with Tauri's dialog API:

```js
const selected = await dialogOpen({
    directory: true,
    multiple: false,
    title: 'Select Music Folder',
});
if (selected) {
    await this.sendCommand('add_folder', { folder: selected });
}
```

This required:
- Adding `"dialog": { "all": false, "open": true }` to the Tauri
  allowlist in `tauri.conf.json`
- Adding the `"dialog-open"` feature to the `tauri` dependency in
  `Cargo.toml`
- Importing `window.__TAURI__.dialog.open` in `app.js` (with a fallback
  stub in the `catch` block)

### D. Response channel for `send_command` (`main.rs`)

Added an `mpsc::channel<serde_json::Value>` to `BackendState`.  The
stdout reader thread now routes `{"type": "response", ...}` messages
through the channel.  `send_command` reads the channel with a 5-second
timeout and returns the **actual** Python backend response instead of a
placeholder.

```rust
match rx.recv_timeout(Duration::from_secs(5)) {
    Ok(value) => serde_json::from_value::<CommandResponse>(value),
    Err(RecvTimeoutError::Timeout) => Err("Timeout waiting for backend response"),
    Err(RecvTimeoutError::Disconnected) => Err("Backend process disconnected"),
}
```

### E. Proper resource bundling (`tauri.conf.json`, `beforeBuildCommand`)

Replaced the flat list of individual files with a `beforeBuildCommand`
that copies the Python source tree into a `backend/` staging directory
preserving the package structure:

```
backend/
  pykaraoke/
    __init__.py
    core/
      __init__.py
      backend.py
      database.py
      manager.py
      player.py
    config/
      __init__.py
      constants.py
      environment.py
      version.py
    players/
      __init__.py
      cdg.py
      ...
```

The `resources` key was changed to `["backend/**"]`, which bundles the
entire directory tree.

### F. Set PYTHONPATH for the backend process (`main.rs`)

Added `PYTHONPATH` to the `python3` spawn command, pointing to the
`backend/` resource directory (the directory that *contains* the
`pykaraoke` package):

```rust
let python_path = backend_script
    .parent()                    // .../pykaraoke/core
    .and_then(|p| p.parent())    // .../pykaraoke
    .and_then(|p| p.parent())    // .../backend
    .unwrap_or_else(|| Path::new("."))
    .to_path_buf();

Command::new("python3")
    .arg(&backend_script)
    .env("PYTHONPATH", &python_path)
    ...
```

## Files changed

| File | Changes |
|------|---------|
| `src/runtimes/tauri/src-tauri/tauri.conf.json` | `dialog` allowlist, `beforeBuildCommand`, `resources` glob |
| `src/runtimes/tauri/src-tauri/Cargo.toml` | Added `dialog-open` feature |
| `src/runtimes/tauri/src-tauri/src/main.rs` | `mpsc` response channel, `PYTHONPATH`, `recv_timeout` |
| `src/runtimes/tauri/src/app.js` | Settings handler, `dialogOpen`, folder picker |
| `src/runtimes/tauri/src/index.html` | Settings modal markup |
| `src/runtimes/tauri/src/styles.css` | Modal styles |
| `src/runtimes/tauri/src/app.test.js` | Updated mock DOM, dialog fallback tests |
| `src/runtimes/tauri/src/index.test.js` | New element IDs in REQUIRED_IDS |

## How to verify

```bash
# Rebuild the .deb
cd src/runtimes/tauri/src-tauri
cargo tauri build --bundles deb

# Install
sudo dpkg -i target/release/bundle/deb/py-karaoke-ng_0.7.5_amd64.deb

# Launch and test:
# 1. Click "Add Folder" → native folder picker should appear
# 2. Select a folder containing .cdg/.kar/.mpg files
# 3. Click "Scan Library" → status bar should show "Scanning library..."
#    then "Library scan complete"
# 4. Click "⚙️ Settings" → modal should appear with Fullscreen and Zoom options
# 5. Change a setting, click Save → status bar should show "Settings saved"
```

## Lessons learned

1. **Tauri flat-bundles individual resource paths.**  When `resources`
   lists individual files from different directories, Tauri v1 copies
   them into a single flat directory.  Files with the same basename
   (like `__init__.py`) overwrite each other silently.  Always use a
   staging directory with the proper tree structure and a glob pattern
   (`"backend/**"`) to preserve directory hierarchy.

2. **Silent process death is the hardest bug to find.**  The Python
   backend process died on import because the package structure was
   destroyed, but the Rust side never checked `child.try_wait()` or
   logged stderr.  The frontend saw `data: null` from the placeholder
   response and silently did nothing.  Three layers of silent failure
   (Python → Rust → JavaScript) made the buttons appear to "do nothing"
   with no visible errors anywhere.

3. **Placeholder return values hide real bugs.**  The `send_command`
   function returned `{ status: "ok", data: null }` unconditionally.
   This made every command appear to succeed.  The frontend checked
   `response.status === 'ok'` (which was always true) and then checked
   `response.data` (which was always null), so it silently skipped all
   result processing.  A proper error ("Backend not responding") would
   have surfaced the issue immediately.

4. **Spawned subprocesses need their environment configured.**  When a
   Rust binary spawns `python3` with a script from a non-standard
   location, `PYTHONPATH` must be set explicitly so Python can resolve
   package imports.  This is easy to miss in development where the source
   tree is structured correctly and the IDE or virtualenv provides the
   right paths automatically.

5. **Tauri allowlist, Cargo features, and JS imports must all agree.**
   Using `window.__TAURI__.dialog.open` requires three synchronized
   changes: the `dialog.open` allowlist entry in `tauri.conf.json`, the
   `dialog-open` feature in `Cargo.toml`, and the JS import/fallback in
   `app.js`.  Missing any one of these produces a silent failure (the API
   exists but returns undefined, or the build fails with a cryptic
   feature-mismatch error).

6. **Always wire event listeners — even for "obvious" buttons.**  The
   Settings button existed in the HTML and was styled correctly, but no
   one noticed it had no `addEventListener` call because it *looked*
   like it should work.  The DOM contract tests in `index.test.js`
   verified the element existed but didn't verify it had a handler.
   Consider adding integration tests that simulate clicks and assert
   side effects.

7. **Test the packaged artifact, not just the source code.**  All unit
   tests passed on the source tree.  The bugs only manifested in the
   `.deb` package because bundling, resource paths, and environment
   variables behave differently in production.  CI/CD pipelines should
   install the built artifact in a clean environment and run smoke tests
   against it.
