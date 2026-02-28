# Build-System Invariants

> **Audience:** All contributors
> **Governance:** [constitution.md](constitution.md) §3.2, §3.7
> **Last updated:** 2026-02-28

This document captures hard-won lessons about the build system.
Every rule here exists because violating it broke CI.

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
| File staging | Node.js script using `fs`/`path` (see `scripts/stage-backend.js`) |
| Build logic | Rust `build.rs` |
| Path construction | `path.join()` (Node) or `PathBuf::join()` (Rust) |
| CI-only commands | Gate with `if: matrix.platform == 'linux'` |

---

## 2. `beforeBuildCommand` in `tauri.conf.json`

- Runs from the **Tauri project root** (`src/runtimes/tauri/`), NOT from
  `src-tauri/`.
- Must be cross-platform — it runs on Linux, Windows, and macOS CI runners.
- Currently: `node scripts/stage-backend.js`
- The script lives at `src/runtimes/tauri/scripts/stage-backend.js`.

### Path depth reference

```
src/runtimes/tauri/          ← Tauri project root (CWD for beforeBuildCommand)
├── scripts/
│   └── stage-backend.js     ← __dirname = src/runtimes/tauri/scripts/
├── src/                     ← Frontend source (devPath / distDir)
└── src-tauri/               ← Rust project
    ├── backend/             ← Staged Python files (created by stage-backend.js)
    ├── tauri.conf.json
    ├── Cargo.toml
    └── build.rs
```

From `src/runtimes/tauri/`:
- Repo root is `../../../` (3 levels up)
- Python source is `../../../src/pykaraoke/` (3 up + 2 down)

From `src/runtimes/tauri/src-tauri/`:
- Repo root is `../../../../` (4 levels up)
- Python source is `../../../../src/pykaraoke/` (4 up + 2 down)

**Mistake that broke CI:** Using `../../../../` (4 levels) in a command that
ran from `src/runtimes/tauri/` (which only needs 3 levels). Always verify
which directory is the actual CWD.

---

## 3. Integration Tests for Build Configuration

### ❌ Don't assert on command strings

```python
# WRONG — breaks when the command is refactored into a script
assert "backend" in before_build_command
assert "core" in before_build_command
```

### ✅ Assert on effects

```python
# RIGHT — verifies the script does the right thing
script_path = resolve_script(before_build_command)
script_source = script_path.read_text()
assert "backend" in script_source
assert "core" in script_source
```

Or even better — run the command and verify files exist:

```python
subprocess.run(before_build_command, cwd=tauri_root, check=True)
assert (src_tauri / "backend" / "pykaraoke" / "core" / "backend.py").exists()
```

---

## 4. `build.rs` Placeholder Logic

`src-tauri/build.rs` creates a `backend/pykaraoke/PLACEHOLDER` file when
no real backend files exist. This satisfies the `"resources": ["backend/**"]`
glob during `cargo test` / `cargo check`, which don't run `beforeBuildCommand`.

If you add new resource globs to `tauri.conf.json`, ensure `build.rs`
creates matching placeholder structures.

---

## 5. Local Validation Checklist

Before pushing any build-system change:

```bash
# 1. Run the staging script from the correct CWD
cd src/runtimes/tauri && node scripts/stage-backend.js

# 2. Verify files landed in the right place
find src-tauri/backend -type f

# 3. Cargo check (fast — no full compile)
cd src-tauri && cargo check

# 4. Full build via act (matches CI)
cd /repo/root
act -j build --workflows .github/workflows/ci-cd.yml \
  -P ubuntu-22.04=catthehacker/ubuntu:act-22.04 \
  --matrix platform:linux --no-cache-server

# 5. Integration tests via act
act -j integration-tests --workflows .github/workflows/ci-cd.yml \
  --no-cache-server
```

---

## 6. Lessons Learned (Postmortem Log)

| Date | What broke | Root cause | Fix | Time wasted |
|------|-----------|------------|-----|-------------|
| 2026-02-27 | All 3 platform builds | `beforeBuildCommand` used `bash -c` with `../../../../` paths; Tauri runs it from `src/runtimes/tauri/` not `src-tauri/` | Added `cd src-tauri &&` prefix | ~3 commits |
| 2026-02-28 | Windows build | `bash -c '...'` not available on Windows runners | Replaced with `node scripts/stage-backend.js` | ~2 commits |
| 2026-02-28 | Integration tests | Tests asserted `"backend" in before_build_command` — fails when command is `node scripts/stage-backend.js` | Tests now read the script file and check its contents | ~1 commit |
