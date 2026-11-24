#!/usr/bin/env python3
"""Collect traces from all 5 harness log sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traces.ingest import collect_all


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--omniroute-limit", type=int, default=5000)
    p.add_argument("--out-dir", type=Path, default=None)
    args = p.parse_args()
    path, n = collect_all(out_dir=args.out_dir, omniroute_limit=args.omniroute_limit)
    print(f"Collected {n} events -> {path}")


if __name__ == "__main__":
    main()
