#!/usr/bin/env python3
"""Build the self-contained web assets for PyKaraoke NG (cross-platform).

Produces, inside src/web/ (the authoritative frontend root that both the
dev server and ``tauri.conf.json``'s ``frontendDist`` ship):

    _wheel/pykaraoke_ng-<version>-py3-none-any.whl   the engine wheel
    _assets/pyodide/                                  the Pyodide runtime
    _assets/pyscript/                                 the PyScript core

Everything under src/web/_assets and src/web/_wheel is generated and
gitignored; a fresh checkout needs to run this script before serving the app
(and before `tauri build`).

The Pyodide and PyScript files are fetched from pinned CDN URLs and their
SHA-256 digests are checked against a manifest (``ASSET_SHA256`` below).  A
file that already exists with the correct digest is reused, so a warm build
needs no network access; a digest mismatch is a hard failure so a silently
swapped upstream asset cannot reach a package.

After vendoring, ``validate_assets`` cross-checks every local asset that
``src/web/index.html`` references (``/_assets/...``, ``/_wheel/...``,
``./src/app.js``, ``./src/helpers.js``) and exits non-zero if any is
missing, so a build can never ship a page that 404s at runtime.

Usage: python src/scripts/build-web.py [--check-only]
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
WEB = ROOT / "src" / "web"
WHEEL_DIR = WEB / "_wheel"
PYODIDE_DIR = WEB / "_assets" / "pyodide"
PYSCRIPT_DIR = WEB / "_assets" / "pyscript"

PYODIDE_VERSION = "0.24.1"
PYSCRIPT_VERSION = "2024.10.1"
PYODIDE_BASE = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full"
PYSCRIPT_BASE = f"https://pyscript.net/releases/{PYSCRIPT_VERSION}"

USER_AGENT = "pykaraoke-ng-build/0.8 (https://github.com/wilsonify/pykaraoke-ng)"

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

# SHA-256 of every vendored runtime file, keyed by "<subdir>/<name>"
# (e.g. "pyodide/pyodide.mjs").  These pin the exact bytes that ship, so a
# CDN compromise or an upstream re-tag is caught instead of packaged.
ASSET_SHA256 = {
    "pyodide/micropip-0.5.0-py3-none-any.whl": "494f8d406706f76bec373188ca54141ba34e52babebb484dad9878bdd1f3f911",
    "pyodide/packaging-23.1-py3-none-any.whl": "81fc5c9676c2a1e121bc66df30bbd2672ce7b7c182dc9b742582750cacc2cb4f",
    "pyodide/pyodide-lock.json": "e313a21e0717839411cecf6f5bb74a92124239a2dffa80ec7ed1b712d621380f",
    "pyodide/pyodide.asm.js": "71250bb1cf7216d1f848505f1056f351bd02187fbb112e966f6e9745465d0c4f",
    "pyodide/pyodide.asm.wasm": "f7141d4928ef91480c6080e2746ebb93fd4f3567bf0077f6a7f65b0ad11b9da5",
    "pyodide/pyodide.mjs": "eaa1080fb039e9692e858ce634135df8757a8f506baecc959d4e1dfe0e7c8c14",
    "pyodide/python_stdlib.zip": "573b362d25c0ade9f5c2c2d2313fae9a92bc46adf66dd2374130d1f80b5ec9ca",
    "pyscript/core-DHft4mQJ.js": "820b3f6a965ebc6334623bc6e40f762656299136399c02246c12dee4a49283d0",
    "pyscript/core-DHft4mQJ.js.map": "2d79ef9089a9a77e8765d75858d0f047226589d54fe3010b264f9f362d1822e7",
    "pyscript/core.css": "568c279e18341abf407cadf73732ea6e9a287816110294e3240bc8192d1bbc71",
    "pyscript/core.js": "6ac03769916d259b87d4de578e490c33712cc166732568f93049202ceefd3a1f",
    "pyscript/core.js.map": "6cf5a54e78d83395543cbd31c6c174eb2cdefa7a9485870f255076ec9aee97ae",
    "pyscript/deprecations-manager-BDRw2fed.js": "ca9c396e62f46746b194925a5079b1678a1a9b1353e6412374cd25cbd1416d31",
    "pyscript/donkey-c355Wa24.js": "0258d8339a114bcb139fc7918c1908d3308cda69706b414eb5a4aff07a12bf10",
    "pyscript/error-CdZsd8BO.js": "1bb465638b199de8c94803c4e1854f60aa2f2cadbcd8de90d4378045cb07dbb4",
    "pyscript/py-editor-BRZBRs2T.js": "efd8aebf39337bb793011c45d82c7834c8af3f018e328b3b620be75a29f40730",
    "pyscript/py-terminal-D_z3jMz-.js": "51b482e5340bcd881ef91fc7e803f6bcc3c65730bb4e36132d55472edaeb7eef",
    "pyscript/toml-CvAfdf9_.js": "361597c3972f7996ba25ffb2cb33c542f5a5ee13ab9fd633e9d48e00fe1074e7",
    "pyscript/toml-DiUM0_qs.js": "15d0faa3d8380d090eb2838661b1fd91bb89fae033eaaafaa9a3df866bea4736",
    "pyscript/zip-Bf48tRr5.js": "73d3e5e165f1d53fb5c191dd8ea2cee72f11f68556a1db2f3bc2b5c2800e44db",
}

# Local paths that index.html references and that must exist at runtime.
# ``/_assets`` and ``/_wheel`` are served from the web root; ``./src`` is the
# module tree loaded by the app bundle.
REQUIRED_RUNTIME_DIRS = [
    WEB / "_assets" / "pyodide",
    WEB / "_assets" / "pyscript",
    WEB / "_wheel",
]


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_verified(url: str, dest: pathlib.Path, expected: str) -> None:
    """Download *url* to *dest*, verifying its SHA-256 against *expected*."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as resp:
        data = resp.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"checksum mismatch for {url}\n  expected sha256 {expected}\n  actual   sha256 {actual}"
        )
    dest.write_bytes(data)
    print(f"  {dest.name}  ok")


def vendor_runtime() -> None:
    """Ensure every runtime file exists with the pinned digest."""
    for d in (PYODIDE_DIR, PYSCRIPT_DIR):
        d.mkdir(parents=True, exist_ok=True)

    plan = [(PYODIDE_DIR, PYODIDE_BASE, name) for name in PYODIDE_FILES]
    plan += [(PYSCRIPT_DIR, PYSCRIPT_BASE, name) for name in PYSCRIPT_FILES]

    to_fetch: list[tuple[str, pathlib.Path, str]] = []
    for subdir, base, name in plan:
        dest = subdir / name
        expected = ASSET_SHA256[f"{subdir.name}/{name}"]
        if dest.exists() and sha256_file(dest) == expected:
            continue  # warm build: reuse the already-vendored, verified file
        to_fetch.append((f"{base}/{name}", dest, expected))

    if not to_fetch:
        print("==> Runtime assets already vendored and verified (no download)")
        return

    print(f"==> Vendoring {len(to_fetch)} runtime asset(s)")
    for url, dest, expected in to_fetch:
        fetch_verified(url, dest, expected)


def build_wheel() -> None:
    """Build the engine wheel into _wheel/, removing any stale wheels first."""
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    for stale in WHEEL_DIR.glob("*.whl"):
        stale.unlink()
    print("==> Building pykaraoke wheel")
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "-w", str(WHEEL_DIR), "--no-deps"],
        check=True,
    )


def _local_refs_in_index() -> list[str]:
    """Local asset paths referenced by src/web/index.html."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    refs: set[str] = set()
    # Root-relative references in src/href attributes.
    for match in re.finditer(r"(?:src|href)=\"(/[^\"]+)\"", html):
        refs.add(match.group(1))
    # Root-relative paths in PyScript config (interpreter and packages).
    for match in re.finditer(r"\"(/[^\"]+)\"", html):
        value = match.group(1)
        if value.startswith(("/_assets/", "/_wheel/")):
            refs.add(value)
    # <script type="module" src="./src/app.js"> (web-root relative)
    for match in re.finditer(r"src=\"\./(src/[^\"]+)\"", html):
        refs.add("/" + match.group(1))
    return sorted(refs)


def validate_assets() -> None:
    """Fail loudly if any asset index.html references is missing."""
    problems: list[str] = []

    for ref in _local_refs_in_index():
        rel = ref.lstrip("/")
        target = WEB / rel
        if not target.exists():
            problems.append(f"index.html references missing asset: {ref} -> {target}")

    wheels = list(WHEEL_DIR.glob("*.whl"))
    if not wheels:
        problems.append(f"no engine wheel found in {WHEEL_DIR}")

    if problems:
        print("==> Asset validation FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        raise SystemExit(1)

    print("==> Asset validation passed")
    for ref in _local_refs_in_index():
        print(f"  {ref}")
    for w in wheels:
        print(f"  _wheel/{w.name}")


def main() -> None:
    if "--check-only" in sys.argv:
        validate_assets()
        return

    build_wheel()
    vendor_runtime()
    validate_assets()
    print("==> Web assets ready")


if __name__ == "__main__":
    main()
