#!/usr/bin/env python3
"""Build a deterministic quantization plan; never downloads or converts."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pheno.model_policy import local_aliases  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan local q2-q8/NVFP4 quantization")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--minimum-free-gb",
        type=int,
        help="explicit test/admin override; defaults to policy",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="refused; conversion requires a separate reviewed runner",
    )
    args = parser.parse_args()
    if args.execute:
        parser.error(
            "plan_quantization.py is plan-only; use a reviewed engine-specific conversion runner"
        )
    plan = (
        yaml.safe_load(
            (ROOT / "config" / "quantization_plan.yaml").read_text(encoding="utf-8")
        )
        or {}
    )
    models = args.models or sorted(local_aliases())
    allowed = local_aliases()
    unknown = sorted(set(models) - allowed)
    if unknown:
        parser.error(f"unlocked local aliases: {unknown}")
    variants = args.variants or [item["id"] for item in plan["weight_variants"]]
    declared = {item["id"]: item for item in plan["weight_variants"]}
    invalid = sorted(set(variants) - set(declared))
    if invalid:
        parser.error(f"unknown variants: {invalid}")
    try:
        free = shutil.disk_usage(args.source_root).free
    except OSError as exc:
        parser.error(f"cannot inspect source root: {exc}")
    minimum_gb = int(
        plan["admission"]["minimum_free_gb"]
        if args.minimum_free_gb is None
        else args.minimum_free_gb
    )
    if minimum_gb < 0:
        parser.error("--minimum-free-gb cannot be negative")
    minimum = minimum_gb * 1024**3
    report: dict[str, Any] = {
        "schema_version": "phenolm.quantization_plan.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_root": str(args.source_root.resolve()),
        "free_bytes": free,
        "minimum_free_bytes": minimum,
        "minimum_free_gb": minimum_gb,
        "admission": "pass" if free >= minimum else "reject_low_disk",
        "download_performed": False,
        "conversion_performed": False,
        "models": models,
        "variants": [declared[item] for item in variants],
        "next_action": "review source paths and run an engine-specific converter explicitly",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "admission": report["admission"],
                "download_performed": False,
                "conversion_performed": False,
            },
            indent=2,
        )
    )
    return 0 if report["admission"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
