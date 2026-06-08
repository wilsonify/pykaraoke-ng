#!/usr/bin/env node
/**
 * stage-backend.js — Stage the Python backend into src-tauri/backend/
 * before a Tauri build.
 *
 * Compiles the headless Python backend into a standalone executable
 * using PyInstaller. Supports Windows, Linux, and macOS.
 *
 * Tauri's beforeBuildCommand runs from the project root (src/runtimes/tauri/).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const PROJECT_ROOT = __dirname.replace(/[\\/]scripts$/, "");
const BACKEND_DIR = path.join(PROJECT_ROOT, "src-tauri", "backend");
const WORK_DIR = path.join(PROJECT_ROOT, "build", "pyinstaller-work");
const SPEC_FILE = path.join(PROJECT_ROOT, "backend.spec");
const IS_WIN = os.platform() === "win32";

function rmrf(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function cleanBuildArtifacts() {
  rmrf(WORK_DIR);
  const pyiBuild = path.join(PROJECT_ROOT, "build");
  if (fs.existsSync(pyiBuild)) {
    const entries = fs.readdirSync(pyiBuild);
    if (entries.length === 0) {
      fs.rmdirSync(pyiBuild);
    }
  }
}

console.log(`Building standalone backend into ${BACKEND_DIR}`);

rmrf(BACKEND_DIR);

// Find Python interpreter — cross-platform
const REPO_ROOT = path.resolve(PROJECT_ROOT, "..", "..", "..");
const venvScriptsDir = IS_WIN ? "Scripts" : "bin";
const pythonExe = IS_WIN ? "python.exe" : "python";
const venvCandidates = [
  path.join(REPO_ROOT, ".venv313", venvScriptsDir, pythonExe),
  path.join(REPO_ROOT, ".venv", venvScriptsDir, pythonExe),
  path.join(PROJECT_ROOT, ".venv313", venvScriptsDir, pythonExe),
  path.join(PROJECT_ROOT, ".venv", venvScriptsDir, pythonExe),
];
let python = venvCandidates.find((p) => fs.existsSync(p));
if (!python) {
  const whichCmd = IS_WIN ? "where python" : "which python";
  try {
    python = execSync(whichCmd, { encoding: "utf8" })
      .split(/\r?\n/)[0]
      .trim();
  } catch {
    python = null;
  }
}

const DIST_DIR = path.join(PROJECT_ROOT, "src-tauri");

// Check if PyInstaller is available; if not, create a minimal placeholder
// so Tauri's resource glob backend/** doesn't fail (same approach as build.rs).
if (python) {
  try {
    execSync(`"${python}" -m PyInstaller --version`, {
      stdio: "pipe",
      encoding: "utf8",
    });
  } catch {
    python = null;
  }
}

if (!python) {
  console.log("PyInstaller or Python not available; creating placeholder backend directory.");
  const placeholderDir = path.join(DIST_DIR, "backend", "pykaraoke");
  fs.mkdirSync(placeholderDir, { recursive: true });
  fs.writeFileSync(
    path.join(placeholderDir, "PLACEHOLDER"),
    "# placeholder so backend/** glob matches during tauri build\n"
  );
  console.log(`Created placeholder at ${placeholderDir}`);
  process.exit(0);
}

// Run PyInstaller
console.log(`Using Python: ${python}`);
console.log(`Spec file:   ${SPEC_FILE}`);

const pyiCmd = `"${python}" -m PyInstaller "${SPEC_FILE}" --distpath "${DIST_DIR}" --workpath "${WORK_DIR}" --clean -y`;
console.log(`Running: ${pyiCmd}`);

try {
  execSync(pyiCmd, {
    stdio: "inherit",
    cwd: PROJECT_ROOT,
    timeout: 5 * 60 * 1000,
  });
} catch (err) {
  console.error(`PyInstaller failed: ${err.message}`);
  cleanBuildArtifacts();
  process.exit(1);
}

cleanBuildArtifacts();

// Verify the binary exists (cross-platform name)
const backendBinary = path.join(DIST_DIR, "backend", IS_WIN ? "backend.exe" : "backend");
if (fs.existsSync(backendBinary)) {
  const stat = fs.statSync(backendBinary);
  console.log(`Backend executable created: ${backendBinary} (${(stat.size / 1024 / 1024).toFixed(1)} MB)`);
} else {
  console.error("Backend executable not found in output directory.");
  process.exit(1);
}
