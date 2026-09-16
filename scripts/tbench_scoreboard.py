#!/usr/bin/env python3
"""Print terminal-bench@2.0 per-model leaderboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.tbench import export_leaderboard, format_leaderboard_table


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--include-combo", action="store_true")
    p.add_argument(
        "--export",
        action="store_true",
        help="Write eval/results/tbench_model_scores.json",
    )
    args = p.parse_args()
    if args.export:
        export_leaderboard(include_combo=args.include_combo)
    print(format_leaderboard_table(include_combo=args.include_combo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
