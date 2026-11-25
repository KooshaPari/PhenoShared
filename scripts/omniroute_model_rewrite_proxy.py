#!/usr/bin/env python3
"""Rewrite Harbor/litellm model id openai/Main -> Main for OmniRoute."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "http://127.0.0.1:20130"
LISTEN = ("127.0.0.1", 20128)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("[rewrite] " + (fmt % args) + "\n")

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        if body and "chat/completions" in self.path:
            try:
                payload = json.loads(body.decode("utf-8"))
                model = payload.get("model")
                if isinstance(model, str) and model.startswith("openai/"):
                    payload["model"] = model.split("/", 1)[1]
                    body = json.dumps(payload).encode("utf-8")
            except Exception:
                pass
        url = UPSTREAM + self.path
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower()
            not in ("host", "content-length", "transfer-encoding", "connection")
        }
        if body:
            headers["Content-Length"] = str(len(body))
        req = urllib.request.Request(
            url, data=body or None, headers=headers, method=self.command
        )
        try:
            with (
                urllib.request.urlopen(req, timeout=600) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() in (
                        "transfer-encoding",
                        "connection",
                        "content-encoding",
                    ):
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = str(e).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def do_OPTIONS(self) -> None:
        self._proxy()


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(LISTEN, Handler)
    print(f"rewrite proxy {LISTEN[0]}:{LISTEN[1]} -> {UPSTREAM}", flush=True)
    httpd.serve_forever()
