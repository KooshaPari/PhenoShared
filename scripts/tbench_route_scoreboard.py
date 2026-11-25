#!/usr/bin/env python3
"""Print TB2 route matrix scoreboard (quality + TPS + cost composite)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.route_matrix import export_route_leaderboard, format_route_table


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--route-kind", help="Filter table by route kind")
    p.add_argument("--export", action="store_true")
    args = p.parse_args()
    if args.export:
        export_route_leaderboard(route_kind=args.route_kind)
    print(format_route_table(route_kind=args.route_kind))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
