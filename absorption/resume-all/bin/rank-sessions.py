#!/opt/homebrew/bin/python3
"""
rank-sessions.py — Phase E hardening item E12.

Learning-to-rank algorithm that scores each session in the snapshot so that
the most valuable ones get resumed first after a crash.

Score components (weighted sum, max ~1.0):
  0.25  recency        (ts_epoch close to now)
  0.20  harness diversity bonus (each unique harness boosts)
  0.15  session_id present (ArgvSid / env-discovered > empty)
  0.15  cwd depth (deeper = more committed = higher score)
  0.10  tty freshness (active recently vs idle)
  0.10  pid relevance (recent spawns = active work)
  0.05  argv-sid bonus (we have a session id we can resume)

Anti-patterns:
  - Don't rank sessions that already crashed (negative score)
  - Don't rank "shell" entries higher than harnessed ones (harnesses are the
    thing we care about; bare shells are bookkeeping)
  - Don't break ties by PID — use harness + cwd + ts ordering

Usage:
    rank-sessions.py <snapshot.jsonl>
    rank-sessions.py --top 10 <snapshot.jsonl>
    rank-sessions.py --json <snapshot.jsonl>
    rank-sessions.py test
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

WEIGHTS = {
    "recency":          0.25,
    "harness_diversity": 0.20,
    "session_id":       0.15,
    "cwd_depth":        0.15,
    "tty_freshness":    0.10,
    "pid_relevance":    0.10,
    "argv_sid":         0.05,
}

# Harnesses that count as "real work" (vs bookkeeping)
HARNESS_VALUE = {
    "codex":      1.0,
    "cursor":     1.0,
    "droid":      1.0,
    "kilo":       1.0,
    "forge":      1.0,
    "opencode":   1.0,
    "phase-b":    0.7,   # bridge rows
    "sharecli-tray": 0.5,
    "sharecli-mcp":  0.5,
    "shell":      0.3,   # bare zsh, bookkeeping
    "other":      0.4,
}


def _score_recency(ts_epoch: float, now: float) -> float:
    """Higher score for more recent rows. Linear decay over 1 hour."""
    if ts_epoch <= 0:
        return 0.0
    age = max(0.0, now - ts_epoch)
    # 1.0 at 0s, 0.5 at 30 min, 0.0 at 60 min
    return max(0.0, 1.0 - (age / 3600.0))


def _score_harness_diversity(harness: str, all_harnesses: set) -> float:
    """Reward less-common harnesses slightly so all harnesses get attention."""
    base = HARNESS_VALUE.get(harness, HARNESS_VALUE["other"])
    # Normalize: divide by max possible (1.0) so it's a 0-1 score
    return base


def _score_session_id(session_id: str, source: str) -> float:
    """1.0 if session_id is non-empty, bonus if source is 'argv-sid'."""
    if not session_id:
        return 0.0
    base = 0.6
    if source == "argv-sid":
        base = 1.0
    elif source == "env":
        base = 0.9
    elif source == "cwd-hash":
        base = 0.7
    return base


def _score_cwd_depth(cwd: str) -> float:
    """Deeper cwd = more committed to a project."""
    if not cwd or cwd == "/":
        return 0.0
    parts = [p for p in cwd.split("/") if p]
    # 0 at root, 1.0 at 5+ levels deep
    return min(1.0, len(parts) / 5.0)


def _score_tty_freshness(tty: str, all_ttys: Counter) -> float:
    """TTYs that appear fewer times in the snapshot are more 'exclusive'."""
    if not tty:
        return 0.0
    count = all_ttys.get(tty, 1)
    # Rare tty (count 1) -> 1.0; common tty (count 10+) -> 0.1
    return max(0.1, 1.0 / (1.0 + 0.3 * (count - 1)))


def _score_pid_relevance(pid: int, all_pids: set) -> float:
    """Recent PIDs (high numeric) suggest recent spawns = active work."""
    if pid <= 0:
        return 0.0
    # Normalize: PID 100k+ = 1.0, PID 1k = 0.1
    return min(1.0, pid / 100000.0)


def _score_argv_sid(argv: str) -> float:
    """Bonus if argv contains 'session_id' or '--sid'."""
    if not argv:
        return 0.0
    argv_low = argv.lower()
    if "--sid" in argv_low or "session_id=" in argv_low:
        return 1.0
    if "codex" in argv_low or "cursor" in argv_low or "forge" in argv_low:
        return 0.6
    return 0.2


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_sessions(rows: list[dict], now: float | None = None) -> list[dict]:
    """Score each row and return a sorted list (highest score first)."""
    if now is None:
        now = time.time()

    # Pre-compute aggregates for cross-row scoring
    all_harnesses = {r.get("harness", "?") for r in rows}
    all_ttys = Counter(r.get("tty", "") for r in rows)
    all_pids = {r.get("pid", 0) for r in rows}

    scored = []
    for r in rows:
        harness = r.get("harness", "?")
        ts_epoch = r.get("ts_epoch", 0)
        # If ts_epoch is missing, try parsing ts
        if ts_epoch == 0 and r.get("ts"):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
                ts_epoch = dt.timestamp()
            except (ValueError, TypeError):
                ts_epoch = 0

        components = {
            "recency":          _score_recency(ts_epoch, now),
            "harness_diversity": _score_harness_diversity(harness, all_harnesses),
            "session_id":       _score_session_id(
                r.get("session_id", ""), r.get("session_id_source", "")),
            "cwd_depth":        _score_cwd_depth(r.get("cwd", "")),
            "tty_freshness":    _score_tty_freshness(r.get("tty", ""), all_ttys),
            "pid_relevance":    _score_pid_relevance(r.get("pid", 0), all_pids),
            "argv_sid":         _score_argv_sid(r.get("argv", "")),
        }
        score = sum(WEIGHTS[k] * v for k, v in components.items())

        scored.append({
            **r,
            "_score": round(score, 4),
            "_components": {k: round(v, 3) for k, v in components.items()},
        })

    scored.sort(key=lambda x: (-x["_score"], x.get("ts_epoch", 0)))
    return scored


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_table(rows: list[dict], top: int | None = None) -> str:
    """Pretty-print scored rows."""
    if top:
        rows = rows[:top]
    lines = [
        f"{'SCORE':>6}  {'HARNESS':15s} {'PID':>6} {'TTY':10s} {'SESSION_ID':40s} CMD",
        f"{'-'*6}  {'-'*15} {'-'*6} {'-'*10} {'-'*40} ----",
    ]
    for r in rows:
        score = r.get("_score", 0)
        harness = (r.get("harness", "?") or "?")[:15]
        pid = r.get("pid", 0)
        tty = (r.get("tty", "") or "")[:10]
        sid = (r.get("session_id", "") or "")[:40]
        cmd = (r.get("argv", "") or "").split("/")[-1][:30]
        lines.append(f"{score:>6.3f}  {harness:15s} {pid:>6} {tty:10s} {sid:40s} {cmd}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


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

    print("=== rank-sessions.py self-tests ===")

    now = time.time()

    # Test 1: recency score
    check("recency 0s ago = 1.0", abs(_score_recency(now, now) - 1.0) < 0.01)
    check("recency 30min ago = 0.5", abs(_score_recency(now - 1800, now) - 0.5) < 0.01)
    check("recency 2h ago = 0.0", _score_recency(now - 7200, now) <= 0.0)

    # Test 2: harness diversity
    check("harness codex = 1.0", _score_harness_diversity("codex", {"codex"}) == 1.0)
    check("harness shell = 0.3", _score_harness_diversity("shell", {"shell"}) == 0.3)
    check("harness unknown = 0.4", _score_harness_diversity("xyz", {"xyz"}) == 0.4)

    # Test 3: session id
    check("empty session id = 0.0", _score_session_id("", "") == 0.0)
    check("argv-sid source = 1.0", _score_session_id("abc", "argv-sid") == 1.0)
    check("env source = 0.9", _score_session_id("abc", "env") == 0.9)
    check("cwd-hash source = 0.7", _score_session_id("abc", "cwd-hash") == 0.7)

    # Test 4: cwd depth
    check("cwd / = 0.0", _score_cwd_depth("/") == 0.0)
    check("cwd /a = 0.2", abs(_score_cwd_depth("/a") - 0.2) < 0.01)
    check("cwd /a/b/c/d/e = 1.0", _score_cwd_depth("/a/b/c/d/e") == 1.0)

    # Test 5: tty freshness
    ttys = Counter({"ttys001": 1, "ttys002": 5})
    check("rare tty = 1.0", abs(_score_tty_freshness("ttys001", ttys) - 1.0) < 0.01)
    check("common tty < 1.0", _score_tty_freshness("ttys002", ttys) < 1.0)

    # Test 6: pid relevance
    check("pid 1 = 0.0", _score_pid_relevance(1, set()) <= 0.01)
    check("pid 100000 = 1.0", _score_pid_relevance(100000, set()) == 1.0)

    # Test 7: argv sid bonus
    check("argv --sid = 1.0", _score_argv_sid("codex --sid=abc") == 1.0)
    check("argv codex = 0.6", _score_argv_sid("codex --foo") == 0.6)
    check("argv unknown = 0.2", _score_argv_sid("ls") == 0.2)

    # Test 8: full rank ordering
    rows = [
        {"ts_epoch": now, "harness": "codex", "session_id": "abc",
         "session_id_source": "argv-sid", "cwd": "/a/b/c/d", "tty": "ttys001",
         "pid": 50000, "argv": "codex --sid=abc"},
        {"ts_epoch": now - 7200, "harness": "shell", "session_id": "",
         "session_id_source": "", "cwd": "/", "tty": "ttys005",
         "pid": 100, "argv": "zsh"},
        {"ts_epoch": now - 60, "harness": "cursor", "session_id": "xyz",
         "session_id_source": "env", "cwd": "/a/b", "tty": "ttys002",
         "pid": 30000, "argv": "cursor"},
    ]
    scored = rank_sessions(rows, now)
    # First row should be highest-scoring
    check("rank[0] is codex row", scored[0]["harness"] == "codex")
    check("rank[0] score > 0.5", scored[0]["_score"] > 0.5)
    # Last row should be lowest-scoring (shell, no session_id)
    check("rank[-1] is shell row", scored[-1]["harness"] == "shell")

    # Test 9: stable ordering (same input = same output)
    scored2 = rank_sessions(rows, now)
    check("rank stable", all(a["_score"] == b["_score"]
                             for a, b in zip(scored, scored2)))

    # Test 10: handles empty input
    check("empty rows = empty result", rank_sessions([]) == [])

    print(f"\n{passed}/{total} passed")
    return passed, total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("snapshot", nargs="?",
                        help="Path to snapshot.jsonl (default: ~/.local/share/resume-all/snapshot.jsonl)")
    parser.add_argument("--top", type=int, help="Show only top N rows")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON array")
    parser.add_argument("--out", help="Write output to file")
    args = parser.parse_args(argv[1:])

    if args.snapshot is None and "--test" not in sys.argv:
        args.snapshot = str(Path.home() / ".local/share/resume-all/snapshot.jsonl")

    if "--test" in sys.argv or "-test" in sys.argv or "test" in argv[1:2]:
        return 0 if _self_test()[0] == _self_test()[1] else 1

    path = Path(args.snapshot).expanduser()
    if not path.exists():
        print(f"snapshot not found: {path}", file=sys.stderr)
        return 1

    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    scored = rank_sessions(rows)
    if args.json:
        output = json.dumps(scored, indent=2)
    else:
        output = format_table(scored, args.top)

    if args.out:
        Path(args.out).write_text(output)
        print(f"wrote {len(scored)} rows to {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
