# PyKaraoke NG — Top-level Makefile
# Builds, tests, and packages the native Rust desktop app.
# No Python or external dependencies required.

TAURI_DIR  := src/runtimes/tauri
TAURI_SRC  := $(TAURI_DIR)/src-tauri
ENGINE_DIR := crates/pykaraoke-engine

# Detect platform
UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)
ifeq ($(findstring MINGW,$(UNAME_S)),MINGW)
  PLATFORM := Windows
else ifeq ($(findstring MSYS,$(UNAME_S)),MSYS)
  PLATFORM := Windows
else ifeq ($(findstring CYGWIN,$(UNAME_S)),CYGWIN)
  PLATFORM := Windows
else ifeq ($(UNAME_S),Windows)
  PLATFORM := Windows
else
  PLATFORM := $(UNAME_S)
endif

# Binary name varies by platform
BINARY_NAME := PyKaraoke NG
ifeq ($(PLATFORM),Windows)
  BINARY := $(TAURI_SRC)/target/release/$(BINARY_NAME).exe
  MSI    := $(TAURI_SRC)/target/release/bundle/msi/$(BINARY_NAME)_0.7.5_x64_en-US.msi
  NSIS   := $(TAURI_SRC)/target/release/bundle/nsis/$(BINARY_NAME)_0.7.5_x64-setup.exe
else ifeq ($(PLATFORM),Darwin)
  BINARY := $(TAURI_SRC)/target/release/$(BINARY_NAME)
  DMG    := $(TAURI_SRC)/target/release/bundle/dmg/$(BINARY_NAME)_0.7.5_x64.dmg
else
  BINARY := $(TAURI_SRC)/target/release/$(BINARY_NAME)
  DEB    := $(TAURI_SRC)/target/release/bundle/deb/$(BINARY_NAME)_0.7.5_amd64.deb
  APPIMAGE := $(TAURI_SRC)/target/release/bundle/appimage/$(BINARY_NAME)_0.7.5_amd64.AppImage
endif

.PHONY: all build clean install uninstall test test-rust test-js run dev help

.DEFAULT_GOAL := help

# ── Default ──────────────────────────────────────────────────────────────

all: build

# ── Build ────────────────────────────────────────────────────────────────

build: $(BINARY)

$(BINARY):
	cd "$(TAURI_DIR)" && npx @tauri-apps/cli@1 build

# Build only the Rust engine crate (faster, no frontend)
build-engine:
	cargo build --release --manifest-path "$(ENGINE_DIR)/Cargo.toml"

# ── Clean ────────────────────────────────────────────────────────────────

clean:
	cd "$(TAURI_SRC)" && cargo clean
	rm -rf "$(TAURI_DIR)/node_modules/.cache"
	rm -rf "$(TAURI_SRC)/target"

clean-engine:
	cd "$(ENGINE_DIR)" && cargo clean

clean-all: clean clean-engine

# ── Install ──────────────────────────────────────────────────────────────

INSTALL_DIR ?= /usr/local/bin

install: $(BINARY)
ifeq ($(PLATFORM),Windows)
	@echo "=== Installing via MSI ==="
	@if exist "$(MSI)" ( \
	  echo Starting MSI installer... && \
	  start /wait "" "$(MSI)" \
	) else if exist "$(NSIS)" ( \
	  echo Starting NSIS installer... && \
	  start /wait "" "$(NSIS)" \
	) else ( \
	  echo "No installer found. Run 'make build' first." && \
	  exit 1 \
	)
else ifeq ($(PLATFORM),Darwin)
	@echo "=== Installing DMG ==="
	hdiutil attach "$(DMG)"
	cp -r "/Volumes/$(BINARY_NAME)/$(BINARY_NAME).app" /Applications/
	hdiutil detach "/Volumes/$(BINARY_NAME)"
else
	@echo "=== Installing binary to $(INSTALL_DIR) ==="
	cp "$(BINARY)" "$(INSTALL_DIR)/"
	chmod +x "$(INSTALL_DIR)/$(BINARY_NAME)"
endif

uninstall:
ifeq ($(PLATFORM),Windows)
	@echo "Uninstall via: Settings > Apps > PyKaraoke NG"
else ifeq ($(PLATFORM),Darwin)
	rm -rf "/Applications/$(BINARY_NAME).app"
else
	rm -f "$(INSTALL_DIR)/$(BINARY_NAME)"
endif

# ── Test ─────────────────────────────────────────────────────────────────

test: test-rust test-js

test-rust:
	cargo test --release --manifest-path "$(ENGINE_DIR)/Cargo.toml"

test-js:
	node "$(TAURI_DIR)/src/app.test.js"

# ── Run (dev mode) ───────────────────────────────────────────────────────

run:
	cd "$(TAURI_DIR)" && npx @tauri-apps/cli@1 dev

# ── Distribution ─────────────────────────────────────────────────────────

dist: build
	@echo "=== Distribution bundles ==="
	@echo "Binary:  $(BINARY)"
	@echo "MSI:     $(MSI)"
	@echo "NSIS:    $(NSIS)"

# ── Help ─────────────────────────────────────────────────────────────────

help:
	@echo "PyKaraoke NG — Makefile"
	@echo ""
	@echo "  Targets:"
	@echo "    all          Default — builds the desktop app (same as 'build')"
	@echo "    build        Build the Tauri desktop app (Rust engine + frontend)"
	@echo "    build-engine  Build only the Rust engine crate (faster)"
	@echo "    clean        Clean Tauri build artifacts"
	@echo "    clean-engine  Clean engine crate artifacts"
	@echo "    clean-all     Clean all build artifacts"
	@echo "    install      Install via platform installer (MSI/NSIS/DMG)"
	@echo "    uninstall    Instructions for uninstalling"
	@echo "    test         Run all tests (Rust engine + frontend JS)"
	@echo "    test-rust    Run Rust engine tests only"
	@echo "    test-js      Run frontend JS tests only"
	@echo "    run          Launch app in development mode"
	@echo "    dist         Show built distribution bundles"
	@echo "    help         Show this message"
	@echo ""
	@echo "  Platform: $(PLATFORM)"
	@echo "  Binary:   $(BINARY)"
