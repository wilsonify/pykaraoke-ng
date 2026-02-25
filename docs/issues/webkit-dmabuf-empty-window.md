# Empty Window on Launch (WebKitGTK DMA-BUF Failure)

| Field | Value |
|-------|-------|
| **Reported** | 2026-02-25 |
| **Affected version** | v0.0.3 / 0.7.5 (.deb) |
| **Platform** | Debian 12 (Bookworm) amd64, WebKitGTK 4.0 |
| **Status** | Fixed |

---

## Symptom

After installing `py-karaoke-ng_0.7.5_amd64.deb` and launching from the
desktop menu (or `/usr/bin/py-karaoke-ng`), the **PyKaraoke NG** window
opens at 1024 × 768 but is **completely blank** — no HTML content, no
controls, no error message visible to the user.

## Root Cause

Three independent issues combined to produce a blank window:

### 1. WebKitGTK GPU buffer allocation failure (primary)

On the affected system the WebKitGTK engine attempts to use **DMA-BUF**
hardware-accelerated rendering.  When the user's session lacks permission
to create GBM (Generic Buffer Manager) buffers via DRM ioctls, the
renderer silently produces a blank surface:

```
KMS: DRM_IOCTL_MODE_CREATE_DUMB failed: Permission denied
Failed to create GBM buffer of size 1024x768: Permission denied
```

This occurs on:
- Machines where `/dev/dri/card0` is owned by `root:video` but the user
  is in the `video` group yet the session was started without proper DRM
  master permissions (e.g. running under `su`, `ssh -X`, or certain
  display managers).
- Virtual machines, containers, and remote-desktop sessions where GPU
  passthrough is not configured.
- Systems with proprietary GPU drivers that don't expose a GBM-capable
  DRM device.

WebKitGTK does **not** fall back to software rendering automatically in
this failure mode — it simply renders nothing.

### 2. Python backend script not found

The Rust `start_backend` command located the Python backend using a
hardcoded relative path (`../../../src/pykaraoke/core/backend.py`)
relative to Tauri's `resource_dir()`.  This path is valid only in the
development source tree; in a `.deb` install the binary is at
`/usr/bin/py-karaoke-ng` and the resource dir resolves elsewhere.

### 3. JavaScript crash when Tauri API unavailable

`app.js` destructured `window.__TAURI__.tauri.invoke` at the module's
top level:

```js
const { invoke } = window.__TAURI__.tauri;   // ← throws if __TAURI__ is undefined
```

If the Tauri IPC bridge was slow to inject (or absent due to the blank
WebKit surface), this threw a `TypeError` and halted all JavaScript
execution, preventing even static HTML from rendering.

## Fix

### A. WebKit DMA-BUF workaround (`main.rs`)

Set `WEBKIT_DISABLE_DMABUF_RENDERER=1` **before** the Tauri webview is
created, gated behind `#[cfg(target_os = "linux")]` and only if the user
has not already set it:

```rust
#[cfg(target_os = "linux")]
{
    if std::env::var("WEBKIT_DISABLE_DMABUF_RENDERER").is_err() {
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    }
}
```

This forces WebKitGTK to use the shared-memory renderer, which works on
all Linux systems regardless of GPU access.

### B. Multi-path backend resolution (`main.rs`)

Replace the single hardcoded path with an ordered list of candidates
that covers bundled resources (production), flat resource layout, dev
source tree, and CWD-based fallback.  Each candidate is tested with
`.exists()` before use.

### C. Bundle Python backend (`tauri.conf.json`)

Add a `"resources"` array to `tauri.bundle` listing all Python modules
the backend needs at runtime, so `tauri build --bundles deb` includes
them in the package.

### D. Resilient Tauri API import (`app.js`)

Wrap the `window.__TAURI__` access in `try/catch` and provide no-op
stubs for `invoke` and `listen` so the UI always renders, even if the
IPC bridge is delayed or missing.

## How to verify

```bash
# Quick check — should see the full karaoke UI, not a blank window
WEBKIT_DISABLE_DMABUF_RENDERER=1 /usr/bin/py-karaoke-ng

# Or from a .desktop launch (the updated Exec line sets the env var)
```

## Workaround for v0.0.3 (already-installed .deb)

Edit the installed desktop file:

```bash
sudo sed -i \
  's|^Exec=py-karaoke-ng|Exec=env WEBKIT_DISABLE_DMABUF_RENDERER=1 py-karaoke-ng|' \
  /usr/share/applications/py-karaoke-ng.desktop
```

Or launch from a terminal with the env var set manually.

## Regression tests

Static-analysis regression tests in
`tests/integration/test_tauri_packaging.py` verify that:

- `main.rs` sets `WEBKIT_DISABLE_DMABUF_RENDERER` before webview creation
- `main.rs` tries multiple backend path candidates with `.exists()`
- `tauri.conf.json` bundles the Python backend files
- `app.js` does not destructure `window.__TAURI__` at the top level

Frontend regression tests in `src/runtimes/tauri/src/app.test.js` verify
the Tauri API fallback logic directly.

## Lessons learned

1. **WebKitGTK GPU failures are silent.**  Unlike Chromium (which shows a
   sad-face tab), WebKitGTK renders a blank surface when GPU buffer
   allocation fails.  Tauri apps on Linux should **always** set
   `WEBKIT_DISABLE_DMABUF_RENDERER=1` as a safe default unless they have
   confirmed GPU access.

2. **Don't assume `resource_dir()` matches the dev layout.**  Tauri's
   `resource_dir()` points to very different locations in development
   (`target/debug/`) vs. production (`/usr/lib/py-karaoke-ng/`).  Always
   try multiple candidate paths.

3. **Guard top-level destructuring from host objects.**  Browser globals
   like `window.__TAURI__` are injected asynchronously.  Top-level
   `const { x } = window.something` will crash the entire module if the
   object is not yet present.  Use `try/catch` or optional chaining.

4. **Bundle everything the binary needs at runtime.**  If the Tauri Rust
   binary spawns a Python subprocess, those Python files must be declared
   in `tauri.conf.json > tauri.bundle.resources` — they won't be included
   automatically.

5. **Test packaging artifacts, not just code logic.**  Unit tests that
   run against source code don't catch "file not bundled in the .deb"
   problems.  Static-analysis tests that inspect config files (like
   checking `tauri.conf.json` has a `resources` key) run in CI and catch
   these regressions before a release.
