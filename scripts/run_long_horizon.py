#!/usr/bin/env python3
"""Plan or explicitly execute the local Pheno long-horizon suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.long_horizon import build_manifest, execute, load_config, write_manifest
from pheno.paths import PHENO_ROOT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--model", default="local/lfm25-8b-a1b")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = load_config()
    task_root = args.tasks or PHENO_ROOT / config["suite"]["default_task_root"]
    try:
        manifest = build_manifest(
            config, task_root=task_root, model_alias=args.model, execute=args.execute
        )
    except ValueError as exc:
        parser.error(str(exc))
    path = write_manifest(manifest)
    print(json.dumps({"manifest": str(path), **manifest}, indent=2))
    if not args.execute:
        return 0
    try:
        return execute(manifest)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
