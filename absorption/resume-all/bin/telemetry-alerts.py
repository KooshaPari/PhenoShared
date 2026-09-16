#!/opt/homebrew/bin/python3
"""
telemetry-alerts.py — Phase E hardening item: telemetry-driven alerting.

Reads the latest telemetry tick and the current health-check status, then:

  - HEALTHY → exit 0 (no-op, no log spam)
  - DEGRADED → write to alert log + (optionally) trigger F14 incident-respond
  - CRITICAL/FAIL → same as DEGRADED but force-trigger incident

Designed to be polled by launchd every 5 minutes. Idempotent — running
multiple times in a row produces no duplicate incidents.

Alert suppression: tracks recent alerts in `alert-state.json` so we only
trigger F14 once per (alert_key, hour_window). Subsequent alerts of the
same key in the same hour just update the log.

Usage:
  telemetry-alerts.py              # one tick, no-op if HEALTHY
  telemetry-alerts.py --force      # always log + run (skip no-op)
  telemetry-alerts.py --status     # show recent alerts
  telemetry-alerts.py test         # self-tests
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DATA = Path.home() / ".local/share/resume-all"
TELEMETRY = DATA / "telemetry.ndjson"
HEALTH = DATA / "health.txt"
ALERT_LOG = DATA / "telemetry-alerts.log"
ALERT_STATE = DATA / "alert-state.json"
SUPPRESS_WINDOW_SEC = 3600  # Don't re-fire same alert within 1 hour


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_state() -> dict:
    try:
        return json.loads(ALERT_STATE.read_text())
    except (OSError, ValueError):
        return {"alerts": {}, "last_run": None}


def save_state(s: dict) -> None:
    ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE.write_text(json.dumps(s, indent=2) + "\n")


def read_latest_telemetry() -> dict:
    if not TELEMETRY.exists():
        return {}
    lines = TELEMETRY.read_text().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line: continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {}


def read_health_status() -> str:
    if not HEALTH.exists():
        return "UNKNOWN"
    for line in HEALTH.read_text().splitlines():
        if line.startswith("Overall:"):
            parts = line.split(":", 1)[-1].strip().split()
            if parts: return parts[0]
    return "UNKNOWN"


def derive_alerts(tel: dict, health_status: str) -> list[tuple[str, str]]:
    """Return list of (level, key, message) tuples.

    Levels: critical, error, warning, info.
    Key is used for de-duplication (e.g. "ipc_degraded", "snap_stale").
    """
    alerts = []
    if health_status in ("DEGRADED", "FAIL", "CRITICAL"):
        alerts.append(("critical", "health_degraded",
                       f"Cockpit {health_status}"))
    if tel and not tel.get("ipc_healthy"):
        alerts.append(("error", "ipc_degraded",
                       f"IPC unhealthy (managed_processes={tel.get('ipc_managed_processes', 0)})"))
    if tel:
        snap_age = tel.get("snapshot_stale_seconds", 0)
        if snap_age > 90:
            alerts.append(("warning", "snap_stale",
                           f"Snapshot stale ({snap_age:.0f}s)"))
        degraded_jobs = tel.get("launchd_jobs_degraded", 0)
        if degraded_jobs > 0:
            alerts.append(("warning", "launchd_degraded",
                           f"{degraded_jobs} launchd job(s) degraded"))
    return alerts


def log_alert(level: str, key: str, msg: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{now()} [{level.upper():8s}] [{key:20s}] {msg}\n"
    with ALERT_LOG.open("a") as f:
        f.write(line)


def maybe_trigger_incident(level: str, key: str, msg: str) -> bool:
    """Trigger F14 incident-respond if severity warrants it."""
    if level not in ("critical", "error"):
        return False
    # Suppress if same alert fired in last hour
    state = load_state()
    alerts = state.get("alerts", {})
    last_ts = alerts.get(key, 0)
    if time.time() - last_ts < SUPPRESS_WINDOW_SEC:
        return False
    # Trigger
    try:
        r = subprocess.run(
            ["/Users/kooshapari/bin/incident-respond.py", "log",
             f"--severity={level}", f"--source=telemetry",
             f"--summary={key}", f"--detail={msg}"],
            capture_output=True, text=True, timeout=10,
        )
        triggered = r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        triggered = False
    # Update state
    alerts[key] = time.time()
    state["alerts"] = alerts
    save_state(state)
    return triggered


def run_one(force: bool = False) -> dict:
    tel = read_latest_telemetry()
    health = read_health_status()
    alerts = derive_alerts(tel, health)
    is_healthy = health in ("HEALTHY", "OK") and not alerts
    summary = {
        "ts": now(),
        "health": health,
        "is_healthy": is_healthy,
        "alerts_count": len(alerts),
        "alerts": [{"level": a[0], "key": a[1], "msg": a[2]} for a in alerts],
        "triggered_incidents": [],
    }
    if is_healthy and not force:
        return summary
    for level, key, msg in alerts:
        log_alert(level, key, msg)
        if maybe_trigger_incident(level, key, msg):
            summary["triggered_incidents"].append(key)
    # Update state last_run
    state = load_state()
    state["last_run"] = now()
    state["last_alerts"] = [
        {"level": a[0], "key": a[1], "msg": a[2]} for a in alerts
    ]
    state["last_health"] = health
    save_state(state)
    return summary


def cmd_status(_args: argparse.Namespace) -> int:
    state = load_state()
    print(f"telemetry-alerts status @ {now()}")
    print(f"  last_run:    {state.get('last_run', 'never')}")
    print(f"  last_health: {state.get('last_health', '?')}")
    print(f"  alerts:      {len(state.get('alerts', {}))}")
    print(f"  last_alerts: {len(state.get('last_alerts', []))}")
    if state.get("last_alerts"):
        for a in state["last_alerts"]:
            print(f"    [{a['level']}] {a['key']}: {a['msg']}")
    print(f"\n  log file:    {ALERT_LOG}")
    return 0


def tests() -> bool:
    ok = 0; fail = 0
    def check(name, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f"PASS {name}")
        else: fail += 1; print(f"FAIL {name}")

    check("now is ISO", "T" in now() and now().endswith("Z"))
    check("ALERT_LOG path", str(ALERT_LOG).endswith("telemetry-alerts.log"))
    check("load_state returns dict", isinstance(load_state(), dict))
    check("save_state round-trips",
          json.loads(ALERT_STATE.read_text()) if ALERT_STATE.exists() else True)
    # derive_alerts — healthy
    alerts = derive_alerts({"ipc_healthy": True, "snapshot_stale_seconds": 30,
                             "launchd_jobs_degraded": 0}, "HEALTHY")
    check("healthy state no alerts", len(alerts) == 0)
    # derive_alerts — degraded
    alerts = derive_alerts({"ipc_healthy": False, "snapshot_stale_seconds": 200,
                             "launchd_jobs_degraded": 2}, "DEGRADED")
    check("degraded state has alerts", len(alerts) >= 3)
    # run_one with HEALTHY + force
    summary = run_one(force=False)
    check("summary has ts", "ts" in summary)
    check("summary has health", "health" in summary)
    check("summary has alerts_count", "alerts_count" in summary)
    print(f"\n{ok}/{ok + fail} passed")
    return fail == 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "test":
        sys.exit(0 if tests() else 1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Always log + run, even if HEALTHY")
    ap.add_argument("--status", action="store_true",
                    help="Print recent alerts and exit")
    args = ap.parse_args(argv)
    if args.status:
        return cmd_status(args)
    summary = run_one(force=args.force)
    print(json.dumps(summary, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
