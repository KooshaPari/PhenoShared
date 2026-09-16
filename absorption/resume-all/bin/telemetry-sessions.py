#!/opt/homebrew/bin/python3
"""
telemetry-sessions.py — Phase E hardening item E09.

Collects session-level telemetry metrics from the snapshot and
launchd state. Designed to be polled periodically (e.g. every 5
minutes via launchd) and appended to a time-series NDJSON file for
historical trend analysis.

Metrics collected per tick:
  ts                       — ISO timestamp
  ts_epoch                 — Unix timestamp
  total_sessions           — count of rows in snapshot
  unique_harnesses         — distinct harness values
  unique_cwds              — distinct cwd values
  with_session_id          — count of rows with non-empty session_id
  without_session_id       — count of rows with empty session_id
  average_age_seconds      — mean age (snapshot ts_epoch → now)
  median_age_seconds       — median age
  oldest_session_seconds   — age of oldest
  newest_session_seconds   — age of newest
  snapshot_stale_seconds   — age of snapshot file (mtime → now)
  ipc_healthy              — bool: IPC daemon responding to health.status
  ipc_managed_processes    — count from IPC daemon
  launchd_jobs_total       — count of active launchd jobs
  launchd_jobs_ok          — count of OK jobs
  launchd_jobs_degraded    — count of DEGRADED jobs

Usage:
  telemetry-sessions.py            # one tick, append to telemetry.ndjson
  telemetry-sessions.py --print    # print latest entry
  telemetry-sessions.py --stats N  # show last N entries summary
  telemetry-sessions.py --json     # JSON output (no append)
  telemetry-sessions.py test       # self-tests
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

BIN = Path("/Users/kooshapari/bin")
DATA = Path.home() / ".local/share/resume-all"
SNAPSHOT = DATA / "snapshot.jsonl"
TELEMETRY = DATA / "telemetry.ndjson"
LAUNCH_AGENTS = Path.home() / "Library/LaunchAgents"
IPC_SOCKET = Path.home() / "Library/Application Support/sharecli/ipc.sock"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_snapshot() -> list[dict]:
    if not SNAPSHOT.exists(): return []
    rows = []
    for line in SNAPSHOT.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def probe_ipc() -> tuple[bool, int]:
    """Probe IPC daemon. Returns (healthy, managed_processes)."""
    if not IPC_SOCKET.exists():
        return False, 0
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(str(IPC_SOCKET))
        msg = {"id": 1, "method": "health.status", "params": {}}
        s.sendall((json.dumps(msg) + "\n").encode())
        buf = b""
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk: break
            buf += chunk
            if buf.endswith(b"\n"): break
        s.close()
        if not buf: return False, 0
        try:
            r = json.loads(buf.decode())
            return (r.get("result", {}).get("healthy", False),
                    r.get("result", {}).get("managed_processes", 0))
        except (json.JSONDecodeError, AttributeError):
            return False, 0
    except (socket.error, OSError):
        return False, 0


def probe_launchd() -> dict:
    """Probe launchd jobs. Returns dict with counts."""
    plists = list(LAUNCH_AGENTS.glob("com.kooshapari.*.plist"))
    total = len(plists)
    ok = 0
    degraded = 0
    for plist in plists:
        label = plist.stem
        try:
            r = subprocess.run(
                ["launchctl", "print", f"gui/501/{label}"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                degraded += 1
                continue
            out = r.stdout
            if "last exit code = (never exited)" in out:
                ok += 1
            elif "state = not running" in out or "xpcproxy" in out.lower():
                # xpcproxy is fine for one-shot wrappers
                ok += 1
            else:
                # Check for explicit DEGRADED text in health.txt
                pass
        except subprocess.TimeoutExpired:
            degraded += 1
    return {"total": total, "ok": ok, "degraded": degraded}


def snapshot_metrics() -> dict:
    """Compute snapshot-derived metrics."""
    rows = read_snapshot()
    total = len(rows)
    harnesses = set()
    cwds = set()
    with_sid = 0
    ages = []
    now_epoch = dt.datetime.now(dt.timezone.utc).timestamp()
    for r in rows:
        h = r.get("harness", "")
        if h: harnesses.add(h)
        c = r.get("cwd", "")
        if c: cwds.add(c)
        if r.get("session_id"): with_sid += 1
        ts = float(r.get("ts_epoch", 0) or 0)
        if ts > 0:
            ages.append(now_epoch - ts)
    avg_age = statistics.mean(ages) if ages else 0
    median_age = statistics.median(ages) if ages else 0
    oldest = max(ages) if ages else 0
    newest = min(ages) if ages else 0
    try:
        snap_age = now_epoch - SNAPSHOT.stat().st_mtime
    except OSError:
        snap_age = -1
    return {
        "total_sessions": total,
        "unique_harnesses": len(harnesses),
        "unique_cwds": len(cwds),
        "with_session_id": with_sid,
        "without_session_id": total - with_sid,
        "average_age_seconds": round(avg_age, 1),
        "median_age_seconds": round(median_age, 1),
        "oldest_session_seconds": round(oldest, 1),
        "newest_session_seconds": round(newest, 1),
        "snapshot_stale_seconds": round(snap_age, 1),
    }


def collect_tick() -> dict:
    """Collect one telemetry tick."""
    snap_m = snapshot_metrics()
    ipc_ok, ipc_procs = probe_ipc()
    launchd = probe_launchd()
    return {
        "ts": now(),
        "ts_epoch": int(dt.datetime.now(dt.timezone.utc).timestamp()),
        **snap_m,
        "ipc_healthy": ipc_ok,
        "ipc_managed_processes": ipc_procs,
        "launchd_jobs_total": launchd["total"],
        "launchd_jobs_ok": launchd["ok"],
        "launchd_jobs_degraded": launchd["degraded"],
    }


def append_tick(tick: dict) -> None:
    TELEMETRY.parent.mkdir(parents=True, exist_ok=True)
    with TELEMETRY.open("a") as f:
        f.write(json.dumps(tick, separators=(",", ":")) + "\n")


def read_history(n: int = 0) -> list[dict]:
    if not TELEMETRY.exists(): return []
    lines = TELEMETRY.read_text().splitlines()
    if n: lines = lines[-n:]
    out = []
    for line in lines:
        line = line.strip()
        if not line: continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def print_stats(n: int) -> int:
    hist = read_history(n)
    if not hist:
        print("telemetry-sessions: no history yet", file=sys.stderr)
        return 1
    print(f"telemetry-sessions: last {len(hist)} tick(s)")
    print(f"{'ts':24s} {'sess':>5s} {'harn':>5s} {'cwds':>5s} "
          f"{'with_sid':>8s} {'avg_age':>8s} {'ipc':>5s} "
          f"{'jobs_ok':>8s} {'snap_age':>8s}")
    for h in hist:
        print(f"{h.get('ts','?'):24s} "
              f"{h.get('total_sessions',0):5d} "
              f"{h.get('unique_harnesses',0):5d} "
              f"{h.get('unique_cwds',0):5d} "
              f"{h.get('with_session_id',0):8d} "
              f"{h.get('average_age_seconds',0):8.1f} "
              f"{'OK' if h.get('ipc_healthy') else 'NO':>5s} "
              f"{h.get('launchd_jobs_ok',0):>4d}/{h.get('launchd_jobs_total',0):<3d} "
              f"{h.get('snapshot_stale_seconds',0):8.1f}s")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true",
                    help="Print latest entry")
    ap.add_argument("--stats", type=int, default=0,
                    help="Show last N entries summary")
    ap.add_argument("--json", action="store_true",
                    help="JSON output (no append)")
    args = ap.parse_args(argv)
    if args.stats:
        return print_stats(args.stats)
    if args.print:
        hist = read_history(1)
        if not hist:
            print("telemetry-sessions: no history yet", file=sys.stderr)
            return 1
        print(json.dumps(hist[-1], indent=2))
        return 0
    tick = collect_tick()
    if args.json:
        print(json.dumps(tick, indent=2))
        return 0
    append_tick(tick)
    print(json.dumps(tick, separators=(",", ":")))
    return 0


def tests() -> bool:
    ok = 0
    fail = 0
    def check(name, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f"PASS {name}")
        else: fail += 1; print(f"FAIL {name}")

    check("now is ISO string",
          "T" in now() and now().endswith("Z"))
    check("read_snapshot returns list",
          isinstance(read_snapshot(), list))
    sm = snapshot_metrics()
    check("snapshot_metrics has keys",
          "total_sessions" in sm and "unique_harnesses" in sm)
    check("snapshot_metrics types",
          isinstance(sm["total_sessions"], int) and
          isinstance(sm["snapshot_stale_seconds"], (int, float)))
    check("probe_ipc returns tuple",
          isinstance(probe_ipc(), tuple) and len(probe_ipc()) == 2)
    ld = probe_launchd()
    check("probe_launchd has keys",
          "total" in ld and "ok" in ld and "degraded" in ld)
    check("probe_launchd types",
          isinstance(ld["total"], int))
    tick = collect_tick()
    check("tick has ts and ts_epoch",
          "ts" in tick and "ts_epoch" in tick)
    check("tick has ipc fields",
          "ipc_healthy" in tick and "ipc_managed_processes" in tick)
    check("tick has launchd fields",
          "launchd_jobs_total" in tick and "launchd_jobs_ok" in tick)
    # Round-trip append/read
    before = read_history()
    append_tick({"ts": now(), "ts_epoch": int(time.time()),
                 "test": True})
    after = read_history()
    check("append_tick grew file", len(after) == len(before) + 1)
    # Cleanup test entry
    if TELEMETRY.exists():
        lines = [l for l in TELEMETRY.read_text().splitlines()
                 if '"test":true' not in l]
        TELEMETRY.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"\n{ok}/{ok + fail} passed")
    return fail == 0


if __name__ == "__main__":
    # Allow test arg
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if tests() else 1)
    sys.exit(main(sys.argv[1:]))
