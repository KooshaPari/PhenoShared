#!/usr/bin/env python3
"""Train Needle router v0 from exported OmniRoute call_logs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from needle.compiler import NeedleRouter


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--glob", default="call_logs_*.jsonl")
    args = p.parse_args()
    router = NeedleRouter()
    learned = router.train_from_call_logs(args.glob)
    print(f"Saved router patterns -> {router.patterns_path}")
    print("Role distribution:", learned.get("role_counts", learned))
    print(f"Default role: {learned.get('default_role', 'patch')}")


if __name__ == "__main__":
    main()
