#!/usr/bin/env node
/**
 * stage-backend.js — Cross-platform script to stage the Python backend
 * into src-tauri/backend/ before a Tauri build.
 *
 * Tauri's beforeBuildCommand runs from the project root (src/runtimes/tauri/).
 * This script replaces the bash one-liner so builds also work on Windows.
 */

const fs = require("fs");
const path = require("path");

const PROJECT_ROOT = __dirname.replace(/[\\/]scripts$/, "");
const BACKEND_DIR = path.join(PROJECT_ROOT, "src-tauri", "backend");
const SRC_PKG = path.resolve(PROJECT_ROOT, "..", "..", "..", "src", "pykaraoke");

/** Directories inside pykaraoke/ whose *.py files should be staged. */
const SUB_PACKAGES = ["core", "config", "players"];

// ── helpers ──────────────────────────────────────────────────────────

function rmrf(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyPy(srcDir, destDir) {
  for (const entry of fs.readdirSync(srcDir)) {
    if (entry.endsWith(".py")) {
      fs.copyFileSync(path.join(srcDir, entry), path.join(destDir, entry));
    }
  }
}

// ── main ─────────────────────────────────────────────────────────────

console.log(`Staging Python backend into ${BACKEND_DIR}`);

// 1. Clean previous staging area
rmrf(BACKEND_DIR);

// 2. Create directory tree
const pkgDir = path.join(BACKEND_DIR, "pykaraoke");
mkdirp(pkgDir);
for (const sub of SUB_PACKAGES) {
  mkdirp(path.join(pkgDir, sub));
}

// 3. Copy top-level __init__.py
fs.copyFileSync(
  path.join(SRC_PKG, "__init__.py"),
  path.join(pkgDir, "__init__.py")
);

// 4. Copy *.py from each sub-package
for (const sub of SUB_PACKAGES) {
  copyPy(path.join(SRC_PKG, sub), path.join(pkgDir, sub));
}

// 5. Summary
let count = 0;
function countFiles(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) countFiles(path.join(dir, entry.name));
    else count++;
  }
}
countFiles(BACKEND_DIR);
console.log(`Staged ${count} files.`);
