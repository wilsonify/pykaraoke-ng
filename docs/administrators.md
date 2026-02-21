# 🔧 Administrator Guide

Deploy and manage PyKaraoke-NG at scale.

[← Back to Home](index.md)

---

## Deployment Options

| 🐳 Docker | ☸️ Kubernetes | 🖥️ Desktop |
|-----------|---------------|------------|
| Containerized deployment | Scalable with kind or production | Tauri for workstations |

---

## Docker Deployment

### Quick Start

```bash
docker pull ghcr.io/wilsonify/pykaraoke-ng:latest
docker run -it --rm \
    -v /path/to/songs:/songs \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    pykaraoke-ng
```

### Build Locally

```bash
docker build -f deploy/docker/Dockerfile -t pykaraoke-ng:local .

docker run -it --rm \
    -v ~/Karaoke:/songs:ro \
    pykaraoke-ng:local
```

### Docker Compose

```bash
# Start the application
docker compose -f deploy/docker/docker-compose.yml up app

# Run in development mode
docker compose -f deploy/docker/docker-compose.yml --profile dev up

# Run tests
docker compose -f deploy/docker/docker-compose.yml --profile test up test
```

### Multi-Stage Build

| Stage | Purpose | Size |
|-------|---------|------|
| `builder` | Install dependencies with uv | ~500MB |
| `runtime` | Production image | ~200MB |
| `development` | Dev tools + hot reload | ~350MB |
| `test` | Test runner | ~350MB |

---

## Kubernetes Deployment

### Local Development with kind

```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create cluster
./scripts/kind-setup.sh create

# Deploy application
./scripts/kind-setup.sh deploy

# Check status
./scripts/kind-setup.sh status
```

### Kubernetes Manifests

```
deploy/kubernetes/
├── kind-config.yaml    # Kind cluster configuration
├── namespace.yaml      # pykaraoke namespace
└── deployment.yaml     # Deployment, Service, ConfigMap, PVC
```

### Manual Deployment

```bash
# Create namespace
kubectl apply -f deploy/kubernetes/namespace.yaml

# Deploy application
kubectl apply -f deploy/kubernetes/deployment.yaml

# Check pods
kubectl get pods -n pykaraoke

# View logs
kubectl logs -n pykaraoke -l app.kubernetes.io/name=pykaraoke-ng
```

### Scaling

```bash
# Scale replicas
kubectl scale deployment pykaraoke-ng -n pykaraoke --replicas=3

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment pykaraoke-ng -n pykaraoke \
    --min=1 --max=5 --cpu-percent=80
```

### Persistent Storage

```yaml
# Mount external NFS storage (edit deployment.yaml)
volumes:
  - name: songs-storage
    nfs:
      server: nfs-server.local
      path: /exports/karaoke
```

---

## Electron Desktop Deployment

### Build Installers

```bash
cd src/runtimes/electron
npm install

npm run build         # Current platform
npm run build:linux   # AppImage, deb, rpm
npm run build:mac     # dmg, zip
npm run build:win     # nsis, portable
```

### Distribution

Built packages in `src/runtimes/electron/dist/`:

- **Linux:** `.AppImage`, `.deb`, `.rpm`
- **macOS:** `.dmg`, `.zip`
- **Windows:** `.exe` (installer and portable)

---

## Tauri Desktop Deployment

Tauri provides a lightweight, secure alternative to Electron using native webview.

### System Requirements

#### Linux
```bash
# Debian/Ubuntu (webkit2gtk 4.0 - older systems)
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget file \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Debian/Ubuntu (webkit2gtk 4.1 - newer systems)
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Fedora
sudo dnf install webkit2gtk4.0-devel openssl-devel curl wget file \
    gtk3-devel libappindicator-gtk3-devel librsvg2-devel

# Arch Linux
sudo pacman -S webkit2gtk base-devel curl wget file openssl gtk3 \
    libappindicator-gtk3 librsvg
```

#### macOS
```bash
xcode-select --install
```

#### Windows
- Install [Microsoft Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Install [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

### Install Tauri CLI

```bash
# Install Rust if needed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI v1 (for webkit2gtk 4.0 compatibility)
cargo install tauri-cli --version "^1"

# OR for Tauri v2 (requires webkit2gtk 4.1)
cargo install tauri-cli
```

> **Note:** Choose the Tauri CLI version based on your webkit2gtk version.
> Check with: `pkg-config --modversion webkit2gtk-4.0 || pkg-config --modversion webkit2gtk-4.1`

### Build Installers

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri build
```

### Distribution

Built packages in `src/runtimes/tauri/src-tauri/target/release/bundle/`:

- **Linux:** `.AppImage`, `.deb`
- **macOS:** `.app`, `.dmg`
- **Windows:** `.msi`, `.exe`

### Icons Requirement

Ensure icons exist in `src/runtimes/tauri/src-tauri/icons/`:
- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.png`
- `icon.ico` (Windows)
- `icon.icns` (macOS)

### Tauri vs Electron

| Feature | Tauri | Electron |
|---------|-------|----------|
| Bundle Size | ~10MB | ~150MB |
| Memory Usage | Lower | Higher |
| Native Look | Yes | Limited |
| Language | Rust + Web | Node.js + Web |
| WebView | System native | Chromium bundled |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYKARAOKE_SONGS_DIR` | `~/Karaoke` | Default songs directory |
| `PYKARAOKE_DB_PATH` | `~/.pykaraoke/songs.db` | Database location |
| `PYKARAOKE_LOG_LEVEL` | `INFO` | Logging verbosity |
| `DISPLAY` | (required) | X11 display for GUI |

### ConfigMap (Kubernetes)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pykaraoke-config
  namespace: pykaraoke
data:
  PYKARAOKE_SONGS_DIR: "/songs"
  PYKARAOKE_LOG_LEVEL: "INFO"
```

---

## Monitoring

### Health Checks

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

# Docker Compose
docker compose logs -f app

# Kubernetes
kubectl logs -f -n pykaraoke deployment/pykaraoke-ng
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup the song database
cp ~/.pykaraoke/songs.db ~/backup/songs-$(date +%Y%m%d).db

# Docker volume backup
docker run --rm \
    -v pykaraoke_data:/data:ro \
    -v $(pwd)/backup:/backup \
    alpine tar czf /backup/pykaraoke-data.tar.gz /data
```

### Kubernetes Backup

```bash
# Export resources
kubectl get all,configmap,pvc -n pykaraoke -o yaml > pykaraoke-backup.yaml

# Backup PVC data
kubectl exec -n pykaraoke deployment/pykaraoke-ng -- \
    tar czf - /app/data | gzip > pvc-backup.tar.gz
```

---

## Security Considerations

> **Important:** PyKaraoke-NG runs as a GUI application and may require X11 access.

### Docker Security

- Run as non-root user (default in our image)
- Use read-only mounts for songs: `-v /songs:/songs:ro`
- Limit X11 socket access
- Use `--security-opt=no-new-privileges`

### Kubernetes Security

- SecurityContext enforces non-root execution
- NetworkPolicy can restrict traffic
- Use RBAC to limit namespace access
- Scan images for vulnerabilities

---

## Troubleshooting

### Cannot connect to X display

```bash
xhost +local:docker
echo $DISPLAY
```

### Permission denied on songs folder

```bash
ls -la /path/to/songs
chmod -R 755 /path/to/songs
```

### Pod stuck in Pending

```bash
kubectl describe pod -n pykaraoke
kubectl get pvc -n pykaraoke
```

---

## Additional Resources

- [Repository Structure](architecture/structure.md) — project layout
- [Quality Improvements](development/quality-improvements.md) — code quality history
- [SonarQube Setup](development/sonarqube-setup.md) — code quality scanning
