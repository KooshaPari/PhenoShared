#!/usr/bin/env python3
"""CI gate: ensure ``pytest tests/ --collect-only`` reports 0 collection errors.

Run this before pushing CI checks or before tagging a release. Exit 0 on
success, non-zero on any collection error or unexpected low test count.

Usage:
    python scripts/check_dep_gaps.py
    python scripts/check_dep_gaps.py --min-tests 500
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-tests",
        type=int,
        default=500,
        help="Minimum number of collected tests required (default 500).",
    )
    parser.add_argument(
        "--target",
        default="tests/",
        help="Pytest target path (default 'tests/').",
    )
    args = parser.parse_args()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            args.target,
            "--collect-only",
            "-q",
            "--no-header",
            "--tb=no",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    combined = proc.stdout + "\n" + proc.stderr
    combined = re.sub(r"\x1b\[[0-9;]*m", "", combined)

    error_lines = [
        line
        for line in combined.splitlines()
        if line.startswith("ERROR ") and "tests/" in line
    ]
    if error_lines:
        print("FAIL: collection errors detected:", file=sys.stderr)
        for line in error_lines[:20]:
            print(f"  {line}", file=sys.stderr)
        if len(error_lines) > 20:
            print(f"  ... and {len(error_lines) - 20} more", file=sys.stderr)
        return 2

    m = re.search(r"(\d+) tests collected", combined)
    if m is None:
        print(
            f"FAIL: could not parse pytest output:\n{combined[:500]!r}",
            file=sys.stderr,
        )
        return 3

    count = int(m.group(1))
    if count < args.min_tests:
        print(
            f"FAIL: only {count} tests collected (expected >= {args.min_tests})",
            file=sys.stderr,
        )
        return 4

    print(f"OK: {count} tests collected, 0 collection errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
