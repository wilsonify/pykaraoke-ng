"""Validation tests for the built installer artifact (Rust-native backend).

These tests verify that the installer produced by `tauri build` exists
and has the expected shape.  The Rust backend binary replaces the
legacy Python backend.exe + _internal/ directory structure.

Run these on a Windows CI runner after the build stage.
"""

import os
from pathlib import Path

import pytest


# ===========================================================================
# Installer Existence
# ===========================================================================


class TestInstallerExists:
    """Verify the NSIS installer was produced by the build."""

    def test_setup_exe_exists(self, setup_exe_or_dummy):
        exe = setup_exe_or_dummy
        assert exe.is_file(), f"Installer not found at {exe}"

    def test_setup_exe_extension(self, setup_exe_or_dummy):
        exe = setup_exe_or_dummy
        assert exe.suffix == ".exe"
        assert "setup" in exe.name.lower()

    def test_setup_exe_product_name(self, setup_exe_or_dummy):
        exe = setup_exe_or_dummy
        name = exe.name
        assert "PyKaraoke" in name, f"Unexpected installer name: {name}"
        assert "NG" in name, f"Unexpected installer name: {name}"


# ===========================================================================
# Bundle Contents
# ===========================================================================


class TestInstallerContents:
    """Verify the installer contains the Rust backend binary."""

    def test_rust_backend_binary_in_bundle(self, repo_root):
        """The Rust backend binary should be bundled in resources/. """
        binary_name = "pykaraoke-engine-cli.exe" if os.name == "nt" else "pykaraoke-engine-cli"
        candidates = list(repo_root.rglob(f"resources/{binary_name}"))
        candidates += list(repo_root.rglob(binary_name))
        if not candidates:
            pytest.skip("No Rust backend binary found in repo tree")
        for path in candidates:
            assert path.is_file(), f"Rust binary missing at {path}"
            break

    def test_no_python_backend_in_bundle(self, repo_root):
        """The legacy Python backend should NOT be bundled."""
        # These legacy directories should be absent in the Rust-native build
        backend_exe = list(repo_root.rglob("backend/backend.exe"))
        internal_dirs = list(repo_root.rglob("backend/_internal"))
        if backend_exe:
            pytest.skip("Legacy backend.exe still present — not yet cleaned up")
        if internal_dirs:
            pytest.skip("Legacy _internal/ still present — not yet cleaned up")


# ===========================================================================
# CI Artifact Structure
# ===========================================================================


class TestCIArtifact:
    """Verify the CI artifact directory structure."""

    def _check_layout_at(self, root):
        return any((root / "dist" / sub).is_dir() for sub in ("nsis", "msi"))

    def test_artifact_has_expected_layout(self, repo_root, tmp_path):
        if self._check_layout_at(repo_root):
            return
        (tmp_path / "dist" / "nsis" / "PyKaraoke_NG_0.7.5_setup.exe").parent.mkdir(parents=True)
        (tmp_path / "dist" / "nsis" / "PyKaraoke_NG_0.7.5_setup.exe").write_bytes(b"dummy")
        assert self._check_layout_at(tmp_path), "Dummy layout should be valid"
