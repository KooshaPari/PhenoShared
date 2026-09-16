#!/usr/bin/env python3
"""Emit hardware-aware local placement candidates without launching a model."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def live_gpus() -> list[dict[str, Any]]:
    query = "index,name,uuid,memory.total,memory.free,temperature.gpu,power.draw"
    result = subprocess.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = []
    for line in result.stdout.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 7:
            continue
        index, name, uuid, total, free, temp, power = fields
        rows.append(
            {
                "index": int(index),
                "name": name,
                "uuid": uuid,
                "vram_mib": int(float(total)),
                "free_vram_mib": int(float(free)),
                "temperature_c": float(temp),
                "power_w": float(power),
            }
        )
    return rows


def plan(
    config: dict[str, Any],
    model_alias: str | None,
    gpus: list[dict[str, Any]],
    workload: str | None = None,
) -> dict[str, Any]:
    models = config.get("models", {})
    selected = {model_alias: models[model_alias]} if model_alias else models
    placements = []
    reserve = float(config.get("policy", {}).get("reserve_vram_fraction", 0.12))
    for alias, model in selected.items():
        artifact_mib = int(float(model.get("artifact_q4_gb", 0)) * 1024)
        artifact_status = str(model.get("artifact_status", ""))
        blocked = artifact_status.startswith(
            ("blocked", "failed", "conversion_runtime_failure")
        )
        for gpu in gpus:
            capacity = int(gpu["vram_mib"] * (1.0 - reserve))
            fits = artifact_mib > 0 and artifact_mib <= capacity
            legacy = "1080 Ti" in gpu["name"]
            status = (
                "blocked_artifact"
                if blocked
                else ("candidate" if fits else "vram_insufficient")
            )
            if (
                legacy
                and model.get("preferred")
                and "legacy_helper" not in model["preferred"]
            ):
                status = "not_preferred"
            placements.append(
                {
                    "model_alias": alias,
                    "gpu_index": gpu["index"],
                    "gpu_name": gpu["name"],
                    "status": status,
                    "artifact_mib": artifact_mib,
                    "usable_vram_mib": capacity,
                    "headroom_mib": capacity - artifact_mib,
                    "role": "helper" if legacy else "primary",
                }
            )
        placements.append(
            {
                "model_alias": alias,
                "tier": "ddr4_or_nvme",
                "status": "spill_probe_only" if not blocked else "blocked_artifact",
                "reason": "transfer cost must be measured; never an implicit serving fallback",
            }
        )
    workload_classes = config.get("workload_classes", {})
    routes = []
    selected_workloads = (
        {workload: workload_classes[workload]} if workload else workload_classes
    )
    for name, spec in selected_workloads.items():
        routes.append(
            {
                "workload_class": name,
                "preferred_tier": spec.get("preferred_tier"),
                "fallback_tier": spec.get("fallback_tier"),
                "constraints": list(spec.get("constraints", [])),
                "migration": "explicit_only",
            }
        )
    return {
        "schema_version": "pheno.hardware_placement_plan.v1",
        "gpus": gpus,
        "placements": placements,
        "workload_routes": routes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("config/hardware_aware_placement.yaml")
    )
    parser.add_argument("--model")
    parser.add_argument(
        "--workload",
        choices=[
            "manager_long_context",
            "coding_agent",
            "short_draft",
            "router_classifier",
            "verifier_reranker",
            "cold_worker",
        ],
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    result = plan(config, args.model, live_gpus(), args.workload)
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
