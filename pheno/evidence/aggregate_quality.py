"""Quality, latency, tools, cache, drift, and stability decisions for the v2 aggregate.

This module owns every per-trial summarization that feeds ``aggregate_trials``.
The bootstrap confidence-interval machinery lives in :mod:`.aggregate_bootstrap`
and is imported here so the two modules share a single, deterministic source
of randomness.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .aggregate_bootstrap import (
    BOOTSTRAP_METHOD,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    QUANTILE_METHOD,
    _bootstrap_mean_ci,
    _seed_digest,
    quantile_type7,
)
from .contracts import ContractError
from .performance_blocks import (
    task_ids_sha256 as performance_task_ids_sha256,
)
from .trial_contracts import (
    TRIAL_SCHEMA_VERSION,
)

_INFRASTRUCTURE_STATE = "infrastructure_exclusion"
_SCORED_STATES = frozenset({"passed", "model_failure"})
_TOOL_TOTAL_FIELDS = (
    "emitted_candidates",
    "parsed_calls",
    "schema_valid_calls",
    "executed_calls",
    "semantically_correct_calls",
    "gold_labeled_calls",
    "exact_tool_matches",
    "exact_argument_matches",
    "schema_valid_but_wrong",
    "repair_attempts",
    "fallbacks",
    "duplicate_calls",
    "loop_events",
    "unauthorized_attempts",
    "risky_action_bypasses",
    "orphan_calls",
    "orphan_observations",
)
_RUNTIME_STABILITY_FIELDS = ("ooms", "deadlocks", "unexplained_restarts")
_DRIFT_CHECKPOINT_TURNS = (1, 5, 10, 25, 50)
_RUNTIME_STABILITY_ADMISSIBILITY_REASONS = frozenset(
    f"integrity.{field} is nonzero" for field in _RUNTIME_STABILITY_FIELDS
)
TRUE_DECODE_FORMULA = (
    "(completion_tokens - 1) / ((last_token_ns - first_token_ns) / 1e9)"
)
TRUE_DECODE_TIMESTAMP_SOURCE = (
    "monotonic_first_and_last_token_timestamps_only; sse_chunk_gaps_excluded"
)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractError(f"{path} must be an integer >= {minimum}")
    return value


def _number(
    value: Any,
    path: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ContractError(f"{path} must be a finite number")
    if minimum is not None and result < minimum:
        raise ContractError(f"{path} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ContractError(f"{path} must be <= {maximum}")
    return result


def _sha256(value: Any, path: str) -> str:
    text = _text(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ContractError(f"{path} must be a lowercase SHA-256 digest")
    return text


def _trial_state(trial: Mapping[str, Any]) -> str:
    return str(_mapping(trial["outcome"], "trial.outcome")["state"])


def _trial_task(trial: Mapping[str, Any]) -> str:
    return str(_mapping(trial["cell"], "trial.cell")["task_id"])


def _trial_ordinal(trial: Mapping[str, Any]) -> int:
    return int(_mapping(trial["cell"], "trial.cell")["attempt_ordinal"])


def _scoreable(trial: Mapping[str, Any]) -> bool:
    outcome = _mapping(trial["outcome"], "trial.outcome")
    return bool(outcome["scoreable"]) and str(outcome["state"]) in _SCORED_STATES


def _accepted_weight(trial: Mapping[str, Any]) -> float:
    """Recompute accepted milestone weight rather than trusting a total."""

    raw_steps = trial.get("accepted_steps", [])
    if not isinstance(raw_steps, list):
        raise ContractError("accepted_steps must be an array")
    ids: set[str] = set()
    accepted: dict[str, tuple[float, list[str]]] = {}
    for index, raw in enumerate(raw_steps):
        step = _mapping(raw, f"accepted_steps[{index}]")
        step_id = _text(
            step.get("step_id", step.get("milestone_id")),
            f"accepted_steps[{index}].step_id",
        )
        if step_id in ids:
            raise ContractError(
                f"accepted_steps contains duplicate step_id {step_id!r}"
            )
        ids.add(step_id)
        weight = _number(
            step.get("weight"), f"accepted_steps[{index}].weight", minimum=0.0
        )
        transitioned = step.get(
            "false_to_true_transition", step.get("transitioned_false_to_true")
        )
        reverified = step.get(
            "terminal_reverified", step.get("terminal_recheck_passed")
        )
        if not isinstance(transitioned, bool) or not isinstance(reverified, bool):
            raise ContractError(
                f"accepted_steps[{index}] needs boolean transition and terminal recheck"
            )
        raw_dependencies = step.get("depends_on", step.get("dependency_ids", []))
        if not isinstance(raw_dependencies, list) or not all(
            isinstance(item, str) and item for item in raw_dependencies
        ):
            raise ContractError(f"accepted_steps[{index}].depends_on must be strings")
        if transitioned and reverified:
            accepted[step_id] = (weight, list(raw_dependencies))

    # Resolve dependencies to a fixed point; cycles and missing prerequisites
    # never earn weight and are rejected instead of being silently ignored.
    pending = dict(accepted)
    resolved: set[str] = set()
    total = 0.0
    while pending:
        progress = False
        for step_id, (weight, dependencies) in list(pending.items()):
            if any(dependency not in accepted for dependency in dependencies):
                raise ContractError(
                    f"accepted step {step_id!r} has a missing accepted dependency"
                )
            if all(dependency in resolved for dependency in dependencies):
                total += weight
                resolved.add(step_id)
                del pending[step_id]
                progress = True
        if not progress:
            raise ContractError("accepted step dependency graph contains a cycle")

    declared = _number(trial.get("total_weight", 0.0), "total_weight", minimum=0.0)
    if not math.isclose(total, declared, rel_tol=1e-12, abs_tol=1e-12):
        raise ContractError(
            f"total_weight {declared} does not equal recomputed accepted weight {total}"
        )
    if _trial_state(trial) == _INFRASTRUCTURE_STATE and total != 0.0:
        raise ContractError(
            "infrastructure exclusions cannot contribute accepted weight"
        )
    return total


def _validate_arm(
    trials: Sequence[Mapping[str, Any]],
    *,
    expected_task_ids: Sequence[str],
    attempts_per_task: int,
    arm: str,
) -> dict[str, Any]:
    # Late-bind trial-helper symbols so tests that ``mock.patch.multiple`` the
    # ``aggregate_contracts`` module see the patched callables here as well.
    from . import aggregate_contracts as _aggregate_contracts

    if not trials:
        raise ContractError(f"{arm} trials must not be empty")
    expected = set(expected_task_ids)
    validated: list[dict[str, Any]] = []
    hashes: list[str] = []
    keys: set[tuple[str, int]] = set()
    pair_keys: set[str] = set()
    cell_ids: set[str] = set()
    suite_locks: set[str] = set()
    run_ids: set[str] = set()
    scoreability: dict[str, list[str]] = {}
    for index, raw in enumerate(trials):
        trial = _aggregate_contracts.validate_trial_record(raw)
        if trial.get("schema_version") != TRIAL_SCHEMA_VERSION:
            raise ContractError(f"{arm}[{index}] has the wrong trial schema")
        digest = _aggregate_contracts.trial_sha256(trial)
        if digest in hashes:
            raise ContractError(f"{arm} contains duplicate canonical trial {digest}")
        task_id = _trial_task(trial)
        ordinal = _trial_ordinal(trial)
        if task_id not in expected:
            raise ContractError(f"{arm} contains unexpected task_id {task_id!r}")
        if ordinal >= attempts_per_task:
            raise ContractError(
                f"{arm} attempt ordinal {ordinal} exceeds the precommitted budget"
            )
        key = (task_id, ordinal)
        if key in keys:
            raise ContractError(f"{arm} duplicates task/attempt {key!r}")
        keys.add(key)
        pair_key = _sha256(trial.get("pair_key"), f"{arm}[{index}].pair_key")
        if pair_key in pair_keys:
            raise ContractError(f"{arm} contains duplicate pair_key {pair_key}")
        pair_keys.add(pair_key)
        cell_ids.add(_sha256(trial.get("cell_id"), f"{arm}[{index}].cell_id"))
        cell = _mapping(trial["cell"], f"{arm}[{index}].cell")
        suite_locks.add(
            _sha256(cell.get("suite_lock_sha256"), f"{arm}[{index}].suite_lock_sha256")
        )
        run_ids.add(_text(trial.get("run_id"), f"{arm}[{index}].run_id"))
        if _scoreable(trial):
            reasons = list(_aggregate_contracts.trial_scoreability_reasons(trial))
            admissibility_reasons = [
                reason
                for reason in reasons
                if reason not in _RUNTIME_STABILITY_ADMISSIBILITY_REASONS
            ]
            if admissibility_reasons:
                raise ContractError(
                    f"{arm}[{index}] is not evidence-admissible: "
                    + "; ".join(admissibility_reasons)
                )
        elif _trial_state(trial) != _INFRASTRUCTURE_STATE:
            raise ContractError(f"{arm}[{index}] is non-excluded but not scoreable")
        _accepted_weight(trial)
        validated.append(trial)
        hashes.append(digest)
    if len(cell_ids) != 1:
        raise ContractError(f"{arm} must contain exactly one immutable cell_id")
    if len(suite_locks) != 1:
        raise ContractError(f"{arm} must contain exactly one suite lock")
    if len(run_ids) != 1:
        raise ContractError(f"{arm} must contain exactly one run_id")
    return {
        "trials": validated,
        "hashes": sorted(hashes),
        "cell_id": next(iter(cell_ids)),
        "suite_lock_sha256": next(iter(suite_locks)),
        "run_id": next(iter(run_ids)),
        "keys": keys,
        "pair_keys": pair_keys,
        "scoreability_reasons": scoreability,
    }


def _counts(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states = Counter(_trial_state(trial) for trial in trials)
    exclusions = Counter(
        str(_mapping(trial["outcome"], "trial.outcome").get("reason", "unknown"))
        for trial in trials
        if _trial_state(trial) == _INFRASTRUCTURE_STATE
    )
    return {
        "attempted": len(trials),
        "scored": sum(states[state] for state in _SCORED_STATES),
        "passed": states["passed"],
        "failed": states["model_failure"],
        "excluded": states[_INFRASTRUCTURE_STATE],
        "excluded_by_reason": dict(sorted(exclusions.items())),
        "infrastructure_exclusion_rate": (
            states[_INFRASTRUCTURE_STATE] / len(trials) if trials else None
        ),
    }


def _quality(
    trials: Sequence[Mapping[str, Any]],
    *,
    expected_task_ids: Sequence[str],
    attempts_per_task: int,
    hashes: Sequence[str],
    resamples: int,
) -> dict[str, Any]:
    by_task: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_task[_trial_task(trial)].append(trial)

    pass1_values: dict[str, float] = {}
    pass4_values: dict[str, float] = {}
    pass_all_values: dict[str, float] = {}
    scored_attempts: dict[str, int] = {}
    complete_tasks: list[str] = []
    for task_id in expected_task_ids:
        task_trials = sorted(by_task.get(task_id, []), key=_trial_ordinal)
        scored = [trial for trial in task_trials if _scoreable(trial)]
        scored_attempts[task_id] = len(scored)
        if scored:
            pass1_values[task_id] = sum(
                _trial_state(trial) == "passed" for trial in scored
            ) / len(scored)
        budget4 = [
            trial
            for trial in task_trials
            if _trial_ordinal(trial) < 4 and _scoreable(trial)
        ]
        if budget4:
            pass4_values[task_id] = float(
                any(_trial_state(trial) == "passed" for trial in budget4)
            )
        if len(scored) == attempts_per_task:
            complete_tasks.append(task_id)
            pass_all_values[task_id] = float(
                all(_trial_state(trial) == "passed" for trial in scored)
            )

    seed_payload = {
        "trial_sha256": sorted(hashes),
        "task_ids": sorted(expected_task_ids),
        "attempts_per_task": attempts_per_task,
    }
    seed = _seed_digest("pheno.eval.aggregate.v2:quality", seed_payload)
    pass1 = sum(pass1_values.values()) / len(pass1_values) if pass1_values else None
    pass4 = sum(pass4_values.values()) / len(pass4_values) if pass4_values else None
    pass_all = (
        sum(pass_all_values.values()) / len(pass_all_values)
        if pass_all_values
        else None
    )
    expected_count = len(expected_task_ids)
    return {
        "pass_at_1": {
            "estimate": pass1,
            "eligible_task_count": len(pass1_values),
            "expected_task_count": expected_count,
            "ci95": _bootstrap_mean_ci(
                pass1_values,
                seed=seed,
                resamples=resamples,
            ),
        },
        "pass_at_4": {
            "estimate": pass4,
            "definition": "fraction solved by at least one scored ordinal in [0, 3]",
            "eligible_task_count": len(pass4_values),
            "expected_task_count": expected_count,
            "ci95": _bootstrap_mean_ci(
                pass4_values,
                seed=_seed_digest("pheno.eval.aggregate.v2:pass-at-4", seed_payload),
                resamples=resamples,
            ),
        },
        "pass_all_k": {
            "k": attempts_per_task,
            "estimate": pass_all,
            "eligible_complete_task_count": len(complete_tasks),
            "expected_task_count": expected_count,
            "complete_task_coverage": len(complete_tasks) / expected_count,
            "conservative_lower_bound": (
                sum(pass_all_values.values()) / expected_count
            ),
            "ci95": (
                _bootstrap_mean_ci(
                    pass_all_values,
                    seed=_seed_digest(
                        "pheno.eval.aggregate.v2:pass-all-k", seed_payload
                    ),
                    resamples=resamples,
                )
                if len(complete_tasks) == expected_count
                else {
                    "lower": None,
                    "upper": None,
                    "resamples": resamples,
                    "task_clusters": len(complete_tasks),
                    "method": BOOTSTRAP_METHOD,
                    "quantile_method": QUANTILE_METHOD,
                    "reason": "one or more tasks has fewer than k scored attempts",
                }
            ),
        },
        "scored_attempts_by_task": dict(sorted(scored_attempts.items())),
        "bootstrap_seed_sha256": seed.hex(),
    }


def _paired_comparison(
    treatment: Sequence[Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]],
    *,
    expected_task_ids: Sequence[str],
    treatment_hashes: Sequence[str],
    baseline_hashes: Sequence[str],
    resamples: int,
) -> dict[str, Any]:
    treatment_by_pair = {str(trial["pair_key"]): trial for trial in treatment}
    baseline_by_pair = {str(trial["pair_key"]): trial for trial in baseline}
    treatment_keys = set(treatment_by_pair)
    baseline_keys = set(baseline_by_pair)
    common = sorted(treatment_keys & baseline_keys)
    missing_treatment = sorted(baseline_keys - treatment_keys)
    missing_baseline = sorted(treatment_keys - baseline_keys)
    paired_values: dict[str, list[float]] = defaultdict(list)
    discordant_exclusions = 0
    for pair_key in common:
        candidate = treatment_by_pair[pair_key]
        control = baseline_by_pair[pair_key]
        if _trial_task(candidate) != _trial_task(control):
            raise ContractError(f"pair_key {pair_key} maps to different tasks")
        if _trial_ordinal(candidate) != _trial_ordinal(control):
            raise ContractError(
                f"pair_key {pair_key} maps to different attempt ordinals"
            )
        if int(candidate["cell"]["seed"]) != int(control["cell"]["seed"]):
            raise ContractError(f"pair_key {pair_key} maps to different seeds")
        candidate_scored = _scoreable(candidate)
        control_scored = _scoreable(control)
        if candidate_scored != control_scored:
            discordant_exclusions += 1
        if candidate_scored and control_scored:
            paired_values[_trial_task(candidate)].append(
                float(_trial_state(candidate) == "passed")
                - float(_trial_state(control) == "passed")
            )
    task_deltas = {
        task_id: sum(values) / len(values)
        for task_id, values in paired_values.items()
        if values
    }
    seed_payload = {
        "treatment_trial_sha256": sorted(treatment_hashes),
        "baseline_trial_sha256": sorted(baseline_hashes),
        "task_ids": sorted(expected_task_ids),
    }
    seed = _seed_digest("pheno.eval.aggregate.v2:paired-pass-at-1", seed_payload)
    delta = sum(task_deltas.values()) / len(task_deltas) if task_deltas else None
    return {
        "pair_key_count": len(common),
        "missing_treatment_pair_keys": missing_treatment,
        "missing_baseline_pair_keys": missing_baseline,
        "paired_scored_attempt_count": sum(
            len(values) for values in paired_values.values()
        ),
        "paired_task_count": len(task_deltas),
        "expected_task_count": len(expected_task_ids),
        "discordant_exclusion_count": discordant_exclusions,
        "discordant_exclusion_rate": (
            discordant_exclusions / len(common) if common else None
        ),
        "pass_at_1_delta": {
            "estimate": delta,
            "ci95": _bootstrap_mean_ci(
                task_deltas,
                seed=seed,
                resamples=resamples,
            ),
            "definition": "macro mean of treatment-minus-baseline paired task pass fractions",
        },
        "bootstrap_seed_sha256": seed.hex(),
    }


def _summarize_tools(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [trial for trial in trials if _scoreable(trial)]
    rows = [trial.get("tools") for trial in scored]
    present = [row for row in rows if isinstance(row, Mapping)]
    totals = dict.fromkeys(_TOOL_TOTAL_FIELDS, 0)
    bad_trials = 0
    repair_trials = 0
    fallback_trials = 0
    for row in present:
        for field in _TOOL_TOTAL_FIELDS:
            value = row.get(field)
            if value is not None:
                totals[field] += int(value)
        if int(row.get("duplicate_calls", 0)) > 0 or int(row.get("loop_events", 0)) > 0:
            bad_trials += 1
        if int(row.get("repair_attempts", 0)) > 0:
            repair_trials += 1
        if int(row.get("fallbacks", 0)) > 0:
            fallback_trials += 1
    parsed = totals["parsed_calls"]
    valid = totals["schema_valid_calls"]
    executed = totals["executed_calls"]
    labeled = totals["gold_labeled_calls"]
    semantic_complete = len(present) == len(scored) and all(
        int(row.get("executed_calls", 0)) == 0
        or row.get("semantically_correct_calls") is not None
        for row in present
    )
    exact_complete = all(
        int(row.get("gold_labeled_calls", 0) or 0) == 0
        or (
            row.get("exact_tool_matches") is not None
            and row.get("exact_argument_matches") is not None
        )
        for row in present
    )
    summary = {
        "coverage_fraction": len(present) / len(scored) if scored else None,
        "totals": totals,
        "parse_rate": (
            parsed / totals["emitted_candidates"]
            if totals["emitted_candidates"]
            else None
        ),
        "schema_valid_rate": valid / parsed if parsed else None,
        "valid_but_wrong_rate": totals["schema_valid_but_wrong"] / valid
        if valid
        else None,
        "semantic_correct_count_complete": semantic_complete,
        "semantic_correct_rate": (
            totals["semantically_correct_calls"] / executed
            if executed and semantic_complete
            else None
        ),
        "repair_attempt_trial_count": repair_trials,
        "repair_attempt_trial_rate": repair_trials / len(scored) if scored else None,
        "fallback_trial_count": fallback_trials,
        "fallback_trial_rate": fallback_trials / len(scored) if scored else None,
        "duplicate_or_loop_trial_count": bad_trials,
        "duplicate_or_loop_trial_rate": bad_trials / len(scored) if scored else None,
        "status": (
            "complete"
            if len(present) == len(scored)
            else "partial"
            if present
            else "missing"
        ),
    }
    if labeled > 0:
        summary.update(
            {
                "exact_match_counts_complete": exact_complete,
                "exact_tool_match_rate": (
                    totals["exact_tool_matches"] / labeled if exact_complete else None
                ),
                "exact_argument_match_rate": (
                    totals["exact_argument_matches"] / labeled
                    if exact_complete
                    else None
                ),
            }
        )
    return summary


def _distribution(values: Sequence[float], expected_count: int) -> dict[str, Any]:
    checked = [float(value) for value in values]
    return {
        "sample_count": len(checked),
        "coverage_fraction": (
            len(checked) / expected_count if expected_count else None
        ),
        "p50": quantile_type7(checked, 0.50),
        "p95": quantile_type7(checked, 0.95),
        "p99": quantile_type7(checked, 0.99),
    }


def _summarize_latency(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize scoreable-trial latency using only named trial measurements.

    Decode throughput is eligible only when the trial has at least two
    completion tokens and a positive first-to-last-token interval.  Transport
    chunk arrival gaps are deliberately not consumed by this contract.
    """

    scored = [trial for trial in trials if _scoreable(trial)]
    values: dict[str, list[float]] = {
        "queue_ms": [],
        "ttft_ms": [],
        "task_wall_ms": [],
        "verifier_ms": [],
        "true_decode_tokens_per_second": [],
    }
    for trial in scored:
        timing = trial.get("timing")
        tokens = trial.get("tokens")
        if not isinstance(timing, Mapping):
            continue
        for field in ("queue_ms", "ttft_ms", "task_wall_ms", "verifier_ms"):
            value = timing.get(field)
            if (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
                and float(value) >= 0.0
            ):
                values[field].append(float(value))
        if not isinstance(tokens, Mapping):
            continue
        completion = tokens.get("completion")
        first = timing.get("first_token_ns")
        last = timing.get("last_token_ns")
        if (
            not isinstance(completion, bool)
            and isinstance(completion, int)
            and completion >= 2
            and not isinstance(first, bool)
            and isinstance(first, int)
            and not isinstance(last, bool)
            and isinstance(last, int)
            and last > first
        ):
            interval_seconds = (last - first) / 1_000_000_000.0
            values["true_decode_tokens_per_second"].append(
                (completion - 1) / interval_seconds
            )
    count = len(scored)
    decode = _distribution(values["true_decode_tokens_per_second"], count)
    decode.update(
        {
            "formula": TRUE_DECODE_FORMULA,
            "timestamp_source": TRUE_DECODE_TIMESTAMP_SOURCE,
        }
    )
    return {
        "population": "scoreable_trials",
        "scoreable_trial_count": count,
        "quantile_method": QUANTILE_METHOD,
        "queue_ms": _distribution(values["queue_ms"], count),
        "ttft_ms": _distribution(values["ttft_ms"], count),
        "task_wall_ms": _distribution(values["task_wall_ms"], count),
        "verifier_ms": _distribution(values["verifier_ms"], count),
        "true_decode_tokens_per_second": decode,
    }


def _summarize_cache(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [trial for trial in trials if _scoreable(trial)]
    rows = [trial.get("cache") for trial in scored]
    present = [row for row in rows if isinstance(row, Mapping)]
    eligible = sum(int(row.get("eligible_prefix_tokens", 0)) for row in present)
    hits = sum(int(row.get("hit_tokens", 0)) for row in present)
    errors = [
        float(row["counter_reconciliation_error"])
        for row in present
        if row.get("counter_reconciliation_error") is not None
    ]
    contamination = sum(bool(row.get("cross_request_contamination")) for row in present)
    return {
        "coverage_fraction": len(present) / len(scored) if scored else None,
        "eligible_prefix_tokens": eligible,
        "hit_tokens": hits,
        "effective_hit_rate": hits / eligible if eligible else None,
        "max_counter_reconciliation_error": max(errors) if errors else None,
        "cross_request_contamination_count": contamination,
        "status": (
            "complete"
            if len(present) == len(scored)
            else "partial"
            if present
            else "missing"
        ),
    }


def _summarize_drift(
    trials: Sequence[Mapping[str, Any]], expected_task_ids: Sequence[str]
) -> dict[str, Any]:
    by_task: dict[str, list[str]] = defaultdict(list)
    checkpoint_totals = {
        turn: {"assertions_retained": 0, "assertions_expected": 0}
        for turn in _DRIFT_CHECKPOINT_TURNS
    }
    manifest_hashes: set[str] = set()
    for trial in trials:
        if _scoreable(trial):
            by_task[_trial_task(trial)].append(_trial_state(trial))
            drift = trial.get("drift")
            if isinstance(drift, Mapping):
                manifest = drift.get("assertion_manifest_sha256")
                if manifest is not None:
                    manifest_hashes.add(
                        _sha256(manifest, "trial.drift.assertion_manifest_sha256")
                    )
                checkpoints = drift.get("checkpoints", [])
                if not isinstance(checkpoints, list):
                    raise ContractError("trial.drift.checkpoints must be an array")
                seen_turns: set[int] = set()
                for index, raw_checkpoint in enumerate(checkpoints):
                    checkpoint = _mapping(
                        raw_checkpoint,
                        f"trial.drift.checkpoints[{index}]",
                    )
                    turn = _integer(
                        checkpoint.get("turn"),
                        f"trial.drift.checkpoints[{index}].turn",
                        minimum=1,
                    )
                    if turn not in _DRIFT_CHECKPOINT_TURNS or turn in seen_turns:
                        raise ContractError(
                            "trial drift checkpoints must use unique turns 1/5/10/25/50"
                        )
                    seen_turns.add(turn)
                    expected_count = _integer(
                        checkpoint.get("assertions_expected"),
                        f"trial.drift.checkpoints[{index}].assertions_expected",
                    )
                    retained_count = _integer(
                        checkpoint.get("assertions_retained"),
                        f"trial.drift.checkpoints[{index}].assertions_retained",
                    )
                    if retained_count > expected_count:
                        raise ContractError(
                            "trial drift retained assertions exceed expected assertions"
                        )
                    checkpoint_totals[turn]["assertions_expected"] += expected_count
                    checkpoint_totals[turn]["assertions_retained"] += retained_count
    if len(manifest_hashes) > 1:
        raise ContractError("scoreable trials use different drift assertion manifests")
    eligible = {
        task_id: states for task_id, states in by_task.items() if len(states) >= 2
    }
    flips = sum(len(set(states)) > 1 for states in eligible.values())
    disagreements = []
    for states in eligible.values():
        modal = Counter(states).most_common(1)[0][1]
        disagreements.append(1.0 - modal / len(states))
    retention_by_turn: dict[str, Any] = {}
    for turn in _DRIFT_CHECKPOINT_TURNS:
        retained_count = checkpoint_totals[turn]["assertions_retained"]
        expected_count = checkpoint_totals[turn]["assertions_expected"]
        retention_by_turn[str(turn)] = {
            "assertions_retained": retained_count,
            "assertions_expected": expected_count,
            "retention": retained_count / expected_count if expected_count else None,
        }
    retained = sum(
        checkpoint["assertions_retained"] for checkpoint in checkpoint_totals.values()
    )
    expected = sum(
        checkpoint["assertions_expected"] for checkpoint in checkpoint_totals.values()
    )
    return {
        "verifier_flip_rate": flips / len(eligible) if eligible else None,
        "decision_disagreement": (
            sum(disagreements) / len(disagreements) if disagreements else None
        ),
        "eligible_repeated_task_count": len(eligible),
        "expected_task_count": len(expected_task_ids),
        "assertion_manifest_sha256": next(iter(manifest_hashes), None),
        "retention_by_turn": retention_by_turn,
        "long_turn_assertion_retention": retained / expected if expected else None,
        "long_turn_assertions_retained": retained,
        "long_turn_assertions_expected": expected,
    }


def _summarize_runtime_stability(
    trials: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    totals = dict.fromkeys(_RUNTIME_STABILITY_FIELDS, 0)
    covered = 0
    for trial in trials:
        integrity = trial.get("integrity")
        if not isinstance(integrity, Mapping):
            continue
        if not all(
            not isinstance(integrity.get(field), bool)
            and isinstance(integrity.get(field), int)
            and int(integrity[field]) >= 0
            for field in _RUNTIME_STABILITY_FIELDS
        ):
            continue
        covered += 1
        for field in _RUNTIME_STABILITY_FIELDS:
            totals[field] += int(integrity[field])
    attempted = len(trials)
    return {
        "attempted_trial_count": attempted,
        "covered_trial_count": covered,
        "coverage_fraction": covered / attempted if attempted else None,
        **totals,
        "status": (
            "complete" if covered == attempted else "partial" if covered else "missing"
        ),
    }


__all__ = [
    "BOOTSTRAP_METHOD",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "QUANTILE_METHOD",
    "TRUE_DECODE_FORMULA",
    "TRUE_DECODE_TIMESTAMP_SOURCE",
    "_RUNTIME_STABILITY_FIELDS",
    "_accepted_weight",
    "_counts",
    "_distribution",
    "_paired_comparison",
    "_quality",
    "_scoreable",
    "_summarize_cache",
    "_summarize_drift",
    "_summarize_latency",
    "_summarize_runtime_stability",
    "_summarize_tools",
    "_validate_arm",
    "performance_task_ids_sha256",
]
