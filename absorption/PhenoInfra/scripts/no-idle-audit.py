#!/usr/bin/env python3
"""
No-Idle Parallelism Audit — automated tick analysis per ADR-0010.

Parses worklog SESSION_*.md files under worklogs/, computes the idle ratio
for each session, flags violations, and writes a summary to stdout or
to .github/ISSUE_TEMPLATE/no-idle-audit.md (in CI).

Usage:
    python scripts/no-idle-audit.py [--strict] [--idle-threshold 5]

    --strict             : exit 1 if any idle_violation=true tick found
    --idle-threshold N   : override default (5) active_count threshold
    --markdown           : output a ready-to-copy ISSUE_TEMPLATE snippet
"""

import argparse
import csv
import os
import re
import sys

WORKLOGS_DIR = os.path.join(os.path.dirname(__file__) or ".", "..", "worklogs")
IDLE_THRESHOLD_DEFAULT = 5


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_ticks_from_md(path: str) -> list[dict]:
    """Extract tick rows from the `## Ticks` section of a worklog MD file."""
    ticks: list[dict] = []
    in_ticks = False

    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            # Section header
            if stripped.startswith("## Ticks"):
                in_ticks = True
                continue

            # Subsequent ##-header ends the Ticks section
            if in_ticks and stripped.startswith("## "):
                break

            if in_ticks and stripped.startswith("|") and not stripped.startswith("|---"):
                parts = [p.strip() for p in stripped.strip("|").split("|")]
                if len(parts) >= 5:
                    tick = {
                        "tick_ts": parts[0],
                        "active_count": int(parts[1]) if parts[1].isdigit() else 0,
                        "queued_tasks": parts[2],
                        "idle_violation": parts[3].lower() == "true",
                        "notes": parts[4] if len(parts) > 4 else "",
                    }
                    ticks.append(tick)

    return ticks


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_ticks(ticks: list[dict], threshold: int) -> dict:
    """Return idle-analysis summary for a single session."""
    total = len(ticks)
    violations = [t for t in ticks if t["idle_violation"]]
    idle_ratio = len(violations) / total if total > 0 else 0.0

    violation_timestamps = [
        f"  - {t['tick_ts']} (active={t['active_count']}, queue={t['queued_tasks']}, notes={t['notes']})"
        for t in violations
    ]

    return {
        "total_ticks": total,
        "violation_count": len(violations),
        "idle_ratio": round(idle_ratio, 3),
        "violation_timestamps": violation_timestamps,
        "threshold": threshold,
        "idle_violations": violations,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

SUMMARY_TEMPLATE = """
## No-Idle Audit Report ({date})

- **Worklogs scanned:** {count}
- **Total ticks:** {total_ticks}
- **Idle violations:** {violation_count}
- **Idle ratio:** {idle_ratio}
- **Threshold:** {threshold} active_count

### Violation Details

{violations}

### Verdict

{verdict}
"""


def format_verdict(violation_count: int) -> str:
    if violation_count == 0:
        return "✅ PASS — no idle violations detected."
    return f"❌ FAIL — {violation_count} idle violation(s) found. See details above."


def format_violation_detail(analyses: list[dict]) -> str:
    parts = []
    for a in analyses:
        if a["violation_count"] == 0:
            continue
        parts.append(f"#### Session ({a['source']})")
        parts.extend(a["violation_timestamps"])
    if not parts:
        return "  *None.*"
    return "\n".join(parts)


def markdown_report(analyses: list[dict], threshold: int) -> str:
    total_ticks = sum(a["total_ticks"] for a in analyses)
    total_violations = sum(a["violation_count"] for a in analyses)
    total_idle_ratio = round(total_violations / total_ticks, 3) if total_ticks > 0 else 0.0

    violations_md = ""
    for a in analyses:
        if a["violation_count"] > 0:
            violations_md += f"**{a['source']}** ({a['violation_count']} violation(s)):\n"
            for vt in a["violation_timestamps"]:
                violations_md += f"{vt}\n"
            violations_md += "\n"

    if not violations_md:
        violations_md = "  *None.*"

    return SUMMARY_TEMPLATE.format(
        date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d"),
        count=len(analyses),
        total_ticks=total_ticks,
        violation_count=total_violations,
        idle_ratio=total_idle_ratio,
        threshold=threshold,
        violations=violations_md,
        verdict=format_verdict(total_violations),
    ).strip()


def issue_template(analyses: list[dict], threshold: int) -> str:
    report = markdown_report(analyses, threshold)
    return f"""---
title: "No-Idle Audit — {__import__('datetime').datetime.utcnow().strftime('%Y-W%V')}"
labels: ["no-idle", "audit"]
---

{report}

---

_Generated by `scripts/no-idle-audit.py` per ADR-0010 / No-Idle Parallelism Policy.
Threshold: active_count < {threshold} with non-empty queue = violation._
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="No-Idle Parallelism Audit")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any violation")
    parser.add_argument("--idle-threshold", type=int, default=IDLE_THRESHOLD_DEFAULT, help="idle active_count threshold")
    parser.add_argument("--markdown", action="store_true", help="output issue template instead of summary")
    args = parser.parse_args()

    worklogs_dir = os.path.abspath(WORKLOGS_DIR)

    if not os.path.isdir(worklogs_dir):
        print(f"::error::Worklogs directory not found: {worklogs_dir}", file=sys.stderr)
        sys.exit(1)

    session_files = sorted([
        f for f in os.listdir(worklogs_dir)
        if f.startswith("SESSION_") and f.endswith(".md")
    ])

    if not session_files:
        print("::notice::No SESSION_*.md files found — audit skipped (clean start).")
        sys.exit(0)

    analyses: list[dict] = []
    total_violations = 0

    for sf in session_files:
        path = os.path.join(worklogs_dir, sf)
        ticks = parse_ticks_from_md(path)
        if not ticks:
            continue
        analysis = analyze_ticks(ticks, args.idle_threshold)
        analysis["source"] = sf
        analyses.append(analysis)
        total_violations += analysis["violation_count"]
        print(f"  {sf}: {analysis['total_ticks']} ticks, {analysis['violation_count']} violations, ratio={analysis['idle_ratio']}")

    if args.markdown:
        print(issue_template(analyses, args.idle_threshold))
    else:
        print(markdown_report(analyses, args.idle_threshold))

    if args.strict and total_violations > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
