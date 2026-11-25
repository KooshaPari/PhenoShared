#!/usr/bin/env python3
"""Local swarm model manager CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.model_manager import ModelManager


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "action", choices=["list", "ensure-always-on", "swap", "status", "cmd"]
    )
    p.add_argument("--name", help="Model tier key e.g. local.qwen35_08b")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    mm = ModelManager()
    if args.action == "list":
        print(json.dumps([s.__dict__ for s in mm.list_models()], indent=2))
    elif args.action == "ensure-always-on":
        print(json.dumps(mm.ensure_always_on(dry_run=args.dry_run), indent=2))
    elif args.action == "swap":
        if not args.name:
            p.error("--name required for swap")
        print(json.dumps(mm.swap_to(args.name, dry_run=args.dry_run), indent=2))
    elif args.action == "status":
        print(json.dumps(mm.status(), indent=2))
    elif args.action == "cmd":
        if not args.name:
            p.error("--name required for cmd")
        print(json.dumps({"cmd": mm.build_cmd(args.name)}, indent=2))


if __name__ == "__main__":
    main()
