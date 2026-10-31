"""Serve the Android APKs to phones on the same Wi-Fi, with a simple download page.

Usage: python mobile/tool/serve_downloads.py [port]      (default port 8080, serves release/android)
Then on the phone open http://<this PC's Wi-Fi IP>:8080
"""

import socket
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DOWNLOADS = Path(__file__).resolve().parents[2] / "release" / "android"


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".apk": "application/vnd.android.package-archive"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.0.1", 1))  # no traffic is sent; this just picks the Wi-Fi interface
        return s.getsockname()[0]
    except OSError:
        return "localhost"
    finally:
        s.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=str(DOWNLOADS)))
    print(f"DerMedics downloads: open http://{lan_ip()}:{port} on your phone (same Wi-Fi)", flush=True)
    server.serve_forever()
