#!/usr/bin/env python3
"""Expand config/local_eval_manifest.yaml into local-only eval manifest JSONL."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "local_eval_manifest.yaml"


def _values(value: Any, name: str) -> list[Any]:
    """Normalize a declared scalar or list axis to a non-empty list."""
    values = value if isinstance(value, list) else [value]
    if not values or any(item is None or item == "" for item in values):
        raise ValueError(f"{name} must declare at least one non-empty value")
    return values


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError("manifest config must be a mapping")
    return config


def build_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build one row for every declared model, engine, and optimization cell."""
    suite = config.get("suite")
    if not isinstance(suite, dict):
        raise ValueError("suite must be a mapping")
    if suite.get("run_mode") != "manifest_only":
        raise ValueError("suite.run_mode must be manifest_only")
    if suite.get("cost_usd") != 0:
        raise ValueError("suite.cost_usd must be 0")

    hardware_profile = config.get("hardware_profile")
    if not isinstance(hardware_profile, str) or not hardware_profile:
        raise ValueError("hardware_profile must be a non-empty string")

    defaults = config.get("defaults")
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping")
    weight_quants = _values(defaults.get("weight_quant"), "defaults.weight_quant")
    kv_quants = _values(defaults.get("kv_quant"), "defaults.kv_quant")
    decodes = _values(defaults.get("decode"), "defaults.decode")
    compressions = _values(defaults.get("compression"), "defaults.compression")

    models = config.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("models must be a non-empty list")

    rows: list[dict[str, Any]] = []
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("each model must be a mapping")
        alias = model.get("alias")
        model_ref = model.get("model_ref")
        if (
            not isinstance(alias, str)
            or not alias
            or not isinstance(model_ref, str)
            or not model_ref
        ):
            raise ValueError("each model requires non-empty alias and model_ref")

        engines = _values(model.get("engines"), f"models[{alias}].engines")
        roles = _values(model.get("roles"), f"models[{alias}].roles")
        for engine, weight_quant, kv_quant, decode, compression in itertools.product(
            engines, weight_quants, kv_quants, decodes, compressions
        ):
            rows.append(
                {
                    "suite_id": suite.get("id"),
                    "dataset": suite.get("dataset"),
                    "n_tasks": suite.get("n_tasks"),
                    "run_mode": "manifest_only",
                    "cost_usd": 0,
                    "hardware_profile": hardware_profile,
                    "model_alias": alias,
                    "model_ref": model_ref,
                    "roles": roles,
                    "engine": engine,
                    "weight_quant": weight_quant,
                    "kv_quant": kv_quant,
                    "decode": decode,
                    "compression": compression,
                }
            )
    return rows


def _write_jsonl(rows: list[dict[str, Any]], output: Path | None) -> None:
    content = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if output is None:
        sys.stdout.write(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate local-only eval manifest JSONL rows"
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="Source YAML manifest"
    )
    parser.add_argument(
        "--output", type=Path, help="Write JSONL to this path (default: stdout)"
    )
    args = parser.parse_args()

    try:
        rows = build_rows(_load_config(args.config))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))

    _write_jsonl(rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
