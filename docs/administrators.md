# Administrator Guide

Deploy and manage PyKaraoke-NG via Docker, Kubernetes, or Tauri desktop builds.

[← Home](index.md)

---

## Docker

### Quick start

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
docker run -it --rm -v ~/Karaoke:/songs:ro pykaraoke-ng:local
```

### Docker Compose

```bash
docker compose -f deploy/docker/docker-compose.yml up app          # run
docker compose -f deploy/docker/docker-compose.yml --profile dev up # dev mode
docker compose -f deploy/docker/docker-compose.yml --profile test up test # tests
```

### Image stages

| Stage | Purpose | ~Size |
|-------|---------|-------|
| `builder` | Install dependencies | 500 MB |
| `runtime` | Production image | 200 MB |
| `development` | Dev tools + hot reload | 350 MB |
| `test` | Test runner | 350 MB |

---

## Kubernetes

### Local cluster with kind

```bash
./scripts/kind-setup.sh create     # create cluster
./scripts/kind-setup.sh deploy     # deploy app
./scripts/kind-setup.sh status     # check status
```

### Manual deployment

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl get pods -n pykaraoke
```

### Manifests

```
deploy/kubernetes/
├── kind-config.yaml    # kind cluster config
├── namespace.yaml      # pykaraoke namespace
└── deployment.yaml     # Deployment, Service, ConfigMap, PVC
```

### Scaling

```bash
kubectl scale deployment pykaraoke-ng -n pykaraoke --replicas=3
```

---

## Tauri Desktop Builds

Tauri produces lightweight native installers (~10 MB) using the system webview.

### System dependencies

**Linux (Debian/Ubuntu):**
```bash
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

**macOS:**
```bash
xcode-select --install
```

**Windows:**
- [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

### Install Tauri CLI

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install tauri-cli --version "^1"
```

### Build

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri build
```

Outputs in `src/runtimes/tauri/src-tauri/target/release/bundle/`:

| Platform | Formats |
|----------|---------|
| Linux | `.AppImage`, `.deb` |
| macOS | `.app`, `.dmg` |
| Windows | `.msi`, `.exe` |

---

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYKARAOKE_SONGS_DIR` | `~/Karaoke` | Songs directory |
| `PYKARAOKE_DB_PATH` | `~/.pykaraoke/songs.db` | Database path |
| `PYKARAOKE_LOG_LEVEL` | `INFO` | Log verbosity |
| `BACKEND_MODE` | `stdio` | `stdio` or `http` |
| `PYKARAOKE_API_HOST` | `127.0.0.1` | HTTP API bind address |
| `PYKARAOKE_API_PORT` | `8080` | HTTP API port |
| `DISPLAY` | — | X11 display (Linux GUI) |

---

## Monitoring

### Health checks

```bash
# Docker
docker inspect --format='{{.State.Health.Status}}' pykaraoke

# Kubernetes
kubectl get pods -n pykaraoke -o wide
```

### Logs

```bash
# Docker
docker logs -f pykaraoke-container

# Kubernetes
kubectl logs -f -n pykaraoke deployment/pykaraoke-ng
```

---

## Backup

### Song database

```bash
cp ~/.pykaraoke/songs.db ~/backup/songs-$(date +%Y%m%d).db
```

### Kubernetes PVC

```bash
kubectl get all,configmap,pvc -n pykaraoke -o yaml > pykaraoke-backup.yaml
```

---

## Security

- Run containers as non-root (default in the provided image).
- Mount songs read-only: `-v /songs:/songs:ro`.
- Use `--security-opt=no-new-privileges` for Docker.
- On Kubernetes, enforce `SecurityContext` with `runAsNonRoot: true`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Cannot connect to X display | `xhost +local:docker` and verify `$DISPLAY` |
| Permission denied on songs | `chmod -R 755 /path/to/songs` |
| Pod stuck in Pending | `kubectl describe pod -n pykaraoke` — check PVC binding |
| Blank Tauri window on Linux | Set `WEBKIT_DISABLE_DMABUF_RENDERER=1` (see [issue](issues/webkit-dmabuf-empty-window.md)) |
