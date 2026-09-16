"""Deterministic trial aggregation for ``pheno.eval.aggregate.v2``.

This module is the public entry point.  It composes three submodules:

* :mod:`.aggregate_bootstrap` — bootstrap confidence-interval machinery and
  the deterministic ``quantile_type7`` implementation.
* :mod:`.aggregate_quality` — per-trial quality, latency, tools, cache, drift,
  and runtime-stability summaries, plus the trial-arm validation primitives.
* :mod:`.aggregate_blocks` — run-provenance validation, efficiency calculation,
  record validators, and the operational gates (tools/cache/long-turn/
  concurrency/thermal).

The module deliberately consumes validated trial records and separate run
provenance.  In particular, it never adds per-trial copies of a shared
server's makespan, memory peak, or cost.  Quality uncertainty is estimated by
resampling *tasks* while retaining every attempt for a sampled task.

The implementation is dependency-free and suitable for offline fixture tests.
It does not run an evaluator, model, server, or benchmark.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .aggregate_blocks import (
    DEFAULT_GATE_POLICY,
    MEMORY_SCOPE,
    RUN_PROVENANCE_SCHEMA_VERSION,
    TRUE_DECODE_FORMULA,
    TRUE_DECODE_TIMESTAMP_SOURCE,
    _close,
    _efficiency,
    _operational_gates,
    _rate_or_none,
    _reject_unknown,
    _validate_ci,
    _validate_drift_summary,
    _validate_latency_summary,
    _validate_run_provenance,
    _validate_runtime_stability_summary,
    _validate_tool_summary,
    validate_performance_block_record,
)
from .aggregate_bootstrap import (
    BOOTSTRAP_METHOD,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    QUANTILE_METHOD,
    quantile_type7,
)
from .aggregate_quality import (
    _RUNTIME_STABILITY_FIELDS,
    _counts,
    _integer,
    _mapping,
    _number,
    _paired_comparison,
    _quality,
    _sha256,
    _summarize_cache,
    _summarize_drift,
    _summarize_latency,
    _summarize_runtime_stability,
    _summarize_tools,
    _text,
    _validate_arm,
    performance_task_ids_sha256,
)
from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .trial_contracts import (
    TRIAL_SCHEMA_VERSION,
    trial_scoreability_reasons,
    trial_sha256,
    validate_trial_record,
)

# Re-export trial-helper symbols so that ``aggregate_quality._validate_arm``
# can late-bind them via ``aggregate_contracts.validate_trial_record`` etc.
# ``mock.patch.multiple`` on the ``aggregate_contracts`` module relies on
# these names being present as module-level attributes.
__all__ = [
    "AGGREGATE_SCHEMA_VERSION",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "MEMORY_SCOPE",
    "RUN_PROVENANCE_SCHEMA_VERSION",
    "TRIAL_SCHEMA_VERSION",
    "TRUE_DECODE_FORMULA",
    "aggregate_sha256",
    "aggregate_trials",
    "trial_scoreability_reasons",
    "trial_sha256",
    "validate_aggregate_against_inputs",
    "validate_aggregate_record",
    "validate_trial_record",
]

AGGREGATE_SCHEMA_VERSION = "pheno.eval.aggregate.v2"


def aggregate_trials(
    trials: Sequence[Mapping[str, Any]],
    *,
    expected_task_ids: Sequence[str],
    attempts_per_task: int,
    run_provenance: Mapping[str, Any] | None,
    baseline_trials: Sequence[Mapping[str, Any]] | None = None,
    baseline_run_provenance: Mapping[str, Any] | None = None,
    performance_block_summary: Mapping[str, Any] | None = None,
    gate_policy: Mapping[str, float] | None = None,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Build one canonical aggregate and optional paired baseline comparison."""

    if not isinstance(expected_task_ids, Sequence) or isinstance(
        expected_task_ids, (str, bytes)
    ):
        raise ContractError("expected_task_ids must be an array")
    task_ids = [_text(task_id, "expected_task_ids[]") for task_id in expected_task_ids]
    if not task_ids or len(task_ids) != len(set(task_ids)):
        raise ContractError("expected_task_ids must be non-empty and unique")
    attempts = _integer(attempts_per_task, "attempts_per_task", minimum=1)
    resamples = _integer(bootstrap_resamples, "bootstrap_resamples", minimum=1)
    if resamples != DEFAULT_BOOTSTRAP_RESAMPLES:
        raise ContractError(
            f"pheno.eval.aggregate.v2 requires exactly {DEFAULT_BOOTSTRAP_RESAMPLES} "
            "bootstrap resamples"
        )
    policy = dict(DEFAULT_GATE_POLICY)
    if gate_policy:
        unknown = sorted(set(gate_policy) - set(policy))
        if unknown:
            raise ContractError(f"gate policy has unknown fields: {unknown}")
        for key, value in gate_policy.items():
            policy[key] = _number(value, f"gate_policy.{key}")
    policy_sha = sha256_hex(canonical_json_bytes(policy))

    treatment = _validate_arm(
        trials,
        expected_task_ids=task_ids,
        attempts_per_task=attempts,
        arm="treatment",
    )
    treatment_counts = _counts(treatment["trials"])
    treatment_quality = _quality(
        treatment["trials"],
        expected_task_ids=task_ids,
        attempts_per_task=attempts,
        hashes=treatment["hashes"],
        resamples=resamples,
    )
    treatment_run = _validate_run_provenance(
        run_provenance,
        expected_run_id=treatment["run_id"],
        trials=treatment["trials"],
        policy=policy,
    )
    latency = _summarize_latency(treatment["trials"])
    tools = _summarize_tools(treatment["trials"])
    cache = _summarize_cache(treatment["trials"])
    drift = _summarize_drift(treatment["trials"], task_ids)
    runtime_stability = _summarize_runtime_stability(treatment["trials"])
    efficiency = _efficiency(treatment["trials"], treatment_run)

    gates: dict[str, Any] = {}
    expected_keys = {
        (task_id, ordinal) for task_id in task_ids for ordinal in range(attempts)
    }
    sample_reasons = []
    if treatment["keys"] != expected_keys:
        sample_reasons.append(
            "scheduled task/attempt matrix is incomplete or unexpected"
        )
    if len(task_ids) < 2:
        sample_reasons.append("at least two task clusters are required for inference")
    if any(
        treatment_quality["scored_attempts_by_task"].get(task_id, 0) == 0
        for task_id in task_ids
    ):
        sample_reasons.append("one or more tasks has no scored attempt")
    gates["sample_adequacy"] = {
        "gate_id": "sample_adequacy",
        "status": "fail" if sample_reasons else "pass",
        "reasons": sample_reasons,
    }
    integrity_reasons = [
        f"{digest}: {'; '.join(reasons)}"
        for digest, reasons in treatment["scoreability_reasons"].items()
    ]
    gates["trial_integrity"] = {
        "gate_id": "trial_integrity",
        "status": "fail" if integrity_reasons else "pass",
        "reasons": integrity_reasons,
    }
    exclusion_reasons = []
    if (
        treatment_counts["infrastructure_exclusion_rate"]
        > policy["infrastructure_exclusion_rate_max"]
    ):
        exclusion_reasons.append("infrastructure exclusion rate exceeds 2%")
    gates["infrastructure_health"] = {
        "gate_id": "infrastructure_health",
        "status": "fail" if exclusion_reasons else "pass",
        "reasons": exclusion_reasons,
    }
    run_reasons = list(treatment_run["reasons"])
    gates["run_provenance"] = {
        "gate_id": "run_provenance",
        "status": "fail" if run_reasons else "pass",
        "reasons": run_reasons,
    }
    gates["cost_completeness"] = {
        "gate_id": "cost_completeness",
        "status": "pass" if treatment_run["cost"]["complete"] else "not_evaluable",
        "reasons": list(treatment_run["cost"].get("reasons", [])),
        "required_for_core_promotion": False,
    }
    stability_reasons = []
    if runtime_stability["status"] != "complete":
        stability_reasons.append("runtime-stability counter coverage is incomplete")
    for field in _RUNTIME_STABILITY_FIELDS:
        if runtime_stability[field]:
            stability_reasons.append(f"one or more {field.replace('_', ' ')} occurred")
    gates["runtime_stability"] = {
        "gate_id": "runtime_stability",
        "status": "fail" if stability_reasons else "pass",
        "reasons": stability_reasons,
    }
    operational, concurrency, thermal = _operational_gates(
        tools=tools,
        cache=cache,
        drift=drift,
        run=treatment_run,
        policy=policy,
    )
    gates.update(operational)

    comparison: dict[str, Any] | None = None
    baseline_block: dict[str, Any] | None = None
    if baseline_trials is not None:
        baseline = _validate_arm(
            baseline_trials,
            expected_task_ids=task_ids,
            attempts_per_task=attempts,
            arm="baseline",
        )
        if baseline["suite_lock_sha256"] != treatment["suite_lock_sha256"]:
            raise ContractError("treatment and baseline use different suite locks")
        baseline_counts = _counts(baseline["trials"])
        if baseline["keys"] != expected_keys:
            gates["sample_adequacy"]["status"] = "fail"
            gates["sample_adequacy"]["reasons"].append(
                "baseline scheduled task/attempt matrix is incomplete or unexpected"
            )
        baseline_integrity_reasons = [
            f"baseline {digest}: {'; '.join(reasons)}"
            for digest, reasons in baseline["scoreability_reasons"].items()
        ]
        if baseline_integrity_reasons:
            gates["trial_integrity"]["status"] = "fail"
            gates["trial_integrity"]["reasons"].extend(baseline_integrity_reasons)
        if (
            baseline_counts["infrastructure_exclusion_rate"]
            > policy["infrastructure_exclusion_rate_max"]
        ):
            gates["infrastructure_health"]["status"] = "fail"
            gates["infrastructure_health"]["reasons"].append(
                "baseline infrastructure exclusion rate exceeds 2%"
            )
        baseline_quality = _quality(
            baseline["trials"],
            expected_task_ids=task_ids,
            attempts_per_task=attempts,
            hashes=baseline["hashes"],
            resamples=resamples,
        )
        baseline_run = _validate_run_provenance(
            baseline_run_provenance,
            expected_run_id=baseline["run_id"],
            trials=baseline["trials"],
            policy=policy,
        )
        paired = _paired_comparison(
            treatment["trials"],
            baseline["trials"],
            expected_task_ids=task_ids,
            treatment_hashes=treatment["hashes"],
            baseline_hashes=baseline["hashes"],
            resamples=resamples,
        )
        rate_difference = abs(
            treatment_counts["infrastructure_exclusion_rate"]
            - baseline_counts["infrastructure_exclusion_rate"]
        )
        paired["infrastructure_exclusion_rate_difference"] = rate_difference
        baseline_efficiency = _efficiency(baseline["trials"], baseline_run)
        avs_speedup = None
        if (
            baseline_efficiency["avs_per_second"] not in (None, 0)
            and efficiency["avs_per_second"] is not None
        ):
            avs_speedup = (
                efficiency["avs_per_second"] / baseline_efficiency["avs_per_second"]
            )
        comparison = {
            **paired,
            "baseline_cell_id": baseline["cell_id"],
            "baseline_counts": baseline_counts,
            "baseline_quality": baseline_quality,
            "baseline_efficiency": baseline_efficiency,
            "avs_goodput_speedup_point": avs_speedup,
            "avs_goodput_speedup_ci95": None,
            "performance_inference_reason": (
                "true run-makespan AVS needs paired independent schedule/run blocks; "
                "task resampling cannot create run-level replication"
            ),
        }
        validated_performance: dict[str, Any] | None = None
        if performance_block_summary is not None:
            validated_performance = validate_performance_block_record(
                performance_block_summary
            )
            if (
                validated_performance["suite_lock_sha256"]
                != treatment["suite_lock_sha256"]
            ):
                raise ContractError(
                    "performance-block suite lock does not match the aggregate"
                )
            if validated_performance["task_ids_sha256"] != performance_task_ids_sha256(
                task_ids
            ):
                raise ContractError(
                    "performance-block task identity does not match the aggregate"
                )
            if validated_performance["treatment_cell_id"] != treatment["cell_id"]:
                raise ContractError(
                    "performance-block treatment cell does not match the aggregate"
                )
            if validated_performance["baseline_cell_id"] != baseline["cell_id"]:
                raise ContractError(
                    "performance-block baseline cell does not match the aggregate"
                )
            for arm_name, run in (
                ("treatment", treatment_run),
                ("baseline", baseline_run),
            ):
                thermal = run.get("thermal")  # type: ignore[assignment]
                load_hash = (
                    thermal.get("load_profile_sha256")
                    if isinstance(thermal, Mapping)
                    else None
                )
                if load_hash != validated_performance["load_profile_sha256"]:
                    raise ContractError(
                        f"performance-block load profile does not match the {arm_name} run"
                    )
            comparison["performance_block"] = validated_performance
        baseline_block = {
            "cell_id": baseline["cell_id"],
            "trial_sha256": baseline["hashes"],
            "run_provenance_sha256": baseline_run["sha256"],
        }
        pairing_reasons = []
        if (
            paired["missing_treatment_pair_keys"]
            or paired["missing_baseline_pair_keys"]
        ):
            pairing_reasons.append("treatment and baseline scheduled pair keys differ")
        if paired["paired_task_count"] != len(task_ids):
            pairing_reasons.append(
                "not every expected task has a scored paired attempt"
            )
        if rate_difference > policy["paired_exclusion_rate_difference_max"]:
            pairing_reasons.append(
                "paired-arm exclusion-rate difference exceeds one percentage point"
            )
        discordance = paired["discordant_exclusion_rate"]
        if (
            discordance is None
            or discordance > policy["paired_exclusion_discordance_rate_max"]
        ):
            pairing_reasons.append("paired exclusion discordance exceeds 2%")
        gates["paired_design"] = {
            "gate_id": "paired_design",
            "status": "fail" if pairing_reasons else "pass",
            "reasons": pairing_reasons,
        }
        quality_reasons = []
        lower = paired["pass_at_1_delta"]["ci95"]["lower"]
        if lower is None:
            quality_reasons.append(
                "paired task-cluster confidence bound is unavailable"
            )
        elif lower < policy["quality_delta_ci95_lower_min"]:
            quality_reasons.append("paired pass@1 lower 95% bound is below -2 points")
        gates["quality_noninferiority"] = {
            "gate_id": "quality_noninferiority",
            "status": "fail" if quality_reasons else "pass",
            "reasons": quality_reasons,
        }
        if validated_performance is None:
            gates["performance_promotion"] = {
                "gate_id": "performance_promotion",
                "status": "not_evaluable",
                "reasons": [comparison["performance_inference_reason"]],
            }
        else:
            promotion = validated_performance["promotion"]
            gates["performance_promotion"] = {
                "gate_id": "performance_promotion",
                "status": promotion["status"],
                "reasons": list(promotion["reasons"]),
            }
    else:
        if performance_block_summary is not None:
            raise ContractError(
                "performance-block evidence requires a paired baseline arm"
            )
        gates["paired_design"] = {
            "gate_id": "paired_design",
            "status": "not_evaluable",
            "reasons": ["no baseline arm supplied"],
        }
        gates["quality_noninferiority"] = {
            "gate_id": "quality_noninferiority",
            "status": "not_evaluable",
            "reasons": ["no baseline arm supplied"],
        }
        gates["performance_promotion"] = {
            "gate_id": "performance_promotion",
            "status": "not_evaluable",
            "reasons": ["no paired independent performance blocks supplied"],
        }

    required_core = {
        "sample_adequacy",
        "trial_integrity",
        "infrastructure_health",
        "run_provenance",
        "tools",
        "cache",
        "long_turn_drift",
        "concurrency",
        "paired_design",
        "quality_noninferiority",
        "performance_promotion",
        "thermal_soak",
        "runtime_stability",
    }
    core_eligible = all(gates[gate_id]["status"] == "pass" for gate_id in required_core)
    result = {
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "suite_lock_sha256": treatment["suite_lock_sha256"],
        "cell_id": treatment["cell_id"],
        "gate_policy": policy,
        "gate_policy_sha256": policy_sha,
        "aggregation": {
            "attempts_per_task": attempts,
            "pass_at_4_budget": 4,  # nosec B105
            "bootstrap_resamples": resamples,
            "bootstrap_method": BOOTSTRAP_METHOD,
            "quantile_method": QUANTILE_METHOD,
            "expected_task_ids": sorted(task_ids),
        },
        "provenance": {
            "contributing_trial_sha256": treatment["hashes"],
            "run_provenance_sha256": treatment_run["sha256"],
            "baseline": baseline_block,
        },
        "counts": treatment_counts,
        "quality": treatment_quality,
        "latency": latency,
        "accepted_verified_steps": {
            "total_weight": efficiency["accepted_verified_step_weight"],
            "definition": "false-to-true, dependency-satisfied, terminally reverified milestones",
        },
        "efficiency": efficiency,
        "tools": tools,
        "cache": cache,
        "drift": drift,
        "runtime_stability": runtime_stability,
        "concurrency": concurrency,
        "thermal": thermal,
        "comparison": comparison,
        "gates": gates,
        "promotion": {
            "core_eligible": core_eligible,
            "dollar_frontier_eligible": core_eligible
            and gates["cost_completeness"]["status"] == "pass",
            "reason_codes": sorted(
                gate_id
                for gate_id, gate_value in gates.items()
                if gate_id in required_core and gate_value["status"] != "pass"
            ),
        },
    }
    return validate_aggregate_record(result)


def validate_aggregate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate persisted identities, counts, rates, and algebraic invariants.

    This validates the self-contained artifact.  Use
    :func:`validate_aggregate_against_inputs` when the contributing trials and
    run provenance are available; that stronger check recomputes every value.
    """

    from .redaction import contains_secret

    root = dict(_mapping(record, "aggregate"))
    root_fields = {
        "schema_version",
        "suite_lock_sha256",
        "cell_id",
        "gate_policy",
        "gate_policy_sha256",
        "aggregation",
        "provenance",
        "counts",
        "quality",
        "latency",
        "accepted_verified_steps",
        "efficiency",
        "tools",
        "cache",
        "drift",
        "runtime_stability",
        "concurrency",
        "thermal",
        "comparison",
        "gates",
        "promotion",
    }
    _reject_unknown(root, root_fields, "aggregate")
    if set(root) != root_fields:
        raise ContractError(
            f"aggregate is missing fields: {sorted(root_fields - set(root))}"
        )
    if root.get("schema_version") != AGGREGATE_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {AGGREGATE_SCHEMA_VERSION}")
    _sha256(root.get("suite_lock_sha256"), "suite_lock_sha256")
    _sha256(root.get("cell_id"), "cell_id")

    policy = _mapping(root.get("gate_policy"), "gate_policy")
    if set(policy) != set(DEFAULT_GATE_POLICY):
        raise ContractError("gate_policy must contain exactly the v2 policy keys")
    for key, value in policy.items():
        _number(value, f"gate_policy.{key}")
    policy_hash = _sha256(root.get("gate_policy_sha256"), "gate_policy_sha256")
    if policy_hash != sha256_hex(canonical_json_bytes(policy)):
        raise ContractError("gate_policy_sha256 does not match gate_policy")

    aggregation = _mapping(root.get("aggregation"), "aggregation")
    _reject_unknown(
        aggregation,
        {
            "attempts_per_task",
            "pass_at_4_budget",
            "bootstrap_resamples",
            "bootstrap_method",
            "quantile_method",
            "expected_task_ids",
        },
        "aggregation",
    )
    attempts_per_task = _integer(
        aggregation.get("attempts_per_task"), "aggregation.attempts_per_task", minimum=1
    )
    if aggregation.get("pass_at_4_budget") != 4:
        raise ContractError("aggregation.pass_at_4_budget must be 4")
    if (
        _integer(
            aggregation.get("bootstrap_resamples"),
            "aggregation.bootstrap_resamples",
            minimum=1,
        )
        != DEFAULT_BOOTSTRAP_RESAMPLES
    ):
        raise ContractError("aggregate must use exactly 10,000 bootstrap resamples")
    if aggregation.get("bootstrap_method") != BOOTSTRAP_METHOD:
        raise ContractError("aggregate bootstrap method is not recognized")
    if aggregation.get("quantile_method") != QUANTILE_METHOD:
        raise ContractError("aggregate quantile method is not recognized")
    task_ids = aggregation.get("expected_task_ids")
    if (
        not isinstance(task_ids, list)
        or not task_ids
        or task_ids != sorted(set(task_ids))
    ):
        raise ContractError("aggregate expected task IDs must be sorted and unique")
    for index, task_id in enumerate(task_ids):
        _text(task_id, f"aggregation.expected_task_ids[{index}]")

    provenance = _mapping(root.get("provenance"), "provenance")
    _reject_unknown(
        provenance,
        {"contributing_trial_sha256", "run_provenance_sha256", "baseline"},
        "provenance",
    )
    hashes = provenance.get("contributing_trial_sha256")
    if not isinstance(hashes, list) or not hashes or hashes != sorted(set(hashes)):
        raise ContractError("contributing trial hashes must be sorted and unique")
    for index, digest in enumerate(hashes):
        _sha256(digest, f"provenance.contributing_trial_sha256[{index}]")
    if provenance.get("run_provenance_sha256") is not None:
        _sha256(provenance["run_provenance_sha256"], "provenance.run_provenance_sha256")
    baseline_provenance = provenance.get("baseline")
    if baseline_provenance is not None:
        baseline = _mapping(baseline_provenance, "provenance.baseline")
        _reject_unknown(
            baseline,
            {"cell_id", "trial_sha256", "run_provenance_sha256"},
            "provenance.baseline",
        )
        _sha256(baseline.get("cell_id"), "provenance.baseline.cell_id")
        baseline_hashes = baseline.get("trial_sha256")
        if (
            not isinstance(baseline_hashes, list)
            or not baseline_hashes
            or baseline_hashes != sorted(set(baseline_hashes))
        ):
            raise ContractError("baseline trial hashes must be sorted and unique")
        for index, digest in enumerate(baseline_hashes):
            _sha256(digest, f"provenance.baseline.trial_sha256[{index}]")
        if baseline.get("run_provenance_sha256") is not None:
            _sha256(
                baseline["run_provenance_sha256"],
                "provenance.baseline.run_provenance_sha256",
            )

    counts = _mapping(root.get("counts"), "counts")
    _reject_unknown(
        counts,
        {
            "attempted",
            "scored",
            "passed",
            "failed",
            "excluded",
            "excluded_by_reason",
            "infrastructure_exclusion_rate",
        },
        "counts",
    )
    attempted = _integer(counts.get("attempted"), "counts.attempted", minimum=1)
    scored = _integer(counts.get("scored"), "counts.scored")
    passed = _integer(counts.get("passed"), "counts.passed")
    failed = _integer(counts.get("failed"), "counts.failed")
    excluded = _integer(counts.get("excluded"), "counts.excluded")
    if (
        scored + excluded != attempted
        or passed + failed != scored
        or attempted != len(hashes)
    ):
        raise ContractError("aggregate attempt counts do not reconcile")
    excluded_by_reason = _mapping(
        counts.get("excluded_by_reason"), "counts.excluded_by_reason"
    )
    if (
        sum(
            _integer(value, f"counts.excluded_by_reason.{key}")
            for key, value in excluded_by_reason.items()
        )
        != excluded
    ):
        raise ContractError("excluded reason counts do not reconcile")
    exclusion_rate = _rate_or_none(
        counts.get("infrastructure_exclusion_rate"),
        "counts.infrastructure_exclusion_rate",
    )
    _close(exclusion_rate, excluded / attempted, "counts.infrastructure_exclusion_rate")
    _validate_latency_summary(root.get("latency"), scoreable_count=scored)
    _validate_tool_summary(root.get("tools"), scoreable_count=scored)
    runtime_stability = _validate_runtime_stability_summary(
        root.get("runtime_stability"),
        attempted_count=attempted,
    )
    _validate_drift_summary(root.get("drift"), expected_task_count=len(task_ids))

    quality = _mapping(root.get("quality"), "quality")
    _reject_unknown(
        quality,
        {
            "pass_at_1",
            "pass_at_4",
            "pass_all_k",
            "scored_attempts_by_task",
            "bootstrap_seed_sha256",
        },
        "quality",
    )
    _sha256(quality.get("bootstrap_seed_sha256"), "quality.bootstrap_seed_sha256")
    for metric_name in ("pass_at_1", "pass_at_4"):
        metric = _mapping(quality.get(metric_name), f"quality.{metric_name}")
        allowed = {"estimate", "eligible_task_count", "expected_task_count", "ci95"}
        if metric_name == "pass_at_4":
            allowed.add("definition")
        _reject_unknown(metric, allowed, f"quality.{metric_name}")
        estimate = _rate_or_none(
            metric.get("estimate"), f"quality.{metric_name}.estimate"
        )
        eligible = _integer(
            metric.get("eligible_task_count"),
            f"quality.{metric_name}.eligible_task_count",
        )
        if metric.get("expected_task_count") != len(task_ids) or eligible > len(
            task_ids
        ):
            raise ContractError(f"quality.{metric_name} task counts do not reconcile")
        if (eligible == 0) != (estimate is None):
            raise ContractError(
                f"quality.{metric_name} nullability contradicts its denominator"
            )
        _validate_ci(metric.get("ci95"), f"quality.{metric_name}.ci95")
    pass_all = _mapping(quality.get("pass_all_k"), "quality.pass_all_k")
    _reject_unknown(
        pass_all,
        {
            "k",
            "estimate",
            "eligible_complete_task_count",
            "expected_task_count",
            "complete_task_coverage",
            "conservative_lower_bound",
            "ci95",
        },
        "quality.pass_all_k",
    )
    if pass_all.get("k") != attempts_per_task:
        raise ContractError("quality.pass_all_k.k must equal attempts_per_task")
    complete_count = _integer(
        pass_all.get("eligible_complete_task_count"),
        "quality.pass_all_k.eligible_complete_task_count",
    )
    if pass_all.get("expected_task_count") != len(task_ids) or complete_count > len(
        task_ids
    ):
        raise ContractError("quality.pass_all_k task counts do not reconcile")
    _close(
        pass_all.get("complete_task_coverage"),
        complete_count / len(task_ids),
        "quality.pass_all_k.complete_task_coverage",
    )
    _rate_or_none(pass_all.get("estimate"), "quality.pass_all_k.estimate")
    conservative = _rate_or_none(
        pass_all.get("conservative_lower_bound"),
        "quality.pass_all_k.conservative_lower_bound",
    )
    estimate = pass_all.get("estimate")
    if (
        estimate is not None
        and conservative is not None
        and conservative > float(estimate) + 1e-12
    ):
        raise ContractError("pass_all_k conservative lower bound exceeds its estimate")
    _validate_ci(pass_all.get("ci95"), "quality.pass_all_k.ci95")
    scored_by_task = _mapping(
        quality.get("scored_attempts_by_task"), "quality.scored_attempts_by_task"
    )
    if set(scored_by_task) != set(task_ids):
        raise ContractError("quality scored-attempt task IDs do not match the suite")
    if (
        sum(
            _integer(value, f"quality.scored_attempts_by_task.{task_id}")
            for task_id, value in scored_by_task.items()
        )
        != scored
    ):
        raise ContractError("per-task scored attempts do not sum to counts.scored")

    accepted = _mapping(root.get("accepted_verified_steps"), "accepted_verified_steps")
    _reject_unknown(accepted, {"total_weight", "definition"}, "accepted_verified_steps")
    accepted_weight = _number(
        accepted.get("total_weight"),
        "accepted_verified_steps.total_weight",
        minimum=0.0,
    )
    _text(accepted.get("definition"), "accepted_verified_steps.definition")
    efficiency = _mapping(root.get("efficiency"), "efficiency")
    _reject_unknown(
        efficiency,
        {
            "accepted_verified_step_weight",
            "run_makespan_seconds",
            "peak_attributable_active_memory_bytes",
            "peak_attributable_active_memory_gb_si",
            "total_amortized_usd",
            "avs_per_second",
            "avs_per_second_per_gb",
            "avs_per_dollar",
            "combined_avs_per_second_gb_dollar",
            "provenance_complete",
            "provenance_reasons",
        },
        "efficiency",
    )
    _close(
        efficiency.get("accepted_verified_step_weight"),
        accepted_weight,
        "efficiency.accepted_verified_step_weight",
    )
    wall = efficiency.get("run_makespan_seconds")
    memory_bytes = efficiency.get("peak_attributable_active_memory_bytes")
    memory_gb = efficiency.get("peak_attributable_active_memory_gb_si")
    total_cost = efficiency.get("total_amortized_usd")
    avs_s = efficiency.get("avs_per_second")
    if wall is not None:
        wall_value = _number(wall, "efficiency.run_makespan_seconds", minimum=1e-15)
        bytes_value = _integer(
            memory_bytes, "efficiency.peak_attributable_active_memory_bytes", minimum=1
        )
        expected_gb = bytes_value / 1_000_000_000.0
        _close(
            memory_gb, expected_gb, "efficiency.peak_attributable_active_memory_gb_si"
        )
        expected_avs_s = accepted_weight / wall_value
        _close(avs_s, expected_avs_s, "efficiency.avs_per_second")
        _close(
            efficiency.get("avs_per_second_per_gb"),
            expected_avs_s / expected_gb,
            "efficiency.avs_per_second_per_gb",
        )
        if total_cost is not None:
            cost_value = _number(
                total_cost, "efficiency.total_amortized_usd", minimum=1e-15
            )
            _close(
                efficiency.get("avs_per_dollar"),
                accepted_weight / cost_value,
                "efficiency.avs_per_dollar",
            )
            _close(
                efficiency.get("combined_avs_per_second_gb_dollar"),
                accepted_weight / wall_value / expected_gb / cost_value,
                "efficiency.combined_avs_per_second_gb_dollar",
            )
        elif (
            efficiency.get("avs_per_dollar") is not None
            or efficiency.get("combined_avs_per_second_gb_dollar") is not None
        ):
            raise ContractError("dollar efficiency must be null without complete cost")
    else:
        for field in (
            "peak_attributable_active_memory_bytes",
            "peak_attributable_active_memory_gb_si",
            "total_amortized_usd",
            "avs_per_second",
            "avs_per_second_per_gb",
            "avs_per_dollar",
            "combined_avs_per_second_gb_dollar",
        ):
            if efficiency.get(field) is not None:
                raise ContractError(
                    f"efficiency.{field} must be null without run provenance"
                )
    provenance_complete = efficiency.get("provenance_complete")
    provenance_reasons = efficiency.get("provenance_reasons")
    if (
        not isinstance(provenance_complete, bool)
        or not isinstance(provenance_reasons, list)
        or not all(isinstance(reason, str) for reason in provenance_reasons)
    ):
        raise ContractError("efficiency provenance status is malformed")
    if provenance_complete != (wall is not None):
        raise ContractError(
            "efficiency provenance status contradicts run-derived fields"
        )
    if provenance_complete == bool(provenance_reasons):
        raise ContractError("efficiency provenance reasons contradict completeness")

    gates = _mapping(root.get("gates"), "gates")
    required_gate_ids = {
        "sample_adequacy",
        "trial_integrity",
        "infrastructure_health",
        "run_provenance",
        "cost_completeness",
        "tools",
        "cache",
        "long_turn_drift",
        "concurrency",
        "thermal_soak",
        "paired_design",
        "quality_noninferiority",
        "performance_promotion",
        "runtime_stability",
    }
    if set(gates) != required_gate_ids:
        raise ContractError(
            f"aggregate gates differ from v2: {sorted(set(gates) ^ required_gate_ids)}"
        )
    for gate_id, raw_gate in gates.items():
        gate = _mapping(raw_gate, f"gates.{gate_id}")
        allowed = {"gate_id", "status", "reasons"}
        if gate_id == "cost_completeness":
            allowed.add("required_for_core_promotion")
        _reject_unknown(gate, allowed, f"gates.{gate_id}")
        if gate.get("gate_id") != gate_id or gate.get("status") not in {"pass", "fail", "not_evaluable", "not_applicable"}:
            raise ContractError(f"gate {gate_id} has an invalid identity or status")
        reasons = gate.get("reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(item, str) for item in reasons
        ):
            raise ContractError(f"gate {gate_id}.reasons must be strings")
    expected_stability_reasons = []
    if runtime_stability["status"] != "complete":
        expected_stability_reasons.append(
            "runtime-stability counter coverage is incomplete"
        )
    for field in _RUNTIME_STABILITY_FIELDS:
        if runtime_stability[field]:
            expected_stability_reasons.append(
                f"one or more {field.replace('_', ' ')} occurred"
            )
    runtime_gate = gates["runtime_stability"]
    if runtime_gate["reasons"] != expected_stability_reasons or runtime_gate[
        "status"
    ] != ("fail" if expected_stability_reasons else "pass"):
        raise ContractError("runtime_stability gate contradicts runtime counters")

    promotion = _mapping(root.get("promotion"), "promotion")
    _reject_unknown(
        promotion,
        {"core_eligible", "dollar_frontier_eligible", "reason_codes"},
        "promotion",
    )
    if not isinstance(promotion.get("core_eligible"), bool) or not isinstance(
        promotion.get("dollar_frontier_eligible"), bool
    ):
        raise ContractError("promotion eligibility fields must be boolean")
    reasons = promotion.get("reason_codes")
    if not isinstance(reasons, list) or reasons != sorted(set(reasons)):
        raise ContractError("promotion.reason_codes must be sorted and unique")
    required_core = {
        "sample_adequacy",
        "trial_integrity",
        "infrastructure_health",
        "run_provenance",
        "tools",
        "cache",
        "long_turn_drift",
        "concurrency",
        "paired_design",
        "quality_noninferiority",
        "performance_promotion",
        "thermal_soak",
        "runtime_stability",
    }
    expected_reasons = sorted(
        gate_id for gate_id in required_core if gates[gate_id]["status"] != "pass"
    )
    expected_core = not expected_reasons
    if reasons != expected_reasons or promotion["core_eligible"] != expected_core:
        raise ContractError("promotion core eligibility does not match gate results")
    expected_dollar = expected_core and gates["cost_completeness"]["status"] == "pass"
    if promotion["dollar_frontier_eligible"] != expected_dollar:
        raise ContractError("dollar frontier eligibility does not match gates")

    # These nested summaries are validated by recomputation when inputs are
    # available.  They still must be mappings and finite JSON here.
    for field in ("cache", "concurrency", "thermal"):
        _mapping(root.get(field), field)
    comparison = root.get("comparison")
    if (baseline_provenance is None) != (comparison is None):
        raise ContractError("comparison and baseline provenance must appear together")
    comparison_mapping: Mapping[str, Any] | None = None
    if comparison is not None:
        comparison_mapping = _mapping(comparison, "comparison")
    persisted_performance = (
        comparison_mapping.get("performance_block")
        if comparison_mapping is not None
        else None
    )
    performance_gate = gates["performance_promotion"]
    if persisted_performance is None:
        if performance_gate["status"] != "not_evaluable":
            raise ContractError(
                "performance promotion cannot pass without performance-block evidence"
            )
    else:
        performance = validate_performance_block_record(
            _mapping(persisted_performance, "comparison.performance_block")
        )
        if performance["suite_lock_sha256"] != root["suite_lock_sha256"]:
            raise ContractError("performance-block suite lock does not match aggregate")
        if performance["task_ids_sha256"] != performance_task_ids_sha256(task_ids):
            raise ContractError(
                "performance-block task identity does not match aggregate"
            )
        if performance["treatment_cell_id"] != root["cell_id"]:
            raise ContractError(
                "performance-block treatment cell does not match aggregate"
            )
        if (
            baseline_provenance is None
            or performance["baseline_cell_id"] != baseline_provenance["cell_id"]
        ):
            raise ContractError(
                "performance-block baseline cell does not match aggregate"
            )
        expected_performance_gate = performance["promotion"]
        if (
            performance_gate["status"] != expected_performance_gate["status"]
            or performance_gate["reasons"] != expected_performance_gate["reasons"]
        ):
            raise ContractError(
                "performance promotion gate contradicts performance-block evidence"
            )
    if contains_secret(root):
        raise ContractError("aggregate contains a credential")
    canonical_json_bytes(root)  # reject NaN and non-JSON values
    return root


def validate_aggregate_against_inputs(
    record: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    *,
    expected_task_ids: Sequence[str],
    attempts_per_task: int,
    run_provenance: Mapping[str, Any] | None,
    baseline_trials: Sequence[Mapping[str, Any]] | None = None,
    baseline_run_provenance: Mapping[str, Any] | None = None,
    performance_block_summary: Mapping[str, Any] | None = None,
    gate_policy: Mapping[str, float] | None = None,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Recompute an aggregate and reject any persisted-value divergence."""

    validated = validate_aggregate_record(record)
    expected = aggregate_trials(
        trials,
        expected_task_ids=expected_task_ids,
        attempts_per_task=attempts_per_task,
        run_provenance=run_provenance,
        baseline_trials=baseline_trials,
        baseline_run_provenance=baseline_run_provenance,
        performance_block_summary=performance_block_summary,
        gate_policy=gate_policy,
        bootstrap_resamples=bootstrap_resamples,
    )
    if canonical_json_bytes(validated) != canonical_json_bytes(expected):
        raise ContractError(
            "aggregate does not match recomputation from contributing inputs"
        )
    return validated


def aggregate_sha256(record: Mapping[str, Any]) -> str:
    """Validate the aggregate record and return its canonical SHA-256 digest."""
    return sha256_hex(canonical_json_bytes(validate_aggregate_record(record)))


__all__ = [
    "AGGREGATE_SCHEMA_VERSION",
    "BOOTSTRAP_METHOD",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "DEFAULT_GATE_POLICY",
    "MEMORY_SCOPE",
    "QUANTILE_METHOD",
    "RUN_PROVENANCE_SCHEMA_VERSION",
    "TRIAL_SCHEMA_VERSION",
    "TRUE_DECODE_FORMULA",
    "TRUE_DECODE_TIMESTAMP_SOURCE",
    "aggregate_sha256",
    "aggregate_trials",
    "quantile_type7",
    "validate_aggregate_against_inputs",
    "validate_aggregate_record",
]
