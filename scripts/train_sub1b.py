#!/usr/bin/env python3
"""Sub-1B Needle + draft training scaffold for 3090 Ti (Phase 6)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import PHENO_ROOT, STATE_DIR


def _expand_env(s: str) -> str:
    if not isinstance(s, str):
        return s
    import os

    s = s.replace("${PHENO_ROOT}", str(PHENO_ROOT)).replace("${HOME}", str(Path.home()))
    return os.path.expandvars(s)


def load_yaml(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "training" / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def count_jsonl(root: Path, glob: str) -> int:
    n = 0
    for path in sorted(root.glob(glob)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                n += 1
    return n


def plan_needle(cfg: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    data_root = Path(_expand_env(cfg["data"]["root"]))
    counts = {
        "router": count_jsonl(data_root, cfg["data"]["router_glob"]),
        "ranker": count_jsonl(data_root, cfg["data"]["ranker_glob"]),
        "budget": count_jsonl(data_root, cfg["data"]["budget_glob"]),
    }
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(_expand_env(cfg["training"]["output_dir"]))
    plan = {
        "mode": "needle",
        "timestamp": ts,
        "data_counts": counts,
        "models": list(cfg["models"].keys()),
        "hardware": cfg["hardware"],
        "targets": cfg["targets"],
        "dry_run": dry_run,
        "output_dir": str(out_dir),
    }
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in cfg["models"]:
            (out_dir / name).mkdir(parents=True, exist_ok=True)
        plan_path = STATE_DIR / f"sub1b_needle_{ts}.json"
        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        plan["plan_path"] = str(plan_path)
        plan["train_cmd_scaffold"] = [
            f"# train {name} — {cfg['models'][name]['params_m']}M params"
            for name in cfg["models"]
        ]
    return plan


def plan_draft(cfg: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    data_root = Path(_expand_env(cfg["data"]["root"]))
    n = count_jsonl(data_root, cfg["data"]["glob"])
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(_expand_env(cfg["distillation"]["output_dir"]))
    plan = {
        "mode": "draft_06b",
        "timestamp": ts,
        "pairs": n,
        "min_pairs": cfg["data"]["min_pairs"],
        "ready": n >= int(cfg["data"]["min_pairs"]),
        "teacher": cfg["teacher"],
        "hardware": cfg["hardware"],
        "dry_run": dry_run,
        "output_dir": str(out_dir),
    }
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        plan_path = STATE_DIR / f"sub1b_draft_{ts}.json"
        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        plan["plan_path"] = str(plan_path)
    return plan


def main() -> None:
    p = argparse.ArgumentParser(description="Sub-1B Needle + draft training scaffold")
    p.add_argument("--mode", choices=("needle", "draft", "all"), default="all")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    results = {}
    if args.mode in ("needle", "all"):
        needle_cfg = load_yaml("sub1b_needle.yaml")
        results["needle"] = plan_needle(needle_cfg, dry_run=args.dry_run)
        print("Needle:", json.dumps(results["needle"], indent=2))

    if args.mode in ("draft", "all"):
        draft_cfg = load_yaml("draft_06b.yaml")
        results["draft"] = plan_draft(draft_cfg, dry_run=args.dry_run)
        print("Draft:", json.dumps(results["draft"], indent=2))

    if not args.dry_run and len(results) > 1:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        combined = STATE_DIR / f"sub1b_combined_{ts}.json"
        combined.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Combined plan: {combined}")


if __name__ == "__main__":
    main()
