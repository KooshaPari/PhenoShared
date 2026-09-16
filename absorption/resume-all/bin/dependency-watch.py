#!/opt/homebrew/bin/python3
"""dependency-watch — cross-session dependency tracker (Phase E07).

Polls ~/.local/share/resume-all/snapshot.jsonl every INTERVAL seconds, loads
~/.config/resume-all/dependencies.toml, and fires each declared dependency
when its trigger pane exits (tty no longer present) provided its depends_on
pane is also absent (idempotency guard).

Fire action: write a synthetic one-row snapshot.jsonl to a temp file and
hand off to resume-all.py via --snapshot-file. This routes through the same
backend dispatch logic the rest of the toolkit uses (Ghostty AppleScript
split / tmux new-window / zmx attach). Falls back to a no-op dry-run log
if --dry-run is passed.

Idempotency is enforced by tracking fired dependency NAMES in memory — a
transient snapshot miss (snapshot writer paused, pane respawning) will not
re-fire. The watcher's state is also persisted to a small JSON file
(STATE_PATH) so a restart doesn't double-fire the same dependency.

Safe to leave running. Logs every decision to LOG.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

DEPS_PATH = Path.home() / ".config/resume-all/dependencies.toml"
SNAPSHOT_PATH = Path.home() / ".local/share/resume-all/snapshot.jsonl"
LOG_PATH = Path.home() / ".local/share/resume-all/dependencies.log"
STATE_PATH = Path.home() / ".local/share/resume-all/dependencies.state.json"
RESUME_ALL = Path.home() / "bin/resume-all.py"
INTERVAL = 5  # seconds


def log(msg: str) -> None:
    """Append a timestamped message to LOG_PATH and echo to stderr."""
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line, file=sys.stderr, flush=True)


def load_dependencies(path: Path = DEPS_PATH) -> list[dict]:
    """Parse dependencies.toml. Returns [] if the file is missing."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        doc = tomllib.load(f)
    return list(doc.get("dependency") or [])


def load_snapshot(path: Path = SNAPSHOT_PATH) -> list[dict]:
    """Read snapshot.jsonl, skipping blank lines and malformed rows."""
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError as exc:
        log(f"ERROR: cannot read snapshot {path}: {exc}")
    return out


def present_ttys(rows: list[dict]) -> set[str]:
    """Return the set of ttys with a non-dead, PID>0 row.

    The "alive" predicate matches resume-watch.py: pid > 0 AND not flagged
    dead AND not pending. PIDs of 0 (i.e. tty existed but had no process)
    are treated as gone.
    """
    present: set[str] = set()
    for r in rows:
        if r.get("dead") or r.get("pending"):
            continue
        tty = (r.get("tty") or "").strip()
        pid = r.get("pid") or 0
        if tty and isinstance(pid, int) and pid > 0:
            present.add(tty)
    return present


def last_argv_for_tty(rows: list[dict], tty: str) -> str:
    """Most recent argv string for tty. Includes dead rows (last-known command)."""
    best = ""
    best_ts = ""
    for r in rows:
        if (r.get("tty") or "").strip() != tty:
            continue
        ts = r.get("ts") or ""
        if ts >= best_ts:
            best_ts = ts
            best = (r.get("argv") or "").strip()
    return best


def load_state(path: Path = STATE_PATH) -> dict:
    """Read persisted fire-state so a restart doesn't double-fire."""
    if not path.exists():
        return {"fired": []}
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"fired": []}
        data.setdefault("fired", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"fired": []}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    """Best-effort write of fire-state. Never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except OSError as exc:
        log(f"WARN: cannot persist state to {path}: {exc}")


def fire(dep: dict, dry_run: bool) -> bool:
    """Hand off the depends_on pane to resume-all via a synthetic snapshot.

    Returns True if the fire command was issued (or dry-run logged).
    Returns False on hard errors (missing resume-all binary, etc.).
    """
    name = dep.get("name", "<unnamed>")
    target = dep.get("depends_on", "?")
    if not RESUME_ALL.exists():
        log(f"ERROR: resume-all not found at {RESUME_ALL}")
        return False

    # Synthetic snapshot: one row, dead-ish, but resume-all's dispatch loop
    # doesn't read `dead` once it builds by_pane — it skips dead rows. So we
    # use a row with pid=0 and no dead flag. resume-all will treat this as
    # an argv-less pane and route it to the picker / new surface path.
    synthetic_row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "surface_id": "",
        "surface_name": "",
        "pane_id": f"g:{target}",
        "tty": target,
        "pid": 0,
        "cwd": "/",
        "argv": "zsh -l -i",
        "harness": "shell",
        "session_id": "",
        "session_id_source": "",
        "needs_picker": False,
        "ports": [],
        "zmx_name": "",
        "_fired_by": name,
    }

    if dry_run:
        log(f"DRY-RUN: would spawn {target} via resume-all (fired by {name})")
        return True

    try:
        fd, tmp_path = tempfile.mkstemp(prefix="dep-snap-", suffix=".jsonl")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps(synthetic_row) + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            cmd = [sys.executable, str(RESUME_ALL),
                   "--snapshot-file", tmp_path,
                   "--backend", "ghostty"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                log(f"WARN: resume-all exited rc={result.returncode} for {name} "
                    f"(stderr: {(result.stderr or '').strip()[:200]})")
            else:
                log(f"FIRE OK: resume-all dispatched {target} for dependency {name}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"ERROR: fire failed for {name}: {exc}")
        return False
    return True


def evaluate(dep: dict, present: set[str], rows: list[dict]) -> str:
    """Decide whether a dependency should fire right now.

    Returns one of:
        "skip:trigger-alive"      trigger pane is still in the snapshot
        "skip:argv-mismatch"      argv filter doesn't match
        "skip:regex-bad"          trigger_command_match is not a valid regex
        "skip:depends-on-alive"   depends_on already running (idempotency)
        "wait"                    delay_seconds > 0 — caller sleeps then fires
        "fire"                    all conditions met, fire immediately
    """
    trigger = (dep.get("trigger") or "").strip()
    depends = (dep.get("depends_on") or "").strip()
    match = (dep.get("trigger_command_match") or "").strip()
    delay = int(dep.get("delay_seconds") or 0)

    if not trigger or not depends:
        return "skip:trigger-alive"  # treat malformed as skip (caller logs)

    if trigger in present:
        return "skip:trigger-alive"

    if match:
        argv = last_argv_for_tty(rows, trigger)
        try:
            if not re.search(match, argv):
                return "skip:argv-mismatch"
        except re.error:
            return "skip:regex-bad"

    if depends in present:
        return "skip:depends-on-alive"

    return "wait" if delay > 0 else "fire"


def run_once(dry_run: bool, state: dict) -> int:
    """One pass over the snapshot. Returns the number of fires issued."""
    deps = load_dependencies()
    if not deps:
        return 0
    rows = load_snapshot()
    present = present_ttys(rows)
    fired_names = set(state.get("fired") or [])
    fires = 0
    for dep in deps:
        name = dep.get("name") or ""
        if not name:
            log("WARN: dependency missing name; skipping")
            continue
        if name in fired_names:
            continue
        decision = evaluate(dep, present, rows)
        trigger = dep.get("trigger", "?")
        depends = dep.get("depends_on", "?")
        if decision.startswith("skip:"):
            log(f"{decision:24s} {name} trigger={trigger} depends={depends}")
            # skip:* is terminal — mark fired so we don't re-evaluate every cycle
            # for the same dead pane.
            fired_names.add(name)
            continue
        delay = int(dep.get("delay_seconds") or 0)
        if decision == "wait":
            log(f"WAIT {delay:>3}s {name} trigger={trigger} depends={depends}")
            # Sleep synchronously for delay_seconds, then re-evaluate present
            # to catch the depends_on pane appearing during the wait.
            time.sleep(delay)
            rows = load_snapshot()
            present = present_ttys(rows)
            if depends in present:
                log(f"skip:depends-on-alive-after-wait {name}")
                fired_names.add(name)
                continue
        log(f"FIRE  {name} trigger={trigger} (gone) -> spawn {depends}")
        if fire(dep, dry_run=dry_run):
            fires += 1
        fired_names.add(name)

    state["fired"] = sorted(fired_names)
    save_state(state)
    return fires


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dependency-watch",
        description="Cross-session dependency watcher (Phase E07).",
    )
    parser.add_argument("--once", action="store_true",
                        help="evaluate one pass and exit (no polling loop)")
    parser.add_argument("--dry-run", action="store_true",
                        help="log decisions without spawning anything")
    parser.add_argument("--interval", type=int, default=INTERVAL,
                        help=f"poll interval in seconds (default {INTERVAL})")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not DEPS_PATH.exists():
        print(f"dependency-watch: no declarations at {DEPS_PATH}; exiting",
              file=sys.stderr)
        return 0

    state = load_state()
    if args.once:
        n = run_once(args.dry_run, state)
        return 0 if n >= 0 else 1

    log(f"dependency-watch started interval={args.interval}s dry_run={args.dry_run}")
    while True:
        try:
            run_once(args.dry_run, state)
        except KeyboardInterrupt:
            log("interrupted; exiting")
            return 0
        except Exception as exc:
            log(f"ERROR: loop iteration failed: {exc}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
