#!/usr/bin/env python3
"""4B energy baseline benchmark: dry-run extrapolation from 0.8B baseline.

Since the 4B model is not downloaded locally, this script extrapolates
energy/latency/memory metrics from the 0.8B baseline using theoretical
scaling factors (5× parameters → ~5× compute per token).

Usage:
    python scripts/run_4b_dryrun.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

SCALING_FACTOR = 5.0
ESTIMATED_MEMORY_GB = 2.0
ESTIMATED_LATENCY_MS_PER_CELL = 750.0
ESTIMATED_ENERGY_MJ_PER_CELL = 375.0

TASKS_PER_SUITE = 25
SUITES = 10

V5_SUITES = [
    "arc-agi-2",
    "bfcl-v4",
    "browsercomp",
    "deep-swe",
    "gpqa-diamond",
    "hle",
    "ifeval",
    "kernelbench",
    "mmlu-pro",
    "mt-bench",
    "osworld",
    "perplexity",
    "pinchbench",
    "swe-bench-verified",
    "terminal-bench",
]


def generate_manifest() -> dict[str, Any]:
    total_cells = TASKS_PER_SUITE * SUITES
    total_estimated_time_min = (total_cells * ESTIMATED_LATENCY_MS_PER_CELL) / (
        60.0 * 1000.0
    )
    total_estimated_energy_j = (total_cells * ESTIMATED_ENERGY_MJ_PER_CELL) / 1000.0

    manifest = {
        "model": "qwen3.5-4b-coder",
        "scaling_factor": SCALING_FACTOR,
        "estimated_memory_gb": ESTIMATED_MEMORY_GB,
        "estimated_latency_ms_per_cell": ESTIMATED_LATENCY_MS_PER_CELL,
        "estimated_energy_mj_per_cell": ESTIMATED_ENERGY_MJ_PER_CELL,
        "tasks": TASKS_PER_SUITE,
        "suites": SUITES,
        "total_estimated_time_min": round(total_estimated_time_min, 2),
        "total_estimated_energy_j": round(total_estimated_energy_j, 2),
    }
    return manifest


def generate_per_suite_estimate() -> list[dict]:
    rows = []
    for suite in V5_SUITES:
        rows.append(
            {
                "suite": suite,
                "tasks": TASKS_PER_SUITE,
                "latency_ms_per_task": ESTIMATED_LATENCY_MS_PER_CELL,
                "energy_mj_per_task": ESTIMATED_ENERGY_MJ_PER_CELL,
                "suite_total_latency_s": round(
                    (TASKS_PER_SUITE * ESTIMATED_LATENCY_MS_PER_CELL) / 1000.0, 2
                ),
                "suite_total_energy_mj": round(
                    TASKS_PER_SUITE * ESTIMATED_ENERGY_MJ_PER_CELL, 2
                ),
            }
        )
    return rows


def main() -> None:
    out_dir = Path("bench/results/4b-dryrun")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = generate_manifest()
    per_suite = generate_per_suite_estimate()

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    matrix_path = out_dir / "matrix.json"
    matrix = {
        "model": "qwen3.5-4b-coder",
        "scaling_factor": SCALING_FACTOR,
        "dry_run": True,
        "source": "extrapolated-from-0.8b",
        "timestamp": time.time(),
        "suites": per_suite,
        "totals": {
            "total_tasks": manifest["tasks"] * manifest["suites"],
            "total_latency_min": manifest["total_estimated_time_min"],
            "total_energy_j": manifest["total_estimated_energy_j"],
            "estimated_memory_gb": manifest["estimated_memory_gb"],
        },
    }
    matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {manifest_path}")
    print(f"Matrix written to {matrix_path}")


if __name__ == "__main__":
    main()
