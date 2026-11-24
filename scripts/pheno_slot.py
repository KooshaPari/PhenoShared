#!/usr/bin/env python3
"""Plan or explicitly start a local SGLang engine-slot swap."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pheno.serve.config import load_config
from pheno.serve.lifecycle import SlotController


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("alias", help="Declared SGLang model alias")
    parser.add_argument("--config", default="config/pheno_serve.yaml")
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the server; default only validates and prints its command",
    )
    args = parser.parse_args()
    controller = SlotController(load_config(args.config))
    try:
        result = controller.start(args.alias, dry_run=not args.start)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
