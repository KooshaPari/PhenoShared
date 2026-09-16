"""Stock-vs-ours report generation and formatting.

Builds summary statistics and writes markdown reports for a single
model comparison run.
"""

from __future__ import annotations

import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from bench.comparison.stock_vs_ours_adapters import (
    DIFFICULTY_MIX,
    MODEL_REGISTRY,
    SUITES,
    model_slug,
)


def _build_summary(
    all_cells: list[dict[str, Any]],
    variants: list[str],
    model_id: str,
    mlx_url: str,
    n_suites: int,
) -> dict[str, Any]:
    """Build the summary dict for a set of cells (one model)."""
    by_variant: dict[str, list[dict[str, Any]]] = {v: [] for v in variants}
    for c in all_cells:
        by_variant[c["variant"]].append(c)

    meta = MODEL_REGISTRY.get(model_id, {})
    summary: dict[str, Any] = {
        "meta": {
            "model_id": model_id,
            "model_slug": model_slug(model_id),
            "model_params": meta.get("params", 0),
            "model_architecture": meta.get("architecture", "unknown"),
            "model_size_on_disk_gb": meta.get("size_on_disk_gb", 0),
            "mlx_url": mlx_url,
            "n_suites": n_suites,
            "n_tasks_per_suite": 25,
            "difficulty_mix": DIFFICULTY_MIX,
            "variants": variants,
            "n_cells": len(all_cells),
        },
        "by_variant": {},
    }
    for variant, cells in by_variant.items():
        if not cells:
            continue
        _gen_ok_mean = statistics.mean(c["gen_ok"] for c in cells)
        summary["by_variant"][variant] = {
            "n_cells": len(cells),
            "gen_ok": _gen_ok_mean,
            "pass_at_1": _gen_ok_mean,
            "verified_pass_at_1": statistics.mean(
                c.get("verified_pass_at_1", 0.0) for c in cells
            ),
            "ok_count": sum(1 for c in cells if c["ok"]),
            "n_hallucinations": sum(c["hallucination_count"] for c in cells),
            "total_tokens_in": sum(c["tokens_read"] for c in cells),
            "total_tokens_out": sum(c["tokens_created"] for c in cells),
            "mean_wall_clock_s": statistics.mean(c["wall_clock_s"] for c in cells),
            "mean_partial_credit": statistics.mean(c["partial_credit"] for c in cells),
            "mean_format_compliance": statistics.mean(
                c["format_compliance_rate"] for c in cells
            ),
            "mean_intent_preservation": statistics.mean(
                c["intent_preservation_rate"] for c in cells
            ),
            "mean_ttft_ms": statistics.mean(c["ttft_ms"] for c in cells),
            "mean_verbosity_chars": statistics.mean(
                c["verbosity_chars"] for c in cells
            ),
            "mean_tokens_read": statistics.mean(c["tokens_read"] for c in cells),
            "mean_tokens_created": statistics.mean(c["tokens_created"] for c in cells),
            "mean_response_quality_score": statistics.mean(
                c["response_quality_score"] for c in cells
            ),
            "mean_energy_efficiency": statistics.mean(
                c["energy_efficiency_tok_per_joule"] for c in cells
            ),
            "mean_cache_hit_rate": statistics.mean(c["cache_hit_rate"] for c in cells),
            "mean_e2e_latency_ms": statistics.mean(c["e2e_latency_ms"] for c in cells),
            "mean_decode_speed_tps": statistics.mean(
                c["decode_speed_tps"] for c in cells
            ),
            "mean_cost_efficiency": statistics.mean(
                c["cost_efficiency"] for c in cells
            ),
            "mean_joules_per_output_token": statistics.mean(
                c["joules_per_output_token"] for c in cells
            ),
            "mean_decode_efficiency": statistics.mean(
                c["decode_efficiency"] for c in cells
            ),
            "mean_memory_bandwidth_utilization_pct": statistics.mean(
                c["memory_bandwidth_utilization_pct"] for c in cells
            ),
            "total_energy_joules": sum(c["energy_proxy_joules"] for c in cells),
            "thermal_throttle_count": sum(
                1 for c in cells if c["thermal_throttle_detected"]
            ),
            "peak_concurrent_session_capacity": max(
                c["concurrent_session_capacity"] for c in cells
            ),
            "mean_quality_asymptote": statistics.mean(
                c["trace"]["quality_asymptote"] for c in cells
            ),
            "mean_completion_asymptote": statistics.mean(
                c["trace"]["completion_asymptote"] for c in cells
            ),
            "mean_waning_magnitude": statistics.mean(
                c["trace"]["waning_magnitude"] for c in cells
            ),
            "n_waning_detected": sum(1 for c in cells if c["trace"]["waning_detected"]),
            "mean_relevance": statistics.mean(
                c["semantic"]["relevance"] for c in cells
            ),
            "mean_coherence": statistics.mean(
                c["semantic"]["coherence"] for c in cells
            ),
            "mean_completeness": statistics.mean(
                c["semantic"]["completeness"] for c in cells
            ),
            "mean_info_density": statistics.mean(
                c["semantic"]["info_density"] for c in cells
            ),
            "factor_distribution": dict(
                Counter(c["failure_analysis"]["primary_factor"] for c in cells)
            ),
            "router_accuracy": (
                sum(1 for c in cells if c["router_correct"]) / len(cells)
                if cells
                else 0.0
            ),
            "mean_router_confidence": statistics.mean(
                c["router_confidence"] for c in cells
            )
            if cells
            else 0.0,
            "mean_router_time_ms": statistics.mean(c["router_time_ms"] for c in cells)
            if cells
            else 0.0,
            "routing_overhead_pct": (
                statistics.mean(c["router_time_ms"] for c in cells)
                / max(
                    statistics.mean(c["router_time_ms"] for c in cells)
                    + statistics.mean(c["wall_clock_s"] for c in cells) * 1000,
                    1.0,
                )
                * 100
                if cells
                else 0.0
            ),
        }
    return summary


def _write_md_report(
    path: Path,
    summary: dict[str, Any],
    all_cells: list[dict[str, Any]],
) -> None:
    """Write the markdown report for a single model run."""
    meta = summary["meta"]
    mid = meta["model_id"]
    mlx_url = meta["mlx_url"]
    n_suites = meta["n_suites"]

    with open(path, "w") as f:
        f.write(f"# {mid} Stock vs Ours — {n_suites} suites × 25 tasks\n\n")
        if mlx_url == "direct":
            f.write(f"Model: `{mid}`  •  Backend: `direct MLX Python API`\n\n")
        else:
            f.write(f"Model: `{mid}`  •  Server: `{mlx_url}`\n\n")
        f.write("## Summary\n\n")
        f.write(
            "| Variant | pass@1 | mean wall | mean partial_credit | format_compliance | intent_preservation | ok | n |\n"
        )
        f.write(
            "|---------|--------|-----------|--------------------|-------------------|--------------------|----|---|\n"
        )
        for variant, s in summary["by_variant"].items():
            f.write(
                f"| {variant} | {s['pass_at_1']:.3f} | {s['mean_wall_clock_s']:.2f}s | {s['mean_partial_credit']:.3f} | {s['mean_format_compliance']:.3f} | {s['mean_intent_preservation']:.3f} | {s['ok_count']}/{s['n_cells']} | {s['n_cells']} |\n"
            )
        f.write("\n## Quality Contract\n\n")
        f.write("| Metric | stock | ours | Δ |\n|--------|-------|------|---|\n")
        sv = summary["by_variant"].get("stock", {})
        ov = summary["by_variant"].get("ours", {})
        for label, key, fmt, unit in [
            ("mean_ttft_ms", "mean_ttft_ms", ".1f", "ms"),
            ("mean_verbosity_chars", "mean_verbosity_chars", ".0f", "chars"),
            ("mean_tokens_read", "mean_tokens_read", ".1f", ""),
            ("mean_tokens_created", "mean_tokens_created", ".1f", ""),
            ("total_tokens_in", "total_tokens_in", ".0f", ""),
            ("total_tokens_out", "total_tokens_out", ".0f", ""),
            ("mean_response_quality_score", "mean_response_quality_score", ".4f", ""),
            ("mean_energy_efficiency", "mean_energy_efficiency", ".4f", "tok/J"),
            ("mean_cache_hit_rate", "mean_cache_hit_rate", ".3f", ""),
            ("mean_e2e_latency_ms", "mean_e2e_latency_ms", ".1f", "ms"),
            ("mean_decode_speed_tps", "mean_decode_speed_tps", ".2f", "tok/s"),
            ("mean_cost_efficiency", "mean_cost_efficiency", ".2f", "tok/s"),
        ]:
            s, o = sv.get(key, 0.0), ov.get(key, 0.0)
            u = (" " + unit) if unit else ""
            f.write(f"| {label} | {s:{fmt}}{u} | {o:{fmt}}{u} | {o - s:+{fmt}} |\n")
        f.write("\n## Efficiency Metrics\n\n")
        f.write("| Metric | stock | ours | Δ |\n|--------|-------|------|---|\n")
        for label, key, fmt, unit in [
            (
                "mean_joules_per_output_token",
                "mean_joules_per_output_token",
                ".4f",
                "J/tok",
            ),
            ("mean_decode_efficiency", "mean_decode_efficiency", ".4f", ""),
            (
                "mean_memory_bandwidth_utilization_pct",
                "mean_memory_bandwidth_utilization_pct",
                ".1f",
                "%",
            ),
            ("total_energy_joules", "total_energy_joules", ".2f", "J"),
            ("thermal_throttle_count", "thermal_throttle_count", "d", ""),
            (
                "peak_concurrent_session_capacity",
                "peak_concurrent_session_capacity",
                "d",
                "",
            ),
        ]:
            s, o = sv.get(key, 0.0), ov.get(key, 0.0)
            u = (" " + unit) if unit else ""
            f.write(f"| {label} | {s:{fmt}}{u} | {o:{fmt}}{u} | {o - s:+{fmt}} |\n")
        f.write("\n## Per-suite breakdown (variant comparison)\n\n")
        f.write(
            "| Suite | stock pass@1 | ours pass@1 | Δ | stock wall | ours wall | Δ | stock pc | ours pc |\n"
        )
        f.write(
            "|-------|-------------|-------------|---|-----------|-----------|---|---------|---------|\n"
        )
        for suite in SUITES:
            s_cells = [
                c for c in all_cells if c["suite"] == suite and c["variant"] == "stock"
            ]
            o_cells = [
                c for c in all_cells if c["suite"] == suite and c["variant"] == "ours"
            ]
            if not s_cells or not o_cells:
                continue
            s_pass = sum(1 for c in s_cells if c["ok"]) / len(s_cells)
            o_pass = sum(1 for c in o_cells if c["ok"]) / len(o_cells)
            s_wall = statistics.mean(c["wall_clock_s"] for c in s_cells)
            o_wall = statistics.mean(c["wall_clock_s"] for c in o_cells)
            s_pc = statistics.mean(c["partial_credit"] for c in s_cells)
            o_pc = statistics.mean(c["partial_credit"] for c in o_cells)
            f.write(
                f"| {suite} | {s_pass:.3f} | {o_pass:.3f} | {o_pass - s_pass:+.3f} | {s_wall:.2f}s | {o_wall:.2f}s | {o_wall - s_wall:+.2f}s | {s_pc:.3f} | {o_pc:.3f} |\n"
            )
        f.write("\n## Methodology\n\n")
        if mlx_url == "direct":
            f.write("- Both variants: direct MLX Python API (bypasses mlx_lm.server)\n")
        else:
            f.write(
                "- Stock: stock model FP16 via local MLX OpenAI server (no pheno kernels)\n"
            )
            f.write(
                "- Ours: same model FP16 routed through pheno-harness dispatch path (4-bit kernel where in-place, FP16 fallback)\n"
            )
        f.write("- Both variants use the same model weights (zero confounders)\n")
        f.write("- 25 tasks per suite (5 easy + 8 medium + 7 hard + 5 ultra)\n")
        f.write("- temperature=0, enable_thinking=false\n")
        f.write("\n## Progress Trace\n\n")
        f.write(
            "| Variant | mean quality asymptote | mean completion asymptote | mean waning magnitude | n waning |\n"
        )
        f.write(
            "|---------|----------------------|--------------------------|----------------------|----------|\n"
        )
        for variant, s in summary["by_variant"].items():
            f.write(
                f"| {variant} | {s['mean_quality_asymptote']:.4f} | {s['mean_completion_asymptote']:.4f} | {s['mean_waning_magnitude']:.4f} | {s['n_waning_detected']} |\n"
            )


__all__ = ["_build_summary", "_write_md_report"]
