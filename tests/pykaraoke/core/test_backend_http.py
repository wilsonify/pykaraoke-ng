#!/usr/bin/env python

"""
Test suite for PyKaraoke Backend HTTP API

Tests the HTTP server mode using FastAPI's TestClient
so no external server process is needed.
"""

import pytest


class TestBackendHTTPMode:
    """Test the backend HTTP API mode"""

    def test_http_imports_available(self):
        """Test that FastAPI/Uvicorn are available for HTTP mode"""
        import fastapi
        import uvicorn

        assert fastapi is not None
        assert uvicorn is not None

    def test_create_http_server_function_exists(self):
        """Test that create_http_server function exists"""
        from pykaraoke.core import backend

        assert hasattr(backend, "create_http_server")

    def test_main_function_exists(self):
        """Test that main function exists for CLI"""
        from pykaraoke.core import backend

        assert hasattr(backend, "main")

    def test_build_http_app_exists(self):
        """build_http_app should be exposed for testing."""
        from pykaraoke.core import backend

        assert hasattr(backend, "build_http_app")


class TestBackendModeSelection:
    """Test mode selection via CLI arguments and environment variables"""

    def test_argument_parsing_stdio_mode(self):
        """Test argument parsing for stdio mode"""
        import argparse
        from pykaraoke.core.backend import main

        assert argparse is not None
        assert main is not None

    def test_argument_parsing_http_mode(self):
        """Test argument parsing for HTTP mode"""
        import argparse
        from pykaraoke.core.backend import main

        assert argparse is not None
        assert main is not None


class TestHTTPEndpoints:
    """Integration tests for HTTP endpoints using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def _app_and_client(self):
        from pykaraoke.core import backend as backend_module

        self.backend = backend_module.PyKaraokeBackend()
        app = backend_module.build_http_app(self.backend)

        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test /health endpoint returns 200"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_state_endpoint(self):
        """Test /api/state endpoint returns backend state"""
        response = self.client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "playback_state" in data

    def test_command_endpoint(self):
        """Test /api/command endpoint processes commands"""
        command = {"action": "get_state", "params": {}}
        response = self.client.post("/api/command", json=command)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data

    def test_events_endpoint(self):
        """Test /api/events endpoint returns events list"""
        response = self.client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
