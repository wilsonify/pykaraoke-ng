#!/usr/bin/env python3
"""Build the self-contained web assets for PyKaraoke NG (cross-platform).

Produces, inside web/:

    _wheel/pykaraoke_ng-<version>-py3-none-any.whl   the engine wheel
    _assets/pyodide/                                  the Pyodide runtime
    _assets/pyscript/                                 the PyScript core

Everything under web/_assets and web/_wheel is generated and gitignored;
a fresh checkout needs to run this script before serving the app (and
before `tauri build`).

Usage: python scripts/build-web.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WHEEL_DIR = WEB / "_wheel"
PYODIDE_DIR = WEB / "_assets" / "pyodide"
PYSCRIPT_DIR = WEB / "_assets" / "pyscript"

PYODIDE_VERSION = "0.24.1"
PYSCRIPT_VERSION = "2024.10.1"
PYODIDE_BASE = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full"
PYSCRIPT_BASE = f"https://pyscript.net/releases/{PYSCRIPT_VERSION}"

# Pyodide resolves packages referenced by pyodide-lock.json relative to
# its own directory, so the runtime wheels sit alongside it.
PYODIDE_FILES = [
    "pyodide.mjs",
    "pyodide.asm.js",
    "pyodide.asm.wasm",
    "pyodide-lock.json",
    "python_stdlib.zip",
    "micropip-0.5.0-py3-none-any.whl",
    "packaging-23.1-py3-none-any.whl",
]

PYSCRIPT_FILES = [
    "core.css",
    "core.js",
    "core.js.map",
    "core-DHft4mQJ.js",
    "core-DHft4mQJ.js.map",
    "toml-CvAfdf9_.js",
    "toml-DiUM0_qs.js",
    "zip-Bf48tRr5.js",
    "deprecations-manager-BDRw2fed.js",
    "donkey-c355Wa24.js",
    "error-CdZsd8BO.js",
    "py-editor-BRZBRs2T.js",
    "py-terminal-D_z3jMz-.js",
]


def fetch(url: str, dest: pathlib.Path) -> None:
    print(f"  {url.split('/')[-1]}")
    # Some CDNs (pyscript.net) reject default urllib User-Agents.
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "pykaraoke-ng-build/0.8 (https://github.com/wilsonify/pykaraoke-ng)"
        },
    )
    with urllib.request.urlopen(request, timeout=120) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    for d in (WHEEL_DIR, PYODIDE_DIR, PYSCRIPT_DIR):
        d.mkdir(parents=True, exist_ok=True)

    print("==> Building pykaraoke wheel")
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "-w", str(WHEEL_DIR), "--no-deps"],
        check=True,
    )

    print(f"==> Vendoring Pyodide {PYODIDE_VERSION}")
    for name in PYODIDE_FILES:
        fetch(f"{PYODIDE_BASE}/{name}", PYODIDE_DIR / name)

    print(f"==> Vendoring PyScript {PYSCRIPT_VERSION}")
    for name in PYSCRIPT_FILES:
        fetch(f"{PYSCRIPT_BASE}/{name}", PYSCRIPT_DIR / name)

    wheels = sorted(WHEEL_DIR.glob("*.whl"))
    print("==> Web assets ready")
    for w in wheels:
        print(f"  {w.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())