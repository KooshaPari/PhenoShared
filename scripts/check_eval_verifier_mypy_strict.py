#!/usr/bin/env python3
"""Run ``mypy --strict`` on the eval/ and verifier/ subpackages.

This is the dedicated type-strict runner introduced in v0.10. It
isolates the eval/ + verifier/ strict-mode findings from the rest of
the project's mypy sweep, so we can gate Phase 3 docstring/type-
narrowing work without blocking the rest of the repo.

Refs: v0.10 WBS task 58.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = ("eval", "verifier")


def run_mypy_strict(targets: list[str], max_errors: int) -> int:
    """Run mypy --strict on the given targets and print a summary.

    Returns the number of error findings (0 on success).
    """
    # Prefer the global `mypy` binary (resolved via PATH) over
    # `python -m mypy` because the system Python doesn't have mypy
    # installed in its env. Fall back to `python -m mypy` if not found.
    import shutil

    mypy_bin = shutil.which("mypy")
    if mypy_bin:
        cmd = [mypy_bin, "--strict", *targets]
    else:
        cmd = [sys.executable, "-m", "mypy", "--strict", *targets]
    print(f"running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    error_lines = [line for line in output.splitlines() if " error:" in line]
    note_lines = [line for line in output.splitlines() if " note:" in line]
    summary_lines = [line for line in output.splitlines() if line.startswith("Found ")]
    print(f"\n=== summary ({len(targets)} target(s): {', '.join(targets)}) ===")
    for line in summary_lines:
        print(line)
    print(f"  errors: {len(error_lines)}")
    print(f"  notes:  {len(note_lines)}")
    if error_lines:
        print("\n=== first 20 errors ===")
        for line in error_lines[:20]:
            print(line)
    if len(error_lines) > max_errors:
        print(
            f"\nFAIL: {len(error_lines)} errors exceed threshold {max_errors}",
            file=sys.stderr,
        )
        return 1
    print("\nOK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        help="mypy target (default: eval verifier)",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=200,
        help="fail if error count exceeds this threshold (default 200)",
    )
    args = parser.parse_args()
    targets = args.target if args.target else list(DEFAULT_TARGETS)
    return run_mypy_strict(targets, args.max_errors)


if __name__ == "__main__":
    sys.exit(main())
