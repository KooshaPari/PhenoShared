#!/opt/homebrew/bin/python3
"""
flag-tray-bridge.py — Wires flag.py changes to the tray menu (item 6).

Watches `flag-history.jsonl` and writes a recent-changes summary that
the tray can read. Subcommands:
  flag-tray-bridge.py tick         # one-shot summary update
  flag-tray-bridge.py loop         # continuous (for launchd)
  flag-tray-bridge.py status       # print recent changes for tray
  flag-tray-bridge.py test

Output: ~/.local/share/resume-all/flag-recent.json
Schema:
{
  "ts": 1234567890,
  "ts_iso": "2026-08-08T...",
  "recent_changes": [
    {"flag": "auto_resume_after_crash", "old": true, "new": false,
     "ts": 1234567000, "ts_iso": "..."}
  ],
  "stale_count": 0
}

The tray app can poll this file (or IPC daemon's `flag.recent` method)
every 30s and show a badge or menu item if recent_changes is non-empty.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".local" / "share" / "resume-all"
HISTORY_FILE = STATE_DIR / "flag-history.jsonl"
RECENT_FILE = STATE_DIR / "flag-recent.json"
STALE_THRESHOLD_SECONDS = 300  # 5 min


def _read_recent_changes(since_ts: float | None = None) -> list[dict]:
    """Read flag history and return recent changes."""
    if not HISTORY_FILE.exists():
        return []
    if since_ts is None:
        since_ts = time.time() - 86400  # default 24h
    out = []
    for line in HISTORY_FILE.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("ts", 0) >= since_ts:
            out.append(e)
    return out


def _detect_stale_flags(changes: list[dict]) -> list[str]:
    """Find flags that were changed and haven't been re-confirmed recently."""
    last_change = {}
    for c in changes:
        flag = c.get("flag")
        if flag:
            last_change[flag] = c.get("ts", 0)
    now = time.time()
    stale = [f for f, ts in last_change.items()
             if now - ts > STALE_THRESHOLD_SECONDS]
    return stale


def tick() -> dict:
    """Run one polling cycle. Returns the summary."""
    recent = _read_recent_changes(time.time() - 3600)  # last hour
    stale = _detect_stale_flags(recent)
    summary = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "recent_changes": recent[-10:],  # last 10 changes max
        "stale_count": len(stale),
        "stale_flags": stale,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Atomic write
    tmp = RECENT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(summary, indent=2))
    tmp.rename(RECENT_FILE)
    return summary


def cmd_tick(args: argparse.Namespace) -> int:
    summary = tick()
    print(f"flag-tray-bridge: wrote {len(summary['recent_changes'])} "
          f"recent changes, {summary['stale_count']} stale")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    interval = args.interval
    print(f"flag-tray-bridge: looping every {interval}s (Ctrl-C to stop)")
    try:
        while True:
            tick()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nflag-tray-bridge: stopped")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print current state formatted for tray."""
    if not RECENT_FILE.exists():
        tick()  # generate fresh
    summary = json.loads(RECENT_FILE.read_text())
    print(f"Recent changes ({len(summary['recent_changes'])}):")
    for c in summary["recent_changes"]:
        flag = c.get("flag", "?")
        old = c.get("old")
        new = c.get("new")
        ts = c.get("ts_iso", "?")
        print(f"  {ts}  {flag:30s} {old!r:15s} -> {new!r}")
    if summary["stale_count"]:
        print(f"\nStale flags ({summary['stale_count']}):")
        for f in summary["stale_flags"]:
            print(f"  {f}")
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

    print("=== flag-tray-bridge.py self-tests ===")

    # Test 1: tick with no history
    backup_history = HISTORY_FILE.read_text() if HISTORY_FILE.exists() else None
    backup_recent = RECENT_FILE.read_text() if RECENT_FILE.exists() else None
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        summary = tick()
        check("tick with empty history works",
              summary["recent_changes"] == [])
        check("summary has ts", "ts" in summary)
        check("summary has ts_iso", "ts_iso" in summary)
        check("summary has stale_count", "stale_count" in summary)

        # Test 2: recent.json written
        check("flag-recent.json exists", RECENT_FILE.exists())

        # Test 3: write some history, then tick
        now = time.time()
        HISTORY_FILE.write_text(
            json.dumps({"ts": now - 60, "flag": "auto_resume",
                        "old": True, "new": False, "reason": "test"}) + "\n"
            + json.dumps({"ts": now - 30, "flag": "verbose_logging",
                        "old": False, "new": True, "reason": "test2"}) + "\n"
        )
        summary = tick()
        check("recent_changes count = 2", len(summary["recent_changes"]) == 2)
        check("flags captured", "auto_resume" in [c.get("flag")
                                                   for c in summary["recent_changes"]])

        # Test 4: stale detection
        HISTORY_FILE.write_text(
            json.dumps({"ts": now - 3600, "flag": "old_flag",
                        "old": True, "new": False}) + "\n"
        )
        summary = tick()
        check("stale_flags includes old_flag",
              "old_flag" in summary["stale_flags"])

        # Test 5: JSON output is valid
        check("flag-recent.json valid JSON",
              isinstance(json.loads(RECENT_FILE.read_text()), dict))
    finally:
        if backup_history is not None:
            HISTORY_FILE.write_text(backup_history)
        elif HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        if backup_recent is not None:
            RECENT_FILE.write_text(backup_recent)
        elif RECENT_FILE.exists():
            RECENT_FILE.unlink()

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("tick").set_defaults(func=cmd_tick)

    p_loop = sub.add_parser("loop")
    p_loop.add_argument("--interval", type=int, default=30)
    p_loop.set_defaults(func=cmd_loop)

    sub.add_parser("status").set_defaults(func=cmd_status)

    sub.add_parser("test").set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv[1:])
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
