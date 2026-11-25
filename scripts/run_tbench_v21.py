#!/usr/bin/env python3
"""Create or explicitly execute a local-only Terminal-Bench 2.x run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.tbench_v21 import build_manifest, execute, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="local/qwen35-08b")
    parser.add_argument(
        "--suite",
        choices=["terminal-bench@2.0", "terminal-bench@2.1"],
        default="terminal-bench@2.0",
    )
    parser.add_argument(
        "--subset",
        choices=["representative-6", "16", "full"],
        default="representative-6",
    )
    parser.add_argument(
        "--subset-manifest", type=Path, help="Explicit JSON task subset manifest"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run Harbor against local pheno-serve; default is a no-side-effect dry run",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Harbor output directory when --execute is set"
    )
    args = parser.parse_args()
    manifest = build_manifest(
        model_alias=args.model,
        subset=args.subset,
        dry_run=not args.execute,
        suite=args.suite,
        subset_manifest=args.subset_manifest,
    )
    manifest_path = write_manifest(manifest)
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))
    if not args.execute:
        return 0
    if not args.output_dir:
        parser.error("--output-dir is required with --execute")
    return execute(manifest, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
