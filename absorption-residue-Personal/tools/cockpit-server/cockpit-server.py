#!/opt/homebrew/bin/python3
"""Serve the cockpit dashboards directory on 127.0.0.1:8791.

Uses a threading server on purpose. The stdlib single-threaded
`http.server` blocks every other client on one stuck connection, and a
cockpit that answers no requests is worse than no cockpit at all.
"""
import os
import socketserver
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.expanduser("~/.local/share/resume-all/dashboards")
PORT = int(os.environ.get("COCKPIT_PORT", "8791"))
BIND = os.environ.get("COCKPIT_BIND", "127.0.0.1")


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        # http.server's server_bind calls socket.getfqdn(), a reverse DNS
        # lookup. Under launchd that lookup can stall and the listening socket
        # is never created, so the service looks "running" forever while never
        # accepting a connection. Skip the lookup and bind directly.
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        # /health must answer without touching the dashboards directory.
        # A health endpoint that does real work cannot distinguish a live
        # server from a wedged one: both time out.
        if self.path.split("?")[0] in ("/health", "/api/health"):
            body = b'{"status":"ok","service":"cockpit"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    os.chdir(ROOT)
    server = Server((BIND, PORT), partial(Handler, directory=ROOT))
    print(f"cockpit serving {ROOT} on http://{BIND}:{PORT}", flush=True)
    server.serve_forever()
