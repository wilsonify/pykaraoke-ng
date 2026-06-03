# Administrator Guide

Deploy PyKaraoke-NG via Docker, Kubernetes, or Tauri desktop builds.

[← Home](index.md)

---

## Docker

```bash
docker pull ghcr.io/wilsonify/pykaraoke-ng:latest
docker run -it --rm \
    -v /path/to/songs:/songs:ro \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    pykaraoke-ng
```

### Build locally

```bash
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng:local .
docker compose -f deploy/docker/docker-compose.yml up app
docker compose -f deploy/docker/docker-compose.yml --profile dev up    # dev
docker compose -f deploy/docker/docker-compose.yml --profile test up   # test
```

---

## Kubernetes

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl get pods -n pykaraoke
kubectl scale deployment pykaraoke-ng -n pykaraoke --replicas=3
```

---

## Tauri Desktop Builds

Build a standalone Windows installer with the Python backend compiled
into a single executable — no Python required on the target machine.

### Prerequisites

| Platform | Requirements |
|----------|-------------|
| Windows | [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), Python 3.10+ |
| Linux | `libwebkit2gtk-4.0-dev build-essential libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev` |
| macOS | `xcode-select --install` |
| All | Rust toolchain, Node.js, Tauri CLI `npm install -g @tauri-apps/cli@1` |

### Build

```bash
cd src/runtimes/tauri
npm install -g @tauri-apps/cli@1               # one-time

# dev (uses local Python interpreter)
npx tauri dev

# production (builds standalone backend.exe via PyInstaller)
python -m pip install pyinstaller               # one-time
npx tauri build
```

The `beforeBuildCommand` runs `scripts/stage-backend.js` which uses
PyInstaller to compile the Python backend (~12 MB). The Tauri resource
glob bundles it into the installer.

### Output

```
src-tauri/target/release/bundle/
├── nsis/PyKaraoke NG_0.7.5_x64-setup.exe    # ~17 MB
└── msi/PyKaraoke NG_0.7.5_x64_en-US.msi      # ~25 MB
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Linker errors (Windows) | Run from Developer Command Prompt or call `vcvars64.bat` first |
| Blank Tauri window (Linux) | Set `WEBKIT_DISABLE_DMABUF_RENDERER=1` (fixed in code) |
| `cargo tauri` CLI not found | Install via npm: `npm install -g @tauri-apps/cli@1` |
| PyInstaller fails | Ensure `python -m pip install pyinstaller` ran in the correct Python env |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PYKARAOKE_SONGS_DIR` | `~/Karaoke` | Songs directory |
| `PYKARAOKE_DB_PATH` | `~/.pykaraoke/songs.db` | Database path |
| `PYKARAOKE_LOG_LEVEL` | `INFO` | Log verbosity |
| `BACKEND_MODE` | `stdio` | `stdio` or `http` |
| `PYKARAOKE_API_HOST` | `127.0.0.1` | HTTP API bind address |
| `PYKARAOKE_API_PORT` | `8080` | HTTP API port |

## Monitoring

```bash
docker inspect --format='{{.State.Health.Status}}' pykaraoke
kubectl get pods -n pykaraoke -o wide
docker logs -f pykaraoke-container
kubectl logs -f -n pykaraoke deployment/pykaraoke-ng
```

## Backup

```bash
cp ~/.pykaraoke/songs.db ~/backup/songs-$(date +%Y%m%d).db
kubectl get all,configmap,pvc -n pykaraoke -o yaml > pykaraoke-backup.yaml
```

## Security

- Run containers as non-root (default).
- Mount songs read-only: `-v /songs:/songs:ro`.
- Use `--security-opt=no-new-privileges` for Docker.
- Enforce `SecurityContext: runAsNonRoot: true` on Kubernetes.
