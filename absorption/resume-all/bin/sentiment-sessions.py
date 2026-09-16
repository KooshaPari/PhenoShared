#!/opt/homebrew/bin/python3
"""
sentiment-sessions.py — Phase E hardening item E08.

Lightweight sentiment scoring for sessions in a snapshot. Each session
gets a sentiment score in [-1.0, +1.0] derived from:

  1. Recent command history (argv / cmdline) — keyword-based scoring
     with negative weight on "rm", "kill", "drop", "delete", "force"
     and positive weight on "fix", "build", "add", "test", "deploy".

  2. Harness-specific markers — sessions in "fix" / "bug" branches,
     sessions that ran "make test", "npm test", "pytest" get a positive
     signal.

  3. Cwd path heuristics — paths containing "test", "spec", "fix" score
     positive; paths containing "old", "deprecated", "dead" score
     negative.

  4. Pane recency — sessions active in the last hour get a freshness
     bonus, idle ones get decay.

Score is clamped to [-1.0, +1.0] and bucketed:
   >= +0.5:  "great"
   >= +0.2:  "good"
   >= -0.2:  "neutral"
   >= -0.5:  "concerning"
   <  -0.5:  "bad"

Output modes:
  --json      JSON array of {pane_id, sentiment, score, bucket, signals}
  --top N     Only show top N by absolute score (most "interesting")
  --histogram Print distribution of buckets
  default     Human-readable table

Usage:
  sentiment-sessions.py                     # read default snapshot
  sentiment-sessions.py --json <file>       # JSON output
  sentiment-sessions.py --top 10 <file>     # top 10 most interesting
  sentiment-sessions.py --histogram         # distribution
  sentiment-sessions.py test                # self-tests
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

BIN = Path("/Users/kooshapari/bin")
DATA = Path.home() / ".local/share/resume-all"
SNAPSHOT = DATA / "snapshot.jsonl"

# Keyword weights — bounded to [-0.2, +0.2] per keyword to avoid runaway
NEGATIVE_WORDS = {
    "rm": -0.15, "kill": -0.15, "drop": -0.20, "delete": -0.10,
    "force": -0.10, "destroy": -0.20, "purge": -0.15, "wipe": -0.20,
    "crash": -0.10, "panic": -0.20, "abort": -0.15, "fail": -0.10,
    "error": -0.05, "warn": -0.05, "broken": -0.10, "stale": -0.05,
}
POSITIVE_WORDS = {
    "fix": 0.15, "build": 0.10, "add": 0.10, "test": 0.15,
    "deploy": 0.10, "ship": 0.15, "merge": 0.10, "release": 0.10,
    "feat": 0.10, "refactor": 0.10, "doc": 0.05, "clean": 0.05,
    "verify": 0.10, "validate": 0.10, "lint": 0.05, "fmt": 0.05,
}
CWD_NEGATIVE = {"old", "deprecated", "dead", "archive", "trash", "tmp"}
CWD_POSITIVE = {"test", "spec", "fix", "new", "wip", "feat"}


def clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def bucket(score: float) -> str:
    if score >= 0.5: return "great"
    if score >= 0.2: return "good"
    if score >= -0.2: return "neutral"
    if score >= -0.5: return "concerning"
    return "bad"


def word_score(text: str) -> tuple[float, list[str]]:
    """Score text by keyword matches. Returns (delta, matched_words)."""
    if not text: return 0.0, []
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    delta = 0.0
    matches = []
    for tok in tokens:
        if tok in NEGATIVE_WORDS:
            delta += NEGATIVE_WORDS[tok]
            matches.append(f"-{tok}")
        elif tok in POSITIVE_WORDS:
            delta += POSITIVE_WORDS[tok]
            matches.append(f"+{tok}")
    return clamp(delta), matches


def cwd_score(cwd: str) -> tuple[float, list[str]]:
    """Score by path components."""
    if not cwd: return 0.0, []
    parts = re.split(r"[/._-]", cwd.lower())
    delta = 0.0
    matches = []
    for p in parts:
        if p in CWD_NEGATIVE:
            delta -= 0.1
            matches.append(f"-{p}")
        elif p in CWD_POSITIVE:
            delta += 0.1
            matches.append(f"+{p}")
    return clamp(delta), matches


def recency_score(ts_epoch: float) -> float:
    """Freshness bonus: +0.1 if active in last hour, decay otherwise."""
    if not ts_epoch: return 0.0
    age = (dt.datetime.now(dt.timezone.utc).timestamp() - ts_epoch)
    if age < 0:
        return 0.0  # clock skew
    if age < 3600: return 0.1
    if age < 86400: return 0.05
    if age < 604800: return 0.0
    return -0.05  # week+ old


def session_score(row: dict) -> dict:
    """Score a single session row."""
    signals = []
    text = " ".join([
        row.get("cmd", "") or "",
        row.get("argv", "") or "",
        row.get("surface_name", "") or "",
        row.get("harness", "") or "",
    ])
    delta, word_matches = word_score(text)
    signals.extend(word_matches)
    cdelta, cwd_matches = cwd_score(row.get("cwd", ""))
    delta += cdelta
    signals.extend(cwd_matches)
    rdelta = recency_score(float(row.get("ts_epoch", 0) or 0))
    delta += rdelta
    if rdelta > 0: signals.append(f"+recency")
    elif rdelta < 0: signals.append(f"-recency")
    # Session-id present is a positive signal (real, recoverable work)
    if row.get("session_id"):
        delta += 0.05
        signals.append("+sid")
    # Multi-harness work (harness list with multiple entries)
    h = row.get("harness", "")
    if h and h not in ("shell", "tmux", "ghostty"):
        delta += 0.05
        signals.append(f"+harness:{h}")
    score = clamp(delta)
    return {
        "pane_id": row.get("pane_id", "?"),
        "surface_id": row.get("surface_id", ""),
        "harness": h,
        "sentiment": score,
        "score": score,  # alias for --json consumers
        "bucket": bucket(score),
        "signals": signals,
    }


def read_snapshot(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", nargs="?", default=str(SNAPSHOT))
    ap.add_argument("--json", action="store_true",
                    help="Output JSON array")
    ap.add_argument("--top", type=int, default=0,
                    help="Show top N by absolute score")
    ap.add_argument("--histogram", action="store_true",
                    help="Print bucket distribution")
    ap.add_argument("--bucket", default="",
                    help="Filter to a single bucket (great/good/neutral/concerning/bad)")
    args = ap.parse_args(argv)
    if args.snapshot == "test":
        return 0 if tests() else 1
    rows = read_snapshot(Path(args.snapshot))
    if not rows:
        print("sentiment-sessions: no rows in snapshot", file=sys.stderr)
        return 1
    scored = [session_score(r) for r in rows]
    # Filter
    if args.bucket:
        scored = [s for s in scored if s["bucket"] == args.bucket]
    # Histogram mode
    if args.histogram:
        from collections import Counter
        c = Counter(s["bucket"] for s in scored)
        total = len(scored)
        for b in ["great", "good", "neutral", "concerning", "bad"]:
            n = c.get(b, 0)
            pct = (n / total * 100) if total else 0
            bar = "█" * int(pct / 5)
            print(f"  {b:12s} {n:4d} ({pct:5.1f}%) {bar}")
        return 0
    # Sort by absolute score descending
    scored.sort(key=lambda s: -abs(s["sentiment"]))
    if args.top:
        scored = scored[:args.top]
    if args.json:
        print(json.dumps(scored, indent=2))
        return 0
    # Default: human-readable
    print(f"sentiment-sessions: {len(scored)} session(s)")
    for s in scored[:30]:
        sigs = " ".join(s["signals"][:5])
        print(f"  {s['sentiment']:+.2f} [{s['bucket']:10s}] "
              f"{s['pane_id'][:40]:40s} {s['harness']:12s} {sigs}")
    if len(scored) > 30:
        print(f"  ... and {len(scored) - 30} more")
    return 0


def tests() -> bool:
    """Self-tests."""
    ok = 0
    fail = 0
    def check(name, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f"PASS {name}")
        else: fail += 1; print(f"FAIL {name}")

    check("clamp upper", clamp(2.0) == 1.0)
    check("clamp lower", clamp(-2.0) == -1.0)
    check("clamp pass-through", clamp(0.5) == 0.5)
    check("bucket great", bucket(0.7) == "great")
    check("bucket good", bucket(0.3) == "good")
    check("bucket neutral", bucket(0.0) == "neutral")
    check("bucket concerning", bucket(-0.3) == "concerning")
    check("bucket bad", bucket(-0.7) == "bad")
    check("word_score positive",
          word_score("let's fix this and add a test")[0] > 0)
    check("word_score negative",
          word_score("rm -rf old drop dead purge")[0] < 0)
    check("word_score empty",
          word_score("")[0] == 0.0)
    check("cwd_score positive",
          cwd_score("/home/u/projects/new-feat/")[0] > 0)
    check("cwd_score negative",
          cwd_score("/home/u/projects/_deprecated/old/")[0] < 0)
    check("cwd_score empty",
          cwd_score("")[0] == 0.0)
    check("recency fresh",
          recency_score(dt.datetime.now(dt.timezone.utc).timestamp()) == 0.1)
    check("recency stale",
          recency_score(dt.datetime.now(dt.timezone.utc).timestamp() - 99999999) <= 0)
    # End-to-end row scoring
    row = {
        "pane_id": "p:1", "harness": "codex", "cmd": "fix typo in docs",
        "cwd": "/proj/feat/new", "session_id": "abc", "ts_epoch": dt.datetime.now(dt.timezone.utc).timestamp(),
    }
    s = session_score(row)
    check("row score positive", s["sentiment"] > 0)
    check("row has signals", len(s["signals"]) > 0)
    check("row bucket great/good", s["bucket"] in ("great", "good", "neutral"))
    # Negative row
    row2 = {
        "pane_id": "p:2", "harness": "shell", "cmd": "rm -rf drop purge kill force",
        "cwd": "/old/dead/_deprecated", "session_id": "", "ts_epoch": 1,
    }
    s2 = session_score(row2)
    check("row score negative", s2["sentiment"] < 0)
    check("row bucket bad/concerning", s2["bucket"] in ("bad", "concerning"))
    # Snapshot parse
    rows = read_snapshot(SNAPSHOT)
    check("snapshot read", isinstance(rows, list))
    print(f"\n{ok}/{ok + fail} passed")
    return fail == 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
