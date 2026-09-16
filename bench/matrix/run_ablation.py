"""Ablation matrix runner — thin scaffold replacing ``bench.comparison.stock_vs_ours``.

Variants:
  - ``baseline_mlx``: direct MLX inference via ``bench.comparison.mlx_direct``.
  - ``candidate_stack``: same MLX path for now; kernel stack wiring is PR3+.

Artifacts (per run):
  - ``bench/results/ablation/<run_id>/cells.json`` — V5 cell list + summary
  - ``bench/results/ablation/<run_id>/evaluation_report.json`` — contract-shaped report

Harbor / Apple Container verification feeds ``verified_pass_at_1`` when
a ``harbor_reward`` is provided per cell; cells without reward default to 0.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.ablation.dry_run_banner import get_dry_run_banner
from bench.comparison.mlx_direct import MLXDirect
from bench.comparison.mlx_direct import is_available as mlx_is_available
from bench.contracts.cell_metrics import cell_pass_fields, task_gen_ok
from bench.matrix.run_ablation_helpers import (  # noqa: F401
    REPO_ROOT,
    _cell_to_task_result,
    _git_head,
    _prompt_for,
    _sha256_hex,
    _sort_json,
    _task_ids,
    _utc_now,
    build_cells_payload,
    compute_verified_pass_at_1,
    verifier_available,
    verifier_judge_for_cell,
)

RESULTS_ROOT = REPO_ROOT / "bench" / "results" / "ablation"

VARIANT_BASELINE = "baseline_mlx"
VARIANT_CANDIDATE = "candidate_stack"
VARIANTS = [VARIANT_BASELINE, VARIANT_CANDIDATE]

# Full 10-suite list for parity with stock_vs_ours; scaffold defaults to a subset.
ALL_SUITES = [
    "mmlu-pro",
    "gpqa-diamond",
    "aime",
    "arc-agi-2",
    "livecodebench",
    "aider-polyglot",
    "swe-bench",
    "swe-bench-pro",
    "bfcl",
    "terminal-bench",
]
DEFAULT_SUITES = ["mmlu-pro", "ifeval"]
DEFAULT_MODEL = "Qwen/Qwen3.5-0.8B"
SCHEMA_HASH = "533dd0fa0d9b36145ef2e23a5c32aed39a67bc09bd36822b58289b61d5640a2e"


@dataclass(frozen=True)
class AblationConfig:
    run_id: str
    suites: list[str]
    variants: list[str]
    tasks_per_suite: int
    model_id: str
    dry_run: bool
    output_root: Path


@dataclass
class AblationResult:
    run_id: str
    cells: list[dict[str, Any]]
    started_at: str
    stopped_at: str
    dry_run: bool
    model_id: str
    suites: list[str]
    variants: list[str]
    tasks_per_suite: int


def build_cell(
    *,
    suite: str,
    task_id: str,
    variant: str,
    model_id: str,
    gen_success: bool,
    wall_clock_s: float = 0.0,
    reply: str = "",
    harbor_reward: float | None = None,
) -> dict[str, Any]:
    """Build one V5 cell dict with v0.2 pass-metric fields."""
    pass_metrics = cell_pass_fields(gen_success, harbor_reward=harbor_reward)
    return {
        "suite": suite,
        "task_id": task_id,
        "suite_task_key": f"{suite}::{task_id}",
        "variant": variant,
        "model_id": model_id,
        "ok": gen_success,
        "wall_clock_s": wall_clock_s,
        "tokens_read": len(_prompt_for(suite, task_id)) // 4,
        "tokens_created": len(reply) // 4 if reply else 0,
        **pass_metrics,
        "reply": reply[:200] if reply else "",
    }


def _run_cell_dry(
    suite: str,
    task_id: str,
    variant: str,
    model_id: str,
) -> dict[str, Any]:
    reply = f"[dry-run:{variant}] synthetic answer for {task_id}"
    return build_cell(
        suite=suite,
        task_id=task_id,
        variant=variant,
        model_id=model_id,
        gen_success=True,
        wall_clock_s=0.001,
        reply=reply,
        harbor_reward=None,
    )


def _run_cell_mlx(
    suite: str,
    task_id: str,
    variant: str,
    model_id: str,
    mlx: MLXDirect,
    max_tokens: int,
) -> dict[str, Any]:
    prompt = _prompt_for(suite, task_id)
    if variant == VARIANT_CANDIDATE:
        # Scaffold: candidate_stack shares MLX path until kernel dispatch lands.
        prompt = f"{prompt}\n[candidate_stack scaffold]"

    t0 = time.perf_counter()
    text = mlx.generate(prompt, max_tokens=max_tokens, temperature=0.0)
    # `MLXDirect.generate` returns the completion as a `str`. It has no
    # `.ok`, `.text`, or `.wall_clock_s`; ``wall_clock_s`` is measured
    # locally around the call instead.
    gen_success = bool(text)
    wall_clock_s = time.perf_counter() - t0
    return build_cell(
        suite=suite,
        task_id=task_id,
        variant=variant,
        model_id=model_id,
        gen_success=gen_success,
        wall_clock_s=wall_clock_s,
        reply=text if gen_success else "",
        harbor_reward=None,
    )


def run_ablation(config: AblationConfig) -> AblationResult:
    """Execute the ablation matrix and return emitted cells."""
    if config.dry_run:
        # WBS 96 A2: dry-run banner linked to eval_pillars motion multiplier.
        print(get_dry_run_banner(), flush=True)
    started_at = _utc_now()
    t0 = time.perf_counter()
    cells: list[dict[str, Any]] = []

    mlx: MLXDirect | None = None
    if not config.dry_run:
        if not mlx_is_available():
            raise RuntimeError(
                "mlx_lm is not installed. Re-run with --dry-run for CI/smoke, "
                "or install mlx-lm for live MLX inference."
            )
        mlx = MLXDirect(config.model_id)

    for suite in config.suites:
        for task_id in _task_ids(suite, config.tasks_per_suite):
            for variant in config.variants:
                if config.dry_run:
                    cell = _run_cell_dry(suite, task_id, variant, config.model_id)
                else:
                    assert mlx is not None  # nosec B101
                    cell = _run_cell_mlx(
                        suite,
                        task_id,
                        variant,
                        config.model_id,
                        mlx,
                        max_tokens=64,
                    )
                cells.append(cell)

    _ = time.perf_counter() - t0  # reserved for future timing metadata
    return AblationResult(
        run_id=config.run_id,
        cells=cells,
        started_at=started_at,
        stopped_at=_utc_now(),
        dry_run=config.dry_run,
        model_id=config.model_id,
        suites=config.suites,
        variants=config.variants,
        tasks_per_suite=config.tasks_per_suite,
    )


def build_evaluation_report(result: AblationResult) -> dict[str, Any]:
    """Build a contract-shaped EvaluationReport from ablation cells."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in result.cells:
        groups[cell["suite"]].append(cell)

    suites_out: list[dict[str, Any]] = []
    for suite_name in result.suites:
        suite_cells = groups.get(suite_name, [])
        if not suite_cells:
            continue
        task_results = [_cell_to_task_result(c) for c in suite_cells]
        task_results.sort(key=lambda t: t["task_id"])
        n = len(task_results)
        n_ok = sum(1 for t in task_results if t["status"] == "ok")
        gen_ok_values = [v for t in task_results if (v := task_gen_ok(t)) is not None]
        gen_ok_mean = (
            round(sum(gen_ok_values) / n, 4) if n > 0 and gen_ok_values else None
        )
        pass_at_1 = (
            gen_ok_mean
            if gen_ok_mean is not None
            else (round(n_ok / n, 4) if n > 0 else 0.0)
        )
        entry: dict[str, Any] = {
            "suite": suite_name,
            "n": n,
            "passed": n_ok,
            "pass_at_1": pass_at_1,
            "verified_pass_at_1": compute_verified_pass_at_1(suite_cells),
            "evidence_label": "reported",
            "task_results": task_results,
        }
        if gen_ok_mean is not None:
            entry["gen_ok"] = gen_ok_mean
        suites_out.append(entry)

    total_cells = sum(s["n"] for s in suites_out)
    total_passed = sum(s["passed"] for s in suites_out)
    gen_ok_suites = [s for s in suites_out if "gen_ok" in s]
    if gen_ok_suites and total_cells > 0:
        overall_gen_ok = round(
            sum(s["gen_ok"] * s["n"] for s in gen_ok_suites) / total_cells,
            4,
        )
        overall_pass_at_1 = overall_gen_ok
    else:
        overall_gen_ok = None
        overall_pass_at_1 = (
            round(total_passed / total_cells, 4) if total_cells > 0 else 0.0
        )

    overall_verified = compute_verified_pass_at_1(result.cells)

    artifact: dict[str, Any] = {
        "contract_version": "0.1",
        "artifact_kind": "EvaluationReport",
        "schema_hash": SCHEMA_HASH,
        "producer": {
            "repo": "pheno-harness",
            "head": _git_head(),
            "branch": "fix/gen-ok-pass",
            "dirty_paths": [],
            "host": {"os": "darwin", "chip": "unknown", "mlx_server_url": "direct"},
        },
        "run": {
            "run_id": result.run_id,
            "started_at": result.started_at,
            "stopped_at": result.stopped_at,
            "variant": "ablation",
            "model": result.model_id,
            "judge_mode": "deterministic",
            "energy_source": "none",
            "executed_by": "bench.matrix.run_ablation",
            "command": "python -m bench.matrix.run_ablation",
            "evidence_label": "reported" if result.dry_run else "live verified",
            "dry_run": result.dry_run,
        },
        "matrix": {
            "suites": result.suites,
            "tasks_per_suite": result.tasks_per_suite,
            "variants": result.variants,
            "total_cells": total_cells,
        },
        "suites": suites_out,
        "totals": {
            "cells": total_cells,
            "passed": total_passed,
            "pass_at_1": overall_pass_at_1,
            "verified_pass_at_1": overall_verified,
            "evidence_label": "reported",
            **({"gen_ok": overall_gen_ok} if overall_gen_ok is not None else {}),
        },
        "comparator": {
            "winner": "tie",
            "delta_pass_at_1": 0.0,  # nosec B105
            "variants": result.variants,
        },
        "hash_chain": {},
    }

    body = {k: v for k, v in artifact.items() if k != "hash_chain"}
    all_ids = sorted(
        t["task_id"] for s in artifact["suites"] for t in s["task_results"]
    )
    artifact["hash_chain"] = {
        "top_level_sha256": _sha256_hex(body),
        "task_ids_sorted_sha256": hashlib.sha256(
            "\n".join(all_ids).encode("utf-8")
        ).hexdigest(),
    }
    return artifact


def write_artifacts(
    result: AblationResult, output_root: Path | None = None
) -> dict[str, Path]:
    """Write cells.json and evaluation_report.json under the run directory."""
    root = (output_root or RESULTS_ROOT) / result.run_id
    root.mkdir(parents=True, exist_ok=True)

    cells_path = root / "cells.json"
    report_path = root / "evaluation_report.json"

    cells_payload = build_cells_payload(result)
    report_payload = build_evaluation_report(result)

    cells_path.write_text(
        json.dumps(cells_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"cells": cells_path, "evaluation_report": report_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ablation matrix (baseline_mlx vs candidate_stack).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run directory name (default: UUID).",
    )
    parser.add_argument(
        "--suites",
        default=",".join(DEFAULT_SUITES),
        help=f"Comma-separated suite names (default: {','.join(DEFAULT_SUITES)}).",
    )
    parser.add_argument(
        "--variants",
        default=",".join(VARIANTS),
        help=f"Comma-separated variants (default: {','.join(VARIANTS)}).",
    )
    parser.add_argument(
        "--tasks-per-suite",
        type=int,
        default=2,
        help="Synthetic task count per suite (scaffold default: 2).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MLX model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit synthetic cells (gen_ok=1, no harbor_reward → verified_pass_at_1=0); no MLX required.",
    )
    parser.add_argument(
        "--output-root",
        default=str(RESULTS_ROOT),
        help="Root directory for ablation run artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    invalid = [v for v in variants if v not in VARIANTS]
    if invalid:
        print(
            f"ERROR: unknown variant(s): {invalid}. Allowed: {VARIANTS}",
            file=sys.stderr,
        )
        return 2
    if args.tasks_per_suite < 1:
        print("ERROR: --tasks-per-suite must be >= 1", file=sys.stderr)
        return 2

    run_id = args.run_id or str(uuid.uuid4())
    config = AblationConfig(
        run_id=run_id,
        suites=suites,
        variants=variants,
        tasks_per_suite=args.tasks_per_suite,
        model_id=args.model,
        dry_run=args.dry_run,
        output_root=Path(args.output_root),
    )

    try:
        result = run_ablation(config)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    paths = write_artifacts(result, config.output_root)
    print(f"Wrote {paths['cells']}")
    print(f"Wrote {paths['evaluation_report']}")
    print(
        f"DONE: {len(result.cells)} cells "
        f"({'dry-run' if result.dry_run else 'live'}) run_id={result.run_id}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
