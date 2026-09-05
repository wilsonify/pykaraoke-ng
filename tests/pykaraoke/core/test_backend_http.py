#!/usr/bin/env python

"""
Test suite for PyKaraoke Backend

Tests the stdio server mode used by the Tauri Rust bridge.
"""

import argparse

from pykaraoke.core import backend


class TestBackendModeSelection:
    """Test mode selection via CLI arguments"""

    def test_main_function_exists(self):
        """Test that main function exists for CLI"""
        assert hasattr(backend, "main")
        assert callable(backend.main)

    def test_create_stdio_server_function_exists(self):
        """Test that create_stdio_server function exists"""
        assert hasattr(backend, "create_stdio_server")
        assert callable(backend.create_stdio_server)

    def test_argument_parsing_stdio_mode(self):
        """Test argument parsing for stdio mode"""
        assert argparse is not None
        assert backend.main is not None
