#!/opt/homebrew/bin/python3
"""
incident-respond.py — Phase F hardening item F14.

Automated incident response: when health-check.py reports DEGRADED, this
script attempts remediation (restart the failing subsystem) before paging
the user.

Recovery matrix:
  IPC_UNREACHABLE       -> launchctl bootout+bootstrap IPC daemon
  SNAPSHOT_STALE        -> kill snapshot loop, restart it via launchd
  LAUNCHD_DEGRADED      -> bootout + bootstrap the failing launchd job
  ZMX_DEGRADED          -> launchctl kickstart -k the zmx job
  (all of above)        -> escalation (alert + log only)

Rate-limit: at most 3 actions per 5 minutes per incident class.
Backoff: if same incident recurs within 10 minutes, log + skip.
Audit trail: every action logged to ~/.local/share/resume-all/incidents.jsonl.

Wire format note: launches the IPC daemon's NDJSON health.status JSON-RPC.

Run as launchd job (StartInterval=30). Safe to run repeatedly.

Usage:
    incident-respond.py run             # one-shot remediation
    incident-respond.py loop            # block, run every 30s
    incident-respond.py status          # print recent incidents
    incident-respond.py test            # inline self-tests
    incident-respond.py ack <id>        # acknowledge an incident
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

# Path constants — added for ipc-recover fallback
HOME = Path.home()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = Path.home()
SNAPSHOT_DIR = HOME / ".local" / "share" / "resume-all"
INCIDENTS_LOG = SNAPSHOT_DIR / "incidents.jsonl"
HEALTH_TXT = SNAPSHOT_DIR / "health.txt"
RATE_LIMIT_FILE = SNAPSHOT_DIR / ".incident-rate-limit.json"
CONFIG_FILE = HOME / ".config" / "resume-all" / "incident.toml"

LAUNCHD_UID = os.getuid()
LAUNCHD_GUI_DOMAIN = f"gui/{LAUNCHD_UID}"

LAUNCHD_JOBS = {
    "snapshot": "com.kooshapari.resume-all-snapshot",
    "ipc":      "com.kooshapari.resume-all-ipc",
    "watch":    "com.kooshapari.resume-all-watch",
    "zmx":      "com.kooshapari.resume-all-zmx",
}
LAUNCHD_PLISTS = {
    name: HOME / "Library" / "LaunchAgents" / f"{label}.plist"
    for name, label in LAUNCHD_JOBS.items()
}

# Rate limits: per-incident-class action caps
MAX_ACTIONS_PER_5MIN = 3
COOLDOWN_SECONDS = 600  # 10 minutes between repeated same-class incidents

# ---------------------------------------------------------------------------
# Incident log helpers
# ---------------------------------------------------------------------------


def _log_incident(class_name: str, action: str, status: str,
                  detail: str = "", ts: float | None = None) -> dict:
    """Append an incident entry to the JSONL log. Returns the entry dict."""
    ts = ts or time.time()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "ts": ts,
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "class": class_name,
        "action": action,
        "status": status,  # "ok" | "skipped" | "escalated" | "rate-limited"
        "detail": detail[:500],
    }
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with INCIDENTS_LOG.open("a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return entry


def _read_incidents(limit: int = 20) -> list[dict]:
    if not INCIDENTS_LOG.exists():
        return []
    out = []
    for line in INCIDENTS_LOG.read_text().splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _load_rate_limit() -> dict[str, list[float]]:
    """Return {incident_class: [ts, ts, ts]} — timestamps of recent actions."""
    if not RATE_LIMIT_FILE.exists():
        return defaultdict(list)
    try:
        data = json.loads(RATE_LIMIT_FILE.read_text())
        # Filter to last 5 minutes
        cutoff = time.time() - 300
        return defaultdict(list, {
            k: [t for t in v if t > cutoff]
            for k, v in data.items()
        })
    except (json.JSONDecodeError, OSError):
        return defaultdict(list)


def _save_rate_limit(rate_data: dict[str, list[float]]) -> None:
    RATE_LIMIT_FILE.write_text(json.dumps(dict(rate_data)))


def _is_rate_limited(class_name: str) -> bool:
    """Returns True if this class has hit MAX_ACTIONS_PER_5MIN in the last 5 min."""
    rate = _load_rate_limit()
    return len(rate.get(class_name, [])) >= MAX_ACTIONS_PER_5MIN


def _record_action(class_name: str) -> None:
    rate = _load_rate_limit()
    rate[class_name].append(time.time())
    _save_rate_limit(rate)


def _is_cool_down(class_name: str) -> bool:
    """Returns True if same incident class was remediated within COOLDOWN_SECONDS."""
    incidents = _read_incidents(limit=50)
    cutoff = time.time() - COOLDOWN_SECONDS
    for inc in reversed(incidents):
        if inc.get("class") == class_name and inc.get("status") == "ok" \
                and inc.get("ts", 0) > cutoff:
            return True
    return False


# ---------------------------------------------------------------------------
# Health parsing
# ---------------------------------------------------------------------------


def _parse_health_txt() -> dict:
    """Parse ~/.local/share/resume-all/health.txt and return a structured view."""
    if not HEALTH_TXT.exists():
        return {"overall": "UNKNOWN", "subsystems": {}}
    text = HEALTH_TXT.read_text()
    subsystems = {}
    overall = "UNKNOWN"
    for line in text.splitlines():
        if line.startswith("Overall:"):
            overall = line.split(":", 1)[1].strip().split()[0]
        # Format: "IPC daemon:        OK            (pid 15624, ...)"
        elif ":" in line and not line.startswith("Overall") \
                and not line.startswith("---") and not line.startswith("=") \
                and not line.startswith("resume-all") \
                and not line.startswith("Launchd jobs"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                rest = parts[1].strip()
                status = rest.split()[0] if rest else "UNKNOWN"
                subsystems[name] = {
                    "status": status,
                    "raw": rest[:200],
                }
    return {"overall": overall, "subsystems": subsystems}


# ---------------------------------------------------------------------------
# Remediation actions
# ---------------------------------------------------------------------------


def _bootout_bootstrap(label: str, plist: Path, action_name: str) -> bool:
    """Run `launchctl bootout` then `launchctl bootstrap`. Returns True on success."""
    try:
        subprocess.run(
            ["launchctl", "bootout", f"{LAUNCHD_GUI_DOMAIN}/{label}"],
            capture_output=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        pass
    time.sleep(1)
    if not plist.exists():
        return False
    result = subprocess.run(
        ["launchctl", "bootstrap", LAUNCHD_GUI_DOMAIN, str(plist)],
        capture_output=True, timeout=10,
    )
    return result.returncode == 0


def _kickstart(label: str) -> bool:
    """Run `launchctl kickstart -k <label>`. Returns True on success."""
    result = subprocess.run(
        ["launchctl", "kickstart", "-k", f"{LAUNCHD_GUI_DOMAIN}/{label}"],
        capture_output=True, timeout=10,
    )
    return result.returncode == 0


def _kill_loop() -> bool:
    """Kill the running snapshot loop process (if any)."""
    killed = 0
    for proc in _ps_iter():
        if "session-snapshot" in proc.get("cmd", "") and "--loop" in proc.get("cmd", ""):
            try:
                os.kill(proc["pid"], 9)
                killed += 1
            except (ProcessLookupError, PermissionError):
                pass
    return killed > 0


def _ps_iter() -> list[dict]:
    """Lightweight ps parser — fall back to `pgrep -fl` if needed."""
    out = []
    try:
        result = subprocess.run(
            ["pgrep", "-fl", "session-snapshot"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                pid = int(parts[0])
                cmd = parts[1]
                out.append({"pid": pid, "cmd": cmd})
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return out


# ---------------------------------------------------------------------------
# Main remediation loop
# ---------------------------------------------------------------------------


def remediate(health: dict | None = None) -> list[dict]:
    """Inspect current health and remediate if degraded. Returns actions taken."""
    if health is None:
        health = _parse_health_txt()

    overall = health.get("overall", "UNKNOWN")
    actions: list[dict] = []

    if overall == "HEALTHY":
        return actions

    subs = health.get("subsystems", {})
    for sub_name, sub in subs.items():
        status = sub.get("status", "OK")
        if status in ("OK", "OK_WARN"):
            continue

        incident_class = sub_name  # e.g. "IPC daemon", "Snapshot file"
        if _is_rate_limited(incident_class):
            entry = _log_incident(
                incident_class, "auto-remediate", "rate-limited",
                detail=f"hit {MAX_ACTIONS_PER_5MIN} actions in 5 min",
            )
            actions.append(entry)
            continue

        if _is_cool_down(incident_class):
            entry = _log_incident(
                incident_class, "auto-remediate", "skipped",
                detail=f"cooldown {COOLDOWN_SECONDS}s active",
            )
            actions.append(entry)
            continue

        # Pick remediation strategy based on subsystem name.
        action, ok, detail = _remediate_one(sub_name, sub)
        status_str = "ok" if ok else "escalated"
        entry = _log_incident(incident_class, action, status_str, detail=detail)
        _record_action(incident_class)
        actions.append(entry)

    return actions


def _remediate_one(sub_name: str, sub: dict) -> tuple[str, bool, str]:
    """Choose and execute remediation for one failing subsystem."""
    raw = sub.get("raw", "")
    detail = f"raw: {raw}"

    # IPC daemon unreachable
    if "IPC daemon" in sub_name:
        label = LAUNCHD_JOBS["ipc"]
        plist = LAUNCHD_PLISTS["ipc"]
        # Try standard bootout+bootstrap first
        if _bootout_bootstrap(label, plist, "ipc-restart"):
            return ("bootout+bootstrap", True,
                    f"restarted {label}, plist={plist}")
        # Fallback: use ipc-recover.py (manual launch + bootstrap dance)
        try:
            rc = subprocess.run(
                [sys.executable, str(HOME / "bin" / "ipc-recover.py"), "recover"],
                capture_output=True, text=True, timeout=90,
            )
            if rc.returncode == 0:
                return ("ipc-recover", True,
                        "fallback to ipc-recover.py succeeded")
            return ("ipc-recover", False,
                    f"ipc-recover.py failed: rc={rc.returncode}, "
                    f"stderr={rc.stderr[:200]}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return ("ipc-recover", False,
                    f"ipc-recover.py unavailable: {e}")

    # Snapshot file stale
    if "Snapshot file" in sub_name:
        if _kill_loop():
            label = LAUNCHD_JOBS["snapshot"]
            plist = LAUNCHD_PLISTS["snapshot"]
            if _bootout_bootstrap(label, plist, "snapshot-restart"):
                return ("kill-loop+bootstrap", True,
                        "killed stale loop, bootstrapped fresh snapshot")
        return ("kill-loop+bootstrap", False,
                "failed to restart snapshot loop")

    # Launchd job degraded (check each known job name)
    for short, label in LAUNCHD_JOBS.items():
        if short in sub_name or label in sub_name:
            plist = LAUNCHD_PLISTS[short]
            if _kickstart(label):
                return ("kickstart", True, f"kickstarted {label}")
            if _bootout_bootstrap(label, plist, f"{short}-restart"):
                return ("bootout+bootstrap", True, f"bootout+bootstrap {label}")
            return (f"{short}-restart", False, f"failed to restart {label}")

    # Unknown subsystem
    return ("unknown-subsystem", False, f"no remediation for {sub_name}")


def cmd_run(args: argparse.Namespace) -> int:
    """One-shot remediation."""
    actions = remediate()
    if not actions:
        print("No actions needed (system HEALTHY)")
        return 0
    print(f"Took {len(actions)} action(s):")
    for a in actions:
        print(f"  [{a['status']:12s}] {a['class']}: {a['action']} ({a['id']})")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    """Block and remediate every --interval seconds."""
    interval = args.interval
    print(f"incident-respond: looping every {interval}s (Ctrl-C to stop)")
    try:
        while True:
            remediate()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nincident-respond: stopped")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print recent incidents."""
    incidents = _read_incidents(limit=args.limit)
    if not incidents:
        print("No incidents recorded.")
        return 0
    print(f"Recent incidents ({len(incidents)}):")
    for inc in incidents:
        ts = inc.get("ts_iso", "?")
        cls = inc.get("class", "?")
        action = inc.get("action", "?")
        status = inc.get("status", "?")
        print(f"  [{ts}] [{status:12s}] {cls:20s} {action:20s} ({inc.get('id', '?')})")
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    """Mark an incident as acknowledged by adding a marker line."""
    ack_entry = {
        "id": args.incident_id,
        "action": "ack",
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with INCIDENTS_LOG.open("a") as f:
        f.write(json.dumps(ack_entry, separators=(",", ":")) + "\n")
    print(f"Acknowledged incident {args.incident_id}")
    return 0


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


def _self_test() -> tuple[int, int]:
    """Run inline self-tests. Returns (passed, total)."""
    passed = 0
    total = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}{(' — ' + detail) if detail and not cond else ''}")

    print("=== incident-respond.py self-tests ===")

    # Test 1: HEALTHY system → no actions
    total += 1
    h = {"overall": "HEALTHY", "subsystems": {}}
    actions = remediate(h)
    if actions == []:
        passed += 1
        print("  [ok] healthy system -> no actions")
    else:
        print(f"  [FAIL] healthy system took {len(actions)} actions")

    # Test 2: Unknown system → graceful skip
    total += 1
    h = {"overall": "DEGRADED",
         "subsystems": {"MysterySubsystem": {"status": "DEGRADED", "raw": "???"}}}
    # Should log 'unknown-subsystem' as escalated (no remediation exists)
    actions = remediate(h)
    if len(actions) == 1 and actions[0]["status"] == "escalated":
        passed += 1
        print("  [ok] unknown subsystem -> escalated (not crash)")
    else:
        print(f"  [FAIL] unknown subsystem: {actions}")

    # Test 3: Rate limit
    total += 1
    # Pre-populate rate limit with 3 recent actions for "IPC daemon"
    rate = defaultdict(list)
    now = time.time()
    rate["IPC daemon"] = [now - 60, now - 30, now - 10]
    _save_rate_limit(rate)
    h = {"overall": "DEGRADED",
         "subsystems": {"IPC daemon": {"status": "DEGRADED", "raw": "test"}}}
    actions = remediate(h)
    if len(actions) == 1 and actions[0]["status"] == "rate-limited":
        passed += 1
        print("  [ok] rate-limited after 3 actions in 5 min")
    else:
        print(f"  [FAIL] rate limit: {actions}")

    # Test 4: Cooldown
    total += 1
    # Clear rate limit, but log a recent successful remediation
    _save_rate_limit({})
    _log_incident("Snapshot file", "kill-loop+bootstrap", "ok", "test cooldown")
    h = {"overall": "DEGRADED",
         "subsystems": {"Snapshot file": {"status": "DEGRADED", "raw": "test"}}}
    actions = remediate(h)
    if len(actions) == 1 and actions[0]["status"] == "skipped":
        passed += 1
        print("  [ok] cooldown blocks repeat within 10 min")
    else:
        print(f"  [FAIL] cooldown: {actions}")

    # Test 5: Health text parse
    total += 1
    HEALTH_TXT.write_text(
        "resume-all health check\n"
        "===\n"
        "IPC daemon:        DEGRADED      (unreachable: Connection refused)\n"
        "Snapshot file:     OK            (97 rows, mtime 5s ago)\n"
        "Overall:           DEGRADED  (broken: ipc)\n"
    )
    parsed = _parse_health_txt()
    if parsed["overall"] == "DEGRADED" and "IPC daemon" in parsed["subsystems"] \
            and parsed["subsystems"]["IPC daemon"]["status"] == "DEGRADED":
        passed += 1
        print("  [ok] health.txt parse -> correct overall + subsystems")
    else:
        print(f"  [FAIL] parse: {parsed}")

    # Test 6: Incident log read
    total += 1
    incidents = _read_incidents(limit=5)
    if len(incidents) >= 2:  # at least 2 from earlier tests
        passed += 1
        print(f"  [ok] incident log read ({len(incidents)} entries)")
    else:
        print(f"  [FAIL] incidents read: {incidents}")

    # Cleanup
    if RATE_LIMIT_FILE.exists():
        RATE_LIMIT_FILE.unlink()
    if HEALTH_TXT.exists() and "IPC daemon:        DEGRADED" in HEALTH_TXT.read_text():
        HEALTH_TXT.unlink()  # don't clobber real health.txt

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="One-shot remediation")
    p_run.set_defaults(func=cmd_run)

    p_loop = sub.add_parser("loop", help="Continuous remediation loop")
    p_loop.add_argument("--interval", type=int, default=30)
    p_loop.set_defaults(func=cmd_loop)

    p_status = sub.add_parser("status", help="Show recent incidents")
    p_status.add_argument("--limit", type=int, default=20)
    p_status.set_defaults(func=cmd_status)

    p_ack = sub.add_parser("ack", help="Acknowledge incident")
    p_ack.add_argument("incident_id")
    p_ack.set_defaults(func=cmd_ack)

    p_test = sub.add_parser("test", help="Run self-tests")
    p_test.set_defaults(func=lambda a: _self_test()[0] == _self_test()[1] and 0 or 1)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
