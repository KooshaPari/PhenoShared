"""Unified benchmark-result contract and north-star derivation.

The contract separates scoreability/integrity from promotion policy.  A fast
but unsafe, synthetic, unpinned, or unverifiable run remains useful diagnostic
data but cannot enter the model/runtime Pareto frontier.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .contracts import ContractError
from .redaction import contains_secret

BENCHMARK_SCHEMA_VERSION = "pheno.benchmark.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"planned", "running", "complete", "failed", "invalid"}
_REQUIRED_FACTOR_KEYS = {
    "model_record_id",
    "artifact_revision",
    "quantization",
    "runtime",
    "runtime_revision",
    "parser_revision",
    "template_revision",
    "context_tokens",
    "cache_mode",
    "decode_mode",
    "concurrency",
    "role",
    "seed",
    "device",
}


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _timestamp(value: Any, path: str) -> None:
    text = _text(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{path} must include a timezone")


def _number(
    value: Any,
    path: str,
    *,
    minimum: float = 0.0,
    maximum: float | None = None,
    integer: bool = False,
) -> float:
    valid = isinstance(value, int) if integer else isinstance(value, (int, float))
    if isinstance(value, bool) or not valid:
        expected = "integer" if integer else "number"
        raise ContractError(f"{path} must be a finite {expected}")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ContractError(f"{path} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ContractError(f"{path} must be <= {maximum}")
    return result


def _digest(value: Any, path: str) -> None:
    text = _text(value, path)
    if not _SHA256.fullmatch(text):
        raise ContractError(f"{path} must be a lowercase SHA-256 digest")


def _optional_rate(container: Mapping[str, Any], key: str, path: str) -> None:
    if key in container and container[key] is not None:
        _number(container[key], f"{path}.{key}", maximum=1.0)


def validate_benchmark_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the structural benchmark contract and basic count invariants."""

    root = _object(record, "record")
    if root.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {BENCHMARK_SCHEMA_VERSION!r}")
    _text(root.get("run_id"), "run_id")
    _timestamp(root.get("created_at"), "created_at")
    status = _text(root.get("status"), "status")
    if status not in _STATUSES:
        raise ContractError(f"status must be one of {sorted(_STATUSES)}")

    suite = _object(root.get("suite"), "suite")
    _text(suite.get("name"), "suite.name")
    _text(suite.get("revision"), "suite.revision")
    _digest(suite.get("task_manifest_sha256"), "suite.task_manifest_sha256")
    task_count = _number(
        suite.get("task_count"), "suite.task_count", minimum=1, integer=True
    )
    _number(
        suite.get("attempts_per_task"),
        "suite.attempts_per_task",
        minimum=1,
        integer=True,
    )

    provenance = _object(root.get("provenance"), "provenance")
    _text(provenance.get("harness_revision"), "provenance.harness_revision")
    if not isinstance(provenance.get("worktree_dirty"), bool):
        raise ContractError("provenance.worktree_dirty must be boolean")
    for field in (
        "config_sha256",
        "tool_schema_sha256",
        "agent_config_sha256",
        "evaluator_sha256",
    ):
        _digest(provenance.get(field), f"provenance.{field}")
    artifacts = _object(
        provenance.get("verifier_artifacts", {}), "provenance.verifier_artifacts"
    )
    for name, digest in artifacts.items():
        _text(name, "provenance.verifier_artifacts key")
        _digest(digest, f"provenance.verifier_artifacts.{name}")

    factors = _object(root.get("factors"), "factors")
    missing = sorted(_REQUIRED_FACTOR_KEYS - set(factors))
    if missing:
        raise ContractError(f"factors is missing required keys: {missing}")
    for field in _REQUIRED_FACTOR_KEYS - {"context_tokens", "concurrency", "seed"}:
        _text(factors.get(field), f"factors.{field}")
    _number(
        factors.get("context_tokens"), "factors.context_tokens", minimum=1, integer=True
    )
    _number(factors.get("concurrency"), "factors.concurrency", minimum=1, integer=True)
    _number(factors.get("seed"), "factors.seed", minimum=0, integer=True)

    integrity = _object(root.get("integrity"), "integrity")
    for field in (
        "no_training_on_eval_tasks",
        "risky_action_gate_enabled",
        "verifier_untampered",
        "secrets_redacted",
        "synthetic",
    ):
        if not isinstance(integrity.get(field), bool):
            raise ContractError(f"integrity.{field} must be boolean")
    _number(
        integrity.get("risky_action_bypass_count"),
        "integrity.risky_action_bypass_count",
        integer=True,
    )
    _number(
        integrity.get("tool_observation_correlation"),
        "integrity.tool_observation_correlation",
        maximum=1.0,
    )
    _number(
        integrity.get("infra_exclusion_rate"),
        "integrity.infra_exclusion_rate",
        maximum=1.0,
    )

    metrics_value = root.get("metrics")
    if status == "complete" and metrics_value is None:
        raise ContractError("complete runs require metrics")
    if metrics_value is not None:
        metrics = _object(metrics_value, "metrics")
        quality = _object(metrics.get("quality"), "metrics.quality")
        accepted = _number(
            quality.get("accepted_verified_steps"),
            "metrics.quality.accepted_verified_steps",
            integer=True,
        )
        attempts = _number(
            quality.get("task_attempts"),
            "metrics.quality.task_attempts",
            minimum=1,
            integer=True,
        )
        successes = _number(
            quality.get("task_successes"),
            "metrics.quality.task_successes",
            integer=True,
        )
        if successes > attempts or attempts < task_count:
            raise ContractError(
                "task success/attempt counts contradict the suite manifest"
            )
        if accepted < successes:
            raise ContractError(
                "accepted_verified_steps cannot be below task_successes"
            )
        for field in ("pass_at_1", "pass_at_k", "ci95_lower", "ci95_upper"):
            _optional_rate(quality, field, "metrics.quality")

        latency = _object(metrics.get("latency"), "metrics.latency")
        _number(
            latency.get("wall_seconds"),
            "metrics.latency.wall_seconds",
            minimum=1e-12,
        )
        for field in (
            "ttft_p50_ms",
            "ttft_p95_ms",
            "ttft_p99_ms",
            "itl_p50_ms",
            "itl_p95_ms",
            "itl_p99_ms",
        ):
            if field in latency and latency[field] is not None:
                _number(latency[field], f"metrics.latency.{field}")

        resources = _object(metrics.get("resources"), "metrics.resources")
        _number(
            resources.get("peak_active_gb"),
            "metrics.resources.peak_active_gb",
            minimum=1e-12,
        )
        for field in ("energy_wh", "average_power_watts", "peak_power_watts"):
            if field in resources and resources[field] is not None:
                _number(resources[field], f"metrics.resources.{field}")

        cost = _object(metrics.get("cost"), "metrics.cost")
        _number(cost.get("amortized_usd"), "metrics.cost.amortized_usd")

        tools = _object(metrics.get("tools", {}), "metrics.tools")
        for field in (
            "schema_valid_rate",
            "exact_rate",
            "wrong_tool_rate",
            "duplicate_loop_rate",
            "recovery_rate",
        ):
            _optional_rate(tools, field, "metrics.tools")
        for group in ("cache", "drift", "concurrency", "thermals", "speculation"):
            _object(metrics.get(group, {}), f"metrics.{group}")

    if contains_secret(root):
        raise ContractError(
            "benchmark record contains a token, credential, or authorization value"
        )
    return dict(root)


def scoreability_reasons(record: Mapping[str, Any]) -> list[str]:
    """Return hard reasons a structurally valid run cannot enter comparisons."""

    validated = validate_benchmark_record(record)
    reasons: list[str] = []
    if validated["status"] != "complete":
        reasons.append("run is not complete")
    integrity = validated["integrity"]
    if integrity["synthetic"]:
        reasons.append("synthetic run")
    for field in (
        "no_training_on_eval_tasks",
        "risky_action_gate_enabled",
        "verifier_untampered",
        "secrets_redacted",
    ):
        if not integrity[field]:
            reasons.append(f"integrity.{field} is false")
    if integrity["risky_action_bypass_count"] != 0:
        reasons.append("risky-action bypass observed")
    if integrity["tool_observation_correlation"] != 1.0:
        reasons.append("tool calls and observations are not fully correlated")
    if integrity["infra_exclusion_rate"] > 0.02:
        reasons.append("infrastructure exclusion rate exceeds 2%")
    provenance = validated["provenance"]
    if provenance["worktree_dirty"]:
        reasons.append("harness worktree is dirty")
    if not provenance["verifier_artifacts"]:
        reasons.append("verifier artifact hashes are missing")
    metrics = validated.get("metrics")
    if metrics is not None and metrics["cost"]["amortized_usd"] <= 0:
        reasons.append("amortized cost must be positive for the /$ comparison")
    return reasons


def derive_efficiency(record: Mapping[str, Any]) -> dict[str, float | None]:
    """Publish the north-star components and an explicitly secondary composite."""

    validated = validate_benchmark_record(record)
    metrics = validated.get("metrics")
    if metrics is None:
        return {
            "avs_per_second": None,
            "avs_per_second_per_peak_gb": None,
            "avs_per_dollar": None,
            "combined_avs_per_second_gb_dollar": None,
        }
    accepted = float(metrics["quality"]["accepted_verified_steps"])
    wall = float(metrics["latency"]["wall_seconds"])
    memory = float(metrics["resources"]["peak_active_gb"])
    cost = float(metrics["cost"]["amortized_usd"])
    return {
        "avs_per_second": accepted / wall,
        "avs_per_second_per_peak_gb": accepted / wall / memory,
        "avs_per_dollar": accepted / cost if cost > 0 else None,
        "combined_avs_per_second_gb_dollar": (
            accepted / wall / memory / cost if cost > 0 else None
        ),
    }


def promotion_reasons(record: Mapping[str, Any]) -> list[str]:
    """Apply default stability gates after scoreability checks."""

    validated = validate_benchmark_record(record)
    reasons = scoreability_reasons(validated)
    metrics = validated.get("metrics")
    if metrics is None:
        return reasons
    tools = metrics.get("tools", {})
    thresholds = {
        "schema_valid_rate": (0.995, "schema-valid tool-call rate below 99.5%"),
        "exact_rate": (0.995, "tool exactness below 99.5%"),
        "recovery_rate": (0.95, "failure-recovery rate below 95%"),
    }
    for field, (minimum, message) in thresholds.items():
        if tools.get(field) is not None and tools[field] < minimum:
            reasons.append(message)
    if tools.get("wrong_tool_rate") is not None and tools["wrong_tool_rate"] > 0.01:
        reasons.append("wrong-tool rate exceeds 1%")
    if (
        tools.get("duplicate_loop_rate") is not None
        and tools["duplicate_loop_rate"] > 0.01
    ):
        reasons.append("duplicate/loop rate exceeds 1%")
    concurrency = metrics.get("concurrency", {})
    if (
        concurrency.get("successful_request_rate") is not None
        and concurrency["successful_request_rate"] < 0.99
    ):
        reasons.append("successful-request rate below 99%")
    if any(
        concurrency.get(field, 0)
        for field in ("oom_count", "restart_count", "deadlock_count")
    ):
        reasons.append("OOM, restart, or deadlock observed")
    thermals = metrics.get("thermals", {})
    if thermals.get("throttled") is True:
        reasons.append("thermal throttling observed")
    if (
        thermals.get("throughput_retention_30m") is not None
        and thermals["throughput_retention_30m"] < 0.90
    ):
        reasons.append("30-minute throughput retention below 90%")
    comparison = metrics.get("comparison", {})
    if (
        comparison.get("quality_delta_ci95_lower") is not None
        and comparison["quality_delta_ci95_lower"] < -0.02
    ):
        reasons.append(
            "quality non-inferiority lower bound is below -2 percentage points"
        )
    return reasons


__all__ = [
    "BENCHMARK_SCHEMA_VERSION",
    "derive_efficiency",
    "promotion_reasons",
    "scoreability_reasons",
    "validate_benchmark_record",
]
