#!/usr/bin/env python3
"""Convert stock_vs_ours.py output (run-v4.json) to feynman v0.1 contract format.

Usage:
    python scripts/convert_to_contract.py bench/results/stock-vs-ours/run-v4.json

Writes:
    - run-v4-stock-contract.json
    - run-v4-ours-contract.json
    - run-v4-contract.json  (combined, both variants)
"""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from bench.contracts.cell_assignment import merge_assignment_into_additional
from bench.contracts.cell_metrics import cell_pass_fields, task_gen_ok

SCHEMA_HASH = "533dd0fa0d9b36145ef2e23a5c32aed39a67bc09bd36822b58289b61d5640a2e"

SUITES_ORDER = [
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

# Fields that map directly into task_results top-level
DIRECT_FIELDS = {
    "wall_clock_s",
    "judge",
    "tokens_in",
    "tokens_out",
    "first_token_latency_s",
    "energy_joules",
    "raw_score",
    "status",
    "task_id",
    "failure_reason",
}


def _sort(obj):
    if isinstance(obj, dict):
        return {k: _sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort(x) for x in obj]
    return obj


def canonical_bytes(obj):
    return json.dumps(
        _sort(obj),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def cell_to_task_result(cell):
    """Map a source cell to a contract task_result dict."""
    ok = cell.get("ok", False)
    failure_reason = cell.get("failure_reason", "")
    if isinstance(failure_reason, str) and failure_reason:
        failure_reason_arr = [failure_reason]
    elif isinstance(failure_reason, list):
        failure_reason_arr = failure_reason
    else:
        failure_reason_arr = []

    task_result = {
        "task_id": cell.get("suite_task_key", cell.get("task_id", "")),
        "status": "ok" if ok else "wrong",
        "judge": "deterministic",
        "wall_clock_s": cell.get("wall_clock_s", 0.0),
        "tokens_in": cell.get("tokens_read", 0),
        "tokens_out": cell.get("tokens_created", 0),
        "first_token_latency_s": cell.get("first_token_latency_ms", 0.0) / 1000.0,
        "energy_joules": cell.get("energy_proxy_joules", 0.0),
        "raw_score": cell.get("response_quality_score", 0.0),
        "failure_reason": failure_reason_arr,
        "additionalProperties": {"synthetic": True},
    }

    pass_metrics = cell_pass_fields(
        ok,
        harbor_reward=cell.get("harbor_reward"),
    )
    if "gen_ok" in cell:
        pass_metrics["gen_ok"] = float(cell["gen_ok"])
        pass_metrics["pass_at_1"] = float(cell.get("pass_at_1", cell["gen_ok"]))
        pass_metrics["verified_pass_at_1"] = float(
            cell.get("verified_pass_at_1", pass_metrics["verified_pass_at_1"])
        )
        pass_metrics["evidence_label"] = cell.get(
            "evidence_label", pass_metrics["evidence_label"]
        )
    task_result["additionalProperties"].update(pass_metrics)
    task_result["evidence_label"] = pass_metrics["evidence_label"]

    # Always surface assignment + full transcript fields (v0.3).
    merge_assignment_into_additional(task_result["additionalProperties"], cell)

    skip_fields = {
        "suite",
        "task_id",
        "difficulty",
        "variant",
        "ok",
        "suite_task_key",
        "trace",
        "semantic",
        # Handled by merge_assignment_into_additional / pass_metrics above:
        "reply",
        "reply_full",
        "reply_preview",
        "prompt",
        "task_title",
        "task_description",
        "acceptance",
        "rubric",
        "progress_trace",
        "chat_trace",
        "assignment",
        "expected_answer",
    }
    mapped_fields = {
        "wall_clock_s",
        "tokens_read",
        "tokens_created",
        "first_token_latency_ms",
        "energy_proxy_joules",
        "response_quality_score",
        "failure_reason",
        "gen_ok",
        "pass_at_1",
        "verified_pass_at_1",
        "evidence_label",
        "harbor_reward",
    }
    for k, v in cell.items():
        if k in skip_fields or k in mapped_fields:
            continue
        task_result["additionalProperties"][k] = v

    return task_result


def group_by_suite(cells):
    """Group cells by suite name, preserving order."""
    groups = defaultdict(list)
    for cell in cells:
        groups[cell["suite"]].append(cell)
    return groups


def build_variant_artifact(source, variant):
    """Build a single-variant contract artifact."""
    cells = [c for c in source["cells"] if c["variant"] == variant]
    groups = group_by_suite(cells)

    suites = []
    for suite_name in SUITES_ORDER:
        if suite_name not in groups:
            continue
        suite_cells = groups[suite_name]
        task_results = [cell_to_task_result(c) for c in suite_cells]
        task_results.sort(key=lambda t: t["task_id"])

        n = len(task_results)
        n_ok = sum(1 for t in task_results if t["status"] == "ok")
        gen_ok_values = [v for t in task_results if (v := task_gen_ok(t)) is not None]
        if gen_ok_values:
            gen_ok_mean = round(sum(gen_ok_values) / n, 4) if n > 0 else 0.0
            pass_at_1 = gen_ok_mean
        else:
            gen_ok_mean = None
            pass_at_1 = round(n_ok / n, 4) if n > 0 else 0.0

        suite_entry = {
            "suite": suite_name,
            "n": n,
            "passed": n_ok,
            "pass_at_1": pass_at_1,
            "evidence_label": "reported",
            "task_results": task_results,
        }
        if gen_ok_mean is not None:
            suite_entry["gen_ok"] = gen_ok_mean
        suites.append(suite_entry)

    total_cells = sum(s["n"] for s in suites)
    total_passed = sum(s["passed"] for s in suites)
    gen_ok_suites = [s["gen_ok"] for s in suites if "gen_ok" in s]
    if gen_ok_suites:
        overall_gen_ok = (
            round(
                sum(s["gen_ok"] * s["n"] for s in suites if "gen_ok" in s)
                / total_cells,
                4,
            )
            if total_cells > 0
            else 0.0
        )
        overall_pass_at_1 = overall_gen_ok
    else:
        overall_gen_ok = None
        overall_pass_at_1 = (
            round(total_passed / total_cells, 4) if total_cells > 0 else 0.0
        )

    summary = source.get("summary", {})
    meta = summary.get("meta", {})
    model = meta.get("model", "unknown")

    artifact = {
        "contract_version": "0.1",
        "artifact_kind": "EvaluationReport",
        "schema_hash": SCHEMA_HASH,
        "producer": {
            "repo": "pheno-harness",
            "head": "converted-from-run-v4",
            "branch": "main",
            "dirty_paths": [],
            "host": {
                "os": "darwin",
                "chip": "unknown",
                "mlx_server_url": meta.get("mlx_url", ""),
            },
        },
        "run": {
            "run_id": "00000000-0000-0000-0000-000000000000",
            "started_at": "2026-01-01T00:00:00Z",
            "stopped_at": "2026-01-01T00:00:00Z",
            "variant": variant,
            "model": model,
            "judge_mode": "deterministic",
            "energy_source": "none",
            "executed_by": "convert_to_contract.py",
            "command": "python scripts/convert_to_contract.py",
            "evidence_label": "reported",
        },
        "matrix": {
            "suites": [s["suite"] for s in suites],
            "tasks_per_suite": suites[0]["n"] if suites else 0,
            "variants": [variant],
            "total_cells": total_cells,
        },
        "suites": suites,
        "totals": {
            "cells": total_cells,
            "passed": total_passed,
            "pass_at_1": overall_pass_at_1,
            "evidence_label": "reported",
            **({"gen_ok": overall_gen_ok} if overall_gen_ok is not None else {}),
        },
        "comparator": {"winner": "tie", "delta_wall_s": 0.0, "delta_pass_at_1": 0.0},
        "hash_chain": {},
    }

    # Compute hash chain
    body = {k: v for k, v in artifact.items() if k != "hash_chain"}
    all_ids = sorted(
        t["task_id"] for s in artifact["suites"] for t in s["task_results"]
    )
    artifact["hash_chain"] = {
        "top_level_sha256": sha256_hex(body),
        "task_ids_sorted_sha256": hashlib.sha256(
            "\n".join(all_ids).encode("utf-8")
        ).hexdigest(),
    }

    return artifact


def build_combined(artifact_stock, artifact_ours):
    """Build a combined artifact with both variants' suites."""
    all_suites = artifact_stock["suites"] + artifact_ours["suites"]

    total_cells = sum(s["n"] for s in all_suites)
    total_passed = sum(s["passed"] for s in all_suites)
    gen_ok_suites = [s for s in all_suites if "gen_ok" in s]
    if gen_ok_suites:
        overall_gen_ok = (
            round(
                sum(s["gen_ok"] * s["n"] for s in gen_ok_suites) / total_cells,
                4,
            )
            if total_cells > 0
            else 0.0
        )
        overall_pass_at_1 = overall_gen_ok
    else:
        overall_gen_ok = None
        overall_pass_at_1 = (
            round(total_passed / total_cells, 4) if total_cells > 0 else 0.0
        )

    combined = {
        "contract_version": "0.1",
        "artifact_kind": "EvaluationReport",
        "schema_hash": SCHEMA_HASH,
        "producer": artifact_stock["producer"],
        "run": {
            "run_id": "00000000-0000-0000-0000-000000000000",
            "started_at": "2026-01-01T00:00:00Z",
            "stopped_at": "2026-01-01T00:00:00Z",
            "variant": "stock",
            "model": artifact_stock["run"]["model"],
            "judge_mode": "deterministic",
            "energy_source": "none",
            "executed_by": "convert_to_contract.py",
            "command": "python scripts/convert_to_contract.py",
            "evidence_label": "reported",
        },
        "matrix": {
            "suites": list(dict.fromkeys(s["suite"] for s in all_suites)),
            "tasks_per_suite": artifact_stock["matrix"]["tasks_per_suite"],
            "variants": ["stock", "ours"],
            "total_cells": total_cells,
        },
        "suites": all_suites,
        "totals": {
            "cells": total_cells,
            "passed": total_passed,
            "pass_at_1": overall_pass_at_1,
            "evidence_label": "reported",
            **({"gen_ok": overall_gen_ok} if overall_gen_ok is not None else {}),
        },
        "comparator": {
            "winner": (
                "ours"
                if artifact_ours["totals"]["pass_at_1"]
                > artifact_stock["totals"]["pass_at_1"]
                else "stock"
                if artifact_stock["totals"]["pass_at_1"]
                > artifact_ours["totals"]["pass_at_1"]
                else "tie"
            ),
            "delta_wall_s": round(
                artifact_stock["totals"].get("pass_at_1", 0)
                - artifact_ours["totals"].get("pass_at_1", 0),
                4,
            ),
            "delta_pass_at_1": round(
                artifact_ours["totals"]["pass_at_1"]
                - artifact_stock["totals"]["pass_at_1"],
                4,
            ),
        },
        "hash_chain": {},
    }

    body = {k: v for k, v in combined.items() if k != "hash_chain"}
    all_ids = sorted(
        t["task_id"] for s in combined["suites"] for t in s["task_results"]
    )
    combined["hash_chain"] = {
        "top_level_sha256": sha256_hex(body),
        "task_ids_sorted_sha256": hashlib.sha256(
            "\n".join(all_ids).encode("utf-8")
        ).hexdigest(),
    }

    return combined


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_to_contract.py <input.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    source = json.loads(input_path.read_text(encoding="utf-8"))
    stem = input_path.stem
    parent = input_path.parent

    for variant in ("stock", "ours"):
        artifact = build_variant_artifact(source, variant)
        out_path = parent / f"{stem}-{variant}-contract.json"
        out_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {out_path}")

    artifact_stock = build_variant_artifact(source, "stock")
    artifact_ours = build_variant_artifact(source, "ours")
    combined = build_combined(artifact_stock, artifact_ours)
    out_path = parent / f"{stem}-contract.json"
    out_path.write_text(
        json.dumps(combined, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
