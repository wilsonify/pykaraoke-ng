# PyKaraoke-NG Docker Image
# Multi-stage build for Python backend and Tauri desktop app
#
# Build Targets:
#   docker build --target backend -t pykaraoke-ng:backend .     # Python backend only
#   docker build --target tauri-dev -t pykaraoke-ng:tauri-dev . # Tauri dev environment
#   docker build --target tauri-runtime -t pykaraoke-ng:tauri . # Full Tauri app
#   docker build --target test -t pykaraoke-ng:test .           # Test environment

# =============================================================================
# Stage 1: Python Builder
# =============================================================================
FROM python:3.12-slim AS python-builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY src/pykaraoke/config/version.py ./src/pykaraoke/config/

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Python dependencies
RUN uv pip install --no-build --no-cache-dir \
    pygame==2.6.1 \
    numpy==2.4.6 \
    mutagen==1.47.0 \
    fastapi==0.136.3 \
    uvicorn==0.48.0

# Copy Python source code
COPY src/pykaraoke /app/src/pykaraoke
COPY assets/ /app/assets/

# =============================================================================
# Stage 2: Python Backend Service (for Tauri)
# =============================================================================
FROM python:3.12-slim AS backend

# Install runtime dependencies for pygame/SDL and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    freepats \
    libfreetype6 \
    libportmidi0 \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    timidity \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash pykaraoke

WORKDIR /app

# Copy virtual environment and source from builder (keep root ownership, read-only for pykaraoke user)
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/src /app/src
COPY --from=python-builder /app/assets /app/assets

# Set restrictive permissions: root owner, read-only for others
RUN chmod -R 555 /app/.venv && chmod -R 555 /app/src && chmod -R 555 /app/assets

USER pykaraoke

# Set environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the Python backend API in HTTP mode
CMD ["python", "-m", "pykaraoke.core.backend", "--http"]

# =============================================================================
# Stage 3: Tauri Development Environment
# =============================================================================
FROM rust:slim-bookworm AS tauri-dev

# Install system dependencies for Tauri
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libasound2-dev \
    libayatana-appindicator3-dev \
    libgtk-3-dev \
    librsvg2-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libwebkit2gtk-4.0-dev \
    libxcb1-dev \
    libxi-dev \
    libxrandr-dev \
    pkg-config \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and Tauri CLI
RUN set -eux; \
    NODE_VERSION="20.18.0"; \
    ARCH="x64"; \
    curl -fsSL --proto '=https' "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" -o /tmp/node.tar.xz; \
    curl -fsSL --proto '=https' "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o /tmp/SHASUMS256.txt; \
    grep "node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" /tmp/SHASUMS256.txt | sha256sum --check -; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1; \
    rm /tmp/node.tar.xz /tmp/SHASUMS256.txt; \
    cargo install tauri-cli --version 1.6.3

# Install uv for Python
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

WORKDIR /app

# Copy Python backend
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/src /app/src
COPY --from=python-builder /app/assets /app/assets

# Copy Tauri source
COPY src/runtimes/tauri /app/tauri

# Set environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV CARGO_HOME=/app/.cargo
ENV RUSTUP_HOME=/app/.rustup

WORKDIR /app/tauri/src-tauri

# Pre-fetch Rust dependencies for caching
RUN cargo fetch

WORKDIR /app/tauri

# Default: interactive shell for development
CMD ["bash"]

# =============================================================================
# Stage 4: Tauri Runtime (built application)
# =============================================================================
FROM debian:bookworm-slim AS tauri-runtime

# Install runtime dependencies only and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    libayatana-appindicator3-1 \
    libgtk-3-0 \
    libpulse0 \
    librsvg2-2 \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libwebkit2gtk-4.0-37 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash pykaraoke

WORKDIR /app

# Copy Python environment (keep root ownership, read-only for pykaraoke user)
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/src /app/src
COPY --from=python-builder /app/assets /app/assets

# Copy built Tauri application (this requires a pre-build step)
# In practice, build with tauri-dev stage and copy the binary
COPY --from=tauri-dev /app/tauri/src-tauri/target/release/pykaraoke-ng /app/pykaraoke-ng

# Set restrictive permissions: root owner, read-only for others
RUN chmod -R 555 /app/.venv && chmod -R 555 /app/src && chmod -R 555 /app/assets && chmod 555 /app/pykaraoke-ng

USER pykaraoke

# Environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/app:$PATH"
ENV PYTHONPATH=/app/src
ENV DISPLAY=:0

# Run the Tauri application
CMD ["/app/pykaraoke-ng"]

# =============================================================================
# Stage 5: Development stage (Python only)
# =============================================================================
FROM backend AS development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install uv for development
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

# Copy additional development files
COPY tests/ /app/tests/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/

# Install dev dependencies including testing and integration test deps
RUN uv pip install --no-build --no-cache-dir \
    pytest==9.0.3 \
    pytest-cov==7.1.0 \
    pytest-xdist==3.8.0 \
    ruff==0.15.15 \
    fastapi==0.136.3 \
    uvicorn==0.48.0 \
    selenium==4.44.0

USER pykaraoke

CMD ["bash"]

# =============================================================================
# Stage 6: Test runner stage
# =============================================================================
FROM development AS test

USER pykaraoke

# Run tests as default command
CMD ["pytest", "tests/", "-v", "--tb=short"]

# =============================================================================
# Stage 7: Browser UI (nginx serving frontend with HTTP bridge)
# =============================================================================
FROM nginx:alpine AS ui

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy frontend static files
COPY src/runtimes/tauri/src/ /usr/share/nginx/html/

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
