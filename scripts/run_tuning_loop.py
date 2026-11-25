#!/usr/bin/env python3
"""Full RLVR tuning loop — traces, nested rewards, DPO, playground, combo weights."""

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
from eval.nested_rlvr import score_batch
from eval.pillars import score_from_wastage
from eval.tbench import best_l2_harbor_reward, export_leaderboard
from pheno.paths import (
    CONFIG_DIR,
    EVAL_RESULTS_DIR,
    PHENO_ROOT,
    STATE_DIR,
    TRAINING_DIR,
)
from traces.ingest import collect_all
from traces.wastage import analyze_wastage


def _load_jsonl(path: Path, limit: int = 200) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def _update_combo_weights(nested: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    """Nightly RL loop: adjust combo tier weights from pass rates + cost."""
    combo_path = CONFIG_DIR / "combo_main.json"
    if not combo_path.exists():
        return {"updated": False, "reason": "combo_main.json missing"}
    combo = json.loads(combo_path.read_text(encoding="utf-8"))
    pass_rate = nested.get("pass_rate") or 0.0
    alert = budget.get("alert_level", "green")

    # Boost local routine weight when pass rate good and budget red
    tiers = combo.get("tiers", combo)
    if isinstance(tiers, dict):
        parallel = tiers.get("parallel_lanes", tiers.get("parallel", {}))
        if isinstance(parallel, dict) and "lanes" in parallel:
            for lane in parallel["lanes"]:
                if lane.get("lane") == "routine":
                    lane["weight"] = min(
                        1.0, float(lane.get("weight", 0.5)) + 0.05 * pass_rate
                    )
                if lane.get("lane") == "ci_pr" and alert in ("red", "blackout"):
                    lane["weight"] = max(0.1, float(lane.get("weight", 0.3)) - 0.05)

    combo["_tuning"] = {
        "updated_at": datetime.now(UTC).isoformat(),
        "pass_rate": pass_rate,
        "alert_level": alert,
    }
    combo_path.write_text(json.dumps(combo, indent=2), encoding="utf-8")
    export = TRAINING_DIR / "combo_main.json"
    export.write_text(json.dumps(combo, indent=2), encoding="utf-8")
    return {"updated": True, "pass_rate": pass_rate, "alert": alert}


def main() -> int:
    p = argparse.ArgumentParser(description="Full pheno RLVR tuning iteration")
    p.add_argument("--skip-dpo", action="store_true")
    p.add_argument("--skip-playground", action="store_true")
    p.add_argument("--skip-repo2rl", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    report: dict[str, Any] = {"started_at": datetime.now(UTC).isoformat(), "steps": {}}

    # 1. Collect traces
    trace_path, n = collect_all(omniroute_limit=5000)
    events = _load_jsonl(trace_path, limit=5000)
    report["steps"]["traces"] = {"path": str(trace_path), "count": n}

    # 2. Wastage + pillars + budget
    wastage = analyze_wastage(events).to_dict()
    budget = estimate_from_omniroute().to_dict()
    pillars = score_from_wastage(wastage, budget).to_dict()
    report["steps"]["wastage"] = wastage
    report["steps"]["pillars"] = pillars
    report["steps"]["budget"] = budget

    # 3. Nested RLVR scoring on OmniRoute traces (+ TB2.0 L2 if available)
    omni = [e for e in events if e.get("source") == "omniroute"][:500]
    harbor_l2 = best_l2_harbor_reward()
    nested = score_batch(omni, wastage=wastage)
    if harbor_l2 is not None:
        nested["harbor_tbench_best_mean"] = harbor_l2
        nested["L2_from_tbench"] = harbor_l2
    export_leaderboard(include_combo=False)
    report["steps"]["tbench_leaderboard"] = str(
        EVAL_RESULTS_DIR / "tbench_model_scores_latest.json"
    )
    report["steps"]["nested_rlvr"] = nested

    if args.dry_run:
        print(json.dumps(report["steps"], indent=2)[:4000])
        return 0

    # 4. Nightly DPO export
    if not args.skip_dpo:
        r = subprocess.run(
            [
                sys.executable,
                str(PHENO_ROOT / "scripts" / "nightly_dpo.py"),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=PHENO_ROOT,
            encoding="utf-8",
            errors="replace",
        )
        report["steps"]["dpo"] = {"code": r.returncode, "stdout": r.stdout[-500:]}

    # 5. Playground local-first slice
    if not args.skip_playground:
        r = subprocess.run(
            [
                sys.executable,
                str(PHENO_ROOT / "scripts" / "run_playground.py"),
                "--harness-types",
                "omniroute_local,forge,codex",
                "--model-nets",
                "qwen35_08b,lfm25_8b_a1b,ornith_8b",
                "--routing-policies",
                "local_first",
                "--decode-experiments",
                "baseline,speculative_06b",
                "--train-modes",
                "none,qlora_role",
                "--limit",
                "12",
            ],
            capture_output=True,
            text=True,
            cwd=PHENO_ROOT,
            encoding="utf-8",
            errors="replace",
        )
        report["steps"]["playground"] = {
            "code": r.returncode,
            "stdout": r.stdout[-800:],
        }

    # 6. Repo2RL harbor oracle on reference dataset
    if not args.skip_repo2rl:
        r = subprocess.run(
            [
                sys.executable,
                str(PHENO_ROOT / "scripts" / "repo2rl_eval.py"),
                "--n-tasks",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=PHENO_ROOT,
            timeout=900,
            encoding="utf-8",
            errors="replace",
        )
        report["steps"]["repo2rl"] = {"code": r.returncode, "stdout": r.stdout[-800:]}

    # 7. Update combo weights from nested pass rate + budget
    report["steps"]["combo_update"] = _update_combo_weights(nested, budget)

    # 8. Record this run in the managed garden ledger as observation-only.
    # Promotion/demotion is handled by scripts/gardener.py once gates exist.
    garden_metrics = {
        "nested_pass_rate": nested.get("pass_rate"),
        "nested_mean_composite": nested.get("mean_composite"),
        "budget_alert_level": budget.get("alert_level"),
        "estimated_monthly_usd": budget.get("estimated_monthly_usd"),
        "pillar_composite": pillars.get("composite"),
        "trace_count": n,
    }
    r = subprocess.run(
        [
            sys.executable,
            str(PHENO_ROOT / "scripts" / "gardener.py"),
            "--observe",
            "--component",
            "phenolm",
            "--candidate-type",
            "observation",
            "--lane",
            "all",
            "--model-id",
            "Main",
            "--provider-or-engine",
            "omniroute-dev",
            "--eval-suite",
            "tuning_loop",
            "--rollback-ref",
            "none",
            "--metrics-json",
            json.dumps(garden_metrics),
        ],
        capture_output=True,
        text=True,
        cwd=PHENO_ROOT,
        encoding="utf-8",
        errors="replace",
    )
    report["steps"]["garden_observe"] = {
        "code": r.returncode,
        "stdout": r.stdout[-500:],
        "stderr": r.stderr[-500:],
    }

    report["finished_at"] = datetime.now(UTC).isoformat()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = EVAL_RESULTS_DIR / f"tuning_loop_{ts}.json"
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (STATE_DIR / "tuning_loop_latest.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(
        f"Nested RLVR pass_rate: {nested.get('pass_rate')} composite: {nested.get('mean_composite')}"
    )
    print(
        f"Budget: ${budget.get('estimated_monthly_usd'):.0f} ({budget.get('alert_level')})"
    )
    print(f"Pillar composite: {pillars.get('composite')}")
    print(f"Full report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
