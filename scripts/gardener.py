#!/usr/bin/env python3
"""PhenoLM garden loop controller.

The first implementation is intentionally observation-only by default. It
validates the garden policy and writes/prints ledger-shaped reports without
promoting candidates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import CONFIG_DIR, PHENO_ROOT, STATE_DIR


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PHENO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _load_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "garden_loop.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _ledger_path(policy: dict[str, Any]) -> Path:
    rel = policy.get("ledger", {}).get("path", "state/garden/ledger.jsonl")
    return PHENO_ROOT / rel


def _parse_metrics(args: argparse.Namespace) -> dict[str, Any]:
    metrics = json.loads(args.metrics_json) if args.metrics_json else {}
    for item in args.metric:
        if "=" not in item:
            raise SystemExit(f"--metric must be key=value, got: {item}")
        key, value = item.split("=", 1)
        try:
            metrics[key] = json.loads(value)
        except json.JSONDecodeError:
            metrics[key] = value
    return metrics


def _base_row(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    metrics = _parse_metrics(args)
    return {
        "run_id": args.run_id or datetime.now(UTC).strftime("garden_%Y%m%dT%H%M%SZ"),
        "timestamp_utc": now,
        "git_sha": _git_sha(),
        "component": args.component,
        "candidate_type": args.candidate_type,
        "lane": args.lane,
        "model_id": args.model_id,
        "provider_or_engine": args.provider_or_engine,
        "eval_suite": args.eval_suite,
        "result": args.result,
        "metrics": metrics,
        "gate_decisions": {
            name: {"required": cfg.get("required", False), "status": "not_evaluated"}
            for name, cfg in (policy.get("gates") or {}).items()
        },
        "rollback_ref": args.rollback_ref,
    }


def _validate_required_fields(row: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    missing = []
    for field in policy.get("ledger", {}).get("required_fields", []):
        if field not in row or row[field] in (None, ""):
            missing.append(field)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="PhenoLM managed garden loop")
    parser.add_argument("--observe", action="store_true", help="Observation-only run")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print row, do not append ledger"
    )
    parser.add_argument("--run-id")
    parser.add_argument("--component", default="phenolm")
    parser.add_argument("--candidate-type", default="observation")
    parser.add_argument("--lane", default="all")
    parser.add_argument("--model-id", default="unknown")
    parser.add_argument("--provider-or-engine", default="unknown")
    parser.add_argument("--eval-suite", default="unknown")
    parser.add_argument("--rollback-ref", default="none")
    parser.add_argument("--result", default="observed")
    parser.add_argument("--metrics-json", default="")
    parser.add_argument(
        "--metric", action="append", default=[], help="Metric as key=value; repeatable"
    )
    args = parser.parse_args()

    policy = _load_policy()
    mode = policy.get("loop", {}).get("default_mode", "observe")
    if not args.observe and mode == "observe":
        raise SystemExit("garden_loop default_mode=observe; pass --observe for now")

    row = _base_row(args, policy)
    missing = _validate_required_fields(row, policy)
    if missing:
        raise SystemExit(
            f"garden ledger row missing required fields: {', '.join(missing)}"
        )

    if args.dry_run:
        print(json.dumps(row, indent=2))
        return 0

    path = _ledger_path(policy)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    (STATE_DIR / "garden_latest.json").write_text(
        json.dumps(row, indent=2), encoding="utf-8"
    )
    print(f"Garden ledger row appended: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
