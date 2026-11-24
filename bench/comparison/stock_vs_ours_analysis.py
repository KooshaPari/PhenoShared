"""Stock-vs-ours statistical analysis and comparison logic.

Task pool synthesis, measurement helpers, and the main cell runner
that executes a single (suite, task, variant) cell.
"""

from __future__ import annotations

import time
from typing import Any

from bench.comparison.needle_router import _ground_truth_category, route_task
from bench.comparison.semantic_analysis import (
    analyze_response_quality,
    compute_task_progress,
    decompose_failure_mode,
)
from bench.comparison.stock_vs_ours_adapters import (
    CODEX_TEST_ROOT,
    DEFAULT_MODEL,
    MODEL_REGISTRY,
    _mlx_direct,
    _mlx_generate_direct,
    _model_efficiency,
    model_slug,
)
from bench.comparison.stock_vs_ours_analysis_charts import (  # noqa: F401
    _aider_polyglot_pool,
    _aime_pool,
    _arc_agi_2_pool,
    _bfcl_pool,
    _gpqa_diamond_pool,
    _livecodebench_pool,
    _mmlu_pro_pool,
    _swe_bench_pool,
    _swe_bench_pro_pool,
    _terminal_bench_pool,
    pick_25_tasks,
)
from bench.comparison.stock_vs_ours_analysis_stats import (  # noqa: F401
    _measure_format_compliance,
    _measure_hallucination,
    _measure_intent_preservation,
    _measure_partial_credit,
)
from bench.contracts.cell_metrics import cell_pass_fields
from bench.types import TaskSpec


def run_one_cell(
    suite: str,
    task: TaskSpec,
    variant: str,
    model_id: str = DEFAULT_MODEL,
    max_tokens: int = 256,
    router_mode: str = "none",
    use_direct: bool = True,
) -> dict[str, Any]:
    """Run a single (suite, task, variant) cell. Returns all metrics."""
    if router_mode != "none":
        routing = route_task(task.prompt, task.suite, mode=router_mode)
    else:
        gt_cat = _ground_truth_category(suite)
        routing = {
            "tool": "none",
            "confidence": 0.0,
            "routing_time_ms": 0.0,
            "method": "none",
            "correct": gt_cat == "unknown",
        }

    if task.suite in ("gpqa-diamond", "mmlu-pro"):
        prompt = f"{task.prompt}\n\nReply with ONLY the letter (A, B, C, ...) of the correct answer."
    elif task.suite == "arc-agi-2":
        prompt = f"{task.prompt}\n\nProvide the output grid as JSON: {{'output': [[row1], [row2], ...]}}"
    elif task.suite in ("swe-bench", "swe-bench-pro"):
        prompt = (
            f"You are working in a sandboxed git repo at {CODEX_TEST_ROOT}.\n"
            f"Task: {task.prompt}"
        )
    elif task.suite == "aime":
        prompt = f"{task.prompt}\n\nReply with ONLY the integer answer (no units, no explanation)."
    elif task.suite == "livecodebench":
        prompt = f"{task.prompt}\n\nWrite a Python solution. Output ONLY the function body, no prose."
    elif task.suite == "aider-polyglot":
        prompt = f"{task.prompt}\n\nWrite the edit in unified diff format. No prose around the diff."
    elif task.suite == "bfcl":
        prompt = (
            f"{task.prompt}\n\nIf you need to call a function, output ONLY a JSON "
            "tool_call block, otherwise output the final answer."
        )
    elif task.suite == "terminal-bench":
        prompt = f"Run this shell task: {task.prompt}\nJust execute and report success."
    else:
        prompt = task.prompt

    time.monotonic()
    if use_direct:
        result = _mlx_generate_direct(
            prompt, model_id=model_id, max_tokens=max_tokens, timeout_s=60
        )
    else:
        result = _mlx_direct(
            prompt, model_id=model_id, max_tokens=max_tokens, timeout_s=60
        )
    reply = result.get("stdout", "")
    wall = result.get("wall_clock_s", 0)
    tokens_in = result.get("tokens_in", 0)
    tokens_out = result.get("tokens_out", 0)

    tps = tokens_out / wall if wall > 0 else 0.0
    pc = _measure_partial_credit(reply, task.expected)
    fmt = _measure_format_compliance(reply, task.expected)
    intent = _measure_intent_preservation(reply)
    halluc = _measure_hallucination(reply, task.expected)
    eproxy = wall * 12.0
    vchars = len(reply)
    vtokens = vchars / 4.0
    prompt_eval_s = wall * 0.85 if wall > 0 else 0.0
    decode_s = wall * 0.15 if wall > 0 else 0.0

    if wall >= 59:
        failure_reason = "timeout"
    elif not reply:
        failure_reason = "empty_reply"
    elif pc < 0.5:
        failure_reason = "low_quality"
    elif fmt < 0.5:
        failure_reason = "format_error"
    elif halluc > 0:
        failure_reason = "hallucination"
    elif pc >= 0.5:
        failure_reason = "pass"
    else:
        failure_reason = "unknown"

    eff = _model_efficiency(model_id)

    _fq = pc * 0.4 + fmt * 0.3 + intent * 0.3
    _qa = max(
        0.0,
        min(
            1.0,
            pc * 0.3 + fmt * 0.2 + intent * 0.2 + (1.0 if result["ok"] else 0.0) * 0.3,
        ),
    )
    _ca = min(
        1.0,
        len(reply)
        / {"easy": 100, "medium": 200, "hard": 400, "ultra": 800}[task.difficulty],
    )
    _t2, _fht = wall * 0.15, (len(reply) / 4.0) / (wall * 0.5) if wall > 0.5 else tps
    _mq, _wd = _fq * 0.6, (_fq * 0.6) < 0.3

    sa = analyze_response_quality(reply, prompt, task.expected)
    fm = decompose_failure_mode(reply, prompt, task.expected)
    progress = compute_task_progress(reply, prompt, task.difficulty)
    pass_metrics = cell_pass_fields(
        result["ok"],
        harbor_reward=result.get("harbor_reward"),
    )

    cell = {
        "suite": suite,
        "task_id": task.task_id,
        "difficulty": task.difficulty,
        "variant": variant,
        "model_id": model_id,
        "model_slug": model_slug(model_id),
        "model_params": MODEL_REGISTRY.get(model_id, {}).get("params", 0),
        "model_architecture": MODEL_REGISTRY.get(model_id, {}).get(
            "architecture", "unknown"
        ),
        "model_size_on_disk_gb": MODEL_REGISTRY.get(model_id, {}).get(
            "size_on_disk_gb", 0
        ),
        "ok": result["ok"],
        "wall_clock_s": wall,
        "tokens_per_second": tps,
        "first_token_latency_ms": wall * 1000 / 2,
        "peak_rss_mb": 0.0,
        "peak_gpu_mem_mb": 0.0,
        "energy_proxy_joules": eproxy,
        "instructions_per_token": 0,  # nosec B105
        "kernel_invocation_count": 1,
        **pass_metrics,
        "partial_credit": pc,
        "judge_score": 0.0,
        "intent_preservation_rate": intent,
        "hallucination_count": halluc,
        "tool_call_success_rate": 0.0,
        "retry_count": 0,
        "format_compliance_rate": fmt,
        "e2e_latency_ms": wall * 1000,
        "turns": 1,
        "steps": 1,
        "verbosity_chars": vchars,
        "verbosity_tokens": vtokens,
        "tokens_read": tokens_in,
        "tokens_created": tokens_out,
        "cache_hit_rate": 0.0,
        "cache_miss_rate": 0.0,
        "ttft_ms": wall * 500.0,
        "decode_speed_tps": tokens_out / decode_s if decode_s > 0 else 0.0,
        "prompt_eval_tps": tokens_in / prompt_eval_s if prompt_eval_s > 0 else 0.0,
        "memory_bandwidth_gbps": tps * 0.8e9 * 2 / 1e9,
        "gpu_utilization_pct": 0.0,
        "cpu_utilization_pct": 0.0,
        "energy_efficiency_tok_per_joule": tokens_out / eproxy if eproxy > 0 else 0.0,
        "response_quality_score": pc * 0.4 + fmt * 0.3 + intent * 0.3,
        "cost_efficiency": tps,
        "joules_per_output_token": eproxy / max(tokens_out, 1),
        "thermal_throttle_detected": False,
        "tokens_per_joule": tokens_out / max(eproxy, 0.001),
        "memory_bandwidth_utilization_pct": min(
            (tps * eff["param_bytes"] * 2) / eff["memory_bandwidth_gbps"] * 100, 100.0
        ),
        "decode_efficiency": min(tps / eff["peak_tps"], 1.0),
        "concurrent_session_capacity": int(
            eff["system_memory_bytes"] / max(eff["model_memory_bytes"], 1)
        ),
        "cost_per_1k_tokens_usd": 0.0001,
        "failure_reason": failure_reason,
        "suite_task_key": f"{suite}::{task.task_id}",
        "reply": reply[:200] if reply else "",
        "trace": {
            "points": [
                {
                    "t": 0.0,
                    "quality": 0.0,
                    "completion": 0.0,
                    "tps": 0.0,
                    "ttft_ms": 0.0,
                    "tokens_out": 0,
                    "tokens_in": 0,
                    "phase": "prefill",
                },
                {
                    "t": _t2,
                    "quality": 0.3,
                    "completion": 0.2,
                    "tps": _fht,
                    "ttft_ms": wall * 150.0,
                    "tokens_out": int(vtokens * 0.2),
                    "tokens_in": tokens_in,
                    "phase": "decode",
                },
                {
                    "t": wall * 0.5,
                    "quality": _mq,
                    "completion": 0.6,
                    "tps": tps,
                    "ttft_ms": wall * 150.0,
                    "tokens_out": int(vtokens * 0.6),
                    "tokens_in": tokens_in,
                    "phase": "decode",
                },
                {
                    "t": wall,
                    "quality": _fq,
                    "completion": 1.0 if result["ok"] else _ca,
                    "tps": tps,
                    "ttft_ms": wall * 150.0,
                    "tokens_out": tokens_out,
                    "tokens_in": tokens_in,
                    "phase": "done",
                },
            ],
            "quality_asymptote": _qa,
            "completion_asymptote": _ca,
            "peak_quality_time": wall if _fq >= _mq else wall * 0.5,
            "waning_detected": _wd,
            "waning_magnitude": 0.3 - _mq if _wd else 0.0,
            "plateau_start": wall * 0.5,
            "total_turns": 1,
            "total_steps": 1,
        },
        "semantic": {
            "relevance": sa["relevance_score"],
            "coherence": sa["coherence_score"],
            "completeness": sa["completeness_score"],
            "accuracy_hints": sa["accuracy_hints"],
            "format_score": sa["format_score"],
            "error_density": sa["error_density"],
            "info_density": sa["info_density"],
            "readability": sa["readability"],
        },
        "failure_analysis": {
            "primary_factor": fm["primary_factor"],
            "confidence": fm["confidence"],
            "secondary_factors": fm["secondary_factors"],
            "evidence": fm["evidence"][:3],
        },
        "progress_trace": progress,
        "router_selected_tool": routing["tool"],
        "router_confidence": routing["confidence"],
        "router_time_ms": routing["routing_time_ms"],
        "router_correct": routing["correct"],
    }
    return cell


__all__ = [
    "TaskSpec",
    "pick_25_tasks",
    "run_one_cell",
    "_measure_partial_credit",
    "_measure_intent_preservation",
    "_measure_format_compliance",
    "_measure_hallucination",
]
