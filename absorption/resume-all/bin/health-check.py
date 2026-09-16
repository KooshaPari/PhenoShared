#!/opt/homebrew/bin/python3
"""
health-check.py — Phase F hardening item F07.

Probes the resume-all crash-recovery toolkit's three control surfaces and
writes a human-readable status file:

  1. IPC daemon at ~/Library/Application Support/sharecli/ipc.sock
     (NDJSON request: {"id": N, "method": "health.status", "params": {}}\\n)
  2. Snapshot file at ~/.local/share/resume-all/snapshot.jsonl
     (must exist, be < 90s old, parse as JSONL)
  3. All four launchd jobs:
       com.kooshapari.resume-all-snapshot
       com.kooshapari.resume-all-ipc
       com.kooshapari.resume-all-watch
       com.kooshapari.resume-all-zmx

Writes a status block to ~/.local/share/resume-all/health.txt with an
Overall: HEALTHY or DEGRADED line. Exit code 0 = HEALTHY, 1 = DEGRADED.

Wire format note: the IPC daemon speaks NDJSON (one JSON object per line).
Never use length-prefixed framing here -- the daemon reads lines, not
4-byte length prefixes.

This is a manual / on-demand tool, NOT a launchd-managed job. Run it from
a shell, or wire it into a CI gate. It is safe to run repeatedly.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SNAPSHOT_MAX_AGE_SECONDS = 90  # snapshot considered "fresh" if mtime < 90s ago
LAUNCHD_UID = os.getuid()
LAUNCHD_GUI_DOMAIN = f"gui/{LAUNCHD_UID}"

LAUNCHD_JOBS: tuple[str, ...] = (
    "com.kooshapari.resume-all-snapshot",
    "com.kooshapari.resume-all-ipc",
    "com.kooshapari.resume-all-watch",
    "com.kooshapari.resume-all-zmx",
)

# Exit codes the snapshot/zmx jobs return when no Ghostty/tmux backend is
# detected -- this is the documented "expected" failure mode when the
# session was launched from a non-Ghostty pane (e.g. droid harness).
EXPECTED_NO_BACKEND_EXIT_CODES: dict[str, frozenset[int]] = {
    "com.kooshapari.resume-all-snapshot": frozenset({2}),
    "com.kooshapari.resume-all-zmx": frozenset({2}),
}


# ---------------------------------------------------------------------------
# Probe: IPC daemon (NDJSON)
# ---------------------------------------------------------------------------

def _ipc_socket_paths() -> tuple[str, ...]:
    """Same resolution order as sharecli_bridge.py: env override, then
    macOS-canonical, then Linux-canonical."""
    env = os.environ.get("SHARECLI_IPC_SOCK")
    if env:
        return (env,)
    return (
        os.path.expanduser("~/Library/Application Support/sharecli/ipc.sock"),
        os.path.expanduser("~/.local/share/sharecli/ipc.sock"),
    )


def probe_ipc_daemon() -> dict:
    """Returns a dict with keys:
        reachable (bool), pid (int|None), managed_processes (int|None),
        snapshot_age (int|None), protocol_version (str|None),
        error (str|None), raw (dict|None), socket (str|None)

    Tolerates the multiple daemon implementations that share the canonical
    socket (the custom Rust sharecli-ipc-daemon AND ShareCLITray's bundled
    daemon). Each returns a slightly different shape for health.status; we
    extract whichever fields are present.
    """
    out: dict = {
        "reachable": False,
        "pid": None,
        "managed_processes": None,
        "snapshot_age": None,
        "protocol_version": None,
        "error": None,
        "raw": None,
        "socket": None,
    }

    socket_path = None
    for candidate in _ipc_socket_paths():
        if os.path.exists(candidate):
            socket_path = candidate
            break
    if socket_path is None:
        socket_path = _ipc_socket_paths()[0]
    out["socket"] = socket_path

    if not os.path.exists(socket_path):
        out["error"] = f"socket file missing: {socket_path}"
        return out

    req_id = uuid.uuid4().int & 0xFFFFFFFF
    request_line = (
        json.dumps(
            {"id": req_id, "method": "health.status", "params": {}},
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(10.0)
        sock.connect(socket_path)
        sock.sendall(request_line)

        # Give the daemon a brief moment to compute and flush the response.
        # The response is one JSON object (~2.6 KiB for health.status). It is
        # terminated by \n. We recv in small chunks and break on \n.
        time.sleep(0.3)

        buf = b""
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if buf.endswith(b"\n"):
                break
    except (OSError, socket.error) as exc:
        out["error"] = f"transport: {exc}"
        return out
    finally:
        try:
            sock.close()
        except OSError:
            pass

    if not buf.strip():
        out["error"] = "empty response from daemon"
        return out

    try:
        response = json.loads(buf.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        out["error"] = f"parse: {exc}"
        return out

    out["raw"] = response
    if not isinstance(response, dict):
        out["error"] = f"non-dict frame: {type(response).__name__}"
        return out
    if response.get("error"):
        err = response["error"]
        # unknown method is non-fatal -- some daemons only implement a
        # subset. Reachability is still confirmed by the JSON-RPC envelope.
        if isinstance(err, str) and err.startswith("unknown method"):
            out["reachable"] = True
            out["error"] = f"daemon partial: {err}"
            return out
        out["error"] = f"daemon error: {err}"
        return out

    out["reachable"] = True
    result = response.get("result") or {}
    if not isinstance(result, dict):
        return out

    # Multiple daemon implementations share the same socket (the canonical
    # Rust sharecli-ipc-daemon AND ShareCLITray's bundled daemon both bind
    # to it). Each responds with a slightly different shape for
    # health.status. Extract whichever fields are present.
    out["pid"] = (
        result.get("pid")
        or (result.get("status") or {}).get("pid")
    )
    out["protocol_version"] = (
        result.get("protocol_version")
        or (result.get("metadata") or {}).get("protocol_version")
        or "unknown"
    )
    # Process count: try several known locations across daemon variants.
    procs = None
    for key in ("managed_processes", "snapshot_count", "process_count"):
        if isinstance(result.get(key), int):
            procs = result[key]
            break
    if procs is None:
        status = result.get("status") or {}
        agents = status.get("agents") or []
        if isinstance(agents, list):
            procs = len(agents)
    out["managed_processes"] = procs

    # Snapshot age: try several known fields, plus raw top-level.
    age = None
    for key in ("snapshot_age_seconds", "snapshot_age"):
        if isinstance(result.get(key), int):
            age = result[key]
            break
    if age is None:
        status = result.get("status") or {}
        # ShareCLITray format: snapshot age may be in seconds somewhere
        age = status.get("snapshot_age_seconds") or status.get("snapshot_age")
    out["snapshot_age"] = age
    return out


# ---------------------------------------------------------------------------
# Probe: snapshot file
# ---------------------------------------------------------------------------

def probe_snapshot() -> dict:
    """Returns a dict with keys:
        path (str), exists (bool), size_bytes (int), mtime (float),
        mtime_age_seconds (int), rows (int), parseable (bool), error (str|None)
    """
    snap_path = Path.home() / ".local" / "share" / "resume-all" / "snapshot.jsonl"
    out: dict = {
        "path": str(snap_path),
        "exists": False,
        "size_bytes": 0,
        "mtime": 0.0,
        "mtime_age_seconds": None,
        "rows": 0,
        "parseable": False,
        "error": None,
    }
    if not snap_path.exists():
        out["error"] = "snapshot file missing"
        return out
    stat = snap_path.stat()
    out["exists"] = True
    out["size_bytes"] = stat.st_size
    out["mtime"] = stat.st_mtime
    out["mtime_age_seconds"] = int(time.time() - stat.st_mtime)

    rows = 0
    parseable = True
    try:
        with snap_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows += 1
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    parseable = False
                    out["error"] = f"row {rows}: {exc}"
                    break
    except OSError as exc:
        out["error"] = f"read: {exc}"
        return out

    out["rows"] = rows
    out["parseable"] = parseable
    return out


# ---------------------------------------------------------------------------
# Probe: launchd jobs
# ---------------------------------------------------------------------------

def probe_launchd_job(label: str) -> dict:
    """Returns a dict with keys:
        label, state, pid, last_exit_code, last_exit_reason, raw_ok, error
    """
    out: dict = {
        "label": label,
        "state": None,
        "pid": None,
        "last_exit_code": None,
        "last_exit_reason": None,
        "raw_ok": False,
        "error": None,
    }
    full_label = f"{LAUNCHD_GUI_DOMAIN}/{label}"
    try:
        proc = subprocess.run(
            ["/bin/launchctl", "print", full_label],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        out["error"] = f"launchctl invocation failed: {exc}"
        return out

    if proc.returncode != 0:
        out["error"] = (
            f"launchctl print returned {proc.returncode}: "
            f"{(proc.stderr or proc.stdout).strip().splitlines()[0] if (proc.stderr or proc.stdout) else ''}"
        )
        return out

    text = proc.stdout

    # state line: "	state = running" (look only at top-level, not nested runs)
    for line in text.splitlines():
        # The top-level state appears before any nested "runs = { ..." block
        if line.startswith("\tstate = "):
            out["state"] = line.split("=", 1)[1].strip()
            break
        if line.startswith("state = "):
            out["state"] = line.split("=", 1)[1].strip()
            break

    if "state = running" not in text and "state = not running" in text:
        out["state"] = "not running"

    # Run count for periodic jobs (StartInterval=...). launchctl prints
    # "	runs = N" at top-level — capture it so we can recognise periodic jobs
    # that exit cleanly between ticks.
    for line in text.splitlines():
        if line.startswith("\truns = "):
            try:
                out["runs"] = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
            break

    # PID is "	pid = 12345" (top-level). Nested services also have "pid" but
    # we want the top-level one. Iterate lines in order, take first match.
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("pid = "):
            try:
                out["pid"] = int(line_stripped.split("=", 1)[1].strip())
            except ValueError:
                pass
            break

    # Last exit code is "	last exit code = 2"
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("last exit code = "):
            value = line_stripped.split("=", 1)[1].strip()
            try:
                out["last_exit_code"] = int(value)
            except ValueError:
                out["last_exit_reason"] = value
            break
        if line_stripped.startswith("last exit reason = "):
            out["last_exit_reason"] = line_stripped.split("=", 1)[1].strip()

    out["raw_ok"] = True
    return out


def probe_all_launchd_jobs() -> list[dict]:
    results = []
    for label in LAUNCHD_JOBS:
        results.append(probe_launchd_job(label))
    return results


# ---------------------------------------------------------------------------
# Verdict + report
# ---------------------------------------------------------------------------

def _verdict_ipc(probe: dict) -> tuple[str, str]:
    """Returns (status, detail). status is OK|DEGRADED|OK_DEGRADED."""
    if not probe["reachable"]:
        return "DEGRADED", f"unreachable: {probe['error']}"
    bits = []
    if probe["pid"]:
        bits.append(f"pid {probe['pid']}")
    if probe["managed_processes"] is not None:
        bits.append(f"{probe['managed_processes']} processes")
    if probe["snapshot_age"] is not None:
        bits.append(f"snapshot {probe['snapshot_age']}s old")
    elif probe["snapshot_age"] is None and probe["protocol_version"]:
        bits.append(f"v{probe['protocol_version']}")
    detail = ", ".join(bits) if bits else "reachable"
    return "OK", detail


def _verdict_snapshot(probe: dict) -> tuple[str, str]:
    if not probe["exists"]:
        return "DEGRADED", probe["error"] or "file missing"
    if not probe["parseable"]:
        return "DEGRADED", probe["error"] or "unparseable"
    age = probe["mtime_age_seconds"]
    if age is None:
        return "DEGRADED", "unknown mtime"
    if age > SNAPSHOT_MAX_AGE_SECONDS:
        return "DEGRADED", f"stale: {age}s old (>{SNAPSHOT_MAX_AGE_SECONDS}s threshold)"
    return "OK", f"{probe['rows']} rows, mtime {age}s ago"


def _verdict_launchd(probe: dict) -> tuple[str, str]:
    """status: OK (clean) | OK_WARN (running but exit code in
    EXPECTED_NO_BACKEND_EXIT_CODES) | DEGRADED (state not running OR
    unexpected exit code)."""
    label = probe["label"]
    state = probe["state"]
    exit_code = probe["last_exit_code"]
    pid = probe["pid"]

    if probe["error"]:
        # launchctl failed entirely -- degrade but keep going
        return "DEGRADED", probe["error"]

    bits = []
    if pid:
        bits.append(f"pid {pid}")
    if exit_code is None:
        bits.append("last exit (never exited)")
    else:
        bits.append(f"last exit {exit_code}")

    if state != "running":
        # Periodic job (StartInterval=...) is healthy if it ran at least once
        # and exited cleanly. launchd reports `state = not running` between
        # ticks but `runs > 0` + last exit 0 means it's working as designed.
        if state == "not running" and exit_code == 0 and probe.get("runs", 0) > 0:
            return "OK", ", ".join(bits) + " (periodic)"
        return "DEGRADED", ", ".join(bits) + f" (state={state})"

    if exit_code is None:
        return "OK", ", ".join(bits)

    allowed = EXPECTED_NO_BACKEND_EXIT_CODES.get(label, frozenset())
    if exit_code == 0:
        return "OK", ", ".join(bits)
    if exit_code in allowed:
        return (
            "OK_WARN",
            ", ".join(bits) + " (expected: no backend detected)",
        )
    return "DEGRADED", ", ".join(bits)


def build_report(
    ipc: dict,
    snapshot: dict,
    launchd_jobs: list[dict],
) -> tuple[str, dict]:
    """Returns (report_text, verdict_map). verdict_map maps each subsystem
    to its verdict status (OK / OK_WARN / DEGRADED)."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"resume-all health check -- {ts}")
    lines.append("=" * 49)

    verdicts: dict[str, str] = {}

    # IPC
    status, detail = _verdict_ipc(ipc)
    verdicts["ipc"] = status
    label = f"{status:<12}" if status == "OK" else f"{status:<12}"
    lines.append(f"IPC daemon:        {label}  ({detail})")

    # Snapshot
    status, detail = _verdict_snapshot(snapshot)
    verdicts["snapshot"] = status
    label = f"{status:<12}"
    lines.append(f"Snapshot file:     {label}  ({detail})")

    # Launchd
    lines.append("Launchd jobs:")
    for probe in launchd_jobs:
        status, detail = _verdict_launchd(probe)
        short = probe["label"].rsplit(".", 1)[-1].replace("resume-all-", "")
        verdicts[probe["label"]] = status
        label = f"{status:<12}"
        lines.append(f"  {short:<14} {label}  ({detail})")

    # Overall
    degraded = [k for k, v in verdicts.items() if v == "DEGRADED"]
    if degraded:
        overall = "DEGRADED"
        overall_detail = "broken: " + ", ".join(degraded)
    else:
        overall = "HEALTHY"
        warns = [k for k, v in verdicts.items() if v == "OK_WARN"]
        overall_detail = (
            f"all subsystems reporting OK ({len(warns)} non-blocking warning(s))"
            if warns
            else "all subsystems reporting OK"
        )
    lines.append("")
    lines.append(f"Overall:           {overall}  ({overall_detail})")

    return ("\n".join(lines) + "\n"), {**verdicts, "overall": overall}


# ---------------------------------------------------------------------------
# I/O + main
# ---------------------------------------------------------------------------

HEALTH_OUTPUT_PATH = Path.home() / ".local" / "share" / "resume-all" / "health.txt"


def write_health_file(report_text: str) -> None:
    HEALTH_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_OUTPUT_PATH.write_text(report_text, encoding="utf-8")


def print_human(ipc: dict, snapshot: dict, launchd: list[dict]) -> None:
    if ipc["reachable"]:
        ipc_summary = "pid={} processes={}".format(
            ipc.get("pid"), ipc.get("managed_processes")
        )
        print(f"IPC:        OK  {ipc_summary}")
    else:
        print(f"IPC:        FAIL  {ipc.get('error')}")
    if snapshot["exists"]:
        age = snapshot["mtime_age_seconds"]
        fresh = "fresh" if age is not None and age <= SNAPSHOT_MAX_AGE_SECONDS else "STALE"
        print(f"snapshot:   {fresh}  rows={snapshot['rows']} age={age}s")
    else:
        print(f"snapshot:   MISSING  ({snapshot['error']})")
    for probe in launchd:
        label = probe["label"].rsplit(".", 1)[-1].replace("resume-all-", "")
        print(
            "launchd:    {:<10} state={} pid={} last_exit={}".format(
                label,
                probe["state"],
                probe["pid"],
                probe["last_exit_code"],
            )
        )


def main() -> int:
    ipc = probe_ipc_daemon()
    snapshot = probe_snapshot()
    launchd = probe_all_launchd_jobs()

    report_text, verdicts = build_report(ipc, snapshot, launchd)
    write_health_file(report_text)

    # Always echo to stdout so the operator sees the summary in their terminal.
    print(report_text)
    print(f"-- written to: {HEALTH_OUTPUT_PATH}")

    return 0 if verdicts["overall"] == "HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(main())
