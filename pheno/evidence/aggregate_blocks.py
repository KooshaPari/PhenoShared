"""Performance-block, run-provenance, and operational-gate machinery.

This module owns every artifact-validation and efficiency calculation that
turns a validated trial set into a single gateable aggregate.  The per-trial
quality and latency decisions live in :mod:`.aggregate_quality` and the
bootstrap confidence intervals in :mod:`.aggregate_bootstrap`; this module
composes them with the run-level provenance, fairness/thermal soak, and the
record validators that the persisted aggregate must satisfy.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .aggregate_quality import (
    _DRIFT_CHECKPOINT_TURNS,
    _RUNTIME_STABILITY_FIELDS,
    TRUE_DECODE_FORMULA,
    TRUE_DECODE_TIMESTAMP_SOURCE,
    _accepted_weight,
    _integer,
    _mapping,
    _number,
    _scoreable,
    _sha256,
    _text,
)
from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .performance_blocks import validate_performance_block_record
from .redaction import contains_secret

MEMORY_SCOPE = "time_aligned_peak_attributable_physical_bytes"
RUN_PROVENANCE_SCHEMA_VERSION = "pheno.eval.run-provenance.v1"

DEFAULT_GATE_POLICY: dict[str, float] = {
    "infrastructure_exclusion_rate_max": 0.02,
    "paired_exclusion_rate_difference_max": 0.01,
    "paired_exclusion_discordance_rate_max": 0.02,
    "quality_delta_ci95_lower_min": -0.02,
    "instrumentation_coverage_min": 0.95,
    "memory_coverage_min": 0.95,
    "schema_valid_rate_min": 0.995,
    "valid_but_wrong_rate_max": 0.01,
    "duplicate_or_loop_trial_rate_max": 0.01,
    "cache_reconciliation_error_max": 0.01,
    "concurrency_error_rate_max": 0.01,
    "jain_fairness_min": 0.95,
    "throughput_retention_30m_min": 0.90,
    "p95_latency_growth_30m_max": 0.15,
    "long_turn_retention_min": 0.95,
}

_GATE_STATUSES = frozenset({"pass", "fail", "not_evaluable", "not_applicable"})
_SHA256_ZERO = "0" * 64


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")


def _rate_or_none(value: Any, path: str) -> float | None:
    if value is None:
        return None
    return _number(value, path, minimum=0.0, maximum=1.0)


def _validate_ci(value: Any, path: str, *, rate: bool = True) -> None:
    from .aggregate_bootstrap import (
        BOOTSTRAP_METHOD,
        DEFAULT_BOOTSTRAP_RESAMPLES,
        QUANTILE_METHOD,
    )

    ci = _mapping(value, path)
    allowed = {
        "lower",
        "upper",
        "resamples",
        "task_clusters",
        "method",
        "quantile_method",
        "reason",
    }
    _reject_unknown(ci, allowed, path)
    lower = ci.get("lower")
    upper = ci.get("upper")
    if (lower is None) != (upper is None):
        raise ContractError(f"{path} bounds must both be null or both be numeric")
    if lower is not None:
        lower_value = _number(
            lower,
            f"{path}.lower",
            minimum=-1.0 if not rate else 0.0,
            maximum=1.0,
        )
        upper_value = _number(
            upper,
            f"{path}.upper",
            minimum=-1.0 if not rate else 0.0,
            maximum=1.0,
        )
        if lower_value > upper_value:
            raise ContractError(f"{path}.lower cannot exceed upper")
    if (
        _integer(ci.get("resamples"), f"{path}.resamples", minimum=1)
        != DEFAULT_BOOTSTRAP_RESAMPLES
    ):
        raise ContractError(f"{path} must use exactly 10,000 resamples")
    _integer(ci.get("task_clusters"), f"{path}.task_clusters")
    if (
        ci.get("method") != BOOTSTRAP_METHOD
        or ci.get("quantile_method") != QUANTILE_METHOD
    ):
        raise ContractError(f"{path} has an unrecognized bootstrap convention")
    if "reason" in ci:
        _text(ci["reason"], f"{path}.reason")


def _close(actual: Any, expected: float, path: str) -> None:
    value = _number(actual, path)
    if not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise ContractError(f"{path} does not reconcile with its source values")


def _validate_distribution(
    value: Any,
    path: str,
    *,
    expected_count: int,
    extra_fields: set[str] | None = None,
) -> Mapping[str, Any]:
    distribution = _mapping(value, path)
    fields = {"sample_count", "coverage_fraction", "p50", "p95", "p99"}
    fields.update(extra_fields or set())
    _reject_unknown(distribution, fields, path)
    if set(distribution) != fields:
        raise ContractError(
            f"{path} is missing fields: {sorted(fields - set(distribution))}"
        )
    count = _integer(distribution.get("sample_count"), f"{path}.sample_count")
    if count > expected_count:
        raise ContractError(f"{path}.sample_count exceeds the scoreable population")
    coverage = distribution.get("coverage_fraction")
    if expected_count:
        _close(coverage, count / expected_count, f"{path}.coverage_fraction")
    elif coverage is not None:
        raise ContractError(
            f"{path}.coverage_fraction must be null for an empty population"
        )
    quantiles = [distribution.get(name) for name in ("p50", "p95", "p99")]
    if count == 0:
        if any(item is not None for item in quantiles):
            raise ContractError(f"{path} quantiles must be null without samples")
    else:
        checked = [
            _number(item, f"{path}.{name}", minimum=0.0)
            for name, item in zip(("p50", "p95", "p99"), quantiles, strict=True)
        ]
        if checked != sorted(checked):
            raise ContractError(f"{path} quantiles must be monotonic")
    return distribution


def _validate_latency_summary(value: Any, *, scoreable_count: int) -> None:
    from .aggregate_bootstrap import QUANTILE_METHOD

    latency = _mapping(value, "latency")
    fields = {
        "population",
        "scoreable_trial_count",
        "quantile_method",
        "queue_ms",
        "ttft_ms",
        "task_wall_ms",
        "verifier_ms",
        "true_decode_tokens_per_second",
    }
    _reject_unknown(latency, fields, "latency")
    if set(latency) != fields:
        raise ContractError(
            f"latency is missing fields: {sorted(fields - set(latency))}"
        )
    if latency.get("population") != "scoreable_trials":
        raise ContractError("latency.population must be scoreable_trials")
    if latency.get("scoreable_trial_count") != scoreable_count:
        raise ContractError("latency scoreable population does not match counts.scored")
    if latency.get("quantile_method") != QUANTILE_METHOD:
        raise ContractError("latency quantile method is not recognized")
    for field in ("queue_ms", "ttft_ms", "task_wall_ms", "verifier_ms"):
        _validate_distribution(
            latency.get(field),
            f"latency.{field}",
            expected_count=scoreable_count,
        )
    decode = _validate_distribution(
        latency.get("true_decode_tokens_per_second"),
        "latency.true_decode_tokens_per_second",
        expected_count=scoreable_count,
        extra_fields={"formula", "timestamp_source"},
    )
    if decode.get("formula") != TRUE_DECODE_FORMULA:
        raise ContractError("true decode throughput formula is not recognized")
    if decode.get("timestamp_source") != TRUE_DECODE_TIMESTAMP_SOURCE:
        raise ContractError("true decode throughput must use token timestamps only")


def _validate_tool_summary(value: Any, *, scoreable_count: int) -> None:
    from .aggregate_quality import _TOOL_TOTAL_FIELDS

    tools = _mapping(value, "tools")
    required = {
        "coverage_fraction",
        "totals",
        "parse_rate",
        "schema_valid_rate",
        "valid_but_wrong_rate",
        "semantic_correct_count_complete",
        "semantic_correct_rate",
        "repair_attempt_trial_count",
        "repair_attempt_trial_rate",
        "fallback_trial_count",
        "fallback_trial_rate",
        "duplicate_or_loop_trial_count",
        "duplicate_or_loop_trial_rate",
        "status",
    }
    conditional_exact = {
        "exact_match_counts_complete",
        "exact_tool_match_rate",
        "exact_argument_match_rate",
    }
    _reject_unknown(tools, required | conditional_exact, "tools")
    totals = _mapping(tools.get("totals"), "tools.totals")
    if set(totals) != set(_TOOL_TOTAL_FIELDS):
        raise ContractError("tools.totals must contain exactly the v2 tool counters")
    counts = {
        field: _integer(totals.get(field), f"tools.totals.{field}")
        for field in _TOOL_TOTAL_FIELDS
    }
    emitted = counts["emitted_candidates"]
    parsed = counts["parsed_calls"]
    valid = counts["schema_valid_calls"]
    executed = counts["executed_calls"]
    semantic = counts["semantically_correct_calls"]
    labeled = counts["gold_labeled_calls"]
    if not emitted >= parsed >= valid >= executed:
        raise ContractError("aggregate tool lifecycle counts do not reconcile")
    if semantic > executed:
        raise ContractError("aggregate semantic-correct calls exceed executed calls")
    if counts["schema_valid_but_wrong"] > valid:
        raise ContractError("aggregate valid-but-wrong calls exceed schema-valid calls")
    if (
        counts["exact_tool_matches"] > labeled
        or counts["exact_argument_matches"] > labeled
    ):
        raise ContractError("aggregate exact-match calls exceed gold-labeled calls")

    expected_fields = required | (conditional_exact if labeled > 0 else set())
    if set(tools) != expected_fields:
        raise ContractError(
            "exact tool-match rates must appear if and only if gold-labeled calls exist"
        )
    coverage = tools.get("coverage_fraction")
    if scoreable_count:
        coverage_value = _rate_or_none(coverage, "tools.coverage_fraction")
        if coverage_value is None:
            raise ContractError(
                "tools.coverage_fraction is required for scoreable trials"
            )
        covered = coverage_value * scoreable_count
        if not math.isclose(covered, round(covered), rel_tol=1e-12, abs_tol=1e-12):
            raise ContractError(
                "tools.coverage_fraction does not represent whole trials"
            )
        expected_status = (
            "complete"
            if coverage_value == 1.0
            else "missing"
            if coverage_value == 0.0
            else "partial"
        )
    else:
        if coverage is not None:
            raise ContractError(
                "tools.coverage_fraction must be null without scoreable trials"
            )
        expected_status = "complete"
    if tools.get("status") != expected_status:
        raise ContractError("tools.status contradicts tool counter coverage")

    def rate(
        field: str, numerator: int, denominator: int, *, available: bool = True
    ) -> None:
        """Check a tool summary rate against the policy threshold."""
        value = tools.get(field)
        if denominator and available:
            _close(value, numerator / denominator, f"tools.{field}")
        elif value is not None:
            raise ContractError(
                f"tools.{field} must be null without a complete denominator"
            )

    rate("parse_rate", parsed, emitted)
    rate("schema_valid_rate", valid, parsed)
    rate("valid_but_wrong_rate", counts["schema_valid_but_wrong"], valid)
    semantic_complete = tools.get("semantic_correct_count_complete")
    if not isinstance(semantic_complete, bool):
        raise ContractError("tools.semantic_correct_count_complete must be boolean")
    rate(
        "semantic_correct_rate",
        semantic,
        executed,
        available=semantic_complete,
    )
    for prefix in ("repair_attempt", "fallback", "duplicate_or_loop"):
        count = _integer(
            tools.get(f"{prefix}_trial_count"),
            f"tools.{prefix}_trial_count",
        )
        if count > scoreable_count:
            raise ContractError(f"tools.{prefix}_trial_count exceeds scoreable trials")
        rate(f"{prefix}_trial_rate", count, scoreable_count)
    if labeled > 0:
        exact_complete = tools.get("exact_match_counts_complete")
        if not isinstance(exact_complete, bool):
            raise ContractError("tools.exact_match_counts_complete must be boolean")
        rate(
            "exact_tool_match_rate",
            counts["exact_tool_matches"],
            labeled,
            available=exact_complete,
        )
        rate(
            "exact_argument_match_rate",
            counts["exact_argument_matches"],
            labeled,
            available=exact_complete,
        )


def _validate_runtime_stability_summary(
    value: Any,
    *,
    attempted_count: int,
) -> Mapping[str, Any]:
    summary = _mapping(value, "runtime_stability")
    fields = {
        "attempted_trial_count",
        "covered_trial_count",
        "coverage_fraction",
        "ooms",
        "deadlocks",
        "unexplained_restarts",
        "status",
    }
    _reject_unknown(summary, fields, "runtime_stability")
    if set(summary) != fields:
        raise ContractError(
            f"runtime_stability is missing fields: {sorted(fields - set(summary))}"
        )
    if summary.get("attempted_trial_count") != attempted_count:
        raise ContractError("runtime stability attempted count does not reconcile")
    covered = _integer(
        summary.get("covered_trial_count"),
        "runtime_stability.covered_trial_count",
    )
    if covered > attempted_count:
        raise ContractError("runtime stability covered count exceeds attempted trials")
    _close(
        summary.get("coverage_fraction"),
        covered / attempted_count,
        "runtime_stability.coverage_fraction",
    )
    for field in _RUNTIME_STABILITY_FIELDS:
        _integer(summary.get(field), f"runtime_stability.{field}")
    expected_status = (
        "complete"
        if covered == attempted_count
        else "missing"
        if covered == 0
        else "partial"
    )
    if summary.get("status") != expected_status:
        raise ContractError("runtime_stability.status contradicts counter coverage")
    return summary


def _validate_drift_summary(value: Any, *, expected_task_count: int) -> None:
    drift = _mapping(value, "drift")
    fields = {
        "verifier_flip_rate",
        "decision_disagreement",
        "eligible_repeated_task_count",
        "expected_task_count",
        "assertion_manifest_sha256",
        "retention_by_turn",
        "long_turn_assertion_retention",
        "long_turn_assertions_retained",
        "long_turn_assertions_expected",
    }
    _reject_unknown(drift, fields, "drift")
    if set(drift) != fields:
        raise ContractError(f"drift is missing fields: {sorted(fields - set(drift))}")
    eligible = _integer(
        drift.get("eligible_repeated_task_count"),
        "drift.eligible_repeated_task_count",
    )
    if (
        eligible > expected_task_count
        or drift.get("expected_task_count") != expected_task_count
    ):
        raise ContractError("drift task counts do not reconcile")
    flip = _rate_or_none(drift.get("verifier_flip_rate"), "drift.verifier_flip_rate")
    disagreement = _rate_or_none(
        drift.get("decision_disagreement"),
        "drift.decision_disagreement",
    )
    if eligible == 0 and (flip is not None or disagreement is not None):
        raise ContractError("drift rates require repeated-task evidence")
    if eligible > 0 and (flip is None or disagreement is None):
        raise ContractError("drift rates are missing for repeated-task evidence")
    manifest = drift.get("assertion_manifest_sha256")
    if manifest is not None:
        _sha256(manifest, "drift.assertion_manifest_sha256")
    by_turn = _mapping(drift.get("retention_by_turn"), "drift.retention_by_turn")
    expected_turn_keys = {str(turn) for turn in _DRIFT_CHECKPOINT_TURNS}
    if set(by_turn) != expected_turn_keys:
        raise ContractError("drift retention_by_turn must contain turns 1/5/10/25/50")
    checkpoint_retained = 0
    checkpoint_expected = 0
    for turn in _DRIFT_CHECKPOINT_TURNS:
        path = f"drift.retention_by_turn.{turn}"
        checkpoint = _mapping(by_turn[str(turn)], path)
        fields = {"assertions_retained", "assertions_expected", "retention"}
        _reject_unknown(checkpoint, fields, path)
        if set(checkpoint) != fields:
            raise ContractError(
                f"{path} is missing fields: {sorted(fields - set(checkpoint))}"
            )
        turn_retained = _integer(
            checkpoint.get("assertions_retained"),
            f"{path}.assertions_retained",
        )
        turn_expected = _integer(
            checkpoint.get("assertions_expected"),
            f"{path}.assertions_expected",
        )
        if turn_retained > turn_expected:
            raise ContractError(
                f"{path} retained assertions exceed expected assertions"
            )
        turn_retention = _rate_or_none(
            checkpoint.get("retention"),
            f"{path}.retention",
        )
        if turn_expected:
            _close(
                turn_retention,
                turn_retained / turn_expected,
                f"{path}.retention",
            )
        elif turn_retention is not None:
            raise ContractError(f"{path}.retention must be null without assertions")
        checkpoint_retained += turn_retained
        checkpoint_expected += turn_expected
    retained = _integer(
        drift.get("long_turn_assertions_retained"),
        "drift.long_turn_assertions_retained",
    )
    expected = _integer(
        drift.get("long_turn_assertions_expected"),
        "drift.long_turn_assertions_expected",
    )
    if retained > expected:
        raise ContractError("retained long-turn assertions exceed expected assertions")
    if retained != checkpoint_retained or expected != checkpoint_expected:
        raise ContractError(
            "drift checkpoint totals do not reconcile with overall totals"
        )
    retention = _rate_or_none(
        drift.get("long_turn_assertion_retention"),
        "drift.long_turn_assertion_retention",
    )
    if expected:
        _close(
            retention,
            retained / expected,
            "drift.long_turn_assertion_retention",
        )
    elif retention is not None:
        raise ContractError("long-turn retention must be null without assertions")


def _validate_run_provenance(
    value: Mapping[str, Any] | None,
    *,
    expected_run_id: str,
    trials: Sequence[Mapping[str, Any]],
    policy: Mapping[str, float],
) -> dict[str, Any]:
    reasons: list[str] = []
    cost_reasons: list[str] = []
    if value is None:
        return {
            "complete": False,
            "reasons": ["run provenance is missing"],
            "sha256": None,
            "makespan_seconds": None,
            "peak_attributable_active_memory_bytes": None,
            "cost": {
                "complete": False,
                "total_amortized_usd": None,
                "reasons": ["run cost provenance is missing"],
            },
        }
    root = dict(_mapping(value, "run_provenance"))
    if contains_secret(root):
        raise ContractError("run provenance contains a credential")
    if root.get("schema_version") != RUN_PROVENANCE_SCHEMA_VERSION:
        raise ContractError(
            f"run_provenance.schema_version must be {RUN_PROVENANCE_SCHEMA_VERSION}"
        )
    run_id = _text(root.get("run_id"), "run_provenance.run_id")
    if run_id != expected_run_id:
        reasons.append("run provenance run_id does not match the trials")
    clock_id = _text(root.get("clock_id"), "run_provenance.clock_id")
    started = _integer(
        root.get("measurement_started_ns"), "run_provenance.measurement_started_ns"
    )
    completed = _integer(
        root.get("measurement_completed_ns"), "run_provenance.measurement_completed_ns"
    )
    if completed <= started:
        raise ContractError("run provenance measurement window must be positive")
    instrumentation = _number(
        root.get("instrumentation_coverage_fraction"),
        "run_provenance.instrumentation_coverage_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    memory_bytes = _integer(
        root.get("peak_attributable_active_memory_bytes"),
        "run_provenance.peak_attributable_active_memory_bytes",
        minimum=1,
    )
    memory_coverage = _number(
        root.get("memory_coverage_fraction"),
        "run_provenance.memory_coverage_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    memory_hash = root.get("memory_provenance_sha256")
    if memory_hash is None:
        reasons.append("memory provenance hash is missing")
    else:
        _sha256(memory_hash, "run_provenance.memory_provenance_sha256")
    if root.get("memory_scope") != MEMORY_SCOPE:
        reasons.append(f"memory_scope must be {MEMORY_SCOPE}")
    if root.get("unified_memory_counted_once") is not True:
        reasons.append("unified memory must be counted exactly once")

    for trial in trials:
        timing = _mapping(trial.get("timing"), "trial.timing")
        trial_clock = timing.get("clock_id")
        if trial_clock is not None and trial_clock != clock_id:
            reasons.append("trial and run provenance use different monotonic clocks")
            break
        enqueued = timing.get("enqueued_ns")
        finished = timing.get("verifier_completed_ns")
        if isinstance(enqueued, int) and enqueued < started:
            reasons.append("a trial begins before the run measurement window")
        if isinstance(finished, int) and finished > completed:
            reasons.append("a trial ends after the run measurement window")

    cost_value = root.get("cost")
    cost_complete = False
    cost_total: float | None = None
    cost_hash: str | None = None
    cost_components: dict[str, Any] = {}
    if isinstance(cost_value, Mapping):
        completeness = cost_value.get("completeness")
        cost_complete = completeness is True or completeness == "complete"
        total = cost_value.get("total_amortized_usd")
        if total is not None:
            cost_total = _number(
                total, "run_provenance.cost.total_amortized_usd", minimum=0.0
            )
        ledger = cost_value.get("ledger_sha256")
        if ledger is not None:
            cost_hash = _sha256(ledger, "run_provenance.cost.ledger_sha256")
        if cost_complete and cost_hash is None:
            cost_reasons.append("complete run cost lacks a ledger hash")
        if cost_complete and (cost_total is None or cost_total <= 0):
            cost_reasons.append("complete run cost must be positive for /$ metrics")
        if not cost_complete:
            cost_reasons.append("run cost ledger is incomplete")
        raw_components = cost_value.get("components")
        if not isinstance(raw_components, Mapping) or not raw_components:
            cost_reasons.append("run cost components are missing")
        else:
            component_sum = 0.0
            for component_name, raw_component in raw_components.items():
                component = _mapping(
                    raw_component,
                    f"run_provenance.cost.components.{component_name}",
                )
                status = component.get("status")
                if status not in {"complete", "not_applicable", "unknown"}:
                    raise ContractError(
                        f"run cost component {component_name} has an invalid status"
                    )
                amount = _number(
                    component.get("amount_usd", 0.0),
                    f"run_provenance.cost.components.{component_name}.amount_usd",
                    minimum=0.0,
                )
                if status == "not_applicable" and amount != 0.0:
                    raise ContractError(
                        f"not-applicable cost component {component_name} must be zero"
                    )
                if status == "unknown":
                    cost_reasons.append(
                        f"run cost component {component_name} is unknown"
                    )
                component_sum += amount
                cost_components[str(component_name)] = {
                    "status": status,
                    "amount_usd": amount,
                }
            if cost_total is not None and not math.isclose(
                component_sum, cost_total, rel_tol=1e-9, abs_tol=1e-9
            ):
                cost_reasons.append(
                    "run cost components do not sum to total_amortized_usd"
                )
    else:
        cost_reasons.append("run cost provenance is missing")

    if instrumentation < policy["instrumentation_coverage_min"]:
        reasons.append("instrumentation coverage is below 95%")
    if memory_coverage < policy["memory_coverage_min"]:
        reasons.append("memory coverage is below 95%")
    return {
        "complete": not reasons,
        "reasons": list(dict.fromkeys(reasons)),
        "sha256": sha256_hex(canonical_json_bytes(root)),
        "clock_id": clock_id,
        "makespan_seconds": (completed - started) / 1_000_000_000.0,
        "instrumentation_coverage_fraction": instrumentation,
        "peak_attributable_active_memory_bytes": memory_bytes,
        "memory_coverage_fraction": memory_coverage,
        "cost": {
            "complete": not cost_reasons,
            "total_amortized_usd": cost_total,
            "ledger_sha256": cost_hash,
            "reasons": list(dict.fromkeys(cost_reasons)),
            "components": cost_components,
        },
        "concurrency": root.get("concurrency"),
        "thermal": root.get("thermal"),
    }


def _efficiency(
    trials: Sequence[Mapping[str, Any]], run: Mapping[str, Any]
) -> dict[str, Any]:
    accepted = sum(_accepted_weight(trial) for trial in trials if _scoreable(trial))
    provenance_complete = bool(run.get("complete"))
    wall = run.get("makespan_seconds") if provenance_complete else None
    memory_bytes = (
        run.get("peak_attributable_active_memory_bytes")
        if provenance_complete
        else None
    )
    memory_gb = memory_bytes / 1_000_000_000.0 if memory_bytes else None
    cost = _mapping(run.get("cost", {}), "run.cost")
    total_cost = (
        cost.get("total_amortized_usd")
        if provenance_complete and cost.get("complete")
        else None
    )
    avs_s = accepted / wall if wall and wall > 0 else None
    return {
        "accepted_verified_step_weight": accepted,
        "run_makespan_seconds": wall,
        "peak_attributable_active_memory_bytes": memory_bytes,
        "peak_attributable_active_memory_gb_si": memory_gb,
        "total_amortized_usd": total_cost,
        "avs_per_second": avs_s,
        "avs_per_second_per_gb": (
            avs_s / memory_gb if avs_s is not None and memory_gb else None
        ),
        "avs_per_dollar": (
            accepted / total_cost if total_cost is not None and total_cost > 0 else None
        ),
        "combined_avs_per_second_gb_dollar": (
            accepted / wall / memory_gb / total_cost
            if wall and memory_gb and total_cost and total_cost > 0
            else None
        ),
        "provenance_complete": provenance_complete,
        "provenance_reasons": list(run.get("reasons", [])),
    }


def _jain(values: Sequence[float]) -> float | None:
    if not values:
        return None
    total = sum(values)
    denominator = len(values) * sum(value * value for value in values)
    if denominator == 0:
        return None
    return total * total / denominator


def _operational_gates(
    *,
    tools: Mapping[str, Any],
    cache: Mapping[str, Any],
    drift: Mapping[str, Any],
    run: Mapping[str, Any],
    policy: Mapping[str, float],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:

    gates: list[dict[str, Any]] = []

    def gate(gate_id: str, status: str, reasons: Iterable[str]) -> None:
        """Append a gate record to the running list (status must be in _GATE_STATUSES)."""
        if status not in _GATE_STATUSES:
            raise AssertionError(status)
        gates.append({"gate_id": gate_id, "status": status, "reasons": list(reasons)})

    tool_reasons: list[str] = []
    if tools.get("status") != "complete":
        tool_reasons.append("tool counter coverage is incomplete")
    if (
        tools.get("schema_valid_rate") is not None
        and tools["schema_valid_rate"] < policy["schema_valid_rate_min"]
    ):
        tool_reasons.append("schema-valid call rate is below 99.5%")
    if (
        tools.get("valid_but_wrong_rate") is not None
        and tools["valid_but_wrong_rate"] > policy["valid_but_wrong_rate_max"]
    ):
        tool_reasons.append("valid-but-wrong call rate exceeds 1%")
    if (
        tools.get("duplicate_or_loop_trial_rate") is not None
        and tools["duplicate_or_loop_trial_rate"]
        > policy["duplicate_or_loop_trial_rate_max"]
    ):
        tool_reasons.append("duplicate-or-loop trial rate exceeds 1%")
    totals = _mapping(tools.get("totals", {}), "tools.totals")
    for field in (
        "risky_action_bypasses",
        "unauthorized_attempts",
        "orphan_calls",
        "orphan_observations",
    ):
        if int(totals.get(field, 0)) != 0:
            tool_reasons.append(f"{field} must be zero")
    gate("tools", "fail" if tool_reasons else "pass", tool_reasons)

    cache_reasons: list[str] = []
    if cache.get("status") != "complete":
        cache_reasons.append("cache counter coverage is incomplete")
    if int(cache.get("cross_request_contamination_count", 0)) != 0:
        cache_reasons.append("cross-request cache contamination observed")
    reconciliation = cache.get("max_counter_reconciliation_error")
    if (
        reconciliation is not None
        and reconciliation > policy["cache_reconciliation_error_max"]
    ):
        cache_reasons.append("cache counter reconciliation error exceeds 1%")
    gate("cache", "fail" if cache_reasons else "pass", cache_reasons)

    long_turn = drift.get("long_turn_assertion_retention")
    if long_turn is None:
        gate(
            "long_turn_drift",
            "not_applicable",
            ["no long-turn assertion fixture in this cell"],
        )
    elif long_turn < policy["long_turn_retention_min"]:
        gate("long_turn_drift", "fail", ["long-turn assertion retention is below 95%"])
    else:
        gate("long_turn_drift", "pass", [])

    concurrency_summary: dict[str, Any] = {
        "jain_fairness": None,
        "error_rate": None,
        "starvation_count": None,
        "status": "not_applicable",
    }
    concurrency = run.get("concurrency")
    if isinstance(concurrency, Mapping):
        raw_goodputs = concurrency.get("stream_goodputs", [])
        provenance_digest = concurrency.get("provenance_sha256")
        homogeneous = concurrency.get("homogeneous_or_normalized_fixture") is True
        unit_ok = concurrency.get("goodput_unit") == "normalized_useful_work_per_second"
        if provenance_digest is not None:
            _sha256(provenance_digest, "run_provenance.concurrency.provenance_sha256")
        if not isinstance(raw_goodputs, list) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            for value in raw_goodputs
        ):
            gate("concurrency", "fail", ["stream goodputs are missing or invalid"])
            concurrency_summary["status"] = "incomplete"
        elif len(raw_goodputs) < 2:
            gate("concurrency", "not_applicable", ["concurrency is below two streams"])
        else:
            fairness = _jain([float(value) for value in raw_goodputs])
            error_rate = float(concurrency.get("error_rate", 1.0))
            starvation = int(concurrency.get("starvation_count", 0))
            reasons = []
            if provenance_digest is None:
                reasons.append("concurrency provenance hash is missing")
            if not homogeneous or not unit_ok:
                reasons.append("fairness fixture is neither homogeneous nor normalized")
            if fairness is None or fairness < policy["jain_fairness_min"]:
                reasons.append("Jain fairness is below 0.95")
            if error_rate > policy["concurrency_error_rate_max"]:
                reasons.append("concurrency error rate exceeds 1%")
            if starvation != 0:
                reasons.append("one or more streams starved")
            concurrency_summary.update(
                {
                    "jain_fairness": fairness,
                    "error_rate": error_rate,
                    "starvation_count": starvation,
                    "stream_count": len(raw_goodputs),
                    "goodput_unit": concurrency.get("goodput_unit"),
                    "provenance_sha256": provenance_digest,
                    "status": "complete",
                }
            )
            gate("concurrency", "fail" if reasons else "pass", reasons)
    else:
        gate(
            "concurrency", "not_applicable", ["no concurrent-load fixture in this cell"]
        )

    thermal_summary: dict[str, Any] = {"status": "missing"}
    thermal = run.get("thermal")
    if not isinstance(thermal, Mapping):
        gate(
            "thermal_soak", "not_evaluable", ["30-minute thermal provenance is missing"]
        )
    else:
        duration = _number(
            thermal.get("duration_seconds", 0.0),
            "run_provenance.thermal.duration_seconds",
            minimum=0.0,
        )
        coverage = _number(
            thermal.get("coverage_fraction", 0.0),
            "run_provenance.thermal.coverage_fraction",
            minimum=0.0,
            maximum=1.0,
        )
        baseline_goodput = thermal.get("baseline_goodput")
        terminal_goodput = thermal.get("terminal_goodput")
        baseline_p95 = thermal.get("baseline_p95_latency_ms")
        terminal_p95 = thermal.get("terminal_p95_latency_ms")
        retention = None
        growth = None
        if baseline_goodput is not None and terminal_goodput is not None:
            baseline_goodput = _number(
                baseline_goodput,
                "run_provenance.thermal.baseline_goodput",
                minimum=1e-15,
            )
            terminal_goodput = _number(
                terminal_goodput,
                "run_provenance.thermal.terminal_goodput",
                minimum=0.0,
            )
            retention = terminal_goodput / baseline_goodput
        if baseline_p95 is not None and terminal_p95 is not None:
            baseline_p95 = _number(
                baseline_p95,
                "run_provenance.thermal.baseline_p95_latency_ms",
                minimum=1e-15,
            )
            terminal_p95 = _number(
                terminal_p95,
                "run_provenance.thermal.terminal_p95_latency_ms",
                minimum=0.0,
            )
            growth = terminal_p95 / baseline_p95 - 1.0
        state = thermal.get("os_thermal_state_peak")
        policy_violation = bool(thermal.get("policy_violation", False))
        reasons = []
        telemetry_hash = thermal.get("telemetry_sha256")
        load_hash = thermal.get("load_profile_sha256")
        if telemetry_hash is None or load_hash is None:
            reasons.append("thermal telemetry or load-profile hash is missing")
        else:
            _sha256(telemetry_hash, "run_provenance.thermal.telemetry_sha256")
            _sha256(load_hash, "run_provenance.thermal.load_profile_sha256")
        expected_windows = {
            "baseline_window_start_s": 300,
            "baseline_window_end_s": 600,
            "terminal_window_start_s": 1500,
            "terminal_window_end_s": 1800,
        }
        for field, expected in expected_windows.items():
            if thermal.get(field) != expected:
                reasons.append(f"thermal {field} must be {expected}")
        if duration < 1800.0:
            reasons.append("thermal soak is shorter than 30 minutes")
        if coverage < policy["instrumentation_coverage_min"]:
            reasons.append("thermal instrumentation coverage is below 95%")
        if retention is None or retention < policy["throughput_retention_30m_min"]:
            reasons.append("30-minute throughput retention is below 90%")
        if growth is None or growth > policy["p95_latency_growth_30m_max"]:
            reasons.append("30-minute p95 latency growth exceeds 15%")
        if state in {"serious", "critical"}:
            reasons.append("phone reached a prohibited OS thermal state")
        if policy_violation:
            reasons.append("device thermal policy was violated")
        thermal_summary = dict(thermal)
        thermal_summary["throughput_retention_30m"] = retention
        thermal_summary["p95_latency_growth_fraction"] = growth
        thermal_summary["status"] = "complete"
        gate("thermal_soak", "fail" if reasons else "pass", reasons)

    return (
        {item["gate_id"]: item for item in gates},
        concurrency_summary,
        thermal_summary,
    )


__all__ = [
    "DEFAULT_GATE_POLICY",
    "MEMORY_SCOPE",
    "RUN_PROVENANCE_SCHEMA_VERSION",
    "TRUE_DECODE_FORMULA",
    "TRUE_DECODE_TIMESTAMP_SOURCE",
    "_efficiency",
    "_jain",
    "_operational_gates",
    "_validate_drift_summary",
    "_validate_latency_summary",
    "_validate_runtime_stability_summary",
    "_validate_run_provenance",
    "_validate_tool_summary",
    "validate_performance_block_record",
]
