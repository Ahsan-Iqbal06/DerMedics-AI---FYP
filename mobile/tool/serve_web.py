"""Serve the Flutter web release build locally with caching disabled, so every rebuild shows up on reload.

Usage: python tool/serve_web.py [port]   (serves mobile/build/web to this PC and phones on the same Wi-Fi)
"""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "build" / "web"


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    server = ThreadingHTTPServer(("0.0.0.0", port), partial(NoCacheHandler, directory=str(WEB_DIR)))
    print(f"Serving {WEB_DIR} on http://localhost:{port} (and http://<this PC's Wi-Fi IP>:{port})")
    server.serve_forever()
