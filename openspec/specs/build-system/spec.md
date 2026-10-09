# Build System Specification

## Purpose

Defines how PyKaraoke-NG is assembled and packaged identically on Windows,
macOS, and Linux. A build produces three things: the self-contained web
application (`src/web/index.html`), one pure-stdlib Python engine wheel, and
the vendored Pyodide/PyScript runtime that `src/scripts/build-web.py` fetches.
Tauri then embeds the whole `src/web/` tree into the desktop installers, so the
same build commands must succeed on every supported platform and CI runner.

> Source: `specs/build-system-invariants.md`, verified against
> `src/runtimes/tauri/src-tauri/tauri.conf.json`,
> `src/runtimes/tauri/package.json`, `src/scripts/build-web.py`,
> `src/scripts/serve-web.py`, and `.github/workflows/ci-cd.yml`.
> Governance: `project-governance` specification §4.2 and §4.7.

## Requirements

### Requirement: Cross-platform build commands

Shared build configuration that executes on more than one platform — Tauri
configuration, CI `run:` blocks, and package scripts — MUST NOT depend on
shell-specific syntax or on Unix-only utilities.

#### Scenario: A shared command runs on the Windows runner

- **WHEN** a shared build command executes on the Windows CI runner
- **THEN** it succeeds without requiring `bash`, `rm -rf`, `cp`, `mv`, `mkdir -p`, or `export`
- **AND** any genuinely platform-specific command is guarded by an explicit platform condition such as `if: matrix.platform == 'linux'`

#### Scenario: Build logic needs more than a single command

- **WHEN** a build step needs conditional logic, file copying, or path construction
- **THEN** that logic lives in a cross-platform script (Python using `pathlib`, Rust, or Node) rather than in shared shell syntax

### Requirement: Tauri hooks run from the Tauri project root

Both Tauri build hooks MUST be written for the directory Tauri actually uses as
their working directory, which is the Tauri project root
(`src/runtimes/tauri/`) and not `src-tauri/`.

#### Scenario: A hook resolves a repository-relative path

- **WHEN** a hook or package script references another part of the repository
- **THEN** the path is expressed relative to `src/runtimes/tauri/`
- **AND** it resolves to an existing file, so `python ../../scripts/build-web.py` and `python ../../scripts/serve-web.py` reach `src/scripts/`

#### Scenario: The hook working directory changes

- **WHEN** the script or hook location changes
- **THEN** every relative path in `tauri.conf.json` and `package.json` is recomputed from the new working directory before the change is pushed

### Requirement: Frontend distribution path

The frontend that Tauri embeds MUST point at the generated web application
directory, expressed relative to `src-tauri/`.

#### Scenario: Tauri bundles the web application

- **WHEN** Tauri builds an installer
- **THEN** `frontendDist` resolves to `src/web/` (`../../../web` from `src-tauri/`)
- **AND** the bundled application contains `index.html`, the vendored runtime, and the engine wheel

### Requirement: Generated web assets are not committed

The engine wheel and the vendored Pyodide/PyScript runtime MUST be produced by
the build, MUST live under `src/web/_wheel/` and `src/web/_assets/`, and MUST
remain excluded from version control.

#### Scenario: A fresh checkout is built

- **WHEN** `python src/scripts/build-web.py` runs from a clean checkout
- **THEN** it writes `src/web/_wheel/pykaraoke_ng-<version>-py3-none-any.whl`
- **AND** it downloads the configured Pyodide and PyScript files into `src/web/_assets/pyodide/` and `src/web/_assets/pyscript/`
- **AND** those generated directories are ignored by Git

#### Scenario: The app is served without a prior build

- **WHEN** `src/web/_wheel/` or `src/web/_assets/` is missing
- **THEN** the page fails to load the engine and the documented remedy is to run `src/scripts/build-web.py` first

### Requirement: Build configuration is verified by effect

Tests and CI steps that validate build configuration MUST check the artifacts a
command produces, not the literal text of the command string.

#### Scenario: A build-command test runs

- **WHEN** a test verifies a Tauri hook
- **THEN** it runs the hook and asserts that the expected artifacts exist (for example `src/web/_wheel/*.whl` and `src/web/_assets/pyscript/core.js`)
- **AND** it does not assert that a particular command substring appears in the configuration

#### Scenario: A build command is refactored

- **WHEN** `beforeBuildCommand` or its script is renamed or rewritten without changing what it produces
- **THEN** the build-configuration tests continue to pass

### Requirement: Local validation before pushing

A contributor MUST be able to reproduce the essential build checks locally, and
a build-system change MUST pass those checks before it is pushed.

#### Scenario: Validating a build change locally

- **WHEN** a contributor validates a build-system change
- **THEN** they regenerate the assets from the Tauri project root with `cd src/runtimes/tauri && npm run build`
- **AND** confirm the wheel and vendored runtime landed in `src/web/`
- **AND** run `cargo check` in `src/runtimes/tauri/src-tauri/`

### Requirement: Platform build matrix

CI MUST build the desktop application on Linux, Windows, and macOS, and each
platform build MUST succeed independently.

#### Scenario: The full build stage runs

- **WHEN** the build stage executes on the default branch
- **THEN** it produces a Linux `deb`, a Windows `nsis` installer, and a macOS `dmg` from the same source
- **AND** a failure on one platform does not suppress the others (fail-fast is disabled)

### Requirement: Builds are reproducible without network at package time

The engine MUST remain pure-stdlib so the built wheel has no runtime
dependencies, and the packaged desktop application MUST work fully offline.

#### Scenario: The wheel is built

- **WHEN** `build-web.py` builds the engine wheel
- **THEN** it builds with `--no-deps`
- **AND** the resulting wheel declares no runtime dependencies

#### Scenario: The packaged application starts offline

- **WHEN** the installed desktop application launches with no network access
- **THEN** it loads the embedded web application, engine wheel, and Pyodide/PyScript runtime from its own resources

## Historical incidents

These are the recorded failures that motivated the requirements above. They are
kept as context for reviewers; each corresponds to one or more requirements.

| Date | What broke | Root cause | Resolution |
|------|-----------|------------|------------|
| 2026-02-27 | All three platform builds | `beforeBuildCommand` used `bash -c` with `../../../../` paths, while Tauri ran it from `src/runtimes/tauri/` | Corrected the hook's working-directory assumption and path depth |
| 2026-02-28 | Windows build | `bash -c '...'` is unavailable on Windows runners | Moved build logic out of the shell into a cross-platform script |
| 2026-02-28 | Build-configuration tests | Tests asserted `"backend" in before_build_command`, which broke on refactor | Tests now run the hook and assert on the artifacts it produces |
| 2026-10-07 | `tauri dev` | `beforeDevCommand` pointed at the wrong path depth after the scripts directory moved | Corrected the relative path to `../../scripts/serve-web.py` |
