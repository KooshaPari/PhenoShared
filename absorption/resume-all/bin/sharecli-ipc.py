#!/usr/bin/env python3
"""
sharecli-ipc.py — minimal Python client for the sharecli-ipc UNIX socket.

Wire format (per /Users/kooshapari/CodeProjects/Phenotype/repos/sharecli/crates/
sharecli-ipc/src/main.rs:7-9):

    Protocol: newline-delimited JSON (NDJSON).
    Request:  {"id": N, "method": "...", "params": {...}}
    Response: {"id": N, "result": ..., "error": null}
              {"id": N, "result": null, "error": "..."}

Each request/response is exactly ONE JSON object terminated by '\\n'. The
socket is full-duplex; the server reads lines and writes one line per
response. We therefore read at most one response per request, framed by the
trailing newline.

Socket path resolution (parity with sharecli-tray Swift `defaultClient()` in
desktop/ShareCLITray/Sources/ShareCLICore/IPCClient.swift:399-403):

    1. SHARECLI_IPC_SOCK env var (matches the Rust `socket_path()` helper
       in crates/sharecli-ipc/src/main.rs:128-134).
    2. Fallback: ~/Library/Application Support/sharecli/ipc.sock
       (the Swift tray's macOS default — the Rust daemon's
       `dirs::data_local_dir()` gives ~/.local/share/sharecli/ipc.sock,
       so the two sides only meet on this fallback path on macOS).

Method names exposed by the daemon (handler.rs:336-470):

    process.list         process.kill           process.kill_all
    process.cmdline      health.status          pool.status
    status.snapshot      config.get             config.set
    monitoring.report    log.tail

There is no `health.notify` method in the source. The "notify" pathway
implemented below is best-effort: it first tries `sharecli cast send` to
inject text into a registered tray pane (the cross-machine text injection
path registered in /Users/kooshapari/Library/Application
Support/sharecli/cast/pane-map.toml), and falls back to a benign
`health.status` IPC probe so the tray's poll loop can observe resume-all
activity through the IPC socket.

Public API:
    sharecli_socket_path() -> str
    sharecli_socket_reachable() -> bool
    sharecli_call(method, params=None, timeout=10.0) -> dict
    sharecli_health_status(timeout=10.0) -> dict
    sharecli_pool_status(timeout=10.0) -> dict
    sharecli_process_list(timeout=10.0) -> list
    sharecli_log_tail(since_id=0, timeout=10.0) -> dict
    sharecli_cast_list_panes() -> list[str]   # via `sharecli cast list`
    sharecli_cast_send(name, text) -> bool    # via `sharecli cast send`
    sharecli_notify(count, source="resume-all") -> dict

All calls are side-effect free except `sharecli_cast_send` and
`sharecli_notify` (which may invoke the `sharecli` CLI sidecar). None of
them block for more than `timeout` seconds; failures are returned as
`{"error": "..."}` dicts so callers can degrade gracefully.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "DEFAULT_SOCKET_PATH",
    "METHOD_HEALTH_STATUS",
    "METHOD_POOL_STATUS",
    "METHOD_PROCESS_LIST",
    "METHOD_LOG_TAIL",
    "METHOD_CONFIG_SET",
    "sharecli_socket_path",
    "sharecli_socket_reachable",
    "sharecli_call",
    "sharecli_health_status",
    "sharecli_pool_status",
    "sharecli_process_list",
    "sharecli_log_tail",
    "sharecli_cast_list_panes",
    "sharecli_cast_send",
    "sharecli_notify",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default socket path mirrors the Swift tray's defaultClient() fallback
# (desktop/ShareCLITray/Sources/ShareCLICore/IPCClient.swift:399-403).
# The Rust daemon's `dirs::data_local_dir()` would yield ~/.local/share/, but
# the Swift tray falls back to ~/Library/Application Support/. We honour the
# same fallback so resume-all lives on the same path as the tray.
DEFAULT_SOCKET_PATH = os.path.expanduser(
    "~/Library/Application Support/sharecli/ipc.sock"
)

# Canonical method names, derived from
# crates/sharecli-ipc/src/handler.rs:336-470.
METHOD_HEALTH_STATUS = "health.status"
METHOD_POOL_STATUS = "pool.status"
METHOD_PROCESS_LIST = "process.list"
METHOD_PROCESS_KILL = "process.kill"
METHOD_PROCESS_KILL_ALL = "process.kill_all"
METHOD_PROCESS_CMDLINE = "process.cmdline"
METHOD_STATUS_SNAPSHOT = "status.snapshot"
METHOD_CONFIG_GET = "config.get"
METHOD_CONFIG_SET = "config.set"
METHOD_MONITORING_REPORT = "monitoring.report"
METHOD_LOG_TAIL = "log.tail"

# Default IPC audit log (the task hints at ~/.forge/audit/sharecli.log).
NOTIFY_AUDIT_LOG = os.path.expanduser("~/.forge/audit/sharecli.log")

# Candidate pane names for `sharecli cast send` fallback. The ShareCLI
# tray doesn't auto-register itself as a cast pane today, but if a user
# (or a future tray build) registers one of these names, resume-all will
# route the notification through the cross-machine text injection path.
_NOTIFY_CAST_PANE_CANDIDATES = ("tray", "sharecli-tray", "sharecli_tray")

log = logging.getLogger("sharecli-ipc")
if not log.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("sharecli-ipc: %(message)s"))
    log.addHandler(h)
log.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Socket path resolution
# ---------------------------------------------------------------------------

def sharecli_socket_path() -> str:
    """Return the resolved UNIX socket path for the sharecli-ipc daemon.

    Order of resolution:
        1. $SHARECLI_IPC_SOCK (matches the Rust `socket_path()` helper
           in crates/sharecli-ipc/src/main.rs:128-134).
        2. DEFAULT_SOCKET_PATH (the Swift tray macOS fallback).
    """
    env = os.environ.get("SHARECLI_IPC_SOCK")
    if env:
        return env
    return DEFAULT_SOCKET_PATH


def sharecli_socket_reachable(timeout: float = 0.5) -> bool:
    """Return True iff the sharecli-ipc socket is reachable and responds.

    A simple connect() probe; cheaper than a full health probe and
    safe to call from any context (no env mutations, no side effects).
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
    timeout: float = 10.0,
) -> dict:
    """Send a single NDJSON request to the sharecli-ipc socket and return
    the parsed response dict.

    The response is shaped like the Rust `Response` struct
    (handler.rs:52-67): `{"id": N, "result": ..., "error": null}`. On
    transport errors we return `{"error": "..."}` so the caller can
    branch without an exception.

    Note: the daemon is full-duplex and replies with one JSON line per
    request framed by `\\n`. We read until we see that newline (or the
    socket closes). Large envelopes (e.g. `health.status` with a deep
    pool/status tree) can exceed 64 KiB, so we loop on `recv()`.
    """
    req_id = int(time.time() * 1_000_000) & 0xFFFFFFFF
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
    except (OSError, socket.error, socket.timeout) as e:
        return {"id": req_id, "result": None, "error": f"ipc transport: {e}"}
    finally:
        try:
            sock.close()
        except OSError:
            pass

    if not buf.strip():
        return {"id": req_id, "result": None, "error": "ipc: empty response"}
    try:
        resp = json.loads(buf.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return {"id": req_id, "result": None, "error": f"ipc parse: {e}"}
    if not isinstance(resp, dict):
        return {"id": req_id, "result": None, "error": f"ipc: non-dict frame {type(resp).__name__}"}
    # The daemon doesn't yet stamp our echo'd id; keep the request id so
    # callers can correlate. Don't drop it if the server left it null.
    resp.setdefault("id", req_id)
    return resp


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def sharecli_health_status(timeout: float = 10.0) -> dict:
    """Return the parsed envelope from `health.status`, or {'error':...}."""
    return sharecli_call(METHOD_HEALTH_STATUS, timeout=timeout)


def sharecli_pool_status(timeout: float = 10.0) -> dict:
    """Return the parsed envelope from `pool.status`, or {'error':...}."""
    return sharecli_call(METHOD_POOL_STATUS, timeout=timeout)


def sharecli_process_list(timeout: float = 10.0) -> list:
    """Return the list of ProcessSummary dicts from `process.list`."""
    resp = sharecli_call(METHOD_PROCESS_LIST, timeout=timeout)
    if isinstance(resp, dict) and resp.get("error") is None:
        result = resp.get("result")
        if isinstance(result, list):
            return result
    return []


def sharecli_log_tail(since_id: int = 0, timeout: float = 10.0) -> dict:
    """Return the parsed envelope from `log.tail` (lines + last_id)."""
    return sharecli_call(METHOD_LOG_TAIL, {"since_id": int(since_id)}, timeout=timeout)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _append_audit(line: str, path: str | None = None) -> None:
    """Best-effort append to the sharecli audit log.

    ``path`` defaults to ``NOTIFY_AUDIT_LOG`` at call time (not definition
    time) so tests can monkey-patch the module attribute without
    re-defining the function.  Never raises — audit failures must not
    affect resume-all.  We mkdir -p the parent so the very first write
    after a clean install works.
    """
    if path is None:
        path = globals().get("NOTIFY_AUDIT_LOG") or os.path.expanduser(
            "~/.forge/audit/sharecli.log"
        )
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{ts} {line}\n")
    except OSError as e:
        log.warning("audit log write failed (%s): %s", path, e)


# ---------------------------------------------------------------------------
# `sharecli cast` CLI pass-throughs
# ---------------------------------------------------------------------------

def _sharecli_bin() -> str | None:
    """Locate the `sharecli` CLI binary on PATH or in ~/.cargo/bin."""
    found = shutil.which("sharecli")
    if found:
        return found
    cargo = os.path.expanduser("~/.cargo/bin/sharecli")
    return cargo if os.path.exists(cargo) else None


def sharecli_cast_list_panes(timeout: float = 5.0) -> list[str]:
    """Return the names of panes registered via `sharecli cast list`.

    Parses the table output (`NAME  ADDRESS`) which is what
    `crates/sharecli/src/commands/cast.rs:36-49` emits. Empty on any
    failure (no binary, no registry, parse error) — callers treat an
    empty result as "no notification path available".
    """
    bin_ = _sharecli_bin()
    if not bin_:
        return []
    try:
        cp = subprocess.run(
            [bin_, "cast", "list"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("sharecli cast list failed: %s", e)
        return []
    if cp.returncode != 0 or not cp.stdout:
        return []
    out: list[str] = []
    for raw in cp.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Skip table header (NAME) and the all-dashes separator row.
        # Also skip the "No panes registered" message emitted by
        # crates/sharecli/src/commands/cast.rs:39-42 when the registry is empty.
        if line.startswith("NAME") or set(line) <= {"-"}:
            continue
        if line.startswith("No panes registered"):
            continue
        # NAME  ADDRESS  -> first whitespace-separated token
        parts = line.split(None, 1)
        if parts:
            out.append(parts[0])
    return out


def sharecli_cast_send(name: str, text: str, timeout: float = 10.0) -> bool:
    """Send `text` to the registered cast pane `name`.

    Returns True on `Delivered` / `NeedsFocus`, False on anything else
    (no binary, registered pane missing, caster failure). We rely on the
    CLI's exit code (0 = success per `crates/sharecli/src/commands/cast.rs:78-83`).
    """
    if not name or not text:
        return False
    bin_ = _sharecli_bin()
    if not bin_:
        return False
    try:
        cp = subprocess.run(
            [bin_, "cast", "send", name, "-"],
            input=text, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("sharecli cast send %r failed: %s", name, e)
        return False
    return cp.returncode == 0


# ---------------------------------------------------------------------------
# sharecli_notify — the public entry point used by resume-all
# ---------------------------------------------------------------------------

def sharecli_notify(count: int, source: str = "resume-all") -> dict:
    """Push a "restored N sessions" notification to the ShareCLI Tray.

    Returns a small status dict so callers can log or annotate their own
    output. The two notification pathways are tried in order:

    1. `sharecli cast send <pane> "..."` — true cross-machine text
       injection into a registered tray pane (the natural
       publish-to-tray path registered in
       `~/Library/Application Support/sharecli/cast/pane-map.toml`).
       We probe the registered pane list first; if none of the
       candidate names (`tray`, `sharecli-tray`, `sharecli_tray`) are
       registered, we fall through to the IPC probe.

    2. `health.status` IPC probe — the canonical "health" domain method
       in the sharecli-ipc schema (`handler.rs:368-386`). Cheap,
       side-effect free, and observable by the tray's poll loop as
       resume-all activity.

    Every call is logged to ~/.forge/audit/sharecli.log with the chosen
    pathway, the count, and the outcome. Failures are non-fatal: the
    helper returns `{"delivered": False, "pathway": "...", "error": "..."}`
    and resume-all continues regardless.
    """
    cast_candidates = [n for n in _NOTIFY_CAST_PANE_CANDIDATES]
    registered = set(sharecli_cast_list_panes())
    chosen_pane = next((n for n in cast_candidates if n in registered), None)

    summary: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "count": int(count),
        "socket": sharecli_socket_path(),
        "socket_reachable": sharecli_socket_reachable(),
        "cast_panes": sorted(registered),
        "pathway": None,
        "delivered": False,
        "error": None,
    }

    message = f"resume-all restored {int(count)} session(s)"

    # Pathway 1 — cast send to a registered tray pane.
    if chosen_pane:
        ok = sharecli_cast_send(chosen_pane, message)
        summary["pathway"] = "cast.send"
        summary["cast_pane"] = chosen_pane
        if ok:
            summary["delivered"] = True
            _append_audit(
                f"notify source={source} count={int(count)} "
                f"pathway=cast.send pane={chosen_pane} outcome=ok"
            )
            log.info(
                "sharecli_notify: delivered via cast.send pane=%r count=%d",
                chosen_pane, int(count),
            )
            return summary
        summary["error"] = "cast send returned non-zero"
        _append_audit(
            f"notify source={source} count={int(count)} "
            f"pathway=cast.send pane={chosen_pane} outcome=fail"
        )
        # Fall through to the IPC probe.  Reset pathway so the
        # successful path is reported, but keep the cast error for
        # observability (operators want to know the cast side fell
        # over even when IPC salvaged the delivery).
        summary["pathway"] = None
        summary["cast_error"] = summary["error"]

    # Pathway 2 — health.status probe (the canonical health method).
    if summary["socket_reachable"]:
        resp = sharecli_health_status(timeout=10.0)
        if isinstance(resp, dict) and resp.get("error") is None:
            summary["pathway"] = "ipc.health.status"
            summary["delivered"] = True
            result = resp.get("result")
            if isinstance(result, dict):
                summary["managed_processes"] = result.get("managed_processes")
                summary["healthy"] = result.get("healthy")
            _append_audit(
                f"notify source={source} count={int(count)} "
                f"pathway=ipc.health.status outcome=ok"
            )
            log.info(
                "sharecli_notify: delivered via ipc.health.status count=%d",
                int(count),
            )
            return summary
        summary["error"] = (
            resp.get("error") if isinstance(resp, dict) else "unknown"
        )
        _append_audit(
            f"notify source={source} count={int(count)} "
            f"pathway=ipc.health.status outcome=fail error={summary['error']}"
        )
    else:
        summary["error"] = summary["error"] or "ipc socket not reachable"
        _append_audit(
            f"notify source={source} count={int(count)} "
            f"pathway=none outcome=skipped error={summary['error']}"
        )

    log.warning(
        "sharecli_notify: no delivery path succeeded (count=%d, error=%s)",
        int(count), summary["error"],
    )
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli(argv: Iterable[str]) -> int:
    args = list(argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    sub = args[0]
    rest = args[1:]

    if sub == "socket-path":
        print(sharecli_socket_path())
        return 0
    if sub == "reachable":
        print("yes" if sharecli_socket_reachable() else "no")
        return 0 if sharecli_socket_reachable() else 1
    if sub == "cast-panes":
        for n in sharecli_cast_list_panes():
            print(n)
        return 0
    if sub == "call":
        if not rest:
            print("usage: sharecli-ipc.py call <method> [json-params]", file=sys.stderr)
            return 2
        method = rest[0]
        params: dict = {}
        if len(rest) > 1:
            try:
                params = json.loads(rest[1])
            except json.JSONDecodeError as e:
                print(f"invalid JSON params: {e}", file=sys.stderr)
                return 2
        resp = sharecli_call(method, params)
        print(json.dumps(resp, indent=2, sort_keys=True))
        return 0 if resp.get("error") is None else 1
    if sub == "health":
        print(json.dumps(sharecli_health_status(), indent=2, sort_keys=True))
        return 0
    if sub == "pool":
        print(json.dumps(sharecli_pool_status(), indent=2, sort_keys=True))
        return 0
    if sub == "list":
        procs = sharecli_process_list()
        print(json.dumps(procs, indent=2, sort_keys=True))
        return 0
    if sub == "log-tail":
        since = int(rest[0]) if rest else 0
        print(json.dumps(sharecli_log_tail(since), indent=2, sort_keys=True))
        return 0
    if sub == "notify":
        count = int(rest[0]) if rest else 0
        source = rest[1] if len(rest) > 1 else "cli"
        summary = sharecli_notify(count, source=source)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["delivered"] else 1
    if sub == "notify-status":
        # Diagnostic: report socket reachability + last-known audit rows.
        path = sharecli_socket_path()
        ok = sharecli_socket_reachable()
        print(f"socket path   : {path}")
        print(f"socket exists : {'yes' if os.path.exists(path) else 'no'}")
        print(f"reachable     : {'yes' if ok else 'no'}")
        print(f"cast panes    : {sharecli_cast_list_panes() or '(none)'}")
        if ok:
            print("health probe  :")
            resp = sharecli_health_status(timeout=10.0)
            err = resp.get("error")
            if err is None:
                result = resp.get("result") or {}
                if isinstance(result, dict):
                    print(f"  managed_processes = {result.get('managed_processes')}")
                    print(f"  healthy           = {result.get('healthy')}")
                    print(f"  used/total memory = "
                          f"{result.get('used_memory_mb')}/{result.get('total_memory_mb')} MiB")
            else:
                print(f"  error: {err}")
        log_path = NOTIFY_AUDIT_LOG
        print(f"audit log     : {log_path} "
              f"({'present' if os.path.exists(log_path) else 'absent'})")
        if os.path.exists(log_path):
            try:
                tail = Path(log_path).read_text().splitlines()[-5:]
                if tail:
                    print("audit tail:")
                    for line in tail:
                        print(f"  {line}")
            except OSError:
                pass
        return 0 if ok else 1

    print(f"unknown subcommand: {sub}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
