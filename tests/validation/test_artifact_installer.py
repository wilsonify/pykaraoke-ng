"""Validation tests for the built NSIS installer artifact.

These tests verify that the Windows installer produced by
`tauri build --bundles nsis` exists and has the expected shape.

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

    def test_setup_exe_exists(self, setup_exe):
        assert setup_exe.is_file(), f"Installer not found at {setup_exe}"
        assert setup_exe.stat().st_size > 1_000_000, (
            f"Installer too small ({setup_exe.stat().st_size} bytes) — "
            "likely a corrupt or truncated build"
        )

    def test_setup_exe_extension(self, setup_exe):
        assert setup_exe.suffix == ".exe"
        assert "setup" in setup_exe.name.lower()

    def test_setup_exe_product_name(self, setup_exe):
        """The installer filename should contain the product name."""
        name = setup_exe.name
        assert "PyKaraoke" in name, f"Unexpected installer name: {name}"
        assert "NG" in name, f"Unexpected installer name: {name}"


# ===========================================================================
# Installer Metadata (if available)
# ===========================================================================


class TestInstallerMetadata:
    """Verify installer metadata using Windows APIs."""

    def test_setup_exe_has_version_info(self, setup_exe):
        """Check that the installer has embedded version metadata."""
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", f"""
                $path = '{setup_exe}';
                $info = (Get-Item $path).VersionInfo;
                Write-Output "ProductName=$($info.ProductName)";
                Write-Output "FileVersion=$($info.FileVersion)";
                Write-Output "ProductVersion=$($info.ProductVersion)";
            """],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout
        assert result.returncode == 0, f"PowerShell failed: {result.stderr}"
        assert "ProductName=" in output
        # Tauri NSIS bundles typically carry version info
        assert "PyKaraoke" in output, f"No product name in version info:\n{output}"


# ===========================================================================
# Bundle Contents
# ===========================================================================


class TestInstallerContents:
    """Verify the installer contains expected resources (static checks)."""

    def test_backend_dir_present_in_bundle(self, repo_root):
        """The backend/ resource directory should exist near the installer."""
        candidates = list(repo_root.rglob("backend/backend.exe"))
        if not candidates:
            pytest.skip("No backend.exe found in repo tree")
        for path in candidates:
            assert path.is_file(), f"backend.exe missing at {path}"
            break

    def test_internal_dir_has_pygame(self, repo_root):
        """The PyInstaller _internal/ dir should contain pygame."""
        internal_dirs = list(repo_root.rglob("backend/_internal/pygame"))
        if not internal_dirs:
            pytest.skip("No _internal/pygame found (might be in CI artifact)")
        assert any(d.is_dir() for d in internal_dirs), "pygame not bundled in _internal/"

    def test_internal_dir_has_numpy(self, repo_root):
        """The PyInstaller _internal/ dir should contain numpy."""
        internal_dirs = list(repo_root.rglob("backend/_internal/numpy"))
        if not internal_dirs:
            pytest.skip("No _internal/numpy found (might be in CI artifact)")
        assert any(d.is_dir() for d in internal_dirs), "numpy not bundled in _internal/"


# ===========================================================================
# CI Artifact Structure
# ===========================================================================


class TestCIArtifact:
    """Verify the CI artifact directory structure (when run in CI)."""

    def test_artifact_has_expected_layout(self, repo_root):
        """Check that the artifact has bundle/nsis/ or bundle/msi/ layout."""
        bundle_dirs = [
            repo_root / "dist" / "nsis",
            repo_root / "dist" / "msi",
        ]
        found_any = any(d.is_dir() for d in bundle_dirs)
        if not found_any:
            installer = _find_installer_in_dist(repo_root)
            if installer:
                found_any = True
        if not found_any:
            pytest.skip("No CI artifact structure found — not running in CI")


def _find_installer_in_dist(repo_root):
    dist = repo_root / "dist"
    if not dist.is_dir():
        return None
    for exe in dist.rglob("*.exe"):
        return exe
    return None
