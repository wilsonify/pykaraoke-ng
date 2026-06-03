#!/usr/bin/env node
/**
 * stage-backend.js — Stage the Python backend into src-tauri/backend/
 * before a Tauri build.
 *
 * Instead of copying raw .py files (which requires a Python interpreter
 * on the target machine), this script compiles the backend into a
 * standalone Windows executable using PyInstaller.
 *
 * Tauri's beforeBuildCommand runs from the project root (src/runtimes/tauri/).
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PROJECT_ROOT = __dirname.replace(/[\\/]scripts$/, "");
const BACKEND_DIR = path.join(PROJECT_ROOT, "src-tauri", "backend");
const WORK_DIR = path.join(PROJECT_ROOT, "build", "pyinstaller-work");
const SPEC_FILE = path.join(PROJECT_ROOT, "backend.spec");

// ── helpers ──────────────────────────────────────────────────────────

function rmrf(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function cleanBuildArtifacts() {
  // Remove the PyInstaller work directory.
  rmrf(WORK_DIR);
  // PyInstaller also leaves a build/ directory at the project root — clean it.
  const pyiBuild = path.join(PROJECT_ROOT, "build");
  if (fs.existsSync(pyiBuild)) {
    const entries = fs.readdirSync(pyiBuild);
    if (entries.length === 0) {
      fs.rmdirSync(pyiBuild);
    }
  }
}

// ── main ─────────────────────────────────────────────────────────────

console.log(`Building standalone backend into ${BACKEND_DIR}`);

// 1. Clean previous staging area
rmrf(BACKEND_DIR);

// 2. Determine which Python to use
// Check repo-root venv first, then project-root venv, then PATH.
const REPO_ROOT = path.resolve(PROJECT_ROOT, "..", "..", "..");
const venvCandidates = [
  path.join(REPO_ROOT, ".venv313", "Scripts", "python.exe"),
  path.join(REPO_ROOT, ".venv", "Scripts", "python.exe"),
  path.join(PROJECT_ROOT, ".venv313", "Scripts", "python.exe"),
  path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"),
];
let python = venvCandidates.find((p) => fs.existsSync(p));
if (!python) {
  try {
    python = execSync("where python", { encoding: "utf8" })
      .split(/\r?\n/)[0]
      .trim();
  } catch {
    python = null;
  }
}

if (!python) {
  console.error("No Python interpreter found.");
  process.exit(1);
}

// 3. Verify PyInstaller is available
try {
  execSync(`"${python}" -m PyInstaller --version`, {
    stdio: "pipe",
    encoding: "utf8",
  });
} catch {
  console.error(
    "PyInstaller not installed. Run: python -m pip install pyinstaller"
  );
  process.exit(1);
}

// 4. Run PyInstaller with the spec file.
//    The COLLECT(name='backend') in the spec creates a backend/ subdirectory
//    under --distpath, so we set --distpath to PROJECT_ROOT/src-tauri so the
//    final layout is src-tauri/backend/backend.exe (alongside _internal/).
const DIST_DIR = path.join(PROJECT_ROOT, "src-tauri");
console.log(`Using Python: ${python}`);
console.log(`Spec file:   ${SPEC_FILE}`);

const pyiCmd = `"${python}" -m PyInstaller "${SPEC_FILE}" --distpath "${DIST_DIR}" --workpath "${WORK_DIR}" --clean -y`;
console.log(`Running: ${pyiCmd}`);

try {
  execSync(pyiCmd, {
    stdio: "inherit",
    cwd: PROJECT_ROOT,
    timeout: 5 * 60 * 1000, // 5 minutes
  });
} catch (err) {
  console.error(`PyInstaller failed: ${err.message}`);
  cleanBuildArtifacts();
  process.exit(1);
}

// 5. Clean up build artifacts
cleanBuildArtifacts();

// 6. Verify the exe exists
const backendExe = path.join(DIST_DIR, "backend", "backend.exe");
if (fs.existsSync(backendExe)) {
  const stat = fs.statSync(backendExe);
  console.log(`Backend executable created: ${backendExe} (${(stat.size / 1024 / 1024).toFixed(1)} MB)`);
} else {
  console.error("backend.exe not found in output directory.");
  process.exit(1);
}
