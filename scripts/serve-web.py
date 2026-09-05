#!/usr/bin/env python3
"""Serve the PyKaraoke web app for development.

Same as ``python -m http.server`` but with ``Cache-Control: no-store`` on
every response, so the webview never shows a stale (pre-rewrite) page.

Usage: python scripts/serve-web.py [port]   (default 18000)
"""

from __future__ import annotations

import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18000


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="web", **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), NoCacheHandler).serve_forever()