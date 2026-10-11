#!/usr/bin/env python3
"""Serve the PyKaraoke web app for development.

Serve ``src/web/`` (the authoritative frontend root — the same tree that
``tauri.conf.json`` ships via ``frontendDist``) with ``Cache-Control:
no-store`` on every response, so the webview never shows a stale page.
``tauri.conf.json`` runs this as ``beforeDevCommand``; it can also be run
by hand from anywhere in the repo:

    python src/scripts/serve-web.py [port]   (default 18000)

``src/web/_assets`` (Pyodide/PyScript) and ``src/web/_wheel`` (the engine
wheel) must exist before serving; run ``python src/scripts/build-web.py``
first to populate them.
"""

from __future__ import annotations

import http.server
import pathlib
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18000
WEB_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "src" / "web"


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


if __name__ == "__main__":
    # Dev-only static server bound to loopback (127.0.0.1); it serves the same
    # public web assets as `python -m http.server` and carries no secrets, so
    # plain HTTP is intentional. TLS would only add cert management to the
    # tauri.conf.json beforeDevCommand flow. This is a reviewed, accepted
    # use of http.server without TLS (Sonar S5332).
    http.server.ThreadingHTTPServer(  # NOSONAR
        ("127.0.0.1", PORT), NoCacheHandler
    ).serve_forever()
