# PyKaraoke-NG Repository Reorganization Plan

## Executive Summary

This document proposes a comprehensive reorganization of the PyKaraoke-NG repository to support:
- Long-term maintenance
- Cross-platform development (Electron and Tauri runtimes)
- Clear separation of concerns
- Scalable growth

## Current State Analysis

### Current Top-Level Structure (Problems)
```
pykaraoke-ng/
├── *.py (13+ Python modules at root - flat structure)
├── electron/ (Electron runtime)
├── tauri-app/ (Tauri runtime)
├── tests/ (Tests)
├── docs/ (Documentation)
├── k8s/ (Kubernetes configs)
├── scripts/ (Build/dev scripts)
├── fonts/ (Font assets)
├── icons/ (Icon assets)
├── install/ (Installation scripts)
├── *.md (10+ markdown files at root)
├── Docker*, setup.py, pyproject.toml, etc.
└── Various config files
```

### Key Issues with Current Structure
1. **Flat Python module layout**: All 13+ Python modules are at the repository root, making it unclear which are core vs runtime-specific
2. **Inconsistent runtime organization**: Electron is in `/electron/`, Tauri is in `/tauri-app/`
3. **Mixed concerns at root**: Code, config files, documentation, build scripts all at top level
4. **Asset disorganization**: Fonts and icons scattered, not clearly part of a runtime
5. **Deployment configs mixed**: k8s/, Dockerfile, docker-compose.yml at root
6. **Documentation scattered**: Some in `/docs/`, many `.md` files at root

## Proposed Structure

### Top-Level Directories
```
pykaraoke-ng/
├── src/                    # All application source code
│   ├── pykaraoke/         # Core Python package (reusable logic)
│   └── runtimes/          # Runtime-specific implementations
│       ├── electron/      # Electron implementation
│       └── tauri/         # Tauri implementation
├── tests/                  # Test suite mirroring src/ structure
├── docs/                   # All documentation
├── deploy/                 # Deployment configurations
├── assets/                 # Shared assets (fonts, icons)
├── scripts/                # Build and development scripts
├── .github/                # GitHub-specific configs (workflows, etc.)
└── [config files]          # Root-level configs only
```

### Detailed Structure with File Mapping

```
src/
├── pykaraoke/                           # Core Python package
│   ├── __init__.py                     # Package initialization
│   ├── players/                        # Format-specific players
│   │   ├── __init__.py
│   │   ├── cdg.py                      # FROM: pycdg.py
│   │   ├── cdg_aux.py                  # FROM: pycdgAux.py
│   │   ├── kar.py                      # FROM: pykar.py
│   │   └── mpg.py                      # FROM: pympg.py
│   ├── core/                           # Core business logic
│   │   ├── __init__.py
│   │   ├── backend.py                  # FROM: pykbackend.py
│   │   ├── player.py                   # FROM: pykplayer.py
│   │   ├── manager.py                  # FROM: pykmanager.py
│   │   ├── database.py                 # FROM: pykdb.py
│   │   └── performer_prompt.py         # FROM: performer_prompt.py
│   ├── config/                         # Configuration modules
│   │   ├── __init__.py
│   │   ├── constants.py                # FROM: pykconstants.py
│   │   ├── environment.py              # FROM: pykenv.py
│   │   └── version.py                  # FROM: pykversion.py
│   ├── legacy/                         # Legacy wxPython implementations
│   │   ├── __init__.py
│   │   ├── pykaraoke.py                # FROM: pykaraoke.py
│   │   └── pykaraoke_mini.py           # FROM: pykaraoke_mini.py
│   └── native/                         # C extensions
│       ├── _cpuctrl.c                  # FROM: _cpuctrl.c
│       └── _pycdgAux.c                 # FROM: _pycdgAux.c
│
└── runtimes/
    ├── electron/                        # Electron runtime
    │   ├── main.js                     # FROM: electron/main.js
    │   ├── renderer.js                 # FROM: electron/renderer.js
    │   ├── preload.js                  # FROM: electron/preload.js
    │   ├── index.html                  # FROM: electron/index.html
    │   ├── styles.css                  # FROM: electron/styles.css
    │   ├── package.json                # FROM: electron/package.json
    │   └── README.md                   # FROM: electron/README.md (create if missing)
    │
    └── tauri/                           # Tauri runtime
        ├── src/                        # Frontend source
        │   ├── index.html              # FROM: tauri-app/src/index.html
        │   ├── app.js                  # FROM: tauri-app/src/app.js
        │   └── styles.css              # FROM: tauri-app/src/styles.css
        ├── src-tauri/                  # Rust backend
        │   ├── src/
        │   │   └── main.rs             # FROM: tauri-app/src-tauri/src/main.rs
        │   ├── Cargo.toml              # FROM: tauri-app/src-tauri/Cargo.toml
        │   ├── tauri.conf.json         # FROM: tauri-app/src-tauri/tauri.conf.json
        │   └── build.rs                # FROM: tauri-app/src-tauri/build.rs
        └── README.md                   # FROM: tauri-app/README.md

tests/
├── pykaraoke/                           # Tests for core package
│   ├── players/
│   │   ├── test_cdg_format.py          # FROM: tests/test_cdg_format.py
│   │   └── test_midi_format.py         # FROM: tests/test_midi_format.py
│   ├── core/
│   │   ├── test_backend_api.py         # FROM: tests/test_backend_api.py
│   │   └── test_file_parsing.py        # FROM: tests/test_file_parsing.py
│   ├── config/
│   │   ├── test_pykconstants.py        # FROM: tests/test_pykconstants.py
│   │   ├── test_pykenv.py              # FROM: tests/test_pykenv.py
│   │   └── test_pykversion.py          # FROM: tests/test_pykversion.py
│   └── test_settings.py                # FROM: tests/test_settings.py
├── integration/
│   └── test_end_to_end.py              # FROM: tests/test_end_to_end.py
└── conftest.py                          # Shared test fixtures (create)

docs/
├── index.md                            # FROM: docs/index.md
├── developers.md                       # FROM: docs/developers.md
├── users.md                            # FROM: docs/users.md
├── administrators.md                   # FROM: docs/administrators.md
├── architecture/
│   ├── overview.md                     # FROM: ARCHITECTURE.md
│   ├── migration-guide.md              # FROM: MIGRATION_GUIDE.md
│   └── next-steps.md                   # FROM: NEXT_STEPS.md
├── development/
│   ├── sonarqube-setup.md              # FROM: SONARQUBE_SETUP.md
│   └── quality-improvements.md         # FROM: QUALITY_IMPROVEMENT_SUMMARY.md
└── _config.yml                         # FROM: docs/_config.yml

deploy/
├── docker/
│   ├── Dockerfile                      # FROM: Dockerfile
│   ├── docker-compose.yml              # FROM: docker-compose.yml
│   └── .dockerignore                   # FROM: .dockerignore
├── kubernetes/
│   ├── deployment.yaml                 # FROM: k8s/deployment.yaml
│   ├── namespace.yaml                  # FROM: k8s/namespace.yaml
│   └── kind-config.yaml                # FROM: k8s/kind-config.yaml
└── install/                            # Installation packages
    ├── linux/
    │   ├── pycdg                       # FROM: install/pycdg
    │   ├── pykar                       # FROM: install/pykar
    │   ├── pykaraoke                   # FROM: install/pykaraoke
    │   ├── pykaraoke.desktop           # FROM: install/pykaraoke.desktop
    │   ├── pykaraoke_mini              # FROM: install/pykaraoke_mini
    │   ├── pykaraoke_mini.desktop      # FROM: install/pykaraoke_mini.desktop
    │   └── pympg                       # FROM: install/pympg
    ├── gp2x/
    │   ├── pykaraoke.gpe               # FROM: install/pykaraoke.gpe
    │   └── rescan_songs.gpe            # FROM: install/rescan_songs.gpe
    ├── windows/
    │   └── installer.nsi               # FROM: install/windows_installer.nsi
    └── converters/
        └── cdg2mpg                     # FROM: install/cdg2mpg

assets/
├── fonts/
│   ├── DejaVuSans.ttf                  # FROM: fonts/DejaVuSans.ttf
│   ├── DejaVuSansCondensed-Bold.ttf    # FROM: fonts/DejaVuSansCondensed-Bold.ttf
│   ├── DejaVuSansCondensed.ttf         # FROM: fonts/DejaVuSansCondensed.ttf
│   └── LICENSE                         # FROM: fonts/LICENSE
└── icons/
    ├── audio_16.png                    # FROM: icons/audio_16.png
    ├── folder_close_16.png             # FROM: icons/folder_close_16.png
    ├── folder_open_16.png              # FROM: icons/folder_open_16.png
    ├── microphone.ico                  # FROM: icons/microphone.ico
    ├── microphone.png                  # FROM: icons/microphone.png
    ├── note.ico                        # FROM: icons/note.ico
    ├── pykaraoke.xpm                   # FROM: icons/pykaraoke.xpm
    ├── splash.png                      # FROM: icons/splash.png
    └── splash.xcf                      # FROM: icons/splash.xcf

scripts/
├── dev/
│   ├── setup-dev-env.sh                # FROM: scripts/setup-dev-env.sh
│   ├── validate-before-refactor.sh     # FROM: scripts/validate-before-refactor.sh
│   └── validate-refactor.sh            # FROM: scripts/validate-refactor.sh
├── testing/
│   ├── run-tests.sh                    # FROM: scripts/run-tests.sh
│   └── test-utils.sh                   # FROM: scripts/test-utils.sh
├── kubernetes/
│   └── kind-setup.sh                   # FROM: scripts/kind-setup.sh
└── build/
    └── cross-build-gp2x.sh             # FROM: cross-build-gp2x.sh

[Root level - config files only]
├── pyproject.toml                      # FROM: pyproject.toml (update paths)
├── setup.py                            # FROM: setup.py (update paths)
├── setup.cfg                           # FROM: setup.cfg (update paths)
├── pytest.ini                          # FROM: pytest.ini (update paths)
├── .coveragerc                         # FROM: .coveragerc (update paths)
├── MANIFEST.in                         # FROM: MANIFEST.in (update paths)
├── sonar-project.properties            # FROM: sonar-project.properties (update paths)
├── uv.lock                             # FROM: uv.lock
├── .gitignore                          # FROM: .gitignore
├── .cvsignore                          # FROM: .cvsignore
├── README.md                           # FROM: README.txt (convert to markdown)
├── COPYING                             # FROM: COPYING (license)
├── ChangeLog                           # FROM: ChangeLog
└── TODO                                # FROM: TODO
```

## Rationale for Key Decisions

### 1. `/src/pykaraoke/` as a proper Python package
**Reasoning**: 
- Enables proper imports: `from pykaraoke.players import cdg`
- Follows Python packaging best practices
- Makes it clear what's part of the installable package
- Simplifies testing and distribution

**Alternatives considered**:
- Keep flat structure: Rejected - doesn't scale, unclear organization
- Use `/lib/` or `/pykaraoke/`: Rejected - `src/` is the modern Python convention

### 2. `/src/runtimes/` for Electron and Tauri
**Reasoning**:
- Both are runtime wrappers around the same core Python logic
- Makes it explicit that these are interchangeable implementations
- Allows for future runtimes (e.g., Qt, GTK) without confusion
- Clear that these depend on `src/pykaraoke/` but not vice versa

**Alternatives considered**:
- Keep at root or in separate top-level dirs: Rejected - doesn't show relationship
- Merge into single UI dir: Rejected - they're fundamentally different runtimes

### 3. Subdirectories within `/src/pykaraoke/`
**Players, Core, Config, Legacy structure**:
- `players/`: Format-specific player implementations (CDG, KAR, MPG)
- `core/`: Core business logic (backend, player engine, manager, database)
- `config/`: Configuration and environment (constants, version, env)
- `legacy/`: Old wxPython implementations (may be deprecated later)
- `native/`: C extensions for performance-critical code

**Reasoning**: 
- Separates concerns clearly
- Makes it easy to find related code
- Legacy code is isolated but still accessible
- Native extensions are clearly marked

### 4. `/deploy/` for all deployment artifacts
**Reasoning**:
- Groups Docker, Kubernetes, and installation packages together
- Clear that these are for deployment, not development
- Easier to maintain and update deployment configs
- Follows GitOps best practices

**Subdirectories**:
- `docker/`: Docker-related files
- `kubernetes/`: K8s manifests
- `install/`: Platform-specific installation packages and scripts

### 5. `/assets/` for shared resources
**Reasoning**:
- Fonts and icons are used by multiple runtimes
- Clear separation from runtime-specific assets
- Easy to reference from different parts of the application
- Standard pattern in modern projects

### 6. Tests mirror source structure
**Reasoning**:
- Makes it obvious what each test file tests
- Easier to find tests for a specific module
- Supports pytest's test discovery
- Industry standard practice

### 7. Documentation consolidation
**Reasoning**:
- All docs in `/docs/` with logical subdirectories
- Architecture docs grouped together
- Development/quality docs grouped together
- Easier to generate documentation sites (MkDocs, etc.)

## Migration Strategy

### Phase 1: Preparation (Low Risk)
1. Create new directory structure (empty)
2. Update `.gitignore` to include new paths
3. Document the migration plan
4. Back up current state

### Phase 2: Core Python Package (Medium Risk)
1. Create `/src/pykaraoke/` package structure
2. Move Python modules with `git mv` to preserve history
3. Add `__init__.py` files to make it a proper package
4. Update internal imports within moved files
5. Run tests to verify nothing broke

### Phase 3: Runtimes (Low Risk - Isolated)
1. Move Electron files to `/src/runtimes/electron/`
2. Move Tauri files to `/src/runtimes/tauri/`
3. Update any path references in these files
4. Test each runtime independently

### Phase 4: Supporting Files (Low Risk)
1. Move assets to `/assets/`
2. Move scripts to `/scripts/` with subdirectories
3. Move deployment configs to `/deploy/`
4. Move/reorganize documentation to `/docs/`

### Phase 5: Configuration Updates (Medium Risk)
1. Update `pyproject.toml` package paths
2. Update `setup.py` package paths
3. Update `pytest.ini` test paths
4. Update `MANIFEST.in` include paths
5. Update `.coveragerc` source paths
6. Update `sonar-project.properties` source paths

### Phase 6: CI/CD Updates (Medium Risk)
1. Update GitHub Actions workflows
2. Update Docker build paths
3. Update any import paths in deployment configs

### Phase 7: Validation (Critical)
1. Run full test suite
2. Build package with `python -m build`
3. Test Electron runtime
4. Test Tauri runtime
5. Verify Docker builds
6. Run linters and type checkers
7. Update all documentation

## Risk Assessment

### High Risk Items
1. **Import path updates**: All Python imports must be updated
   - Mitigation: Use find/replace carefully, run tests frequently
   
2. **Build system configuration**: Package discovery might break
   - Mitigation: Test builds early and often, update configs incrementally

3. **CI/CD pipelines**: Workflows might fail
   - Mitigation: Test in feature branch, update paths carefully

### Medium Risk Items
1. **Runtime-specific paths**: Electron/Tauri might have hardcoded paths
   - Mitigation: Review carefully, test each runtime

2. **Asset references**: Icons/fonts paths in code
   - Mitigation: Use relative paths, update systematically

### Low Risk Items
1. **Documentation moves**: Low impact on functionality
2. **Script moves**: Can be updated easily
3. **Deployment config moves**: Isolated from main code

## Ambiguous Items / Questions

### 1. C Extension Files (`_cpuctrl.c`, `_pycdgAux.c`)
**Options**:
- A) Move to `/src/pykaraoke/native/` (proposed)
- B) Move to separate `/native/` at root
- C) Keep at root

**Recommendation**: Option A - keeps all source code together

### 2. Cross-build Script (`cross-build-gp2x.sh`)
**Options**:
- A) Move to `/scripts/build/` (proposed)
- B) Move to `/deploy/gp2x/`
- C) Delete if obsolete (GP2X is very old hardware)

**Recommendation**: Option A for now, but verify if still needed

### 3. Installation Scripts in `/install/`
**Options**:
- A) Move to `/deploy/install/` (proposed)
- B) Keep as top-level `/install/`
- C) Move to `/packaging/`

**Recommendation**: Option A - deployment-related

### 4. MPlayer Patch File (`install/mplayer-gp2x-cmdline-pykaraoke.diff`)
**Options**:
- A) Move to `/deploy/install/gp2x/` (proposed)
- B) Move to `/patches/`
- C) Delete if obsolete

**Recommendation**: Option A - GP2X specific

### 5. Legacy wxPython Files
**Options**:
- A) Move to `/src/pykaraoke/legacy/` (proposed)
- B) Move to separate `/legacy/` at root
- C) Delete if no longer maintained

**Recommendation**: Option A - keep as part of package but isolated

## Benefits of Proposed Structure

1. **Clear Separation of Concerns**
   - Core logic in one place (`/src/pykaraoke/`)
   - Runtime implementations clearly separated
   - Deployment separate from code

2. **Scalability**
   - Easy to add new runtimes
   - Easy to add new player formats
   - Clear structure for new features

3. **Maintainability**
   - Related code grouped together
   - Easy to find what you're looking for
   - Standard Python package structure

4. **Cross-Platform Support**
   - Multiple runtimes supported equally
   - Shared core logic
   - Platform-specific code isolated

5. **Testing**
   - Tests mirror source structure
   - Easy to run specific test suites
   - Clear test organization

6. **Documentation**
   - All docs in one place
   - Logical organization
   - Easy to generate doc sites

7. **Development Experience**
   - Standard structure familiar to Python developers
   - Clear imports and module hierarchy
   - Easier onboarding for new contributors

8. **Packaging and Distribution**
   - Proper Python package structure
   - Clear what gets installed
   - Easier to publish to PyPI

## Trade-offs and Considerations

### Cons of Reorganization
1. **Breaking changes**: All imports must be updated
2. **Documentation updates**: All docs referencing old paths need updates
3. **Learning curve**: Contributors need to learn new structure
4. **Git history**: Some history might be harder to follow (mitigated by `git mv`)

### Why These Trade-offs Are Worth It
1. **One-time cost**: Pain now, benefits forever
2. **Industry standard**: Structure is familiar to Python developers
3. **Future-proof**: Supports growth and multiple runtimes
4. **Professional**: Makes project look mature and well-organized

## Implementation Checklist

See the main PR checklist for detailed implementation steps.

## Success Criteria

The reorganization is successful if:
1. ✅ All tests pass
2. ✅ Package builds successfully
3. ✅ Both Electron and Tauri runtimes work
4. ✅ Docker builds work
5. ✅ CI/CD pipelines pass
6. ✅ Documentation is updated
7. ✅ No functionality is lost
8. ✅ Code is more organized and maintainable
