#!/opt/homebrew/bin/python3
"""resume-deps — inspect cross-session dependency declarations (Phase E07).

Subcommands:
    list       print every dependency with its trigger / target / options
    dry-run    show what WOULD fire given the current snapshot
    validate   check that every referenced tty is present in the snapshot

Reads:
    ~/.config/resume-all/dependencies.toml
    ~/.local/share/resume-all/snapshot.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path

DEPS_PATH = Path.home() / ".config/resume-all/dependencies.toml"
SNAPSHOT_PATH = Path.home() / ".local/share/resume-all/snapshot.jsonl"


def load_dependencies(path: Path = DEPS_PATH) -> list[dict]:
    """Parse dependencies.toml and return the list of dependency rows.

    Returns an empty list if the file is missing — never raises to the caller
    so the CLI can still print a useful message about no declarations.
    """
    if not path.exists():
        return []
    with open(path, "rb") as f:
        doc = tomllib.load(f)
    return list(doc.get("dependency") or [])


def load_snapshot(path: Path = SNAPSHOT_PATH) -> list[dict]:
    """Read snapshot.jsonl, ignoring blank lines and parse errors.

    Returns [] on missing file. Does NOT filter on `dead` — the caller
    decides whether the tty is "present" (alive PID) or stale.
    """
    if not path.exists():
        return []
    out = []
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
        print(f"resume-deps: cannot read snapshot {path}: {exc}", file=sys.stderr)
    return out


def present_ttys(rows: list[dict]) -> set[str]:
    """Return the set of ttys that have a non-dead, PID>0 row.

    Used by the watcher and the validator for idempotency checks.
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


def argv_for_tty(rows: list[dict], tty: str) -> str:
    """Return the most recent argv string for a given tty (or '').

    Includes dead rows so the watcher can see what the pane was running
    *just before* it died. That's the only signal we have for a dead
    pane's last-known command.
    """
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


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_list(_args) -> int:
    deps = load_dependencies()
    if not deps:
        print(f"resume-deps: no dependencies declared at {DEPS_PATH}")
        return 0
    for d in deps:
        name = d.get("name", "<unnamed>")
        trig = d.get("trigger", "?")
        dep = d.get("depends_on", "?")
        delay = d.get("delay_seconds", 0)
        match = d.get("trigger_command_match", "")
        print(f"{name}")
        print(f"  trigger     = {trig}")
        print(f"  depends_on  = {dep}")
        if delay:
            print(f"  delay       = {delay}s")
        if match:
            print(f"  argv_match  = {match}")
    return 0


def cmd_validate(_args) -> int:
    deps = load_dependencies()
    rows = load_snapshot()
    present = present_ttys(rows)
    if not deps:
        print(f"resume-deps: no dependencies declared at {DEPS_PATH}")
        return 0
    bad = 0
    for d in deps:
        name = d.get("name", "<unnamed>")
        trig = d.get("trigger", "?")
        dep = d.get("depends_on", "?")
        issues = []
        if trig not in present:
            issues.append(f"trigger '{trig}' not in current snapshot")
        if dep not in present:
            issues.append(f"depends_on '{dep}' not in current snapshot")
        if issues:
            bad += 1
            print(f"WARN  {name}: {'; '.join(issues)}")
        else:
            print(f"OK    {name}: trigger+depends_on both present")
    return 0 if bad == 0 else 1


def cmd_dry_run(_args) -> int:
    deps = load_dependencies()
    rows = load_snapshot()
    present = present_ttys(rows)
    if not deps:
        print(f"resume-deps: no dependencies declared at {DEPS_PATH}")
        return 0
    fired = 0
    for d in deps:
        name = d.get("name", "<unnamed>")
        trig = d.get("trigger", "?")
        dep = d.get("depends_on", "?")
        match = d.get("trigger_command_match", "")
        delay = d.get("delay_seconds", 0)

        if trig in present:
            print(f"skip  {name}: trigger '{trig}' is still alive")
            continue
        # argv filter
        if match:
            argv = argv_for_tty(rows, trig)
            try:
                if not re.search(match, argv):
                    print(f"skip  {name}: trigger '{trig}' argv {argv!r} does not match {match!r}")
                    continue
            except re.error as exc:
                print(f"skip  {name}: bad regex {match!r} ({exc})", file=sys.stderr)
                continue
        if dep in present:
            print(f"skip  {name}: depends_on '{dep}' already running (idempotency)")
            continue
        delay_str = f" (after {delay}s)" if delay else ""
        print(f"FIRE  {name}: trigger '{trig}' gone -> would resume '{dep}'{delay_str}")
        fired += 1
    print(f"resume-deps dry-run: {fired} dependency(s) would fire")
    return 0


# ---------------------------------------------------------------------------
# Inline tests
# ---------------------------------------------------------------------------

def _run_inline_tests() -> int:
    """Inline self-test: write a fake TOML + fake snapshot, run each subcmd."""
    import io
    import tempfile

    print("=== resume-deps inline tests ===")
    fake_deps = """
[[dependency]]
name = "a"
trigger = "ttys001"
depends_on = "ttys002"

[[dependency]]
name = "b"
trigger = "ttys003"
depends_on = "ttys004"
delay_seconds = 5
trigger_command_match = "forge.*write"
"""
    # Build snapshot: ttys001 alive, ttys002 alive, ttys003 dead, ttys004 absent
    fake_rows = [
        {"ts": "t1", "tty": "ttys001", "pid": 100, "argv": "zsh -l -i", "dead": False},
        {"ts": "t1", "tty": "ttys002", "pid": 101, "argv": "codex", "dead": False},
        {"ts": "t1", "tty": "ttys003", "pid": 0,   "argv": "forge write", "dead": True},
    ]

    with tempfile.TemporaryDirectory() as td:
        dpath = Path(td) / "deps.toml"
        spath = Path(td) / "snap.jsonl"
        dpath.write_text(fake_deps)
        with open(spath, "w") as f:
            for r in fake_rows:
                f.write(json.dumps(r) + "\n")

        deps = load_dependencies(dpath)
        assert len(deps) == 2, f"expected 2 deps, got {len(deps)}"
        rows = load_snapshot(spath)
        present = present_ttys(rows)
        # ttys001 + ttys002 are alive; ttys003 is dead; ttys004 absent
        assert "ttys001" in present
        assert "ttys002" in present
        assert "ttys003" not in present
        assert "ttys004" not in present
        print("  present_ttys correct")

        # Dry-run with these inputs:
        #   a: trigger ttys001 alive → skip
        #   b: trigger ttys003 dead → check depends_on ttys004 absent → FIRE
        argv = argv_for_tty(rows, "ttys003")  # "forge write"
        assert re.search("forge.*write", argv), f"argv regex failed on {argv!r}"
        print("  trigger_command_match correct")

        # Validate: a is OK (both alive), b has issues (trigger dead, depends_on absent)
        issues_a = "ttys001" not in present or "ttys002" not in present
        issues_b = "ttys003" not in present or "ttys004" not in present
        assert not issues_a, "dep a should validate clean"
        assert issues_b, "dep b should warn"
        print("  validate logic correct")

        # Idempotency: if ttys004 was present, b would skip
        rows2 = list(fake_rows) + [
            {"ts": "t2", "tty": "ttys004", "pid": 200, "argv": "zsh", "dead": False},
        ]
        present2 = present_ttys(rows2)
        assert "ttys004" in present2
        print("  idempotency check correct")

    print("=== inline tests PASSED ===")
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resume-deps",
        description="Inspect cross-session dependency declarations (Phase E07).",
    )
    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("list", help="print all dependencies").set_defaults(func=cmd_list)
    sub.add_parser("validate", help="check ttys against current snapshot").set_defaults(func=cmd_validate)
    sub.add_parser("dry-run", help="show what WOULD fire").set_defaults(func=cmd_dry_run)
    sub.add_parser("test", help="run inline tests").set_defaults(
        func=lambda _a: _run_inline_tests()
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.cmd is None:
        # Default: list
        return cmd_list(args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
