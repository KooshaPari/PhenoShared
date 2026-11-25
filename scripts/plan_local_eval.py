#!/usr/bin/env python3
"""Validate a local-only eval manifest against declared serving capabilities.

This produces an execution plan, not an execution request: it never starts an
engine, downloads an artifact, or calls a provider.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pheno.serve.config import load_config
from pheno.serve.registry import ProfileRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def _matrix(path: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    models = raw.get("models") or {}
    if not isinstance(models, dict):
        raise ValueError("local model matrix must contain models mapping")
    by_alias = {
        str(model.get("alias")): model
        for model in models.values()
        if isinstance(model, dict)
    }
    if not by_alias or "None" in by_alias:
        raise ValueError("local model matrix has no aliases")
    return by_alias


def _profile_for_engine(registry: ProfileRegistry, alias: str, engine: str):
    candidate_aliases = [alias]
    if engine == "vllm":
        candidate_aliases.append(f"{alias}-vllm")
    elif engine == "tensorrt_llm":
        candidate_aliases.append(f"{alias}-trtllm")
    for candidate in candidate_aliases:
        try:
            profile = registry.get(candidate)
        except KeyError:
            continue
        if profile.alias == candidate and profile.engine == engine:
            return profile
    return None


def build_plan(
    rows: list[dict[str, Any]],
    matrix: dict[str, dict[str, Any]],
    registry: ProfileRegistry,
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for row in rows:
        alias = str(row.get("model_alias", ""))
        engine = str(row.get("engine", ""))
        item = dict(row)
        item["action"] = "blocked"
        item["reason"] = "unknown"
        if row.get("run_mode") != "manifest_only" or row.get("cost_usd") != 0:
            item["reason"] = "not_local_only"
        elif alias not in matrix:
            item["reason"] = "unknown_model_alias"
        else:
            model = matrix[alias]
            if row.get("model_ref") != model.get("hf_owner_id"):
                item["reason"] = "model_reference_mismatch"
            elif engine not in model.get("engines", []):
                item["reason"] = "engine_not_declared_for_model"
            else:
                profile = _profile_for_engine(registry, alias, engine)
                if profile is None:
                    item["reason"] = "engine_profile_not_configured"
                else:
                    item["action"] = "requires_local_artifact"
                    item["reason"] = "profile_declared"
                    item["profile_alias"] = profile.alias
                    item["profile_status"] = profile.status
        plan.append(item)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-side-effect local evaluation execution plan"
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--matrix",
        type=Path,
        default=REPO_ROOT / "config" / "local_model_bench_matrix.yaml",
    )
    parser.add_argument(
        "--serve-config", type=Path, default=REPO_ROOT / "config" / "pheno_serve.yaml"
    )
    parser.add_argument(
        "--output", type=Path, help="Write full JSON plan; default prints summary only"
    )
    args = parser.parse_args()
    try:
        plan = build_plan(
            _read_jsonl(args.manifest),
            _matrix(args.matrix),
            ProfileRegistry(load_config(args.serve_config)),
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    summary = {
        "rows": len(plan),
        "actions": dict(Counter(row["action"] for row in plan)),
        "reasons": dict(Counter(row["reason"] for row in plan)),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"summary": summary, "plan": plan}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
