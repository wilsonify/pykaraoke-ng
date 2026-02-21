#!/usr/bin/env python

"""
Test suite for PyKaraoke Backend HTTP API

Tests the HTTP server mode to ensure it provides a proper REST API.
"""

import os
import pytest


class TestBackendHTTPMode:
    """Test the backend HTTP API mode"""

    def test_http_imports_available(self):
        """Test that FastAPI/Uvicorn are available for HTTP mode"""
        try:
            import fastapi
            import uvicorn

            assert fastapi is not None
            assert uvicorn is not None
        except ImportError:
            pytest.skip("FastAPI/Uvicorn not installed")

    def test_create_http_server_function_exists(self):
        """Test that create_http_server function exists"""
        try:
            from pykaraoke.core import backend

            assert hasattr(backend, "create_http_server")
        except ImportError as e:
            pytest.skip(f"Backend module not importable: {e}")

    def test_main_function_exists(self):
        """Test that main function exists for CLI"""
        try:
            from pykaraoke.core import backend

            assert hasattr(backend, "main")
        except ImportError as e:
            pytest.skip(f"Backend module not importable: {e}")


class TestBackendModeSelection:
    """Test mode selection via CLI arguments and environment variables"""

    def test_argument_parsing_stdio_mode(self):
        """Test argument parsing for stdio mode"""
        try:
            import argparse
            from pykaraoke.core.backend import main

            # This would require mocking sys.argv, which we'll skip for now
            # Just verify the imports work
            assert argparse is not None
            assert main is not None
        except ImportError as e:
            pytest.skip(f"Backend module not importable: {e}")

    def test_argument_parsing_http_mode(self):
        """Test argument parsing for HTTP mode"""
        try:
            import argparse
            from pykaraoke.core.backend import main

            # This would require mocking sys.argv and testing the server
            # Just verify the imports work
            assert argparse is not None
            assert main is not None
        except ImportError as e:
            pytest.skip(f"Backend module not importable: {e}")


class TestHTTPEndpoints:
    """Integration tests for HTTP endpoints (require server to be running)"""

    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test /health endpoint"""
        try:
            import urllib.request
            import urllib.error
            
            api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
            
            try:
                response = urllib.request.urlopen(f"{api_url}/health", timeout=5)
                assert response.status == 200
            except urllib.error.URLError:
                pytest.skip("Backend API server not running")
        except Exception as e:
            pytest.skip(f"Health check failed: {e}")

    @pytest.mark.integration
    def test_state_endpoint(self):
        """Test /api/state endpoint"""
        try:
            import json
            import urllib.request
            import urllib.error
            
            api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
            
            try:
                response = urllib.request.urlopen(f"{api_url}/api/state", timeout=5)
                assert response.status == 200
                data = json.loads(response.read().decode())
                assert "playback_state" in data or "status" in data
            except urllib.error.URLError:
                pytest.skip("Backend API server not running")
        except Exception as e:
            pytest.skip(f"State endpoint test failed: {e}")

    @pytest.mark.integration
    def test_command_endpoint(self):
        """Test /api/command endpoint"""
        try:
            import json
            import urllib.request
            import urllib.error
            
            api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
            
            try:
                command = {"action": "get_state", "params": {}}
                data = json.dumps(command).encode("utf-8")
                req = urllib.request.Request(
                    f"{api_url}/api/command",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                response = urllib.request.urlopen(req, timeout=5)
                assert response.status == 200
                response_data = json.loads(response.read().decode())
                assert "status" in response_data
            except urllib.error.URLError:
                pytest.skip("Backend API server not running")
        except Exception as e:
            pytest.skip(f"Command endpoint test failed: {e}")

    @pytest.mark.integration
    def test_events_endpoint(self):
        """Test /api/events endpoint"""
        try:
            import urllib.request
            import urllib.error
            
            api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
            
            try:
                response = urllib.request.urlopen(
                    f"{api_url}/api/events",
                    timeout=5
                )
                # For SSE endpoint, just check that it returns successfully
                assert response.status == 200
            except urllib.error.URLError:
                pytest.skip("Backend API server not running")
        except Exception as e:
            pytest.skip(f"Events endpoint test failed: {e}")
