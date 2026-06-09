# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PyKaraoke NG backend.

Builds the headless Python backend into a Windows executable that
communicates over stdin/stdout JSON.  Uses onedir layout so the
Tauri resource glob backend/** picks up all required files.
"""

import os
import sys

SPEC_DIR = os.getcwd()
REPO_ROOT = os.path.normpath(os.path.join(SPEC_DIR, "..", "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets")

sys.path.insert(0, SRC_DIR)

block_cipher = None

a = Analysis(
    [os.path.join(SRC_DIR, "pykaraoke", "interfaces", "backend_api.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=[
        (os.path.join(ASSETS_DIR, "fonts"), "fonts"),
    ],
    hiddenimports=[
        "pygame",
        "numpy",
        "mutagen",
        "pykaraoke.config.constants",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "wx", "wxpython",
        "jupyter", "ipython", "notebook",
        "pytest", "nose", "sphinx", "docutils",
        "tkinter", "PyQt5", "PySide2", "PyQt6", "PySide6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="backend",
)
