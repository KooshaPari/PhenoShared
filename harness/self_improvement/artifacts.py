"""Turn completed local benchmark artifacts into garden observations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _number(value: Any) -> float | None:
    return (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else None
    )


def observation_from_artifact(
    payload: dict[str, Any], *, artifact: Path, git_sha: str
) -> dict[str, Any]:
    """Build a ledger row; incomplete or failed artifacts remain non-scoreable."""
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    runtime = (
        payload.get("runtime_validation")
        if isinstance(payload.get("runtime_validation"), dict)
        else {}
    )
    status = str(payload.get("status", payload.get("suite_status", "unknown")))
    decision = (
        payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    )
    if status == "unknown" and decision:
        status = str(decision.get("status", "unknown"))
    if status == "unknown" and result:
        errors = result.get("error_count")
        requests = result.get("request_count")
        status = (
            "pass"
            if errors == 0 and isinstance(requests, (int, float)) and requests > 0
            else "failed"
        )
    if status == "unknown" and runtime:
        status = (
            "pass"
            if runtime.get("status") in {"pass", "passed"}
            else str(runtime.get("status", "unknown"))
        )
    levels = payload.get("levels") if isinstance(payload.get("levels"), list) else []
    variants = (
        payload.get("variants") if isinstance(payload.get("variants"), list) else []
    )
    if status == "unknown" and levels:
        status = (
            "pass"
            if all(
                isinstance(level, dict) and level.get("error_count", 0) == 0
                for level in levels
            )
            else "failed"
        )
    if status == "unknown" and variants:
        # Bakeoffs are useful diagnostic evidence, but cannot become promotion
        # signals until the artifact also carries semantic-quality gates.
        status = "diagnostic_only"
    metrics: dict[str, Any] = {}
    source = payload.get("metrics", result or runtime or payload)
    if not payload.get("metrics") and levels:
        source = {
            "aggregate_tokens_per_s": max(
                (level.get("aggregate_tokens_per_s", 0) for level in levels), default=0
            ),
            "latency_ms_p95": max(
                (level.get("latency_ms_p95", 0) for level in levels), default=0
            ),
            "request_count": sum(level.get("request_count", 0) for level in levels),
            "success_count": sum(level.get("success_count", 0) for level in levels),
        }
    for source_key, metric_key in (
        ("aggregate_tokens_per_s", "aggregate_tokens_per_s"),
        ("generation_tok_s", "generation_tok_s"),
        ("p95_ttft_ms", "p95_ttft_ms"),
        ("p95_latency_ms", "p95_latency_ms"),
        ("latency_ms_p95", "p95_latency_ms"),
        ("successes", "successes"),
        ("success_count", "successes"),
        ("total_requests", "total_requests"),
        ("request_count", "total_requests"),
        ("trial_count", "trial_count"),
        ("reward", "reward"),
        ("error_count", "error_count"),
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("episodes", "episodes"),
        ("completed", "completed"),
        ("total", "total"),
    ):
        value = _number(source.get(source_key)) if isinstance(source, dict) else None
        if value is not None:
            metrics[metric_key] = value
    if variants:
        generation_rates = [
            float(item["generation_tok_s"])
            for item in variants
            if isinstance(item, dict)
            and _number(item.get("generation_tok_s")) is not None
        ]
        if generation_rates:
            metrics["variant_count"] = float(len(generation_rates))
            metrics["max_generation_tok_s"] = max(generation_rates)
            metrics["min_generation_tok_s"] = min(generation_rates)
    medians = payload.get("medians") if isinstance(payload.get("medians"), dict) else {}
    if medians:
        baseline_raw = medians.get("baseline")
        baseline = baseline_raw if isinstance(baseline_raw, dict) else {}
        candidate_raw = medians.get("ngram-simple")
        candidate = candidate_raw if isinstance(candidate_raw, dict) else {}
        baseline_rate = _number(baseline.get("median_tok_s"))
        candidate_rate = _number(candidate.get("median_tok_s"))
        if baseline_rate is not None:
            metrics["baseline_median_tok_s"] = baseline_rate
        if candidate_rate is not None:
            metrics["candidate_median_tok_s"] = candidate_rate
        if baseline_rate and candidate_rate is not None:
            metrics["candidate_speedup"] = candidate_rate / baseline_rate
    if metrics.get("total_requests") and "success_rate" not in metrics:
        successes = metrics.get("successes")
        if successes is not None:
            metrics["success_rate"] = successes / metrics["total_requests"]
    notes = payload.get("measurement_notes", [])
    contaminated = any("contended" in str(note).lower() for note in notes) or any(
        marker in artifact.name.lower() for marker in ("shared", "contended")
    )
    scoreable = (
        status in {"pass", "passed", "complete", "completed"}
        and bool(metrics)
        and not contaminated
    )
    return {
        "run_id": str(payload.get("run_id") or artifact.stem),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_sha": git_sha,
        "component": "local-eval",
        "candidate_type": "observation",
        "lane": str(payload.get("lane", "serving")),
        "model_id": str(
            payload.get(
                "model_alias", payload.get("model_id", payload.get("model", "unknown"))
            )
        ),
        "provider_or_engine": str(
            payload.get("engine", payload.get("provider_or_engine", "local"))
        ),
        "eval_suite": str(
            payload.get(
                "suite",
                payload.get(
                    "suite_name", payload.get("schema_version", "local-performance")
                ),
            )
        ),
        "result": "scoreable" if scoreable else "non_scoreable",
        "scoreable": scoreable,
        "artifact": str(artifact),
        "artifact_status": status,
        "contended": contaminated,
        "metrics": metrics,
        "gate_decisions": {
            "artifact_integrity": {
                "required": True,
                "status": "green" if scoreable else "red",
            }
        },
        "rollback_ref": "none",
    }


__all__ = ["observation_from_artifact"]
