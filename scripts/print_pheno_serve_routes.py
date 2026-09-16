#!/usr/bin/env python3
"""Print OpenAI-compatible env rows for pheno-serve Harbor routes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import CONFIG_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Print pheno-serve route overlay")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = CONFIG_DIR / "harbor_tbench_pheno_serve.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    routes = cfg.get("routes", [])
    rows = []
    for route in routes:
        key_env = route.get("api_key_env", "PHENO_SERVE_API_KEY")
        rows.append(
            {
                **route,
                "env": {
                    "OPENAI_BASE_URL": route["base_url"],
                    "OPENAI_API_KEY": os.environ.get(
                        key_env, route.get("api_key_default", "local-no-key")
                    ),
                },
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            print(
                f"{row['id']}: {row['harbor_model']} @ {row['base_url']} ({row['engine']}, {row['decode_method']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
