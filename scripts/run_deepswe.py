#!/usr/bin/env python3
"""Plan or explicitly execute a local DeepSWE run through Pier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.deepswe import build_manifest, execute, load_config, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="local/lfm25-8b-a1b")
    parser.add_argument("--subset", type=int, default=16)
    parser.add_argument("--env", choices=["docker"], default="docker")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build_manifest(
            load_config(),
            model_alias=args.model,
            subset=args.subset,
            environment=args.env,
            execute=args.execute,
        )
    except ValueError as exc:
        parser.error(str(exc))
    manifest_path = write_manifest(manifest)
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))
    if not args.execute:
        return 0
    try:
        return execute(manifest)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
