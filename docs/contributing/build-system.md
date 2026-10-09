# Build system

How PyKaraoke-NG is assembled and packaged on Windows, macOS, and Linux — and
the rules that keep those builds working on every CI runner.

[← Development](index.md) · [Architecture overview](../architecture/overview.md)

---

## What a build produces

There is no front-end build step: `src/web/index.html` is the whole
application. A build produces the two things that file needs at runtime, and
Tauri then embeds the whole `src/web/` tree into the desktop installers:

```text
src/pykaraoke/                      pure-stdlib Python engine
        │
        │  python src/scripts/build-web.py
        ▼
src/web/
├── index.html                      the application (checked in)
├── _wheel/pykaraoke_ng-*.whl       engine wheel        (generated, git-ignored)
└── _assets/
    ├── pyodide/                    vendored runtime    (generated, git-ignored)
    └── pyscript/                   vendored runtime    (generated, git-ignored)
        │
        │  npx tauri build   (frontendDist → src/web/)
        ▼
src/runtimes/tauri/src-tauri/target/release/bundle/   deb / NSIS / dmg
```

The engine wheel is built with `--no-deps` and declares no runtime
dependencies, so the packaged application works fully offline.

!!! note "The authoritative rules"
    The binding requirements live in the
    [build-system specification](https://github.com/wilsonify/pykaraoke-ng/blob/main/openspec/specs/build-system/spec.md).
    This page is the practical companion.

---

## Building

### Generate the web assets

```bash
python src/scripts/build-web.py
```

This builds `src/web/_wheel/pykaraoke_ng-*.whl` and vendors Pyodide and
PyScript into `src/web/_assets/`. Run it before serving the page by hand:

```bash
python -m http.server 18000 --directory src/web
```

### Build the desktop app

```bash
cd src/runtimes/tauri
npm ci
npx tauri build --bundles nsis   # Windows
npx tauri build --bundles dmg    # macOS
npx tauri build --bundles deb    # Linux
```

`beforeBuildCommand` runs `build-web.py` for you, so you do not have to
regenerate the assets first. Output lands in
`src/runtimes/tauri/src-tauri/target/release/bundle/`.

For a running comparison, see [Quick start](../getting-started/quickstart.md).

---

## Tauri hooks and their working directory

Both hooks run from the **Tauri project root** (`src/runtimes/tauri/`) — *not*
from `src-tauri/`. That single fact has caused every path bug in this build.

| Hook | Value | Effect |
|------|-------|--------|
| `beforeBuildCommand` | `npm run build` → `python ../../scripts/build-web.py` | Rebuild the wheel and vendor the runtime into `src/web/` |
| `beforeDevCommand` | `python ../../scripts/serve-web.py 18000` | Serve `src/web/` for `devUrl` |
| `frontendDist` | `../../../web` | What Tauri embeds; expressed relative to `src-tauri/` |

```text
src/runtimes/tauri/          ← CWD for both hooks
├── package.json             ← "build": python ../../scripts/build-web.py
└── src-tauri/               ← the Rust project
    ├── tauri.conf.json      ← frontendDist: ../../../web
    ├── Cargo.toml
    └── build.rs
```

From `src/runtimes/tauri/`, the scripts are two levels up
(`../../scripts/...`); from `src-tauri/`, the checkout root and the web
directory are three levels up (`../../../`). When a hook or package script
moves, recompute **every** relative path from the new working directory before
pushing.

---

## Cross-platform command rules

Shared build configuration — `tauri.conf.json`, CI `run:` blocks, and package
scripts — executes on every platform. It must not assume a POSIX shell.

!!! warning "Prohibited in shared build configuration"
    `bash -c '...'`, `rm -rf`, `cp`, `mv`, `mkdir -p`, and `export VAR=val` do
    not work on the Windows runner. Hardcoded forward-slash paths are fragile
    too.

| Need | Cross-platform solution |
|------|-------------------------|
| Build logic (wheel + asset vendoring) | `python src/scripts/build-web.py` using stdlib `pathlib` |
| Build logic that belongs to Rust | `build.rs` |
| Path construction | `pathlib` (Python) or `PathBuf::join()` (Rust) |
| A genuinely platform-specific step | Guard it, e.g. `if: matrix.platform == 'linux'` |

If a step needs conditional logic, file copying, or path building, put that
logic in a cross-platform script rather than in shared shell syntax.

---

## Generated assets stay out of Git

`src/web/_wheel/` and `src/web/_assets/` are build outputs and are ignored by
Git. Never commit them, and never hand-edit them — the next build overwrites
them.

A fresh checkout has no `_wheel/` or `_assets/`, so a page opened before the
first build loads but never starts the engine. The remedy is always the same:
run `src/scripts/build-web.py`.

---

## Local validation checklist

Run these before pushing any build-system change:

```bash
# 1. Regenerate the wheel + vendored runtime from the correct CWD
cd src/runtimes/tauri && npm run build

# 2. Confirm the artifacts landed in src/web/
ls src/web/_wheel src/web/_assets

# 3. Fast Rust check (no full compile)
cd src/runtimes/tauri/src-tauri && cargo check
```

When the change touches the CI workflow itself, reproduce the build stage
locally with [act](https://github.com/nektos/act):

```bash
act -j build --workflows .github/workflows/ci-cd.yml \
  -P ubuntu-latest=catthehacker/ubuntu:act-22.04 \
  --matrix platform:linux --no-cache-server
```

---

## CI build matrix

The `build` stage fans out across three runners and produces one installer per
platform. `fail-fast: false` means one platform failing does not suppress the
others.

| Platform | Runner | Bundle | Artifact |
|----------|--------|--------|----------|
| Linux | `ubuntu-latest` | `deb` | `tauri-linux-x86_64` |
| Windows | `windows-latest` | `nsis` | `tauri-windows-x86_64` |
| macOS | `macos-latest` | `dmg` | `tauri-macos-aarch64` |

Each runner installs the Tauri CLI with `npm ci`, sets up Python for the wheel,
and runs `npx tauri build --bundles <bundle>` — which triggers
`beforeBuildCommand` and rebuilds the assets as part of the build.

### Test the effect, not the command text

Build-configuration tests must assert on what a command **produces**, never on
the literal string it contains.

```python
# WRONG — breaks the moment the command is refactored
assert "build-web" in before_build_command

# RIGHT — verify the artifacts the hook must produce
subprocess.run(hook, cwd=tauri_root, check=True)
assert list(web_dir.glob("_wheel/*.whl"))
assert (web_dir / "_assets" / "pyscript" / "core.js").exists()
```

---

## Lessons learned

Every rule on this page exists because breaking it broke CI.

| Date | What broke | Root cause | Resolution |
|------|-----------|------------|------------|
| 2026-02-27 | All three platform builds | `beforeBuildCommand` used `bash -c` with four-level paths while Tauri ran it from `src/runtimes/tauri/` (three levels) | Fixed the hook's assumed working directory and path depth |
| 2026-02-28 | Windows build | `bash -c '...'` is unavailable on the Windows runner | Moved the build logic out of the shell into a cross-platform Python script |
| 2026-02-28 | Build-configuration tests | Tests asserted `"backend" in before_build_command`, which broke on refactor | Tests now run the hook and assert on the artifacts it produces |
| 2026-10-07 | `tauri dev` | `beforeDevCommand` used the wrong path depth after the scripts directory moved | Corrected the relative path to `../../scripts/serve-web.py` |

The deeper lesson: **always confirm which directory is the actual CWD** before
writing a relative path, and prefer a cross-platform script over shell syntax.
