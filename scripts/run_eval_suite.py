#!/usr/bin/env python3
"""Unified eval suite: traces -> wastage -> pillars -> budget -> playground manifest.

.. deprecated::
    This script is deprecated as of 2026-07-21. Use the canonical
    ``harbor`` CLI from the portage fork instead. The ``--small-grid
    --verify`` flow that this script supports is the legacy
    smoke-test-only entry point; production runs go through
    ``harbor run --dataset <name>``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from eval.budget import estimate_from_omniroute
from eval.pillars import score_from_wastage
from eval.tbench import export_leaderboard, format_leaderboard_table
from pheno.paths import EVAL_RESULTS_DIR, PHENO_ROOT
from traces.ingest import collect_all
from traces.wastage import analyze_wastage


def main() -> None:
    p = argparse.ArgumentParser(description="Run full pheno eval suite")
    p.add_argument("--skip-traces", action="store_true")
    p.add_argument("--skip-playground", action="store_true")
    p.add_argument(
        "--small-grid", action="store_true", help="Run 2x2 playground matrix"
    )
    p.add_argument(
        "--harbor-oracle", action="store_true", help="Run Harbor oracle sanity"
    )
    p.add_argument(
        "--energy-source",
        choices=["none", "m1_pmu", "nvidia_smi", "powermetrics"],
        default="none",
        help="Energy measurement source (default: none)",
    )
    args = p.parse_args()

    results: dict[str, Any] = {"started_at": datetime.now(UTC).isoformat(), "steps": {}}

    if not args.skip_traces:
        path, n = collect_all(omniroute_limit=5000)
        events = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        wastage = analyze_wastage(events).to_dict()
        budget = estimate_from_omniroute().to_dict()
        pillars = score_from_wastage(wastage, budget).to_dict()
        results["steps"]["traces"] = {"path": str(path), "count": n}
        results["steps"]["wastage"] = wastage
        results["steps"]["pillars"] = pillars
        results["steps"]["budget"] = budget

    if not args.skip_playground:
        pg_args = [sys.executable, str(PHENO_ROOT / "scripts" / "run_playground.py")]
        if args.small_grid:
            pg_args.append("--small-grid")
        else:
            pg_args.extend(["--count-only"])
        if args.energy_source != "none":
            pg_args.extend(["--energy-source", args.energy_source])
        proc = subprocess.run(pg_args, capture_output=True, text=True, cwd=PHENO_ROOT)
        results["steps"]["playground"] = {
            "stdout": proc.stdout[-500:],
            "code": proc.returncode,
        }

    if args.harbor_oracle:
        ps1 = PHENO_ROOT / "harbor" / "run_tbench_local.ps1"
        if ps1.exists():
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-File", str(ps1)],
                capture_output=True,
                text=True,
                cwd=PHENO_ROOT,
                timeout=900,
            )
            results["steps"]["harbor"] = {
                "code": proc.returncode,
                "tail": proc.stdout[-800:],
            }

    export_leaderboard(include_combo=False)
    results["steps"]["tbench"] = {
        "leaderboard": format_leaderboard_table(include_combo=False),
        "path": str(EVAL_RESULTS_DIR / "tbench_model_scores_latest.json"),
    }

    results["finished_at"] = datetime.now(UTC).isoformat()
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = (
        EVAL_RESULTS_DIR
        / f"eval_suite_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results.get("steps", {}), indent=2)[:4000])
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
