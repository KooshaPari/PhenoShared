#!/usr/bin/env python3
"""Run RLVR playground combinatorial matrix (3090 Ti lab)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typing import Any

from playground.runner import PlaygroundRunner


def _parse_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="RLVR playground matrix runner")
    parser.add_argument(
        "--matrix",
        type=Path,
        default=None,
        help="Path to playground_matrix.yaml (default: config/playground_matrix.yaml)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Write manifests only, no verify"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Run verifier/rewards on traces"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max experiments to emit"
    )
    parser.add_argument(
        "--count-only", action="store_true", help="Print filtered grid size and exit"
    )
    parser.add_argument(
        "--small-grid",
        action="store_true",
        help="small subset: omniroute_local+forge × locked local aliases, train_mode=none",
    )
    parser.add_argument(
        "--harness-types", type=str, help="Comma-separated harness_types filter"
    )
    parser.add_argument(
        "--model-nets", type=str, help="Comma-separated model_nets filter"
    )
    parser.add_argument(
        "--routing-policies", type=str, help="Comma-separated routing_policies filter"
    )
    parser.add_argument(
        "--decode-experiments",
        type=str,
        help="Comma-separated decode_experiments filter",
    )
    parser.add_argument(
        "--train-modes", type=str, help="Comma-separated train_modes filter"
    )
    args = parser.parse_args()

    runner = PlaygroundRunner(matrix_path=args.matrix)

    subset: dict[str, Any] = {}
    if args.small_grid:
        subset = {
            "harness_types": ["omniroute_local", "forge"],
            "model_nets": ["qwen35_08b", "lfm25_8b_a1b", "ornith_8b"],
            "routing_policies": ["local_first"],
            "decode_experiments": ["baseline"],
            "train_modes": ["none"],
        }
    else:
        for key, val in (
            ("harness_types", args.harness_types),
            ("model_nets", args.model_nets),
            ("routing_policies", args.routing_policies),
            ("decode_experiments", args.decode_experiments),
            ("train_modes", args.train_modes),
        ):
            parsed = _parse_list(val)
            if parsed:
                subset[key] = parsed

    total = runner.count_experiments(**subset)
    print(f"Filtered experiment count: {total}")

    if args.count_only:
        return 0

    paths = runner.run(
        limit=args.limit,
        run_verify=args.verify and not args.dry_run,
        dry_run=args.dry_run,
        **subset,
    )
    print(f"Wrote {len(paths)} manifest(s) to {runner.experiments_dir}")
    for p in paths[:10]:
        print(f"  {p.name}")
    if len(paths) > 10:
        print(f"  ... and {len(paths) - 10} more")

    if args.small_grid and paths:
        sample = json.loads(paths[0].read_text(encoding="utf-8"))
        print("\nSample manifest (first experiment):")
        print(
            json.dumps(
                {k: sample[k] for k in ("experiment_id", "dimensions", "status")},
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
