#!/opt/homebrew/bin/python3
"""
postmortem.py — Phase F hardening item F15.

Generate a markdown post-incident report from incident logs, health-check
history, and crash-forensic timelines.

When something breaks, this script produces a structured report with:
  * Summary (one paragraph)
  * Timeline (events with timestamps)
  * Root cause (best-effort heuristic based on incident classes)
  * Contributing factors (what else was degraded)
  * Action items (derived from recurring patterns)

Output: ~/.local/share/resume-all/postmortem-YYYY-MM-DD.md

Usage:
    postmortem.py generate [--since 24h|7d|...] [--out PATH]
    postmortem.py template
    postmortem.py status
    postmortem.py test
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = Path.home()
SNAPSHOT_DIR = HOME / ".local" / "share" / "resume-all"
INCIDENTS_LOG = SNAPSHOT_DIR / "incidents.jsonl"
HEALTH_HISTORY = SNAPSHOT_DIR / "health-history.jsonl"
CRASH_FORENSIC = HOME / "bin" / "crash-forensic.py"
POSTMORTEM_DIR = SNAPSHOT_DIR

TIME_SPECS = {
    "1h": 3600,
    "6h": 21600,
    "12h": 43200,
    "24h": 86400,
    "7d": 604800,
    "30d": 2592000,
}

# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------


def _parse_since(spec: str) -> float:
    """Parse '24h' / '7d' / '<seconds>' into epoch seconds cutoff."""
    if spec in TIME_SPECS:
        return time.time() - TIME_SPECS[spec]
    if spec.endswith("h"):
        return time.time() - int(spec[:-1]) * 3600
    if spec.endswith("d"):
        return time.time() - int(spec[:-1]) * 86400
    if spec.isdigit():
        return time.time() - int(spec)
    return time.time() - 86400  # default 24h


def _format_ts(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _format_local(epoch: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(epoch))


# ---------------------------------------------------------------------------
# Incident reading
# ---------------------------------------------------------------------------


def _read_incidents(since_ts: float) -> list[dict]:
    if not INCIDENTS_LOG.exists():
        return []
    out = []
    for line in INCIDENTS_LOG.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("ts", 0) >= since_ts:
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# Crash-forensic integration
# ---------------------------------------------------------------------------


def _run_crash_forensic(since_ts: float) -> str:
    """Invoke crash-forensic.py and return its text output."""
    delta = int(time.time() - since_ts)
    try:
        result = subprocess.run(
            [sys.executable, str(CRASH_FORENSIC), f"--since={delta}s",
             "--format", "text"],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"(crash-forensic unavailable: {e})"


# ---------------------------------------------------------------------------
# Root cause heuristics
# ---------------------------------------------------------------------------


def _classify_root_cause(incidents: list[dict]) -> str:
    """Best-effort root cause based on incident class distribution."""
    if not incidents:
        return "No incidents in window. Likely transient false alarm."

    classes = Counter(i.get("class", "?") for i in incidents
                      if i.get("status") == "ok")
    total = sum(classes.values())

    # Check canary state
    canary_state_file = SNAPSHOT_DIR / "canary-state.json"
    canary_note = ""
    if canary_state_file.exists():
        try:
            canary_state = json.loads(canary_state_file.read_text())
            degraded = canary_state.get("degraded_targets", [])
            if degraded:
                canary_note = (
                    f" Canary targets currently degraded: "
                    f"{', '.join(degraded)}."
                )
        except json.JSONDecodeError:
            pass

    # If 80%+ of incidents are one class, that's the root cause
    if classes:
        top_class, top_count = classes.most_common(1)[0]
        if top_count / total >= 0.8 and total >= 3:
            return (
                f"Recurring `{top_class}` failures — automated remediation "
                f"kicked in {top_count} times. Underlying issue not yet "
                f"resolved (system cycles between degraded → fixed → degraded)."
            )

    # IPC + snapshot both fail = launchd cascade
    if "IPC daemon" in classes and "Snapshot file" in classes:
        return (
            "Cascading launchd failure: both IPC daemon and snapshot loop "
            "fell over together. Root cause likely shared (PATH, environment, "
            "or filesystem state at bootout/bootstrap boundary)."
        )

    # All launchd jobs degraded = system-level issue
    job_incidents = sum(c for k, c in classes.items()
                        if k.startswith("com.kooshapari."))
    if job_incidents >= 3:
        return (
            "Multiple launchd-managed jobs degraded simultaneously. "
            "Likely cause: launchd itself in a bad state (cache, "
            "Bootstrap context, or kernel-level resource exhaustion)."
        )

    return (
        f"Mixed incident classes ({', '.join(c for c, _ in classes.most_common(3))}). "
        f"Recommend reviewing logs around {_format_ts(min(i.get('ts', 0) for i in incidents))} "
        f"for the trigger event."
    )


def _contributing_factors(incidents: list[dict]) -> list[str]:
    """Heuristic contributing factors based on incident patterns."""
    factors = []
    classes = Counter(i.get("class", "?") for i in incidents)

    if classes.get("IPC daemon", 0) >= 2:
        factors.append(
            "- IPC daemon stability: restarted multiple times in window. "
            "Check `~/Library/Logs/resume-all/ipc.err.log` for `Broken pipe` "
            "patterns indicating the daemon crashes mid-request."
        )
    if classes.get("Snapshot file", 0) >= 2:
        factors.append(
            "- Snapshot loop reliability: walker timeouts (procs/thegent-proc-zig) "
            "may indicate the system is under heavy load or the binary path "
            "is wrong."
        )
    if any(i.get("status") == "rate-limited" for i in incidents):
        factors.append(
            "- Rate limits hit on incident-respond.py. The same class fired "
            "more than 3 times in 5 minutes — automation gave up. Consider "
            "raising MAX_ACTIONS_PER_5MIN or fixing the root cause faster."
        )
    if any(i.get("status") == "skipped" for i in incidents):
        factors.append(
            "- Cooldown blocks hit (same class remediated within 10 min). "
            "If the system recovered the first time, why did it fail again? "
            "Probably the fix didn't take effect."
        )
    if not factors:
        factors.append(
            "- No obvious recurring patterns. Single isolated failure."
        )
    return factors


def _action_items(incidents: list[dict]) -> list[str]:
    """Generate actionable items from incidents."""
    items = []
    classes = Counter(i.get("class", "?") for i in incidents
                      if i.get("status") in ("ok", "escalated"))

    if classes.get("IPC daemon", 0) >= 3:
        items.append(
            "- [P1] Investigate IPC daemon root cause. The pattern of "
            "`Broken pipe` followed by `Connection refused` indicates "
            "the daemon is starting but failing to bind its socket. "
            "Check the binary's path handling and verify HOME env var "
            "is being respected under launchd. Consider running "
            "`ipc-recover.py recover` as a fallback."
        )
    if classes.get("Snapshot file", 0) >= 2:
        items.append(
            "- [P2] Review snapshot walker timeouts. `procs` is timing out "
            "in 3s, falling through to `thegent-proc-zig` (10s), then "
            "`thegent-procx` (15s). Total 28s + write is right at the 30s "
            "loop interval. Either reduce timeouts or increase interval."
        )
    if any(i.get("status") == "escalated" for i in incidents):
        items.append(
            "- [P2] Add a remediation path for the escalated subsystems. "
            "Currently they log only — no recovery action is attempted."
        )
    if any(i.get("status") == "rate-limited" for i in incidents):
        items.append(
            "- [P3] Tune incident-respond rate limits. Either raise "
            "MAX_ACTIONS_PER_5MIN or shorten the cooldown if legitimate "
            "recovery actions are getting blocked."
        )

    # Canary targets (F12) — check canary-runner state
    _canary_items = _canary_action_items()
    items.extend(_canary_items)

    if not items:
        items.append(
            "- [P3] No urgent action items — system recovered. Continue "
            "monitoring via health-check.py + incident-respond.py."
        )
    return items


def _canary_action_items() -> list[str]:
    """Read canary-runner state and generate items if any targets degraded."""
    canary_state_file = SNAPSHOT_DIR / "canary-state.json"
    if not canary_state_file.exists():
        return []
    try:
        state = json.loads(canary_state_file.read_text())
    except json.JSONDecodeError:
        return []
    degraded = state.get("degraded_targets", [])
    if not degraded:
        return []
    items = [f"- [P2] Canary targets degraded: {', '.join(degraded)}. "
             f"Run `canary-runner.py status` and `canary.py health <target>` "
             f"for details. Consider `canary.py rollback <target>` if the "
             f"canary cohort is unstable."]
    return items


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _format_timeline(incidents: list[dict]) -> str:
    if not incidents:
        return "_No incidents in window._"
    lines = ["| Time | Class | Action | Status | Detail |",
             "|------|-------|--------|--------|--------|"]
    for inc in sorted(incidents, key=lambda x: x.get("ts", 0)):
        ts = inc.get("ts_iso", "?")
        cls = inc.get("class", "?")
        action = inc.get("action", "?")
        status = inc.get("status", "?")
        detail = inc.get("detail", "")[:80]
        lines.append(f"| {ts} | {cls} | {action} | {status} | {detail} |")
    return "\n".join(lines)


def generate_report(since_ts: float, out_path: Path | None = None) -> Path:
    """Build a postmortem markdown report. Returns the output path."""
    incidents = _read_incidents(since_ts)
    since_iso = _format_ts(since_ts)
    until_iso = _format_ts(time.time())

    total = len(incidents)
    ok = sum(1 for i in incidents if i.get("status") == "ok")
    escalated = sum(1 for i in incidents if i.get("status") == "escalated")
    rate_limited = sum(1 for i in incidents if i.get("status") == "rate-limited")
    skipped = sum(1 for i in incidents if i.get("status") == "skipped")

    root_cause = _classify_root_cause(incidents)
    factors = _contributing_factors(incidents)
    action_items_list = _action_items(incidents)
    timeline = _format_timeline(incidents)

    summary = (
        f"Between {since_iso} and {until_iso}, the resume-all toolkit "
        f"experienced **{total} incident(s)**: {ok} auto-remediated, "
        f"{escalated} escalated (no recovery path), "
        f"{rate_limited} rate-limited, "
        f"{skipped} cooldown-blocked."
    )

    crash_section = _run_crash_forensic(since_ts)

    md = f"""# Postmortem — {until_iso[:10]}

_Generated {until_iso} from `~/.local/share/resume-all/incidents.jsonl`._

## Summary

{summary}

## Timeline

{timeline}

## Root cause

{root_cause}

## Contributing factors

{chr(10).join(factors)}

## Action items

{chr(10).join(action_items_list)}

## Crash-forensic excerpt

```
{crash_section[:2000]}
```

## References

- Incident log: `~/.local/share/resume-all/incidents.jsonl`
- Health history: `~/.local/share/resume-all/health.txt`
- Runbook: `~/handoff/RUNBOOK.md` (when present)
- Tool: `~/bin/postmortem.py generate --since <window>`
"""

    if out_path is None:
        out_path = POSTMORTEM_DIR / f"postmortem-{until_iso[:10]}.md"
    out_path.write_text(md)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    since_ts = _parse_since(args.since)
    out = Path(args.out).expanduser() if args.out else None
    path = generate_report(since_ts, out)
    print(f"Generated: {path}")
    return 0


def cmd_template(args: argparse.Namespace) -> int:
    print(generate_report(time.time() - 86400).read_text()[:1500])
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not INCIDENTS_LOG.exists():
        print("No incidents logged.")
        return 0
    incidents = _read_incidents(0)  # all
    print(f"Total incidents: {len(incidents)}")
    by_class = Counter(i.get("class", "?") for i in incidents)
    print("By class:")
    for cls, count in by_class.most_common(10):
        print(f"  {count:4d}  {cls}")
    return 0


def _self_test() -> tuple[int, int]:
    passed = 0
    total = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}")

    print("=== postmortem.py self-tests ===")

    # Test 1: 24h parse
    t = _parse_since("24h")
    check("24h parse ~ 1 day back", abs(t - (time.time() - 86400)) < 5)

    # Test 2: 7d parse
    t = _parse_since("7d")
    check("7d parse ~ 7 days back", abs(t - (time.time() - 604800)) < 5)

    # Test 3: classify empty
    msg = _classify_root_cause([])
    check("classify empty -> 'no incidents'",
          "no incidents" in msg.lower() or "false alarm" in msg.lower())

    # Test 4: classify recurring IPC daemon
    incidents = [
        {"class": "IPC daemon", "status": "ok", "ts": time.time() - i * 60}
        for i in range(5)
    ]
    msg = _classify_root_cause(incidents)
    check("classify 5x IPC daemon -> mentions IPC daemon", "IPC daemon" in msg)

    # Test 5: action items generation
    items = _action_items([
        {"class": "IPC daemon", "status": "ok", "ts": time.time() - i * 60}
        for i in range(4)
    ])
    check("action items for repeated IPC daemon -> has P1",
          any("P1" in i for i in items))

    # Test 6: contributing factors for rate-limited
    factors = _contributing_factors([
        {"class": "IPC daemon", "status": "rate-limited", "ts": time.time()}
    ])
    check("factors include rate limit mention",
          any("rate" in f.lower() for f in factors))

    # Test 7: full generate round-trip
    try:
        out = POSTMORTEM_DIR / "postmortem-self-test.md"
        path = generate_report(time.time() - 3600, out)
        ok = path.exists() and path.stat().st_size > 500
        check(f"generate round-trip -> {path.stat().st_size if path.exists() else 0} bytes",
              ok)
        if path.exists():
            path.unlink()
    except Exception as e:
        check(f"generate crashed: {e}", False)

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("generate", help="Generate postmortem report")
    p_gen.add_argument("--since", default="24h",
                       help="Time window: 1h/6h/12h/24h/7d/30d or seconds")
    p_gen.add_argument("--out", default=None,
                       help="Output path (default: postmortem-YYYY-MM-DD.md)")
    p_gen.set_defaults(func=cmd_generate)

    p_tmpl = sub.add_parser("template", help="Print template")
    p_tmpl.set_defaults(func=cmd_template)

    p_status = sub.add_parser("status", help="Show incident counts")
    p_status.set_defaults(func=cmd_status)

    p_test = sub.add_parser("test", help="Run self-tests")
    p_test.set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
