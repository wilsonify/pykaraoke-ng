# Administrator Guide

Deploy PyKaraoke-NG via Docker, Kubernetes, or Tauri desktop builds.

[← Home](index.md)

---

## Docker

Build targets (multi-stage):

| Target | Image | Use |
|--------|-------|-----|
| `python-builder` | — | Intermediate: installs Python deps |
| `backend` | ~150 MB | Python HTTP API server (no desktop) |
| `tauri-dev` | ~2 GB | Full Tauri dev environment with Rust toolchain |
| `tauri-runtime` | ~200 MB | Built Tauri app runtime |
| `development` | ~200 MB | Backend + test/development tools |
| `test` | ~200 MB | Runs `pytest tests/ -v` by default |

### Run the HTTP backend

```bash
docker build --target backend -t pykaraoke-ng:backend .
docker run -p 8080:8080 \
    -v /path/to/songs:/songs:ro \
    -e PYKARAOKE_SONGS_DIR=/songs \
    pykaraoke-ng:backend
curl http://localhost:8080/health
```

### Run tests in Docker

```bash
docker compose -f deploy/docker/docker-compose.yml --profile test run test-all
docker compose -f deploy/docker/docker-compose.yml --profile integration run test-integration
```

### Docker Compose profiles

| Profile | Services | Purpose |
|---------|----------|---------|
| `dev` | UI, backend, app | Interactive development with hot reload |
| `integration` | backend-test, test-integration | Integration tests against live HTTP API |
| `test` | test, test-all, test-all-coverage | Unit + integration test suite |
| `e2e` | backend, ui, selenium, tests | BDD end-to-end (Cucumber.js) |
| `app` | app | Deploy the Tauri app (full desktop) |

---

## Kubernetes

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl get pods -n pykaraoke
kubectl scale deployment pykaraoke-ng -n pykaraoke --replicas=3
```

The Kubernetes manifests deploy the HTTP backend.  The `tauri-runtime`
Docker target can be used for desktop-in-Docker deployments with X11
forwarding.

---

## Tauri Desktop Builds

Build a standalone installer with the Python backend compiled into a
single executable — no Python required on the target machine.

### Prerequisites

| Platform | Requirements |
|----------|-------------|
| Windows | [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), Python 3.10+, Node.js |
| Linux | `libwebkit2gtk-4.0-dev build-essential libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev`, Node.js |
| macOS | `xcode-select --install`, Node.js |
| All | Rust toolchain, Tauri CLI: `npm install -g @tauri-apps/cli@1` |

### Build

```bash
cd src/runtimes/tauri

# Production build (builds standalone backend.exe via PyInstaller)
python -m pip install pyinstaller               # one-time
npm install -g @tauri-apps/cli@1                # one-time
npx tauri build --bundles nsis                  # Windows installer
npx tauri build --bundles dmg                   # macOS DMG
npx tauri build --bundles deb                   # Linux deb
```

The `beforeBuildCommand` runs `scripts/stage-backend.js` which:
1. Locates the Python environment (venv or system)
2. Runs PyInstaller against `backend.spec`
3. Places the compiled `backend.exe` (~12 MB) into `src-tauri/backend/`

The Tauri resource glob (`backend/**`) bundles it into the installer.

### Output

```
src-tauri/target/release/bundle/
├── nsis/PyKaraoke NG_<version>_x64-setup.exe    # ~17 MB (Windows)
├── msi/PyKaraoke NG_<version>_x64_en-US.msi      # ~25 MB (Windows)
├── deb/pykaraoke-ng_<version>_amd64.deb          # Linux
└── dmg/PyKaraoke NG_<version>_x64.dmg            # macOS
```

### Standalone backend artifact

Build just the backend without the full Tauri build:

```bash
cd src/runtimes/tauri
python -m PyInstaller backend.spec --distpath src-tauri --workpath build/pyinstaller-work --clean -y
```

The resulting `src-tauri/backend/backend.exe` can be run standalone:

```bash
echo '{"action":"get_state","params":{}}' | src-tauri/backend/backend.exe
```

### Validate the built artifact

```bash
export PYKARAOKE_BACKEND_EXE=src/runtimes/tauri/src-tauri/backend/backend.exe
pytest tests/validation/test_artifact_backend.py -v
```

This launches the real binary as a subprocess and tests it via
stdin/stdout — 16 smoke tests covering startup, settings, library scan,
playlist operations, volume, and error handling.

### Troubleshooting

| Problem | Fix |
|---------|------|
| Linker errors (Windows) | Run from Developer Command Prompt or call `vcvars64.bat` first |
| Blank Tauri window (Linux) | `WEBKIT_DISABLE_DMABUF_RENDERER=1` is set automatically in code |
| `cargo tauri` CLI not found | Install via npm: `npm install -g @tauri-apps/cli@1` |
| PyInstaller fails | Ensure `pip install pyinstaller` ran in the correct Python env |
| Hidden import missing | Add to `backend.spec:hiddenimports` and rebuild |
| Backend.exe crashes on start | Test standalone: `echo '{"action":"get_state"}' \| ./backend.exe` |

---

## Release Process

Releases are automated via the CI/CD pipeline (`.github/workflows/ci-cd.yml`):

1. Push to `main` triggers the full pipeline.
2. All unit, integration, E2E, and BDD tests must pass.
3. SonarQube quality gate must pass (no blocker/critical issues).
4. Platform builds produce installers for Windows, macOS, and Linux.
5. E2E stage validates each platform's artifact.
6. Release stage creates a semver tag + GitHub Release with all artifacts.

Manual release:

```bash
# Push a version tag to trigger a release
git tag v0.8.0
git push origin v0.8.0
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PYKARAOKE_SONGS_DIR` | `~/Karaoke` | Songs directory |
| `PYKARAOKE_DB_PATH` | `~/.pykaraoke/songs.db` | Database path |
| `PYKARAOKE_LOG_LEVEL` | `INFO` | Log verbosity |
| `BACKEND_MODE` | `stdio` | `stdio` or `http` |
| `PYKARAOKE_API_HOST` | `127.0.0.1` | HTTP API bind address |
| `PYKARAOKE_API_PORT` | `8080` | HTTP API port |
| `PYKARAOKE_BACKEND_EXE` | (auto) | Path to custom `backend.exe` for testing |

## Monitoring

```bash
docker inspect --format='{{.State.Health.Status}}' pykaraoke
kubectl get pods -n pykaraoke -o wide
docker logs -f pykaraoke-container
kubectl logs -f -n pykaraoke deployment/pykaraoke-ng
```

Health endpoint (HTTP mode): `GET /health` → `{"status": "healthy", "timestamp": ...}`

## Backup

```bash
cp ~/.pykaraoke/songs.db ~/backup/songs-$(date +%Y%m%d).db
kubectl get all,configmap,pvc -n pykaraoke -o yaml > pykaraoke-backup.yaml
```

## Security

- Run containers as non-root (default in Dockerfile).
- Mount songs read-only: `-v /songs:/songs:ro`.
- Use `--security-opt=no-new-privileges` for Docker.
- Enforce `SecurityContext: runAsNonRoot: true` on Kubernetes.
- All pip install commands in CI use `--only-binary :all:` to prevent
  arbitrary code execution from setup scripts (see SonarQube rules).
