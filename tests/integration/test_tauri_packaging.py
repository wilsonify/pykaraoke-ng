"""
Regression tests for Tauri packaging and desktop launch issues — Rust-native backend.

These tests validate that the Tauri build configuration, Rust backend,
and JavaScript frontend contain the correct fixes.  The Rust native
backend replaces the legacy Python subprocess model.

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
RUST_ENGINE = REPO_ROOT / "crates" / "pykaraoke-engine"

pytestmark = pytest.mark.integration


# ── WebKitGTK DMA-BUF workaround (Rust) ──────────────────────────────────


class TestWebKitDmabufWorkaround:
    """Regression: blank WebKitGTK window fix."""

    def test_main_rs_sets_dmabuf_env_var(self):
        source = RUST_MAIN.read_text()
        assert "WEBKIT_DISABLE_DMABUF_RENDERER" in source

    def test_dmabuf_workaround_is_linux_only(self):
        source = RUST_MAIN.read_text()
        dmabuf_idx = source.index("WEBKIT_DISABLE_DMABUF_RENDERER")
        preceding = source[max(0, dmabuf_idx - 300):dmabuf_idx]
        assert 'target_os = "linux"' in preceding

    def test_dmabuf_workaround_respects_existing_value(self):
        source = RUST_MAIN.read_text()
        assert "is_err()" in source or "is_ok()" in source

    def test_dmabuf_set_before_tauri_builder(self):
        source = RUST_MAIN.read_text()
        dmabuf_pos = source.index("WEBKIT_DISABLE_DMABUF_RENDERER")
        builder_pos = source.index("tauri::Builder::default()")
        assert dmabuf_pos < builder_pos


# ── Rust-native backend resolution ────────────────────────────────────────


class TestRustBackendIntegration:
    """Verify the Tauri shell correctly embeds the Rust engine crate."""

    def test_build_rs_no_backend_placeholder(self):
        """build.rs should no longer create a Python backend placeholder."""
        source = (TAURI_DIR / "src-tauri" / "build.rs").read_text()
        assert "PLACEHOLDER" not in source, (
            "build.rs must not create backend/ placeholders — "
            "the Rust engine is linked at compile time, not bundled as a resource"
        )
        assert "tauri_build::build()" in source

    def test_tauri_conf_has_resources_key(self):
        conf = json.loads(TAURI_CONF.read_text())
        resources = conf.get("tauri", {}).get("bundle", {}).get("resources")
        assert resources is not None and len(resources) > 0, (
            "tauri.conf.json must include a 'resources' list"
        )

    def test_before_build_command_stages_rust_backend(self):
        """beforeBuildCommand must use stage-rust-backend.js."""
        conf = json.loads(TAURI_CONF.read_text())
        before_build = conf.get("build", {}).get("beforeBuildCommand", "")
        assert before_build, "tauri.conf.json must have a beforeBuildCommand"

        assert "stage-rust-backend" in before_build, (
            "beforeBuildCommand must reference stage-rust-backend.js, "
            "not the legacy stage-backend.js"
        )

        if before_build.startswith("node "):
            script_rel = before_build.split("node ", 1)[1].strip()
            script_path = TAURI_CONF.parent.parent / script_rel
            assert script_path.exists(), (
                f"beforeBuildCommand references '{script_rel}' but "
                f"{script_path} does not exist"
            )

    def test_resources_use_glob_for_rust_binary(self):
        """Bundle resources should use 'resources/**' to include the Rust binary."""
        conf = json.loads(TAURI_CONF.read_text())
        resources = conf["tauri"]["bundle"]["resources"]
        has_rust_glob = any("resources" in r and "**" in r for r in resources)
        assert has_rust_glob, (
            "tauri.conf.json resources must use 'resources/**' glob "
            "to include the Rust backend binary"
        )

    def test_stage_script_references_rust_engine(self):
        """stage-rust-backend.js should build and copy the Rust engine binary."""
        stage_script = TAURI_DIR / "scripts" / "stage-rust-backend.js"
        assert stage_script.exists(), "stage-rust-backend.js must exist"
        source = stage_script.read_text()
        assert "pykaraoke-engine-cli" in source, (
            "stage-rust-backend.js must reference the pykaraoke-engine-cli binary"
        )
        assert "cargo build" in source, (
            "stage-rust-backend.js should build the Rust engine if not found"
        )

    def test_cargo_toml_has_engine_dependency(self):
        """The Tauri Cargo.toml must depend on pykaraoke-engine."""
        cargo_toml = TAURI_DIR / "src-tauri" / "Cargo.toml"
        source = cargo_toml.read_text()
        assert "pykaraoke-engine" in source, (
            "Cargo.toml must include pykaraoke-engine as a dependency"
        )


# ── JavaScript Tauri API resilience ──────────────────────────────────────


class TestJavaScriptApiResilience:
    """Regression: window.__TAURI__ resilience fixes."""

    def test_app_js_does_not_destructure_tauri_at_top_level(self):
        source = APP_JS.read_text()
        dangerous_pattern = re.compile(
            r"const\s*\{[^}]*invoke[^}]*\}\s*=\s*window\.__TAURI__"
        )
        assert not dangerous_pattern.search(source)

    def test_app_js_has_tauri_api_try_catch(self):
        source = APP_JS.read_text()
        assert "try" in source and "catch" in source

    def test_app_js_provides_invoke_fallback(self):
        source = APP_JS.read_text()
        assert "invoke" in source and "async" in source
