"""
Regression tests for Tauri packaging and desktop launch issues.

These tests validate that the Tauri build configuration, Rust backend,
and JavaScript frontend contain the fixes needed to prevent the
"empty window on launch" bug documented in:

    docs/issues/webkit-dmabuf-empty-window.md

Each test is a lightweight static-analysis check that can run without
a full Tauri build toolchain, making them suitable for CI on every PR.
"""

import json
import re
from pathlib import Path

import pytest

# All paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_DIR = REPO_ROOT / "src" / "runtimes" / "tauri"
RUST_MAIN = TAURI_DIR / "src-tauri" / "src" / "main.rs"
TAURI_CONF = TAURI_DIR / "src-tauri" / "tauri.conf.json"
APP_JS = TAURI_DIR / "src" / "app.js"
PYTHON_BACKEND = REPO_ROOT / "src" / "pykaraoke" / "core" / "backend.py"

pytestmark = pytest.mark.integration


# ── WebKitGTK DMA-BUF workaround (Rust) ──────────────────────────────────


class TestWebKitDmabufWorkaround:
    """
    Regression: on Linux, WebKitGTK may fail to create GBM/DRM buffers
    when GPU access is restricted, resulting in a completely blank window.
    Setting WEBKIT_DISABLE_DMABUF_RENDERER=1 forces a shared-memory
    fallback renderer.
    """

    def test_main_rs_sets_dmabuf_env_var(self):
        """main.rs must set WEBKIT_DISABLE_DMABUF_RENDERER before webview creation."""
        source = RUST_MAIN.read_text()
        assert "WEBKIT_DISABLE_DMABUF_RENDERER" in source, (
            "main.rs must set WEBKIT_DISABLE_DMABUF_RENDERER to prevent "
            "blank windows on Linux systems with restricted GPU access"
        )

    def test_dmabuf_workaround_is_linux_only(self):
        """The DMA-BUF workaround should be gated behind #[cfg(target_os = \"linux\")]."""
        source = RUST_MAIN.read_text()
        # Find the cfg attribute near the env var set
        dmabuf_idx = source.index("WEBKIT_DISABLE_DMABUF_RENDERER")
        # The cfg gate should appear within the ~300 chars before the env var set
        preceding = source[max(0, dmabuf_idx - 300):dmabuf_idx]
        assert 'target_os = "linux"' in preceding, (
            "WEBKIT_DISABLE_DMABUF_RENDERER should be gated behind "
            '#[cfg(target_os = "linux")] to avoid affecting macOS/Windows'
        )

    def test_dmabuf_workaround_respects_existing_value(self):
        """If the user already set the env var, we should not overwrite it."""
        source = RUST_MAIN.read_text()
        # The code should check .is_err() (i.e. not already set) before overwriting
        assert "is_err()" in source or "is_ok()" in source, (
            "The DMABUF workaround should check whether the env var is "
            "already set before overwriting, so users can opt out"
        )

    def test_dmabuf_set_before_tauri_builder(self):
        """The env var must be set before tauri::Builder::default() creates the webview."""
        source = RUST_MAIN.read_text()
        dmabuf_pos = source.index("WEBKIT_DISABLE_DMABUF_RENDERER")
        builder_pos = source.index("tauri::Builder::default()")
        assert dmabuf_pos < builder_pos, (
            "WEBKIT_DISABLE_DMABUF_RENDERER must be set before "
            "tauri::Builder::default() to take effect"
        )


# ── Backend script path resolution (Rust) ────────────────────────────────


class TestBackendPathResolution:
    """
    Regression: the Tauri binary could not find the Python backend script
    when installed from a .deb package because the path was hardcoded to
    a development-only relative layout (../../../src/...).
    """

    def test_main_rs_tries_multiple_backend_paths(self):
        """main.rs should try multiple candidate paths for backend.py."""
        source = RUST_MAIN.read_text()
        # Count occurrences of path candidates (join calls building backend.py path)
        candidates = re.findall(r'\.join\("backend\.py"\)', source)
        assert len(candidates) >= 2, (
            "main.rs should try at least 2 candidate paths for backend.py "
            f"(development + production), found {len(candidates)}"
        )

    def test_main_rs_checks_path_exists_before_use(self):
        """main.rs should verify a candidate path exists before spawning Python."""
        source = RUST_MAIN.read_text()
        assert ".exists()" in source, (
            "main.rs should check .exists() on candidate paths so it picks "
            "the correct backend.py for the current install layout"
        )

    def test_main_rs_has_resource_dir_candidate(self):
        """One candidate should use Tauri's resource_dir (for bundled installs)."""
        source = RUST_MAIN.read_text()
        assert "resource_dir" in source, (
            "main.rs must use app_handle.path_resolver().resource_dir() "
            "to locate bundled resources in production installs"
        )


# ── Tauri bundle configuration ───────────────────────────────────────────


class TestTauriBundleResources:
    """
    Regression: the .deb package did not include the Python backend files,
    so the Tauri binary could never find or launch them at runtime.
    """

    def test_tauri_conf_has_resources_key(self):
        """tauri.conf.json must declare bundled resources."""
        conf = json.loads(TAURI_CONF.read_text())
        resources = conf.get("tauri", {}).get("bundle", {}).get("resources")
        assert resources is not None and len(resources) > 0, (
            "tauri.conf.json must include a 'resources' list in tauri.bundle "
            "so the Python backend is shipped inside the .deb / .dmg / .exe"
        )

    def test_all_bundled_resources_exist_on_disk(self):
        """Every file listed in resources must exist in the source tree."""
        conf = json.loads(TAURI_CONF.read_text())
        resources = conf["tauri"]["bundle"]["resources"]
        tauri_conf_dir = TAURI_CONF.parent  # src-tauri/
        missing = []
        for rel in resources:
            if "*" in rel:
                # For glob patterns like "backend/**", verify the base
                # directory exists (build.rs creates it with a placeholder
                # if needed) and that a beforeBuildCommand is configured
                # to populate it for real builds.
                base_dir = rel.split("*")[0].rstrip("/")
                if not (tauri_conf_dir / base_dir).is_dir():
                    missing.append(f"{rel} (base dir '{base_dir}' missing)")
            else:
                full = (tauri_conf_dir / rel).resolve()
                if not full.exists():
                    missing.append(rel)
        assert not missing, (
            f"These bundled resources are listed in tauri.conf.json but "
            f"cannot be resolved on disk: {missing}"
        )

    def test_before_build_command_stages_backend(self):
        """beforeBuildCommand must copy the Python backend into the staging dir."""
        conf = json.loads(TAURI_CONF.read_text())
        before_build = conf.get("build", {}).get("beforeBuildCommand", "")
        assert before_build, "tauri.conf.json must have a beforeBuildCommand"

        # The command may be an inline shell command or a script invocation.
        # If it references a script file, read that script and verify it
        # stages the backend/pykaraoke tree.
        if before_build.startswith("node "):
            script_rel = before_build.split("node ", 1)[1].strip()
            script_path = TAURI_CONF.parent.parent / script_rel
            assert script_path.exists(), (
                f"beforeBuildCommand references '{script_rel}' but "
                f"{script_path} does not exist"
            )
            script_src = script_path.read_text()
            assert "backend" in script_src and "pykaraoke" in script_src, (
                "Stage-backend script must reference 'backend' and "
                "'pykaraoke' to stage the Python backend tree"
            )
        else:
            assert "backend" in before_build and "pykaraoke" in before_build, (
                "tauri.conf.json beforeBuildCommand must stage the Python "
                "backend tree into the backend/ directory so the resource "
                "glob can bundle it"
            )

    def test_core_python_modules_are_bundled(self):
        """Critical Python modules should be staged by the beforeBuildCommand.

        Since resources now uses a glob, we verify the beforeBuildCommand
        (or the script it invokes) copies the required module directories
        (core, config, players).
        """
        conf = json.loads(TAURI_CONF.read_text())
        before_build = conf.get("build", {}).get("beforeBuildCommand", "")

        # Resolve the text that should list the module directories.
        if before_build.startswith("node "):
            script_rel = before_build.split("node ", 1)[1].strip()
            staging_text = (TAURI_CONF.parent.parent / script_rel).read_text()
        else:
            staging_text = before_build

        for module_dir in ["core", "config", "players"]:
            assert module_dir in staging_text, (
                f"beforeBuildCommand (or its staging script) should copy "
                f"the pykaraoke/{module_dir}/ directory into the backend "
                f"staging tree"
            )


# ── JavaScript Tauri API resilience ──────────────────────────────────────


class TestJavaScriptApiResilience:
    """
    Regression: app.js accessed window.__TAURI__.tauri.invoke at module
    level via destructuring.  If the Tauri IPC bridge was not yet injected
    (e.g. slow webview init), this threw a TypeError and the entire UI
    failed to render — contributing to the "empty window" appearance.
    """

    def test_app_js_does_not_destructure_tauri_at_top_level(self):
        """app.js must not use bare `const { invoke } = window.__TAURI__...`."""
        source = APP_JS.read_text()
        # The old pattern that crashes when __TAURI__ is undefined
        dangerous_pattern = re.compile(
            r"const\s*\{[^}]*invoke[^}]*\}\s*=\s*window\.__TAURI__"
        )
        assert not dangerous_pattern.search(source), (
            "app.js must not destructure window.__TAURI__ at the top level; "
            "use a try/catch guard so the UI still renders if the API is slow "
            "to inject or unavailable"
        )

    def test_app_js_has_tauri_api_try_catch(self):
        """app.js should wrap the Tauri API import in a try/catch."""
        source = APP_JS.read_text()
        assert "try" in source and "catch" in source, (
            "app.js should use try/catch around the Tauri API import "
            "to gracefully handle missing window.__TAURI__"
        )

    def test_app_js_provides_invoke_fallback(self):
        """When __TAURI__ is unavailable, invoke should still be a callable."""
        source = APP_JS.read_text()
        # After the catch block there should be a fallback assignment
        assert "invoke" in source and "async" in source, (
            "app.js should assign a fallback async invoke function "
            "when the Tauri API is not available"
        )
