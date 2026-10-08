# Build-System Invariants

> **Audience:** All contributors
> **Governance:** [constitution.md](constitution.md) §4.2, §4.7
> **Last updated:** 2026-10-07

This document captures hard-won lessons about the build system.
Every rule here exists because violating it broke CI.

The build is: `web/index.html` (no front-end build) + one Python wheel +
vendored Pyodide/PyScript assets, all produced by
`scripts/build-web.py` and embedded by Tauri.

---

## 1. Cross-Platform Commands

### ❌ Prohibited in `tauri.conf.json`, CI `run:` blocks, or any config that executes on all platforms

| Command | Problem |
|---------|---------|
| `bash -c '...'` | Windows runners don't have `bash` in PATH |
| `rm -rf` | Windows `cmd.exe` / PowerShell syntax differs |
| `cp`, `mv`, `mkdir -p` | Unix-only; not available on Windows |
| `export VAR=val` | PowerShell uses `$env:VAR = "val"` |
| `/path/with/forward/slashes` hardcoded | Windows uses `\` |

### ✅ Cross-platform alternatives

| Need | Solution |
|------|----------|
| Build logic (wheel + asset vendoring) | `python scripts/build-web.py` (stdlib `pathlib`) |
| Build logic native to the shell | Rust `build.rs` |
| Path construction | `pathlib` (Python) or `PathBuf::join()` (Rust) |
| CI-only commands | Gate with `if: matrix.platform == 'linux'` |

---

## 2. Tauri hook commands

Both hooks run from the **Tauri project root** (`src/runtimes/tauri/`),
NOT from `src-tauri/`. They must be cross-platform — they run on Linux,
Windows, and macOS CI runners.

| Hook | Command | Effect |
|------|---------|--------|
| `beforeBuildCommand` | `npm run build` → `python ../../../scripts/build-web.py` | Rebuild wheel + vendor Pyodide/PyScript into `web/` |
| `beforeDevCommand` | `python ../../../scripts/serve-web.py 18000` | Serve `web/` for `devUrl` |
| `frontendDist` | `../../../../web` | What gets embedded; relative to `src-tauri/`, which is 4 levels below the repo root |

### Path depth reference

```
src/runtimes/tauri/          ← Tauri project root (CWD for both hooks)
├── package.json             ← "build": python ../../../scripts/build-web.py
└── src-tauri/               ← Rust project
    ├── tauri.conf.json
    ├── Cargo.toml
    └── build.rs             ← default tauri_build::build()
```

From `src/runtimes/tauri/`:
- Repo root is `../../../` (3 levels up)
- `web/` is `../../../../web` relative to `src-tauri/` (4 levels up)
- Python source is `../../../src/pykaraoke/`

**Mistake that broke CI:** Using `../../../../` (4 levels) in a command that
ran from `src/runtimes/tauri/` (which only needs 3 levels). Always verify
which directory is the actual CWD.

---

## 3. Tests for Build Configuration

### ❌ Don't assert on command strings

```python
# WRONG — breaks when the command is refactored
assert "build-web" in before_build_command
```

### ✅ Assert on effects

```python
# RIGHT — verify the artifacts the hook must produce
subprocess.run(hook, cwd=tauri_root, check=True)
assert list(web_dir.glob("_wheel/*.whl"))
assert (web_dir / "_assets" / "pyscript" / "core.js").exists()
```

---

## 4. Local Validation Checklist

Before pushing any build-system change:

```bash
# 1. Regenerate the wheel + vendored runtime from the correct CWD
cd src/runtimes/tauri && npm run build

# 2. Verify artifacts landed in web/
ls web/_wheel web/_assets

# 3. Cargo check (fast — no full compile)
cd src/runtimes/tauri/src-tauri && cargo check

# 4. Full build via act (matches CI)
act -j build --workflows .github/workflows/ci-cd.yml \
  -P ubuntu-latest=catthehacker/ubuntu:act-22.04 \
  --matrix platform:linux --no-cache-server
```

---

## 5. Lessons Learned (Postmortem Log)

| Date | What broke | Root cause | Fix | Time wasted |
|------|-----------|------------|-----|-------------|
| 2026-02-27 | All 3 platform builds | `beforeBuildCommand` used `bash -c` with `../../../../` paths; Tauri runs it from `src/runtimes/tauri/` not `src-tauri/` | Added `cd src-tauri &&` prefix | ~3 commits |
| 2026-02-28 | Windows build | `bash -c '...'` not available on Windows runners | Moved build logic out of shell and into a cross-platform script | ~2 commits |
| 2026-02-28 | Integration tests | Tests asserted `"backend" in before_build_command` — fails when the command is refactored | Tests read the script and assert on effects | ~1 commit |
| 2026-10-07 | `tauri dev` | `beforeDevCommand` used `../../scripts/...` (2 levels) instead of `../../../` | Corrected to 3 levels | ~1 commit |
