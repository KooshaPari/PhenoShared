"""Strict, deterministic validation for ``pheno.eval.trial.v2`` records."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .atif import validate_atif_integrity
from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .redaction import contains_secret

TRIAL_SCHEMA_VERSION = "pheno.eval.trial.v2"
ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION = "pheno.eval.artifact_bundle_summary.v1"
MAX_ARTIFACT_BUNDLE_BYTES = 64 * 1024 * 1024

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OCI_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_ROOT_FIELDS = {
    "schema_version",
    "run_id",
    "trial_id",
    "cell_id",
    "pair_key",
    "evidence_class",
    "run_mode",
    "cell",
    "outcome",
    "accepted_steps",
    "total_weight",
    "tools",
    "timing",
    "tokens",
    "cache",
    "resources",
    "cost",
    "integrity",
    "drift",
    "artifacts",
}
_MODEL_FAILURE_REASONS = {
    "verifier_fail",
    "timeout",
    "context_exhausted",
    "oom",
    "unsafe",
}
_EXCLUSION_REASONS = {
    "harness_crash",
    "provider_error",
    "verifier_error",
    "network_error",
    "evaluator_infrastructure_error",
}
_TOOL_FIELDS = {
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
}
_NULLABLE_TOOL_FIELDS = {
    "semantically_correct_calls",
    "gold_labeled_calls",
    "exact_tool_matches",
    "exact_argument_matches",
}
_EVIDENCE_CLASSES = {
    "local_measured",
    "dry_run",
    "synthetic",
    "vendor",
    "anecdotal",
}
_INTENT_NODE_KINDS = {
    "run",
    "model_call",
    "tool_call",
    "verifier",
    "artifact",
    "decision",
    "subagent",
}
_INTENT_EDGE_KINDS = {
    "contains",
    "depends_on",
    "produces",
    "verifies",
    "follows",
    "delegates",
}


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _exact(value: Any, fields: set[str], path: str) -> Mapping[str, Any]:
    obj = _object(value, path)
    missing = sorted(fields - set(obj))
    unknown = sorted(set(obj) - fields)
    if missing:
        raise ContractError(f"{path} is missing fields: {missing}")
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")
    return obj


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{path} must be boolean")
    return value


def _number(
    value: Any,
    path: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    nullable: bool = False,
) -> float | None:
    if value is None and nullable:
        return None
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


def _integer(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    nullable: bool = False,
) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        suffix = " or null" if nullable else ""
        raise ContractError(f"{path} must be an integer >= {minimum}{suffix}")
    return value


def _sha256(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    text = _text(value, path)
    if not _SHA256.fullmatch(text):
        raise ContractError(f"{path} must be a lowercase SHA-256 digest")
    return text


def _close(actual: Any, expected: float, path: str) -> None:
    value = _number(actual, path, minimum=0.0)
    assert value is not None  # nosec B101
    if not math.isclose(value, expected, rel_tol=1e-9, abs_tol=1e-6):
        raise ContractError(f"{path} does not reconcile with monotonic timestamps")


def _validate_parser(value: Any, path: str) -> None:
    parser = _exact(value, {"name", "revision"}, path)
    _text(parser["name"], f"{path}.name")
    _text(parser["revision"], f"{path}.revision")


def _validate_cell(value: Any) -> Mapping[str, Any]:
    fields = {
        "suite_lock_sha256",
        "task_id",
        "attempt_ordinal",
        "seed",
        "model",
        "runtime",
        "harness",
        "device",
        "treatment",
        "sampling",
    }
    cell = _exact(value, fields, "cell")
    _sha256(cell["suite_lock_sha256"], "cell.suite_lock_sha256")
    _text(cell["task_id"], "cell.task_id")
    _integer(cell["attempt_ordinal"], "cell.attempt_ordinal")
    _integer(cell["seed"], "cell.seed")

    model_fields = {
        "canonical_id",
        "revision",
        "artifact_sha256",
        "quantization",
        "chat_template_sha256",
        "reasoning_parser",
        "tool_parser",
    }
    model = _exact(cell["model"], model_fields, "cell.model")
    for field in ("canonical_id", "revision", "quantization"):
        _text(model[field], f"cell.model.{field}")
    _sha256(model["artifact_sha256"], "cell.model.artifact_sha256")
    _sha256(model["chat_template_sha256"], "cell.model.chat_template_sha256")
    _validate_parser(model["reasoning_parser"], "cell.model.reasoning_parser")
    _validate_parser(model["tool_parser"], "cell.model.tool_parser")

    runtime_fields = {
        "name",
        "version",
        "revision",
        "container_digest",
        "launch_config_sha256",
    }
    runtime = _exact(cell["runtime"], runtime_fields, "cell.runtime")
    for field in ("name", "version", "revision"):
        _text(runtime[field], f"cell.runtime.{field}")
    container = runtime["container_digest"]
    if container is not None and not _OCI_DIGEST.fullmatch(
        _text(container, "cell.runtime.container_digest")
    ):
        raise ContractError("cell.runtime.container_digest must be sha256:<digest>")
    _sha256(runtime["launch_config_sha256"], "cell.runtime.launch_config_sha256")

    harness_fields = {
        "name",
        "revision",
        "prompt_sha256",
        "tool_definitions_sha256",
    }
    harness = _exact(cell["harness"], harness_fields, "cell.harness")
    _text(harness["name"], "cell.harness.name")
    _text(harness["revision"], "cell.harness.revision")
    _sha256(harness["prompt_sha256"], "cell.harness.prompt_sha256")
    _sha256(
        harness["tool_definitions_sha256"],
        "cell.harness.tool_definitions_sha256",
    )

    device_fields = {
        "profile_id",
        "device_ids",
        "os_build",
        "driver_build",
        "power_policy",
    }
    device = _exact(cell["device"], device_fields, "cell.device")
    for field in ("profile_id", "os_build", "driver_build", "power_policy"):
        _text(device[field], f"cell.device.{field}")
    ids = device["device_ids"]
    if not isinstance(ids, list) or not ids:
        raise ContractError("cell.device.device_ids must be a non-empty array")
    checked_ids = [
        _text(item, f"cell.device.device_ids[{index}]")
        for index, item in enumerate(ids)
    ]
    if len(set(checked_ids)) != len(checked_ids):
        raise ContractError("cell.device.device_ids must be unique")

    treatment_fields = {
        "context_length",
        "cache_mode",
        "decode_mode",
        "concurrency",
        "role",
    }
    treatment = _exact(cell["treatment"], treatment_fields, "cell.treatment")
    _integer(treatment["context_length"], "cell.treatment.context_length", minimum=1)
    _integer(treatment["concurrency"], "cell.treatment.concurrency", minimum=1)
    for field in ("cache_mode", "decode_mode", "role"):
        _text(treatment[field], f"cell.treatment.{field}")

    sampling_fields = {
        "temperature",
        "top_p",
        "top_k",
        "max_output_tokens",
        "deterministic_requested",
    }
    sampling = _exact(cell["sampling"], sampling_fields, "cell.sampling")
    _number(sampling["temperature"], "cell.sampling.temperature", minimum=0.0)
    _number(sampling["top_p"], "cell.sampling.top_p", minimum=0.0, maximum=1.0)
    _integer(sampling["top_k"], "cell.sampling.top_k", nullable=True)
    _integer(
        sampling["max_output_tokens"],
        "cell.sampling.max_output_tokens",
        minimum=1,
    )
    _boolean(
        sampling["deterministic_requested"], "cell.sampling.deterministic_requested"
    )
    return cell


def _validate_outcome(value: Any) -> Mapping[str, Any]:
    outcome = _exact(
        value,
        {"state", "reason", "scoreable", "reward", "verifier_components"},
        "outcome",
    )
    state = outcome["state"]
    if state not in {"passed", "model_failure", "infrastructure_exclusion"}:
        raise ContractError("outcome.state is invalid")
    reason = outcome["reason"]
    expected_scoreable = state != "infrastructure_exclusion"
    if _boolean(outcome["scoreable"], "outcome.scoreable") != expected_scoreable:
        raise ContractError("outcome.scoreable contradicts outcome.state")
    if state == "passed":
        if reason is not None:
            raise ContractError("passed outcomes require a null reason")
    else:
        allowed = (
            _MODEL_FAILURE_REASONS if state == "model_failure" else _EXCLUSION_REASONS
        )
        if reason not in allowed:
            raise ContractError(f"outcome.reason is invalid for {state}")
    reward = _number(outcome["reward"], "outcome.reward", nullable=True)
    components = _object(outcome["verifier_components"], "outcome.verifier_components")
    for key, component in components.items():
        _text(key, "outcome.verifier_components key")
        _number(component, f"outcome.verifier_components.{key}")
    if state == "infrastructure_exclusion":
        if reward is not None or components:
            raise ContractError(
                "infrastructure exclusions require null reward and empty "
                "verifier_components"
            )
    elif reward is None:
        raise ContractError("passed and model-failure outcomes require a finite reward")
    return outcome


def _validate_steps(
    value: Any,
    total: Any,
    state: str,
    subtask_verifiers_present: bool,
) -> None:
    if not isinstance(value, list):
        raise ContractError("accepted_steps must be an array")
    fields = {
        "step_id",
        "weight",
        "predicate_sha256",
        "depends_on",
        "false_to_true_transition",
        "terminal_reverified",
    }
    weights: dict[str, float] = {}
    dependencies: dict[str, list[str]] = {}
    for index, raw in enumerate(value):
        path = f"accepted_steps[{index}]"
        step = _exact(raw, fields, path)
        step_id = _text(step["step_id"], f"{path}.step_id")
        if step_id in weights:
            raise ContractError(
                f"accepted_steps contains duplicate step_id {step_id!r}"
            )
        _sha256(step["predicate_sha256"], f"{path}.predicate_sha256")
        weight = _number(step["weight"], f"{path}.weight", minimum=0.0)
        assert weight is not None  # nosec B101
        raw_dependencies = step["depends_on"]
        if not isinstance(raw_dependencies, list):
            raise ContractError(f"{path}.depends_on must be an array")
        deps = [
            _text(dep, f"{path}.depends_on[{i}]")
            for i, dep in enumerate(raw_dependencies)
        ]
        if len(set(deps)) != len(deps) or step_id in deps:
            raise ContractError(
                f"{path}.depends_on must be unique and cannot contain itself"
            )
        if (
            _boolean(
                step["false_to_true_transition"], f"{path}.false_to_true_transition"
            )
            is not True
        ):
            raise ContractError(f"{path} did not transition false to true")
        if (
            _boolean(step["terminal_reverified"], f"{path}.terminal_reverified")
            is not True
        ):
            raise ContractError(f"{path} was not terminally reverified")
        weights[step_id] = weight
        dependencies[step_id] = deps
    for step_id, deps in dependencies.items():
        missing = sorted(set(deps) - set(weights))
        if missing:
            raise ContractError(
                f"accepted step {step_id!r} has missing dependencies: {missing}"
            )
    pending = set(weights)
    resolved: set[str] = set()
    while pending:
        ready = {step for step in pending if set(dependencies[step]) <= resolved}
        if not ready:
            raise ContractError("accepted step dependency graph contains a cycle")
        resolved.update(ready)
        pending -= ready
    declared = _number(total, "total_weight", minimum=0.0)
    assert declared is not None  # nosec B101
    if not math.isclose(sum(weights.values()), declared, rel_tol=1e-12, abs_tol=1e-12):
        raise ContractError("total_weight does not equal accepted step weight")
    if state == "passed" and not value:
        raise ContractError(
            "passed outcomes require at least one accepted verified step"
        )
    if state == "passed" and not subtask_verifiers_present:
        if len(value) != 1 or not math.isclose(
            next(iter(weights.values())), 1.0, rel_tol=0.0, abs_tol=0.0
        ):
            raise ContractError(
                "passed outcomes without subtask verifiers require exactly one "
                "accepted step of weight 1.0"
            )
    if state == "infrastructure_exclusion" and (value or declared != 0.0):
        raise ContractError(
            "infrastructure exclusions cannot contribute accepted weight"
        )


def _validate_tools(value: Any) -> Mapping[str, Any]:
    tools = _exact(value, _TOOL_FIELDS, "tools")
    counts: dict[str, int | None] = {}
    for field in _TOOL_FIELDS:
        counts[field] = _integer(
            tools[field], f"tools.{field}", nullable=field in _NULLABLE_TOOL_FIELDS
        )
    emitted = counts["emitted_candidates"] or 0
    parsed = counts["parsed_calls"] or 0
    valid = counts["schema_valid_calls"] or 0
    executed = counts["executed_calls"] or 0
    if not emitted >= parsed >= valid >= executed:
        raise ContractError(
            "tool candidate/parse/schema/execution counts do not reconcile"
        )
    if (counts["schema_valid_but_wrong"] or 0) > valid:
        raise ContractError("tools.schema_valid_but_wrong exceeds schema_valid_calls")
    for field in _NULLABLE_TOOL_FIELDS:
        count = counts[field]
        if count is not None and count > executed:
            raise ContractError(f"tools.{field} exceeds executed_calls")
    gold = counts["gold_labeled_calls"]
    exact_tool = counts["exact_tool_matches"]
    exact_arguments = counts["exact_argument_matches"]
    if gold is None:
        if exact_tool is not None or exact_arguments is not None:
            raise ContractError(
                "exact tool/argument matches must be null without gold labels"
            )
    elif exact_tool is None or exact_arguments is None:
        raise ContractError(
            "gold-labeled calls require exact tool and argument match counts"
        )
    elif not exact_arguments <= exact_tool <= gold:
        raise ContractError(
            "exact match counts must satisfy exact_argument_matches <= "
            "exact_tool_matches <= gold_labeled_calls"
        )
    return tools


def _validate_timing(value: Any) -> Mapping[str, Any]:
    fields = {
        "clock_id",
        "enqueued_ns",
        "dispatched_ns",
        "first_token_ns",
        "last_token_ns",
        "completed_ns",
        "verifier_completed_ns",
        "queue_ms",
        "ttft_ms",
        "decode_ms",
        "task_wall_ms",
        "verifier_ms",
    }
    timing = _exact(value, fields, "timing")
    _text(timing["clock_id"], "timing.clock_id")
    points = {
        field: _integer(
            timing[field],
            f"timing.{field}",
            nullable=field in {"first_token_ns", "last_token_ns"},
        )
        for field in (
            "enqueued_ns",
            "dispatched_ns",
            "first_token_ns",
            "last_token_ns",
            "completed_ns",
            "verifier_completed_ns",
        )
    }
    enqueued = points["enqueued_ns"]
    dispatched = points["dispatched_ns"]
    completed = points["completed_ns"]
    verified = points["verifier_completed_ns"]
    assert (
        enqueued is not None
        and dispatched is not None
        and completed is not None
        and verified is not None
    )  # nosec B101
    if not enqueued <= dispatched <= completed <= verified:
        raise ContractError(
            "timing timestamps must use one monotonic clock in lifecycle order"
        )
    first = points["first_token_ns"]
    last = points["last_token_ns"]
    if (first is None) != (last is None):
        raise ContractError(
            "timing first/last token timestamps must both be null or present"
        )
    if (
        first is not None
        and last is not None
        and not dispatched <= first <= last <= completed
    ):
        raise ContractError("token timestamps fall outside the task lifecycle")
    _close(timing["queue_ms"], (dispatched - enqueued) / 1_000_000, "timing.queue_ms")
    _close(
        timing["task_wall_ms"],
        (completed - dispatched) / 1_000_000,
        "timing.task_wall_ms",
    )
    _close(
        timing["verifier_ms"], (verified - completed) / 1_000_000, "timing.verifier_ms"
    )
    if first is None:
        if timing["ttft_ms"] is not None or timing["decode_ms"] is not None:
            raise ContractError("token latency must be null without token timestamps")
    else:
        _close(timing["ttft_ms"], (first - dispatched) / 1_000_000, "timing.ttft_ms")
        assert last is not None  # nosec B101
        _close(timing["decode_ms"], (last - first) / 1_000_000, "timing.decode_ms")
    return timing


def _validate_tokens(value: Any, timing: Mapping[str, Any]) -> None:
    fields = {
        "prompt",
        "cached_read",
        "cached_write",
        "completion",
        "reasoning",
        "draft_proposed",
        "draft_accepted",
    }
    tokens = _exact(value, fields, "tokens")
    values = {
        field: _integer(
            tokens[field],
            f"tokens.{field}",
            nullable=field in {"reasoning", "draft_proposed", "draft_accepted"},
        )
        for field in fields
    }
    if (values["cached_read"] or 0) > (values["prompt"] or 0):
        raise ContractError("tokens.cached_read cannot exceed prompt tokens")
    reasoning = values["reasoning"]
    if reasoning is not None and reasoning > (values["completion"] or 0):
        raise ContractError("tokens.reasoning cannot exceed completion tokens")
    proposed, accepted = values["draft_proposed"], values["draft_accepted"]
    if (proposed is None) != (accepted is None):
        raise ContractError("draft token counts must both be null or present")
    if proposed is not None and accepted is not None and accepted > proposed:
        raise ContractError("tokens.draft_accepted cannot exceed draft_proposed")
    if values["completion"] and timing["first_token_ns"] is None:
        raise ContractError("completion tokens require token timestamps")


def _validate_cache(value: Any) -> Mapping[str, Any]:
    fields = {
        "eligible_prefix_tokens",
        "hit_tokens",
        "misses",
        "writes",
        "evictions",
        "restored_tokens",
        "kv_bytes_peak",
        "counter_reconciliation_error",
        "cross_request_contamination",
    }
    cache = _exact(value, fields, "cache")
    for field in fields - {
        "counter_reconciliation_error",
        "cross_request_contamination",
    }:
        _integer(cache[field], f"cache.{field}", nullable=field == "kv_bytes_peak")
    if cache["hit_tokens"] > cache["eligible_prefix_tokens"]:
        raise ContractError("cache.hit_tokens cannot exceed eligible_prefix_tokens")
    _number(
        cache["counter_reconciliation_error"],
        "cache.counter_reconciliation_error",
        minimum=0.0,
        maximum=1.0,
        nullable=True,
    )
    _boolean(cache["cross_request_contamination"], "cache.cross_request_contamination")
    return cache


def _validate_resources(value: Any) -> Mapping[str, Any]:
    fields = {
        "sampling_interval_ms",
        "coverage_fraction",
        "peak_attributable_active_memory_bytes",
        "gpu_vram_peak_bytes",
        "attributable_ram_peak_bytes",
        "unified_memory_peak_bytes",
        "gpu_util_mean_pct",
        "gpu_power_mean_w",
        "energy_wh",
        "temperature_peak_c",
        "thermal_throttle_seconds",
        "os_thermal_state",
        "battery_delta_pct",
        "throughput_retention",
    }
    resources = _exact(value, fields, "resources")
    _number(
        resources["sampling_interval_ms"],
        "resources.sampling_interval_ms",
        minimum=1e-15,
    )
    _number(
        resources["coverage_fraction"],
        "resources.coverage_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    _integer(
        resources["peak_attributable_active_memory_bytes"],
        "resources.peak_attributable_active_memory_bytes",
    )
    for field in (
        "gpu_vram_peak_bytes",
        "attributable_ram_peak_bytes",
        "unified_memory_peak_bytes",
    ):
        _integer(resources[field], f"resources.{field}", nullable=True)
    _number(
        resources["gpu_util_mean_pct"],
        "resources.gpu_util_mean_pct",
        minimum=0.0,
        maximum=100.0,
        nullable=True,
    )
    for field in (
        "gpu_power_mean_w",
        "energy_wh",
        "temperature_peak_c",
        "thermal_throttle_seconds",
        "throughput_retention",
    ):
        _number(resources[field], f"resources.{field}", minimum=0.0, nullable=True)
    state = resources["os_thermal_state"]
    if state is not None:
        _text(state, "resources.os_thermal_state")
    _number(
        resources["battery_delta_pct"],
        "resources.battery_delta_pct",
        minimum=-100.0,
        maximum=100.0,
        nullable=True,
    )
    return resources


def _validate_drift(value: Any) -> Mapping[str, Any]:
    drift = _exact(value, {"assertion_manifest_sha256", "checkpoints"}, "drift")
    manifest = _sha256(
        drift["assertion_manifest_sha256"],
        "drift.assertion_manifest_sha256",
        nullable=True,
    )
    checkpoints = drift["checkpoints"]
    if not isinstance(checkpoints, list):
        raise ContractError("drift.checkpoints must be an array")
    allowed_turns = {1, 5, 10, 25, 50}
    previous_turn = 0
    checkpoint_fields = {
        "turn",
        "assertions_expected",
        "assertions_retained",
    }
    for index, raw_checkpoint in enumerate(checkpoints):
        path = f"drift.checkpoints[{index}]"
        checkpoint = _exact(raw_checkpoint, checkpoint_fields, path)
        turn = _integer(checkpoint["turn"], f"{path}.turn", minimum=1)
        assert turn is not None  # nosec B101
        if turn not in allowed_turns:
            raise ContractError(f"{path}.turn must be one of 1, 5, 10, 25, or 50")
        if turn <= previous_turn:
            raise ContractError(
                "drift.checkpoints must have unique turns in ascending order"
            )
        previous_turn = turn
        expected = _integer(
            checkpoint["assertions_expected"],
            f"{path}.assertions_expected",
        )
        retained = _integer(
            checkpoint["assertions_retained"],
            f"{path}.assertions_retained",
        )
        assert expected is not None and retained is not None  # nosec B101
        if retained > expected:
            raise ContractError(
                f"{path}.assertions_retained cannot exceed assertions_expected"
            )
    if checkpoints and manifest is None:
        raise ContractError(
            "drift.assertion_manifest_sha256 is required when checkpoints exist"
        )
    if not checkpoints and manifest is not None:
        raise ContractError(
            "drift.assertion_manifest_sha256 must be null without checkpoints"
        )
    return drift


def _validate_cost(value: Any) -> Mapping[str, Any]:
    fields = {
        "completeness",
        "provider_usd",
        "sandbox_usd",
        "electricity_usd",
        "hardware_amortization_usd",
        "total_amortized_usd",
        "ledger_sha256",
    }
    cost = _exact(value, fields, "cost")
    if cost["completeness"] not in {"complete", "incomplete"}:
        raise ContractError("cost.completeness must be complete or incomplete")
    component_fields = (
        "provider_usd",
        "sandbox_usd",
        "electricity_usd",
        "hardware_amortization_usd",
    )
    components = [
        _number(cost[field], f"cost.{field}", minimum=0.0, nullable=True)
        for field in component_fields
    ]
    total = _number(
        cost["total_amortized_usd"],
        "cost.total_amortized_usd",
        minimum=0.0,
        nullable=True,
    )
    ledger = _sha256(cost["ledger_sha256"], "cost.ledger_sha256", nullable=True)
    if cost["completeness"] == "complete" and (
        any(component is None for component in components)
        or total is None
        or ledger is None
    ):
        raise ContractError(
            "complete cost requires every component, total, and ledger hash"
        )
    if cost["completeness"] == "incomplete" and (
        total is not None or ledger is not None
    ):
        raise ContractError(
            "incomplete cost requires null total_amortized_usd and ledger_sha256"
        )
    if total is not None and all(component is not None for component in components):
        expected = sum(component for component in components if component is not None)
        if not math.isclose(total, expected, rel_tol=1e-9, abs_tol=1e-9):
            raise ContractError("cost components do not sum to total_amortized_usd")
    return cost


def _validate_integrity(
    value: Any,
    tools: Mapping[str, Any],
    cache: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> Mapping[str, Any]:
    bool_fields = {
        "atif_valid",
        "artifacts_valid",
        "secrets_absent",
        "held_out",
        "risky_action_gate_enabled",
        "verifier_untampered",
        "harness_worktree_dirty",
        "cross_request_contamination",
        "subtask_verifiers_present",
    }
    count_fields = {
        "risky_action_bypasses",
        "orphan_calls",
        "ooms",
        "deadlocks",
        "unexplained_restarts",
    }
    integrity = _exact(value, bool_fields | count_fields, "integrity")
    for field in bool_fields:
        _boolean(integrity[field], f"integrity.{field}")
    for field in count_fields:
        _integer(integrity[field], f"integrity.{field}")
    if integrity["risky_action_bypasses"] != tools["risky_action_bypasses"]:
        raise ContractError("integrity risky-action count does not match tools")
    if integrity["orphan_calls"] != tools["orphan_calls"]:
        raise ContractError("integrity orphan-call count does not match tools")
    if integrity["cross_request_contamination"] != cache["cross_request_contamination"]:
        raise ContractError("integrity cache-contamination flag does not match cache")
    expected_ooms = int(
        outcome["state"] == "model_failure" and outcome["reason"] == "oom"
    )
    if integrity["ooms"] != expected_ooms:
        raise ContractError("integrity.ooms does not match the trial outcome")
    return integrity


def _validate_artifact(value: Any, path: str) -> str:
    artifact = _exact(value, {"path", "sha256"}, path)
    artifact_path = _text(artifact["path"], f"{path}.path")
    parsed = PurePosixPath(artifact_path)
    if (
        parsed.is_absolute()
        or ".." in parsed.parts
        or "\\" in artifact_path
        or "\x00" in artifact_path
        or any(":" in part for part in parsed.parts)
    ):
        raise ContractError(f"{path}.path must be a safe relative POSIX path")
    _sha256(artifact["sha256"], f"{path}.sha256")
    return artifact_path


def _validate_artifacts(value: Any) -> None:
    fields = {"atif_trajectory", "intent_graph", "verifier_outputs", "patch"}
    artifacts = _exact(value, fields, "artifacts")
    paths = [
        _validate_artifact(artifacts["atif_trajectory"], "artifacts.atif_trajectory"),
        _validate_artifact(artifacts["intent_graph"], "artifacts.intent_graph"),
    ]
    outputs = artifacts["verifier_outputs"]
    if not isinstance(outputs, list) or not outputs:
        raise ContractError("artifacts.verifier_outputs must be a non-empty array")
    paths.extend(
        _validate_artifact(item, f"artifacts.verifier_outputs[{index}]")
        for index, item in enumerate(outputs)
    )
    if artifacts["patch"] is not None:
        paths.append(_validate_artifact(artifacts["patch"], "artifacts.patch"))
    if len(set(paths)) != len(paths):
        raise ContractError("artifact paths must be unique")


def validate_trial_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one persisted trial and return a plain root dictionary."""

    root = _exact(record, _ROOT_FIELDS, "trial")
    if root["schema_version"] != TRIAL_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {TRIAL_SCHEMA_VERSION}")
    _text(root["run_id"], "run_id")
    _text(root["trial_id"], "trial_id")
    _sha256(root["cell_id"], "cell_id")
    _sha256(root["pair_key"], "pair_key")
    if root["evidence_class"] not in _EVIDENCE_CLASSES:
        raise ContractError(
            "evidence_class must be local_measured, dry_run, synthetic, vendor, "
            "or anecdotal"
        )
    if root["run_mode"] not in {"execute", "dry_run", "replay", "synthetic"}:
        raise ContractError("run_mode must be execute, dry_run, replay, or synthetic")

    cell = _validate_cell(root["cell"])
    identity = {
        "suite_lock_sha256": cell["suite_lock_sha256"],
        "model": cell["model"],
        "runtime": cell["runtime"],
        "harness": cell["harness"],
        "device": cell["device"],
        "treatment": cell["treatment"],
        "sampling": cell["sampling"],
    }
    expected_cell_id = sha256_hex(canonical_json_bytes(identity))
    if root["cell_id"] != expected_cell_id:
        raise ContractError("cell_id does not match the immutable cell identity")
    pair_identity = {
        "suite_lock_sha256": cell["suite_lock_sha256"],
        "task_id": cell["task_id"],
        "attempt_ordinal": cell["attempt_ordinal"],
        "seed": cell["seed"],
    }
    expected_pair_key = sha256_hex(canonical_json_bytes(pair_identity))
    if root["pair_key"] != expected_pair_key:
        raise ContractError("pair_key does not match suite/task/attempt/seed")

    outcome = _validate_outcome(root["outcome"])
    tools = _validate_tools(root["tools"])
    timing = _validate_timing(root["timing"])
    _validate_tokens(root["tokens"], timing)
    cache = _validate_cache(root["cache"])
    _validate_resources(root["resources"])
    _validate_drift(root["drift"])
    _validate_cost(root["cost"])
    integrity = _validate_integrity(root["integrity"], tools, cache, outcome)
    _validate_steps(
        root["accepted_steps"],
        root["total_weight"],
        str(outcome["state"]),
        bool(integrity["subtask_verifiers_present"]),
    )
    _validate_artifacts(root["artifacts"])
    try:
        canonical_json_bytes(root)
    except (TypeError, ValueError) as exc:
        raise ContractError("trial must contain finite JSON-compatible values") from exc
    if contains_secret(root):
        raise ContractError("trial contains a credential")
    if integrity["secrets_absent"] is True and contains_secret(root):
        raise ContractError("integrity.secrets_absent contradicts the trial payload")
    return dict(root)


class _DuplicateJsonKey(ValueError):
    pass


def _strict_json_object(raw: bytes, path: str) -> Mapping[str, Any]:
    """Decode one bounded artifact without accepting JSON extensions."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """object_pairs_hook that rejects duplicate keys in any nested object."""
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKey(f"duplicate object key {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        """parse_constant hook: refuse NaN/Infinity constants from JSON."""
        raise ValueError(f"non-finite JSON constant {value}")

    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise ContractError(f"{path} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def _validate_intent_graph_artifact(
    value: Mapping[str, Any], *, expected_run_id: str
) -> dict[str, Any]:
    graph = _exact(
        value,
        {
            "schema_version",
            "run_id",
            "suite",
            "created_at",
            "metadata",
            "nodes",
            "edges",
        },
        "artifacts.intent_graph JSON",
    )
    if isinstance(graph["schema_version"], bool) or graph["schema_version"] != 1:
        raise ContractError("intent graph schema_version must be integer 1")
    run_id = _text(graph["run_id"], "intent graph run_id")
    if run_id != expected_run_id:
        raise ContractError("intent graph run_id does not match the trial run_id")
    _text(graph["suite"], "intent graph suite")
    _text(graph["created_at"], "intent graph created_at")
    _object(graph["metadata"], "intent graph metadata")

    raw_nodes = graph["nodes"]
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ContractError("intent graph nodes must be a non-empty array")
    node_fields = {
        "id",
        "kind",
        "name",
        "status",
        "started_at",
        "finished_at",
        "duration_ms",
        "attributes",
    }
    node_ids: set[str] = set()
    indegree: dict[str, int] = {}
    adjacency: dict[str, list[str]] = {}
    for index, raw_node in enumerate(raw_nodes):
        path = f"intent graph nodes[{index}]"
        node = _exact(raw_node, node_fields, path)
        node_id = _text(node["id"], f"{path}.id")
        if node_id in node_ids:
            raise ContractError(f"intent graph contains duplicate node id {node_id!r}")
        node_ids.add(node_id)
        indegree[node_id] = 0
        adjacency[node_id] = []
        if node["kind"] not in _INTENT_NODE_KINDS:
            raise ContractError(f"{path}.kind is invalid")
        _text(node["name"], f"{path}.name")
        _text(node["status"], f"{path}.status")
        for field in ("started_at", "finished_at"):
            if node[field] is not None:
                _text(node[field], f"{path}.{field}")
        _number(node["duration_ms"], f"{path}.duration_ms", minimum=0.0, nullable=True)
        _object(node["attributes"], f"{path}.attributes")

    raw_edges = graph["edges"]
    if not isinstance(raw_edges, list):
        raise ContractError("intent graph edges must be an array")
    edge_fields = {"source", "target", "kind"}
    seen_edges: set[tuple[str, str, str]] = set()
    for index, raw_edge in enumerate(raw_edges):
        path = f"intent graph edges[{index}]"
        edge = _exact(raw_edge, edge_fields, path)
        source = _text(edge["source"], f"{path}.source")
        target = _text(edge["target"], f"{path}.target")
        kind = edge["kind"]
        if kind not in _INTENT_EDGE_KINDS:
            raise ContractError(f"{path}.kind is invalid")
        if source == target:
            raise ContractError("intent graph self edges are not allowed")
        if source not in node_ids or target not in node_ids:
            raise ContractError(
                f"intent graph edge references an unknown node: {source} -> {target}"
            )
        edge_identity = (source, target, str(kind))
        if edge_identity in seen_edges:
            raise ContractError(
                f"intent graph contains duplicate edge {edge_identity!r}"
            )
        seen_edges.add(edge_identity)
        adjacency[source].append(target)
        indegree[target] += 1

    root_count = sum(degree == 0 for degree in indegree.values())
    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        node_id = ready.pop(0)
        visited += 1
        for target in sorted(adjacency[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
        ready.sort()
    if visited != len(node_ids):
        raise ContractError("intent graph contains a cycle")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "node_count": len(node_ids),
        "edge_count": len(seen_edges),
        "root_node_count": root_count,
    }


def _bundle_declarations(
    root: Mapping[str, Any],
) -> list[tuple[str, int | None, Mapping[str, Any]]]:
    artifacts = _object(root["artifacts"], "artifacts")
    declarations: list[tuple[str, int | None, Mapping[str, Any]]] = [
        (
            "atif_trajectory",
            None,
            _object(artifacts["atif_trajectory"], "artifacts.atif_trajectory"),
        ),
        (
            "intent_graph",
            None,
            _object(artifacts["intent_graph"], "artifacts.intent_graph"),
        ),
    ]
    outputs = artifacts["verifier_outputs"]
    assert isinstance(outputs, list) and outputs  # nosec B101
    declarations.extend(
        (
            "verifier_output",
            index,
            _object(item, f"artifacts.verifier_outputs[{index}]"),
        )
        for index, item in enumerate(outputs)
    )
    if artifacts["patch"] is not None:
        declarations.append(
            ("patch", None, _object(artifacts["patch"], "artifacts.patch"))
        )
    return declarations


def validate_trial_artifact_bundle(
    record: Mapping[str, Any], artifact_root: str | os.PathLike[str]
) -> dict[str, Any]:
    """Prove byte integrity and closed schema integrity for a trial bundle.

    Trial integrity flags are diagnostic assertions only.  This function
    independently resolves, reads, hashes, and validates each referenced file.
    The returned summary contains no host-specific absolute path and is stable
    for the same trial and artifact bytes.
    """

    root = validate_trial_record(record)
    try:
        unresolved_root = Path(artifact_root)
        if unresolved_root.is_symlink():
            raise ContractError("artifact_root must not be a symlink")
        bundle_root = unresolved_root.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ContractError(f"artifact_root cannot be resolved: {exc}") from exc
    if not bundle_root.is_dir():
        raise ContractError("artifact_root must be a directory")

    declarations = _bundle_declarations(root)
    total_bytes = 0
    verified: list[dict[str, Any]] = []
    payloads: dict[tuple[str, int | None], bytes] = {}
    resolved_targets: dict[Path, str] = {}
    for role, index, declaration in declarations:
        artifact_path = str(declaration["path"])
        parsed = PurePosixPath(artifact_path)
        try:
            candidate = bundle_root.joinpath(*parsed.parts)
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(bundle_root)
        except ValueError as exc:
            raise ContractError(
                f"artifact path escapes artifact_root: {artifact_path!r}"
            ) from exc
        except (OSError, RuntimeError) as exc:
            raise ContractError(
                f"artifact cannot be resolved: {artifact_path!r}: {exc}"
            ) from exc
        if resolved in resolved_targets:
            raise ContractError(
                f"artifact paths {resolved_targets[resolved]!r} and "
                f"{artifact_path!r} resolve to the same file"
            )
        resolved_targets[resolved] = artifact_path

        try:
            if not stat.S_ISREG(resolved.stat().st_mode):
                raise ContractError(
                    f"artifact is not a regular file: {artifact_path!r}"
                )
            with resolved.open("rb") as handle:
                file_stat = os.fstat(handle.fileno())
                if not stat.S_ISREG(file_stat.st_mode):
                    raise ContractError(
                        f"artifact is not a regular file: {artifact_path!r}"
                    )
                if file_stat.st_size > MAX_ARTIFACT_BUNDLE_BYTES - total_bytes:
                    raise ContractError(
                        "artifact bundle exceeds the maximum total byte count"
                    )
                chunks: list[bytes] = []
                file_bytes = 0
                digest = hashlib.sha256()
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    file_bytes += len(chunk)
                    total_bytes += len(chunk)
                    if total_bytes > MAX_ARTIFACT_BUNDLE_BYTES:
                        raise ContractError(
                            "artifact bundle exceeds the maximum total byte count"
                        )
                    digest.update(chunk)
                    chunks.append(chunk)
        except ContractError:
            raise
        except OSError as exc:
            raise ContractError(
                f"artifact cannot be read: {artifact_path!r}: {exc}"
            ) from exc
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != declaration["sha256"]:
            raise ContractError(f"artifact SHA-256 mismatch for {artifact_path!r}")
        payloads[(role, index)] = b"".join(chunks)
        verified.append(
            {
                "role": role,
                "index": index,
                "path": artifact_path,
                "sha256": actual_sha256,
                "bytes": file_bytes,
            }
        )

    for role, index, declaration in declarations:
        raw = payloads[(role, index)]
        artifact_path = str(declaration["path"])
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        if contains_secret(decoded):
            raise ContractError(
                f"artifact bundle contains a credential in {artifact_path!r}"
            )
        if (
            role == "verifier_output"
            and PurePosixPath(artifact_path).suffix.lower() == ".json"
        ):
            verifier_payload = _strict_json_object(
                raw, f"artifacts.verifier_outputs[{index}]"
            )
            if contains_secret(verifier_payload):
                raise ContractError(
                    f"artifact bundle contains a credential in {artifact_path!r}"
                )

    atif_payload = _strict_json_object(
        payloads[("atif_trajectory", None)], "artifacts.atif_trajectory"
    )
    intent_payload = _strict_json_object(
        payloads[("intent_graph", None)], "artifacts.intent_graph"
    )
    if contains_secret(atif_payload) or contains_secret(intent_payload):
        raise ContractError("structured artifact bundle contains a credential")

    try:
        from harbor.models.trajectories import Trajectory as HarborTrajectory
    except ImportError as exc:  # pragma: no cover - environment gate
        raise ContractError(
            "installed Harbor is required to validate an ATIF artifact bundle"
        ) from exc
    try:
        harbor_trajectory = HarborTrajectory.model_validate(atif_payload, strict=True)
    except Exception as exc:
        raise ContractError(f"Harbor rejected the ATIF trajectory: {exc}") from exc
    atif_summary = validate_atif_integrity(harbor_trajectory.to_json_dict())

    intent_summary = _validate_intent_graph_artifact(
        intent_payload, expected_run_id=str(root["run_id"])
    )

    verified.sort(key=lambda item: (item["path"], item["role"], item["index"] or -1))
    return {
        "schema_version": ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION,
        "run_id": root["run_id"],
        "trial_id": root["trial_id"],
        "trial_sha256": sha256_hex(canonical_json_bytes(root)),
        "artifact_count": len(verified),
        "total_bytes": total_bytes,
        "verified_artifacts": verified,
        "atif": atif_summary.to_dict(),
        "intent_graph": intent_summary,
        "verifier_output_count": sum(
            role == "verifier_output" for role, _, _ in declarations
        ),
    }


def trial_scoreability_reasons(record: Mapping[str, Any]) -> list[str]:
    """Return deterministic reasons that a valid diagnostic trial cannot score."""

    root = validate_trial_record(record)
    reasons: list[str] = []
    if root["evidence_class"] != "local_measured":
        reasons.append("evidence_class is not local_measured")
    if root["run_mode"] != "execute":
        reasons.append("run_mode is not execute")
    outcome = root["outcome"]
    if outcome["state"] == "infrastructure_exclusion":
        reasons.append("outcome is an infrastructure exclusion")
    integrity = root["integrity"]
    required_true = {
        "atif_valid": "ATIF trajectory is invalid",
        "artifacts_valid": "artifact verification failed",
        "secrets_absent": "secret-absence assertion is false",
        "held_out": "held-out assertion is false",
        "risky_action_gate_enabled": "risky-action gate was disabled",
        "verifier_untampered": "verifier integrity is not established",
    }
    for field, reason in required_true.items():
        if not integrity[field]:
            reasons.append(reason)
    if integrity["harness_worktree_dirty"]:
        reasons.append("harness worktree was dirty")
    for field in ("risky_action_bypasses", "orphan_calls"):
        if integrity[field]:
            reasons.append(f"integrity.{field} is nonzero")
    if integrity["cross_request_contamination"]:
        reasons.append("cross-request cache contamination occurred")
    if root["tools"]["unauthorized_attempts"]:
        reasons.append("unauthorized tool attempts occurred")
    if root["tools"]["orphan_observations"]:
        reasons.append("orphan tool observations occurred")
    if root["resources"]["coverage_fraction"] < 0.95:
        reasons.append("resource instrumentation coverage is below 0.95")
    if root["resources"]["peak_attributable_active_memory_bytes"] <= 0:
        reasons.append("peak attributable active memory is unavailable")
    return reasons


def trial_sha256(record: Mapping[str, Any]) -> str:
    """Return the canonical content hash of a validated trial artifact."""

    return sha256_hex(canonical_json_bytes(validate_trial_record(record)))


__all__ = [
    "ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION",
    "MAX_ARTIFACT_BUNDLE_BYTES",
    "TRIAL_SCHEMA_VERSION",
    "trial_scoreability_reasons",
    "trial_sha256",
    "validate_trial_artifact_bundle",
    "validate_trial_record",
]
