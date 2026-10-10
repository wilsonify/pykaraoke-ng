#!/usr/bin/env python3
"""Serve the PyKaraoke web app for development.

Same as ``python -m http.server`` but with ``Cache-Control: no-store`` on
every response, so the webview never shows a stale (pre-rewrite) page.
``tauri.conf.json`` runs this as ``beforeDevCommand``; it can also be run
by hand from anywhere in the repo:

    python src/scripts/serve-web.py [port]   (default 18000)
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
    # tauri.conf.json beforeDevCommand flow. NOSONAR documents that this is a
    # reviewed, accepted use of http.server (S5332).
    http.server.ThreadingHTTPServer(  # NOSONAR S5332
        ("127.0.0.1", PORT), NoCacheHandler
    ).serve_forever()
