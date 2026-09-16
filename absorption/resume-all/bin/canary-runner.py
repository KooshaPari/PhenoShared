#!/opt/homebrew/bin/python3
"""
canary-runner.py — Wires the canary system (F12) to launchd.

Runs every 5 minutes (StartInterval=300):
  1. Polls canary health for each enabled target
  2. Records results in canary-state.json
  3. If any canary target is degraded, attempts rollback
  4. Generates action items for F15 postmortem to consume

This is the bridge between the canary registry (canary.py) and the
launchd-managed recovery system (incident-respond.py).

Subcommands:
    canary-runner.py tick       # one-shot poll + record
    canary-runner.py loop       # continuous (for launchd)
    canary-runner.py status     # print current state
    canary-runner.py test
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".local" / "share" / "resume-all"
STATE_FILE = STATE_DIR / "canary-state.json"
CANARY_TOML = HOME / ".config" / "resume-all" / "canary.toml"
SNAPSHOT_DIR = STATE_DIR

LAUNCHD_UID = __import__("os").getuid()
LAUNCHD_GUI_DOMAIN = f"gui/{LAUNCHD_UID}"


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {"ticks": [], "degraded_targets": []}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {"ticks": [], "degraded_targets": []}


def _write_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _run_canary_subcommand(subcommand: str, *args) -> tuple[int, str]:
    """Run canary.py subcommand. Returns (returncode, stdout)."""
    cmd = [sys.executable, str(HOME / "bin" / "canary.py"), subcommand, *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired:
        return -1, "(timeout)"
    except FileNotFoundError:
        return -2, "(canary.py not found)"


def tick() -> dict:
    """Run one polling cycle. Returns the action summary."""
    state = _read_state()
    actions = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "targets_polled": [],
        "degraded": [],
        "rolled_back": [],
        "healthy": [],
    }

    if not CANARY_TOML.exists():
        actions["error"] = "canary.toml not configured"
        return actions

    # Parse canary.toml to get target list (lightweight parse)
    targets = []
    in_target = False
    for line in CANARY_TOML.read_text().splitlines():
        line = line.strip()
        if line.startswith("[targets."):
            target = line.split(".")[1].rstrip("]").strip()
            in_target = True
            current = {"name": target, "enabled": True}
            targets.append(current)
            continue
        if in_target and line.startswith("enabled"):
            current["enabled"] = line.split("=")[1].strip().lower() == "true"

    # Poll each enabled target
    for t in targets:
        if not t["enabled"]:
            continue
        actions["targets_polled"].append(t["name"])
        rc, output = _run_canary_subcommand("health", t["name"])
        if rc != 0:
            actions["degraded"].append({
                "target": t["name"],
                "reason": output[:200],
            })
            continue
        # Parse canary health output
        if "DEGRADED" in output:
            actions["degraded"].append({
                "target": t["name"],
                "reason": "health returned DEGRADED",
            })
        else:
            actions["healthy"].append(t["name"])

    # Roll back any degraded targets (best-effort)
    for d in actions["degraded"]:
        rc, output = _run_canary_subcommand("rollback", d["target"])
        if rc == 0:
            actions["rolled_back"].append(d["target"])

    # Persist
    state["ticks"].append(actions)
    state["ticks"] = state["ticks"][-100:]  # keep last 100
    state["degraded_targets"] = [d["target"] for d in actions["degraded"]]
    state["last_tick"] = actions["ts_iso"]
    _write_state(state)

    return actions


def cmd_tick(args: argparse.Namespace) -> int:
    actions = tick()
    n_polled = len(actions.get("targets_polled", []))
    n_degraded = len(actions.get("degraded", []))
    n_rolled = len(actions.get("rolled_back", []))
    n_healthy = len(actions.get("healthy", []))
    print(f"canary-runner: polled {n_polled} targets")
    print(f"  healthy:   {n_healthy}")
    print(f"  degraded:  {n_degraded}")
    print(f"  rolled-back: {n_rolled}")
    if actions.get("error"):
        print(f"  error: {actions['error']}")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    interval = args.interval
    print(f"canary-runner: looping every {interval}s (Ctrl-C to stop)")
    try:
        while True:
            tick()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\ncanary-runner: stopped")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = _read_state()
    ticks = state.get("ticks", [])
    print(f"Canary runner state ({len(ticks)} ticks):")
    print(f"  Last tick:    {state.get('last_tick', 'never')}")
    print(f"  Degraded now: {state.get('degraded_targets', [])}")
    if ticks:
        last = ticks[-1]
        print(f"  Last poll:    {len(last.get('targets_polled', []))} targets, "
              f"{len(last.get('degraded', []))} degraded")
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

    print("=== canary-runner.py self-tests ===")

    # Test 1: state file shape
    state = _read_state()
    check("state has 'ticks' key", "ticks" in state)
    check("state has 'degraded_targets' key", "degraded_targets" in state)

    # Test 2: write state round-trip
    test_state = {"ticks": [{"ts": time.time(), "test": True}],
                  "degraded_targets": ["foo"]}
    _write_state(test_state)
    loaded = _read_state()
    check("state write/read round-trip",
          loaded.get("degraded_targets") == ["foo"])
    check("ticks preserved", len(loaded.get("ticks", [])) == 1)

    # Test 3: tick with no canary.toml
    backup = CANARY_TOML.read_text() if CANARY_TOML.exists() else None
    try:
        if CANARY_TOML.exists():
            CANARY_TOML.unlink()
        actions = tick()
        check("tick with no canary.toml returns gracefully",
              "error" in actions and "canary.toml not configured" in actions["error"])
    finally:
        if backup is not None:
            CANARY_TOML.write_text(backup)

    # Test 4: tick with valid canary.toml
    if backup is None:
        # No canary.toml to restore, create one
        CANARY_TOML.parent.mkdir(parents=True, exist_ok=True)
        CANARY_TOML.write_text(
            "[canary]\n"
            "cohort_size_pct = 5\n"
            "auto_rollback = true\n"
            "cohort_key = \"pid_mod_20\"\n"
            "\n"
            "[targets.test-target]\n"
            "production = \"1.0.0\"\n"
            "canary = \"1.1.0-rc1\"\n"
            "enabled = true\n"
            "auto_promote_after_successful_ticks = 100\n"
        )
    actions = tick()
    check("tick with valid canary.toml polls targets",
          len(actions.get("targets_polled", [])) >= 1)

    # Test 5: state retention (last 100)
    state = _read_state()
    check("state retains ticks", len(state.get("ticks", [])) >= 1)

    # Cleanup test state
    state["ticks"] = []
    state["degraded_targets"] = []
    _write_state(state)

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("tick").set_defaults(func=cmd_tick)

    p_loop = sub.add_parser("loop")
    p_loop.add_argument("--interval", type=int, default=300)
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
