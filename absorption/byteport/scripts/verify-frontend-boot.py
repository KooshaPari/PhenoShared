#!/usr/bin/env python3
"""Probe server: proves BytePort's SvelteKit frontend actually booted.

If the Tauri window were still blank, no JS would run and no request would
arrive here. A hit on /authenticate proves the root route mounted and its
onMount logic executed.
"""

import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# S5443: never write to a fixed path in a shared temp dir — mkstemp creates
# this log with mode 0600 in a private, unpredictable name.
_fd, LOG = tempfile.mkstemp(prefix="byteport-boot-probe-", suffix=".log")
os.close(_fd)


def record(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        # Wildcard is invalid alongside credentials; reflect what was asked for.
        requested = self.headers.get("Access-Control-Request-Headers")
        self.send_header(
            "Access-Control-Allow-Headers", requested or "Content-Type,Authorization"
        )

    def do_OPTIONS(self) -> None:  # noqa: N802
        record(f"OPTIONS {self.path} origin={self.headers.get('Origin')}")
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        record(f"GET {self.path} ua={self.headers.get('User-Agent', '')[:40]}")
        body = json.dumps({"User": {"id": "probe", "name": "probe"}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        # Override: silence BaseHTTPRequestHandler's default stderr access
        # log so probe output stays the single readiness line.
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("")
    print(f"probe server listening on {port}", flush=True)
    # Loopback-only probe: plain HTTP is the protocol under test.
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()  # NOSONAR
