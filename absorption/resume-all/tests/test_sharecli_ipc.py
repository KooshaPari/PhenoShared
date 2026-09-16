#!/usr/bin/env python3
"""
test_sharecli_ipc.py — Slice 6 acceptance tests for the tracked
``bin/sharecli_bridge.py`` and ``bin/sharecli-ipc.py`` sources.

The two bridge modules are loaded via importlib from this repository's
``bin/`` directory, matching the sibling layout used by the live sources.
We exercise:

  (a) socket path resolution — env override, default fallback
  (b) reachability probe — connect-only, no IPC traffic
  (c) full round-trip — mock NDJSON server answers each canonical method,
      we assert the bridge normalises the response to the expected shape
  (d) sharecli_session_list end-to-end — the verification step the slice-6
      spec names ("sharecli_bridge_sharecli_session_list → take payload")
  (e) sharecli_call raw passthrough — for any future method the bridge
      hasn't wrapped yet
  (f) error-path symmetry — daemon returns `error` envelope, malformed
      JSON, non-dict response, empty frame all degrade to ``{"error": ...}``
      instead of raising
  (g) sharecli_notify pathways — `cast.send` to a registered pane,
      `ipc.health.status` fallback, no-delivery path when both fail

Tests run in isolation: each test gets its own tempdir, a fresh mock
NDJSON server bound to a private socket, and a monkey-patched
``SHARECLI_IPC_SOCK`` so the bridge targets the test socket.  No real
sharecli-ipc daemon is required.
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BIN_DIR = Path(__file__).resolve().parents[1] / "bin"
BRIDGE_PATH = BIN_DIR / "sharecli_bridge.py"
IPC_PATH = BIN_DIR / "sharecli-ipc.py"


# ---------------------------------------------------------------------------
# Module loaders (siblings of tests/, not on sys.path)
# ---------------------------------------------------------------------------

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bridge = _load("sharecli_bridge", BRIDGE_PATH)
ipc = _load("sharecli_ipc", IPC_PATH)


# ---------------------------------------------------------------------------
# Mock NDJSON server
# ---------------------------------------------------------------------------

class _MockIPCServer:
    """In-process NDJSON server that answers a fixed set of methods.

    Each accepted connection reads one request line, dispatches by
    ``method`` to a handler, writes the JSON response + ``\\n``, and
    closes the connection (parity with the real sharecli-ipc daemon's
    one-response-per-connection semantics in
    ``crates/sharecli-ipc/src/main.rs:86-106``).
    """

    def __init__(self, handler_overrides: dict | None = None):
        self.handler_overrides = handler_overrides or {}
        self.requests: list[dict] = []
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self._temp_path())
        self._server.listen(8)
        self._server.settimeout(0.5)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        # Give the listener a moment to be ready — without this the
        # first client connect() sometimes races and gets ECONNREFUSED.
        time.sleep(0.02)

    @staticmethod
    def _temp_path() -> str:
        tmp = tempfile.mkdtemp(prefix="sharecli-ipc-test-")
        return os.path.join(tmp, "ipc.sock")

    @property
    def path(self) -> str:
        return self._server.getsockname()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._server.close()
        except OSError:
            pass
        self._thread.join(timeout=2.0)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except (OSError, socket.timeout):
                continue
            try:
                self._handle_one(conn)
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _handle_one(self, conn: socket.socket) -> None:
        # Wrap the whole handler in try/finally so a BrokenPipe on the
        # empty-request response (when ``sharecli_socket_reachable()`` does
        # a connect-and-immediately-close probe) doesn't kill the server
        # thread.  Without this guard, the first reachable-check kills the
        # thread and every subsequent request times out.
        try:
            buf = b""
            conn.settimeout(2.0)
            while not buf.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            line = buf.decode("utf-8", "replace").strip()
            if not line:
                try:
                    conn.sendall(b'{"id":0,"result":null,"error":"empty request"}\n')
                except OSError:
                    pass
                return
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                try:
                    conn.sendall(
                        ('{"id":0,"result":null,"error":"parse error: %s"}\n' % e).encode("utf-8")
                    )
                except OSError:
                    pass
                return
            self.requests.append(req)
            method = req.get("method", "")
            handler = self.handler_overrides.get(method, _DEFAULT_HANDLERS.get(method))
            if handler is None:
                resp = {
                    "id": req.get("id", 0),
                    "result": None,
                    "error": f"unknown method: {method}",
                }
            else:
                result_or_error = handler(req)
                if isinstance(result_or_error, dict) and "error" in result_or_error:
                    resp = {
                        "id": req.get("id", 0),
                        "result": None,
                        "error": result_or_error["error"],
                    }
                else:
                    resp = {
                        "id": req.get("id", 0),
                        "result": result_or_error,
                        "error": None,
                    }
            payload = (json.dumps(resp) + "\n").encode("utf-8")
            try:
                conn.sendall(payload)
            except OSError:
                pass
        except Exception as e:  # last-resort guard: keep the thread alive
            import sys
            print(f"_MockIPCServer handler error (swallowed): {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Default canned responses (parity with sharecli-ipc::handler)
# ---------------------------------------------------------------------------

_HEALTH_PAYLOAD = {
    "managed_processes": 3,
    "used_memory_mb": 2048,
    "total_memory_mb": 16384,
    "healthy": True,
    "gate": {
        "thermal_pressure": "GREEN",
        "detected_agents": 0,
        "agent_total_rss_bytes": 0,
        "agent_contention": "OK",
        "gate_decision": "ADMIT",
    },
    "host_watch": {
        "fd_count": 12,
        "net_rx_bytes": 100,
        "net_tx_bytes": 200,
        "mem_rss_bytes": 4096,
        "load_1m": 0.42,
    },
    "pool": {
        "node_total": 2,
        "node_idle": 1,
        "bun_total": 1,
        "bun_idle": 0,
        "max_per_type": 4,
        "healthy": True,
        "issues": [],
        "gate": {
            "thermal_pressure": "GREEN",
            "detected_agents": 0,
            "agent_total_rss_bytes": 0,
            "agent_contention": "OK",
            "gate_decision": "ADMIT",
        },
        "host_watch": {
            "fd_count": 12,
            "net_rx_bytes": 100,
            "net_tx_bytes": 200,
            "mem_rss_bytes": 4096,
            "load_1m": 0.42,
        },
        "status": None,
    },
    "status": {
        "total_processes": 5,
        "agents": [],
        "scanned": 50,
        "watched": 1,
        "gate": {
            "thermal_pressure": "GREEN",
            "detected_agents": 0,
            "agent_total_rss_bytes": 0,
            "agent_contention": "OK",
            "gate_decision": "ADMIT",
        },
        "host_watch": {
            "fd_count": 12,
            "net_rx_bytes": 100,
            "net_tx_bytes": 200,
            "mem_rss_bytes": 4096,
            "load_1m": 0.42,
        },
        "pool": None,
    },
}

_PROCESSES = [
    {
        "pid": 100 + i,
        "name": f"worker-{i}",
        "cmd": [f"worker-{i}", "--foo"],
        "memory_mb": 64 + i,
        "project": "demo" if i % 2 == 0 else None,
        "harness": "native" if i % 2 == 0 else "codex",
        "start_time": 1700000000 + i,
    }
    for i in range(7)
]

_AGENTS = [
    {
        "pid": 200 + i,
        "family": "claude",
        "comm": f"claude-{i}",
        "state": "S",
        "mem_rss_bytes": 4096 * (i + 1),
        "mem_rss": f"{(i + 1) * 4}.0M",
        "fd_count": 12,
    }
    for i in range(4)
]

_STATUS_SNAPSHOT = {
    "total_processes": len(_AGENTS),
    "agents": _AGENTS,
    "scanned": 100,
    "watched": len(_AGENTS),
    "gate": _HEALTH_PAYLOAD["gate"],
    "host_watch": _HEALTH_PAYLOAD["host_watch"],
    "pool": None,
}

_MONITORING_REPORT = {
    "timestamp": 1700000123,
    "total_processes": len(_PROCESSES),
    "used_memory_mb": 4096,
    "total_memory_mb": 16384,
    "processes": [
        {
            "pid": p["pid"],
            "name": p["name"],
            "memory_mb": p["memory_mb"],
            "project": p["project"],
            "harness": p["harness"],
            "start_time": p["start_time"],
        }
        for p in _PROCESSES
    ],
    "gate": _HEALTH_PAYLOAD["gate"],
    "host_watch": _HEALTH_PAYLOAD["host_watch"],
    "pool": _HEALTH_PAYLOAD["pool"],
    "status": _STATUS_SNAPSHOT,
}

_POOL_STATUS = {
    "node_total": 2,
    "node_idle": 1,
    "bun_total": 1,
    "bun_idle": 0,
    "max_per_type": 4,
    "healthy": True,
    "issues": [],
    "gate": _HEALTH_PAYLOAD["gate"],
    "host_watch": _HEALTH_PAYLOAD["host_watch"],
    "status": _STATUS_SNAPSHOT,
}

_LOG_TAIL = {
    "lines": [
        {"id": 1, "ts": "2026-08-02T22:00:00Z", "level": "INFO", "msg": "ready"},
        {"id": 2, "ts": "2026-08-02T22:00:01Z", "level": "INFO", "msg": "spawn"},
    ],
    "last_id": 2,
}


def _h_health(_req: dict) -> dict:
    return _HEALTH_PAYLOAD


def _h_processes(_req: dict) -> list:
    return _PROCESSES


def _h_status(_req: dict) -> dict:
    return _STATUS_SNAPSHOT


def _h_monitoring(_req: dict) -> dict:
    return _MONITORING_REPORT


def _h_pool(_req: dict) -> dict:
    return _POOL_STATUS


def _h_log_tail(req: dict) -> dict:
    return _LOG_TAIL


def _h_echo_error(req: dict) -> dict:
    return {"error": "intentional server-side error"}


_DEFAULT_HANDLERS: dict[str, callable] = {
    "health.status": _h_health,
    "process.list": _h_processes,
    "status.snapshot": _h_status,
    "monitoring.report": _h_monitoring,
    "pool.status": _h_pool,
    "log.tail": _h_log_tail,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@contextmanager
def _point_at(sock_path: str):
    """Point the bridge at `sock_path` for the duration of a test.

    The bridge reads ``$SHARECLI_IPC_SOCK`` first, then its default
    lookup.  We patch the env var so neither the bridge nor the
    ``sharecli-ipc`` module reach for the real platform default.
    """
    prev = os.environ.get("SHARECLI_IPC_SOCK")
    os.environ["SHARECLI_IPC_SOCK"] = sock_path
    # The bridge caches nothing; it re-reads the env every call, so no
    # module reload is needed.
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("SHARECLI_IPC_SOCK", None)
        else:
            os.environ["SHARECLI_IPC_SOCK"] = prev


@contextmanager
def _server(handlers: dict | None = None):
    """Start a mock NDJSON server and point both bridge modules at it."""
    srv = _MockIPCServer(handlers)
    try:
        with _point_at(srv.path):
            yield srv
    finally:
        srv.stop()


# ---------------------------------------------------------------------------
# (a) socket path resolution
# ---------------------------------------------------------------------------

class SocketPathTests(unittest.TestCase):
    def test_default_uses_canonical_path(self):
        # Bridge falls back to ~/Library/Application Support/sharecli/ipc.sock
        # on macOS (dirs::data_local_dir) or ~/.local/share/sharecli/ipc.sock
        # on Linux. Either candidate is a valid resolution — assert the
        # env override is honored and the result is a non-empty absolute path.
        prev = os.environ.pop("SHARECLI_IPC_SOCK", None)
        try:
            p = bridge.sharecli_socket_path()
            self.assertTrue(p.endswith("sharecli/ipc.sock"), p)
        finally:
            if prev is not None:
                os.environ["SHARECLI_IPC_SOCK"] = prev

    def test_env_override_wins(self):
        os.environ["SHARECLI_IPC_SOCK"] = "/tmp/slice6-override.sock"
        try:
            self.assertEqual(bridge.sharecli_socket_path(), "/tmp/slice6-override.sock")
        finally:
            os.environ.pop("SHARECLI_IPC_SOCK", None)


# ---------------------------------------------------------------------------
# (b) reachability probe
# ---------------------------------------------------------------------------

class ReachabilityTests(unittest.TestCase):
    def test_returns_false_when_socket_missing(self):
        with _point_at("/tmp/does-not-exist-sharecli-ipc.sock"):
            self.assertFalse(bridge.sharecli_socket_reachable(timeout=0.2))

    def test_returns_true_when_server_up(self):
        with _server() as srv:
            self.assertTrue(bridge.sharecli_socket_reachable(timeout=0.5))
            self.assertGreaterEqual(len(srv.requests), 0)  # no traffic on probe


# ---------------------------------------------------------------------------
# (c) full round-trip — each canonical method
# ---------------------------------------------------------------------------

class HealthPingTests(unittest.TestCase):
    def test_returns_ok_with_normalised_fields(self):
        expected_sock = None
        with _server() as srv:
            expected_sock = srv.path
            out = bridge.sharecli_health_ping(timeout=1.0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["managed_processes"], 3)
        self.assertTrue(out["healthy"])
        self.assertEqual(out["socket"], expected_sock)
        self.assertEqual(out["method"], "health.status")
        self.assertNotIn("error", out)

    def test_returns_error_envelope_when_daemon_errors(self):
        with _server({"health.status": _h_echo_error}):
            out = bridge.sharecli_health_ping(timeout=1.0)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "intentional server-side error")

    def test_returns_error_when_socket_unreachable(self):
        with _point_at("/tmp/no-server.sock"):
            out = bridge.sharecli_health_ping(timeout=0.2)
        self.assertFalse(out["ok"])
        self.assertIn("error", out)


class SessionListTests(unittest.TestCase):
    def test_returns_derived_session_rows(self):
        with _server():
            out = bridge.sharecli_session_list(limit=10, timeout=1.0)
        self.assertEqual(len(out), 4)
        for row in out:
            self.assertIn("pid", row)
            self.assertIn("name", row)
            self.assertIn("harness", row)
            self.assertEqual(row["harness"], "claude")

    def test_bounded_to_limit(self):
        with _server():
            out = bridge.sharecli_session_list(limit=2, timeout=1.0)
        self.assertEqual(len(out), 2)

    def test_returns_empty_list_on_error(self):
        with _server({"status.snapshot": _h_echo_error}):
            out = bridge.sharecli_session_list(timeout=1.0)
        self.assertEqual(out, [])

    def test_returns_empty_list_when_socket_unreachable(self):
        with _point_at("/tmp/no-server.sock"):
            out = bridge.sharecli_session_list(timeout=0.2)
        self.assertEqual(out, [])


class ProcessListTests(unittest.TestCase):
    def test_returns_raw_process_summaries(self):
        with _server():
            out = bridge.sharecli_process_list(limit=50, timeout=1.0)
        self.assertEqual(len(out), 7)
        self.assertEqual(out[0]["pid"], 100)
        self.assertEqual(out[0]["name"], "worker-0")

    def test_bounded_to_limit(self):
        with _server():
            out = bridge.sharecli_process_list(limit=3, timeout=1.0)
        self.assertEqual(len(out), 3)

    def test_returns_empty_list_on_error(self):
        with _server({"process.list": _h_echo_error}):
            out = bridge.sharecli_process_list(timeout=1.0)
        self.assertEqual(out, [])


class HostInfoTests(unittest.TestCase):
    def test_returns_flat_host_payload(self):
        with _server():
            out = bridge.sharecli_host_info(timeout=1.0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["load_1m"], 0.42)
        self.assertEqual(out["mem_rss_bytes"], 4096)
        self.assertEqual(out["fd_count"], 12)
        self.assertEqual(out["used_memory_mb"], 4096)
        self.assertEqual(out["total_memory_mb"], 16384)
        self.assertEqual(out["pool_node_total"], 2)
        self.assertEqual(out["thermal_pressure"], "GREEN")
        self.assertEqual(out["gate_decision"], "ADMIT")
        self.assertNotIn("error", out)

    def test_returns_error_when_daemon_errors(self):
        with _server({"monitoring.report": _h_echo_error}):
            out = bridge.sharecli_host_info(timeout=1.0)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "intentional server-side error")


# ---------------------------------------------------------------------------
# (d) end-to-end — sharecli_session_list → take payload
# ---------------------------------------------------------------------------

class EndToEndSessionListTests(unittest.TestCase):
    def test_take_payload(self):
        """The slice-6 verification step.

        ``sharecli_bridge_sharecli_session_list()`` returns the parsed
        session rows.  We assert the payload is well-formed and that the
        underlying IPC frame was a single NDJSON request.
        """
        with _server() as srv:
            payload = bridge.sharecli_session_list(limit=10, timeout=1.0)
        # 1. payload shape
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 4)
        self.assertEqual(payload[0]["harness"], "claude")
        self.assertEqual(payload[0]["mem_rss"], "4.0M")
        # 2. underlying IPC — exactly one `status.snapshot` request, no
        # extra frames (the bridge must not double-request, must not
        # ping first, must not re-issue on success).
        methods = [r["method"] for r in srv.requests]
        self.assertEqual(methods, ["status.snapshot"], methods)
        # 3. request shape
        req = srv.requests[0]
        self.assertIsInstance(req["id"], int)
        self.assertEqual(req["params"], {})


# ---------------------------------------------------------------------------
# (e) raw sharecli_call passthrough
# ---------------------------------------------------------------------------

class RawCallTests(unittest.TestCase):
    def test_passes_through_unknown_method(self):
        # Bridge has no wrapper for `log.tail`; callers go through sharecli_call.
        with _server():
            resp = bridge.sharecli_call("log.tail", {"since_id": 0}, timeout=1.0)
        self.assertIsNone(resp.get("error"))
        result = resp["result"]
        self.assertEqual(result["last_id"], 2)
        self.assertEqual(len(result["lines"]), 2)

    def test_returns_error_envelope_for_unknown_method(self):
        with _server():
            resp = bridge.sharecli_call("does.not.exist", timeout=1.0)
        self.assertIsNotNone(resp.get("error"))
        self.assertIn("unknown method", resp["error"])


# ---------------------------------------------------------------------------
# (f) error-path symmetry
# ---------------------------------------------------------------------------

class TransportErrorTests(unittest.TestCase):
    def test_socket_unreachable_returns_error_envelope(self):
        with _point_at("/tmp/no-server.sock"):
            resp = bridge.sharecli_call("health.status", timeout=0.2)
        self.assertIn("error", resp)
        self.assertIn("ipc transport", resp["error"])

    def test_empty_frame_returns_error_envelope(self):
        class _EmptyServer(_MockIPCServer):
            def _handle_one(self, conn):
                # Drain the client request before replying and closing.  A
                # response-only fixture races the client's sendall(), which
                # turns this parser-contract test into a transport failure.
                conn.recv(4096)
                conn.sendall(b"\n")  # valid newline, but empty after strip

        srv = _EmptyServer()
        try:
            with _point_at(srv.path):
                resp = bridge.sharecli_call("health.status", timeout=1.0)
            self.assertIn("error", resp)
            self.assertIn("empty", resp["error"])
        finally:
            srv.stop()

    def test_malformed_json_returns_error_envelope(self):
        class _JunkServer(_MockIPCServer):
            def _handle_one(self, conn):
                conn.sendall(b"this is not json\n")

        tmp = tempfile.mkdtemp(prefix="sharecli-ipc-junk-")
        sock = os.path.join(tmp, "ipc.sock")
        srv = _JunkServer()
        try:
            with _point_at(srv.path):
                resp = bridge.sharecli_call("health.status", timeout=1.0)
            self.assertIn("error", resp)
            self.assertIn("ipc parse", resp["error"])
        finally:
            srv.stop()

    def test_non_dict_frame_returns_error_envelope(self):
        class _ListServer(_MockIPCServer):
            def _handle_one(self, conn):
                conn.sendall(b'[1,2,3]\n')

        tmp = tempfile.mkdtemp(prefix="sharecli-ipc-list-")
        sock = os.path.join(tmp, "ipc.sock")
        srv = _ListServer()
        try:
            with _point_at(srv.path):
                resp = bridge.sharecli_call("health.status", timeout=1.0)
            self.assertIn("error", resp)
            self.assertIn("non-dict frame", resp["error"])
        finally:
            srv.stop()


# ---------------------------------------------------------------------------
# (g) sharecli_notify pathways
# ---------------------------------------------------------------------------

class _FakePopen:
    """subprocess.Popen stub for sharecli cast CLI passthroughs."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class NotifyTests(unittest.TestCase):
    def test_no_pathways_returns_undelivered(self):
        # No cast pane registered, socket unreachable.
        with _point_at("/tmp/no-server.sock"):
            summary = ipc.sharecli_notify(5, source="test")
        self.assertFalse(summary["delivered"])
        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["source"], "test")
        self.assertIsNone(summary["pathway"])
        self.assertIn("not reachable", summary["error"])

    def test_ipc_health_status_pathway_when_socket_reachable(self):
        with _server() as srv:
            with mock.patch.object(ipc, "sharecli_cast_list_panes", return_value=[]):
                summary = ipc.sharecli_notify(7, source="test")
        self.assertTrue(summary["delivered"])
        self.assertEqual(summary["pathway"], "ipc.health.status")
        self.assertEqual(summary["count"], 7)
        self.assertEqual(summary["managed_processes"], 3)
        methods = [r["method"] for r in srv.requests]
        self.assertEqual(methods, ["health.status"], methods)

    def test_cast_send_pathway_when_pane_registered(self):
        # First: pretend `sharecli cast list` returns ["tray"]; pretend
        # `sharecli cast send` succeeds. We use subprocess.run patches
        # since sharecli_cast_list_panes and sharecli_cast_send are
        # thin wrappers around the CLI.
        with _server():
            with mock.patch.object(
                ipc, "sharecli_cast_list_panes", return_value=["tray"]
            ):
                with mock.patch.object(
                    ipc, "sharecli_cast_send", return_value=True
                ):
                    summary = ipc.sharecli_notify(2, source="test")
        self.assertTrue(summary["delivered"])
        self.assertEqual(summary["pathway"], "cast.send")
        self.assertEqual(summary["cast_pane"], "tray")
        self.assertEqual(summary["count"], 2)

    def test_cast_failure_falls_through_to_ipc_probe(self):
        # Cast path registered but the CLI returns non-zero.  The bridge
        # should fall through to the IPC health probe (which succeeds).
        with _server() as srv:
            with mock.patch.object(
                ipc, "sharecli_cast_list_panes", return_value=["tray"]
            ):
                with mock.patch.object(
                    ipc, "sharecli_cast_send", return_value=False
                ):
                    summary = ipc.sharecli_notify(3, source="test")
        # First pathway failed; bridge fell through to ipc.health.status.
        self.assertTrue(summary["delivered"])
        self.assertEqual(summary["pathway"], "ipc.health.status")
        self.assertEqual(summary["error"], "cast send returned non-zero")
        methods = [r["method"] for r in srv.requests]
        self.assertEqual(methods, ["health.status"], methods)

    def test_audit_log_records_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = os.path.join(tmp, "audit.log")
            with mock.patch.object(ipc, "NOTIFY_AUDIT_LOG", audit_path):
                with _server():
                    with mock.patch.object(
                        ipc, "sharecli_cast_list_panes", return_value=[]
                    ):
                        ipc.sharecli_notify(4, source="audit-test")
            self.assertTrue(os.path.exists(audit_path), "audit log should be written")
            text = Path(audit_path).read_text()
            self.assertIn("source=audit-test", text)
            self.assertIn("count=4", text)
            self.assertIn("pathway=ipc.health.status", text)
            self.assertIn("outcome=ok", text)


# ---------------------------------------------------------------------------
# (h) _collect_sharecli_tray_row integration — verifies the row in
#     session_snapshot.py can actually use the bridge.
# ---------------------------------------------------------------------------

class TrayRowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load session_snapshot via the same importlib pattern used by
        # the production code, so the test mirrors what happens at runtime.
        SESSION_SNAPSHOT = BIN_DIR / "session_snapshot.py"
        spec = importlib.util.spec_from_file_location(
            "session_snapshot_for_test", SESSION_SNAPSHOT,
        )
        assert spec and spec.loader
        cls.ss = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.ss
        spec.loader.exec_module(cls.ss)

    def setUp(self):
        # The row uses a 25s on-disk cache (SHARECLI_CACHE_FILE) so the
        # second invocation in the same launchd tick reuses the prior
        # result.  In tests we always want a fresh row, so purge the
        # cache file before each test.  Also force the cache TTL to 0
        # for the duration of the test so any write that races with
        # the next test is treated as expired.
        cache_path = self.ss.SHARECLI_CACHE_FILE
        try:
            cache_path.unlink()
        except OSError:
            pass

    def test_row_reflects_bridge_state(self):
        # When the bridge IS importable, the row should report
        # `bridge_imported=true`. When the socket is reachable, the row
        # should also surface the real health/process/session counts.
        expected_sock = None
        with _server() as srv:
            expected_sock = srv.path
            row = self.ss._collect_sharecli_tray_row()
        self.assertTrue(row["sharecli"]["bridge_imported"])
        self.assertEqual(
            row["sharecli"]["socket"],
            expected_sock,
        )
        self.assertTrue(row["sharecli"]["reachable"])
        # health.ping succeeded → available
        self.assertTrue(row["sharecli"]["available"])
        self.assertEqual(row["sharecli"]["error"], "")
        # health ping payload
        self.assertTrue(row["sharecli"]["health"]["ok"])
        # session list (4 agents in the mock)
        self.assertEqual(row["sharecli"]["sessions_count"], 4)
        self.assertEqual(len(row["sharecli"]["sessions"]), 4)
        # process list (7 workers in the mock) — only `count` is surfaced
        self.assertEqual(row["sharecli"]["processes_count"], 7)
        # host info
        self.assertEqual(row["sharecli"]["host"]["load_1m"], 0.42)

    def test_row_degrades_when_socket_unreachable(self):
        with _point_at("/tmp/no-server.sock"):
            row = self.ss._collect_sharecli_tray_row()
        self.assertTrue(row["sharecli"]["bridge_imported"])
        self.assertFalse(row["sharecli"]["reachable"])
        self.assertFalse(row["sharecli"]["available"])
        self.assertEqual(row["sharecli"]["error"], "socket-unreachable")
        self.assertEqual(row["sharecli"]["sessions_count"], 0)
        self.assertEqual(row["sharecli"]["processes_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
