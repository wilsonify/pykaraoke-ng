#!/usr/bin/env node
/**
 * stage-rust-backend.js — Stage the Rust native backend binary into
 * src-tauri/resources/ before a Tauri build.
 *
 * The Rust engine crate (crates/pykaraoke-engine) is part of the workspace
 * and is already compiled during `cargo build`.  This script copies the
 * compiled binary into the resource directory so Tauri's bundler can
 * include it in the installer.
 *
 * Tauri's beforeBuildCommand runs from the project root (src/runtimes/tauri/).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const PROJECT_ROOT = __dirname.replace(/[\\/]scripts$/, "");
const RESOURCE_DIR = path.join(PROJECT_ROOT, "src-tauri", "resources");

const IS_WIN = os.platform() === "win32";
const BINARY_NAME = IS_WIN ? "pykaraoke-engine-cli.exe" : "pykaraoke-engine-cli";

// Resolve the Rust binary from the workspace build output.
// The Tauri Cargo workspace is at src/runtimes/tauri/src-tauri/,
// but the engine is in crates/pykaraoke-engine/ at the repo root.
// We walk up to find the repo root, then locate the workspace target.
const TAURI_SRC_DIR = path.join(PROJECT_ROOT, "src-tauri");
const REPO_ROOT = path.resolve(PROJECT_ROOT, "..", "..", "..");

// Workspace target directory (shared by all workspace members)
const WORKSPACE_TARGET = path.join(REPO_ROOT, "target");

// Determine build profile — Tauri builds use release, so default to that.
const PROFILE = process.env.CARGO_BUILD_PROFILE || "release";
const BINARY_PATH = path.join(WORKSPACE_TARGET, PROFILE, BINARY_NAME);

// Also check debug (for dev builds)
const DEBUG_BINARY_PATH = path.join(WORKSPACE_TARGET, "debug", BINARY_NAME);

console.log(`Staging Rust backend binary into ${RESOURCE_DIR}`);

// Ensure resource directory exists
fs.mkdirSync(RESOURCE_DIR, { recursive: true });

// Find the binary
let srcPath = null;
if (fs.existsSync(BINARY_PATH)) {
  srcPath = BINARY_PATH;
} else if (fs.existsSync(DEBUG_BINARY_PATH)) {
  srcPath = DEBUG_BINARY_PATH;
}

if (!srcPath) {
  console.log(`Rust backend binary not found at ${BINARY_PATH} or ${DEBUG_BINARY_PATH}.`);
  console.log("Building Rust engine...");
  try {
    execSync("cargo build --workspace --bin pykaraoke-engine-cli --release", {
      cwd: REPO_ROOT,
      stdio: "inherit",
      timeout: 5 * 60 * 1000,
    });
    srcPath = BINARY_PATH;
  } catch (err) {
    console.error("Failed to build Rust engine:", err.message);
    process.exit(1);
  }
}

if (!srcPath || !fs.existsSync(srcPath)) {
  console.error(`Rust backend binary not found after build attempt: ${srcPath}`);
  process.exit(1);
}

const destPath = path.join(RESOURCE_DIR, BINARY_NAME);
fs.copyFileSync(srcPath, destPath);

// Preserve executable permissions on Linux/macOS
if (!IS_WIN) {
  fs.chmodSync(destPath, 0o755);
}

const stat = fs.statSync(destPath);
console.log(`Rust backend binary staged: ${destPath} (${(stat.size / 1024 / 1024).toFixed(1)} MB)`);
