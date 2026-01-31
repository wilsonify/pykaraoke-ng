# PyKaraoke-NG Docker Image
# Multi-stage build for optimal image size
#
# Build:  docker build -t pykaraoke-ng .
# Run:    docker run -it --rm pykaraoke-ng

# =============================================================================
# Stage 1: Build stage with uv
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY pykversion.py ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies (without the package itself)
RUN uv pip install --no-cache-dir \
    pygame>=2.5.0 \
    numpy>=1.24.0 \
    mutagen>=1.47.0

# Copy source code
COPY *.py ./
COPY fonts/ ./fonts/
COPY icons/ ./icons/

# =============================================================================
# Stage 2: Runtime stage
# =============================================================================
FROM python:3.12-slim AS runtime

# Install runtime dependencies for pygame/SDL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libfreetype6 \
    libportmidi0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pykaraoke

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/*.py /app/
COPY --from=builder /app/fonts /app/fonts/
COPY --from=builder /app/icons /app/icons/

# Set ownership
RUN chown -R pykaraoke:pykaraoke /app

# Switch to non-root user
USER pykaraoke

# Set environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port for potential web interface
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pygame; print('healthy')" || exit 1

# Default command
CMD ["python", "-c", "import pykversion; print(f'PyKaraoke-NG v{pykversion.PYKARAOKE_VERSION_STRING}')"]

# =============================================================================
# Stage 3: Development stage
# =============================================================================
FROM runtime AS development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for development
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy test files
COPY tests/ /app/tests/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/

# Install dev dependencies
RUN uv pip install --no-cache-dir pytest pytest-cov pytest-xdist

# Switch back to non-root user
USER pykaraoke

CMD ["pytest", "tests/", "-v"]

# =============================================================================
# Stage 4: Test runner stage
# =============================================================================
FROM development AS test

# Ensure non-root user for security
USER pykaraoke

# Run tests as default command
CMD ["pytest", "tests/", "-v", "--tb=short"]
