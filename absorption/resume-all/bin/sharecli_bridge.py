#!/usr/bin/env python3
"""
sharecli_bridge.py — minimal Python client for the sharecli-ipc UNIX socket.

This is a *client-only* module: import it, call its functions, no CLI surface.
The companion daemon (`sharecli-ipc`) listens on a UNIX domain socket and
serves newline-delimited JSON (NDJSON) requests. Each request is a single
JSON object terminated by ``\\n``; the server replies with one
JSON object per request, also newline-terminated, on the same connection.

Wire format (canonical, per
``/Users/kooshapari/CodeProjects/Phenotype/repos/sharecli/crates/sharecli-ipc/src/main.rs:7-9``):

    Protocol: newline-delimited JSON (NDJSON).
    Request:  {"id": N, "method": "...", "params": {...}}
    Response: {"id": N, "result": ..., "error": null}
              {"id": N, "result": null, "error": "..."}

.. note::
   Some prior clients describe the wire as "length-prefixed". That is NOT the
   canonical sharecli-ipc wire format — the daemon reads lines, not length
   prefixes, and writes one line per response. This client uses NDJSON so it
   actually works against the live server. Verified end-to-end against
   ``sharecli-ipc`` built from ``sharecli/target/release/sharecli-ipc``.

Socket path resolution
~~~~~~~~~~~~~~~~~~~~~~
The daemon's ``socket_path()`` (in ``main.rs:116-122``) picks:

    1. ``$SHARECLI_IPC_SOCK`` env var (overrides everything)
    2. ``dirs::data_local_dir() + sharecli/ipc.sock``

``dirs::data_local_dir()`` returns:
    * macOS:   ``~/Library/Application Support/sharecli/ipc.sock``
    * Linux:   ``~/.local/share/sharecli/ipc.sock``

We mirror that resolution exactly, but probe both portable paths on macOS so
operators who set the Linux-style path (``~/.local/share/sharecli/ipc.sock``)
also work without a manual ``SHARECLI_IPC_SOCK`` override.

Public API
~~~~~~~~~~
* :func:`sharecli_socket_path`     — resolved UNIX socket path
* :func:`sharecli_socket_reachable` — connect-probe (no IPC traffic)
* :func:`sharecli_call`             — raw NDJSON request / response
* :func:`sharecli_health_ping`      — ``health.ping`` (wraps ``health.status``)
* :func:`sharecli_process_list`     — ``process.list`` (bounded, defaults to 50)
* :func:`sharecli_session_list`     — ``session.list`` (derives from
                                      ``status.snapshot.agents``)
* :func:`sharecli_host_info`        — ``host.info`` (derives from
                                      ``monitoring.report``)
"""
from __future__ import annotations

import json
import os
import socket
import time
import uuid
from typing import Any

__all__ = [
    "DEFAULT_SOCKET_PATHS",
    "sharecli_socket_path",
    "sharecli_socket_reachable",
    "sharecli_call",
    "sharecli_health_ping",
    "sharecli_process_list",
    "sharecli_session_list",
    "sharecli_host_info",
]

# ---------------------------------------------------------------------------
# Socket path resolution
# ---------------------------------------------------------------------------

# Ordered candidate list. The daemon's `dirs::data_local_dir()` returns one of
# these depending on the platform; we probe all of them so a symlink or a
# misconfigured install still finds a live socket.
DEFAULT_SOCKET_PATHS: tuple[str, ...] = (
    # macOS canonical (the dirs crate's data_local_dir() on Darwin).
    os.path.expanduser("~/Library/Application Support/sharecli/ipc.sock"),
    # Linux canonical (the dirs crate's data_local_dir() on Linux), and the
    # path the slice-6 task spec names. On macOS this is the user-requested
    # location — it only resolves if the operator has wired the daemon to it
    # via $SHARECLI_IPC_SOCK or a symlink.
    os.path.expanduser("~/.local/share/sharecli/ipc.sock"),
)


def sharecli_socket_path() -> str:
    """Return the resolved sharecli-ipc UNIX socket path.

    Order:
        1. ``$SHARECLI_IPC_SOCK`` env var (parity with the daemon's
           ``socket_path()`` in ``main.rs:116-122``).
        2. First existing entry in :data:`DEFAULT_SOCKET_PATHS`.
        3. The macOS canonical default (so callers always get a path string,
           even if the daemon isn't running).
    """
    env = os.environ.get("SHARECLI_IPC_SOCK")
    if env:
        return env
    for candidate in DEFAULT_SOCKET_PATHS:
        if os.path.exists(candidate):
            return candidate
    # Neither path exists — return the first (macOS canonical) so callers can
    # log the expected location. `sharecli_socket_reachable` will report False.
    return DEFAULT_SOCKET_PATHS[0]


def sharecli_socket_reachable(timeout: float = 0.5) -> bool:
    """Return True iff ``sharecli_socket_path()`` connects.

    Connect-only probe. No IPC traffic — safe to call from any context.
    """
    path = sharecli_socket_path()
    if not os.path.exists(path):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(path)
        return True
    except (OSError, socket.error):
        return False


# ---------------------------------------------------------------------------
# Core NDJSON request / response
# ---------------------------------------------------------------------------

def sharecli_call(
    method: str,
    params: dict | None = None,
    timeout: float = 5.0,
) -> dict:
    """Send a single NDJSON request to the sharecli-ipc socket and return
    the parsed response dict.

    Wire format: ``{"id": N, "method": "...", "params": {...}}\\n``.
    The server replies with one JSON object per request, also newline
    terminated. We read until the trailing newline (or EOF). Large
    envelopes (e.g. ``status.snapshot`` with all agents) can exceed 64 KiB,
    so we loop on ``recv()`` until we see the newline.

    Transport errors are returned as ``{"error": "..."}`` dicts so callers
    can branch without an exception — matches the convention used by the
    other sharecli clients in this repo.
    """
    req_id = uuid.uuid4().int & 0xFFFFFFFF
    payload = {"id": req_id, "method": method, "params": params or {}}
    line = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")

    path = sharecli_socket_path()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect(path)
        sock.sendall(line)
        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if buf.endswith(b"\n"):
                break
    except (OSError, socket.error, socket.timeout) as exc:
        return {"id": req_id, "result": None, "error": f"ipc transport: {exc}"}
    finally:
        try:
            sock.close()
        except OSError:
            pass

    if not buf.strip():
        return {"id": req_id, "result": None, "error": "ipc: empty response"}
    try:
        resp = json.loads(buf.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"id": req_id, "result": None, "error": f"ipc parse: {exc}"}
    if not isinstance(resp, dict):
        return {"id": req_id, "result": None, "error": f"ipc: non-dict frame {type(resp).__name__}"}
    resp.setdefault("id", req_id)
    return resp


# ---------------------------------------------------------------------------
# User-facing methods (the four the slice-6 spec asks for)
# ---------------------------------------------------------------------------

def sharecli_health_ping(timeout: float = 5.0) -> dict:
    """``health.ping`` — lightweight liveness check.

    The sharecli-ipc schema exposes ``health.status`` (handler.rs:410) as its
    health probe. There is no ``health.ping`` method on the wire; this is a
    thin alias that calls ``health.status`` and normalises the response to a
    flat ``{ok, managed_processes, healthy, ts}`` shape suitable for the
    snapshot's availability row.

    Returns ``{"ok": False, "error": "..."}`` on transport or daemon error.
    """
    resp = sharecli_call("health.status", timeout=timeout)
    out: dict[str, Any] = {
        "ok": False,
        "managed_processes": None,
        "healthy": None,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "socket": sharecli_socket_path(),
        "method": "health.status",
    }
    if not isinstance(resp, dict) or resp.get("error") is not None:
        out["error"] = (resp or {}).get("error", "unknown")
        return out
    result = resp.get("result") or {}
    if isinstance(result, dict):
        out["managed_processes"] = result.get("managed_processes")
        out["healthy"] = result.get("healthy")
    out["ok"] = True
    return out


def sharecli_process_list(limit: int = 50, timeout: float = 5.0) -> list[dict]:
    """``process.list`` — list managed processes, bounded to ``limit``.

    The canonical ``process.list`` method (handler.rs:390) returns the full
    ``Vec<ProcessSummary>``. The slice-6 spec asks for a *bounded* result,
    so we slice the response client-side. ``limit <= 0`` returns the full
    list (useful when the caller knows the count is small).

    Returns an empty list on any transport or daemon error so callers can
    report ``"0 processes"`` instead of crashing.
    """
    resp = sharecli_call("process.list", timeout=timeout)
    if not isinstance(resp, dict) or resp.get("error") is not None:
        return []
    result = resp.get("result")
    if not isinstance(result, list):
        return []
    if limit and limit > 0:
        return list(result[:limit])
    return list(result)


def sharecli_session_list(limit: int = 50, timeout: float = 5.0) -> list[dict]:
    """``session.list`` — list detected agent sessions.

    The sharecli-ipc schema does NOT expose a ``session.list`` method (the
    canonical session RPC lives in the separate ``sharecli-session`` crate's
    ``rpc.rs`` on a different socket). We derive the session view here from
    ``status.snapshot`` (handler.rs:442), whose ``agents`` field is the
    authoritative list of detected agent processes — exactly what the
    snapshotter wants for a "session" row.

    Each row is normalised to a small dict with the fields the snapshot
    cares about: ``pid``, ``comm``/``name``, ``family``/``harness``,
    ``state``, ``mem_rss_bytes``, ``mem_rss``, ``session_id`` (best-effort).
    """
    resp = sharecli_call("status.snapshot", timeout=timeout)
    if not isinstance(resp, dict) or resp.get("error") is not None:
        return []
    result = resp.get("result") or {}
    if not isinstance(result, dict):
        return []
    agents = result.get("agents") or []
    if not isinstance(agents, list):
        return []
    out: list[dict] = []
    for a in agents:
        if not isinstance(a, dict):
            continue
        out.append({
            "pid": a.get("pid"),
            "name": a.get("comm") or a.get("name") or "",
            "harness": a.get("family") or a.get("harness") or "",
            "state": a.get("state") or "",
            "mem_rss": a.get("mem_rss") or "",
            "mem_rss_bytes": a.get("mem_rss_bytes"),
            "session_id": a.get("session_id") or a.get("id") or "",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    if limit and limit > 0:
        return out[:limit]
    return out


def sharecli_host_info(timeout: float = 5.0) -> dict:
    """``host.info`` — host-level resource snapshot.

    The sharecli-ipc schema does NOT expose a ``host.info`` method. We
    derive the host view from ``monitoring.report`` (handler.rs:538) which
    returns the union of ``host_watch`` (load, mem, net, fd), pool and
    status siblings, plus the ``used_memory_mb``/``total_memory_mb``
    scalars. The result is normalised to a flat dict for the snapshot row.

    Returns ``{"ok": False, "error": "..."}`` on transport or daemon error.
    """
    resp = sharecli_call("monitoring.report", timeout=timeout)
    out: dict[str, Any] = {
        "ok": False,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "socket": sharecli_socket_path(),
        "method": "monitoring.report",
    }
    if not isinstance(resp, dict) or resp.get("error") is not None:
        out["error"] = (resp or {}).get("error", "unknown")
        return out
    result = resp.get("result") or {}
    if not isinstance(result, dict):
        out["error"] = "non-dict result"
        return out

    hw = result.get("host_watch") or {}
    if isinstance(hw, dict):
        out["load_1m"] = hw.get("load_1m")
        out["mem_rss_bytes"] = hw.get("mem_rss_bytes")
        out["fd_count"] = hw.get("fd_count")
        out["net_rx_bytes"] = hw.get("net_rx_bytes")
        out["net_tx_bytes"] = hw.get("net_tx_bytes")

    out["used_memory_mb"] = result.get("used_memory_mb")
    out["total_memory_mb"] = result.get("total_memory_mb")
    out["total_processes"] = result.get("total_processes")

    pool = result.get("pool") or {}
    if isinstance(pool, dict):
        out["pool_healthy"] = pool.get("healthy")
        out["pool_node_total"] = pool.get("node_total")
        out["pool_node_idle"] = pool.get("node_idle")
        out["pool_bun_total"] = pool.get("bun_total")
        out["pool_bun_idle"] = pool.get("bun_idle")

    gate = result.get("gate") or {}
    if isinstance(gate, dict):
        out["thermal_pressure"] = gate.get("thermal_pressure")
        out["gate_decision"] = gate.get("gate_decision")

    out["ok"] = True
    return out
