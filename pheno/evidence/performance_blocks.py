"""Deterministic independent-block performance comparison contracts.

``pheno.eval.performance-block.v1`` is deliberately an offline artifact.  It
does not execute a benchmark or infer statistical replication from task-level
rows.  Instead, it requires at least three independently scheduled, paired
run blocks and derives a deterministic confidence interval over their
block-level AVS/s speedups.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .redaction import contains_secret

PERFORMANCE_BLOCK_SCHEMA_VERSION = "pheno.eval.performance-block.v1"
BOOTSTRAP_METHOD = "paired-block-log-speedup-percentile-bootstrap-v1"
QUANTILE_METHOD = "Hyndman-Fan-type-7"
BOOTSTRAP_RESAMPLES = 10_000
MINIMUM_BLOCK_COUNT = 3
MINIMUM_SPEEDUP = 1.0

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARM_FIELDS = {
    "evidence_class",
    "suite_lock_sha256",
    "task_ids_sha256",
    "task_order_sha256",
    "load_profile_sha256",
    "schedule_manifest_sha256",
    "cell_id",
    "run_provenance_sha256",
    "aggregate_sha256",
    "avs_per_second",
}
_SHARED_PAIR_FIELDS = (
    "suite_lock_sha256",
    "task_ids_sha256",
    "task_order_sha256",
    "load_profile_sha256",
    "schedule_manifest_sha256",
)
_ROOT_FIELDS = {
    "schema_version",
    "comparison_id",
    "suite_lock_sha256",
    "task_ids_sha256",
    "load_profile_sha256",
    "treatment_cell_id",
    "baseline_cell_id",
    "minimum_speedup",
    "bootstrap_resamples",
    "blocks",
    "statistics",
    "promotion",
}
_STATISTIC_FIELDS = {
    "block_count",
    "baseline_avs_per_second_mean",
    "treatment_avs_per_second_mean",
    "geometric_mean_speedup",
    "paired_log_speedup_mean",
    "speedup_ci95",
    "bootstrap_seed_sha256",
    "method",
    "quantile_method",
}


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _exact(value: Any, fields: set[str], path: str) -> Mapping[str, Any]:
    obj = _mapping(value, path)
    missing = sorted(fields - set(obj))
    unknown = sorted(set(obj) - fields)
    if missing:
        raise ContractError(f"{path} is missing fields: {missing}")
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")
    return obj


def _sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ContractError(f"{path} must be a lowercase SHA-256 digest")
    return value


def _positive_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{path} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ContractError(f"{path} must be a finite positive number")
    return result


def task_ids_sha256(task_ids: Sequence[str]) -> str:
    """Hash a non-empty task set independently of caller ordering."""

    if isinstance(task_ids, (str, bytes)) or not isinstance(task_ids, Sequence):
        raise ContractError("task_ids must be an array")
    checked = []
    for index, task_id in enumerate(task_ids):
        if not isinstance(task_id, str) or not task_id.strip():
            raise ContractError(f"task_ids[{index}] must be a non-empty string")
        checked.append(task_id)
    if not checked or len(checked) != len(set(checked)):
        raise ContractError("task_ids must be non-empty and unique")
    return sha256_hex(canonical_json_bytes({"task_ids": sorted(checked)}))


def _validate_arm(value: Any, path: str) -> dict[str, Any]:
    arm = _exact(value, _ARM_FIELDS, path)
    if arm["evidence_class"] != "local_measured":
        raise ContractError(f"{path}.evidence_class must be local_measured")
    checked: dict[str, Any] = {"evidence_class": "local_measured"}
    for field in _ARM_FIELDS - {"evidence_class", "avs_per_second"}:
        checked[field] = _sha256(arm[field], f"{path}.{field}")
    checked["avs_per_second"] = _positive_number(
        arm["avs_per_second"], f"{path}.avs_per_second"
    )
    return checked


def performance_block_id(block: Mapping[str, Any]) -> str:
    """Return the content-derived ID for one validated paired block row."""

    row = _mapping(block, "block")
    allowed = {"baseline", "treatment", "block_id"}
    unknown = sorted(set(row) - allowed)
    if unknown:
        raise ContractError(f"block contains unknown fields: {unknown}")
    if "baseline" not in row or "treatment" not in row:
        raise ContractError("block requires baseline and treatment arms")
    baseline = _validate_arm(row["baseline"], "block.baseline")
    treatment = _validate_arm(row["treatment"], "block.treatment")
    return sha256_hex(
        canonical_json_bytes(
            {
                "schema_version": PERFORMANCE_BLOCK_SCHEMA_VERSION,
                "baseline": baseline,
                "treatment": treatment,
            }
        )
    )


def _validate_block(value: Any, index: int) -> dict[str, Any]:
    path = f"blocks[{index}]"
    block = _exact(value, {"block_id", "baseline", "treatment"}, path)
    baseline = _validate_arm(block["baseline"], f"{path}.baseline")
    treatment = _validate_arm(block["treatment"], f"{path}.treatment")
    for field in _SHARED_PAIR_FIELDS:
        if baseline[field] != treatment[field]:
            raise ContractError(f"{path} arms disagree on {field}")
    if baseline["cell_id"] == treatment["cell_id"]:
        raise ContractError(f"{path} baseline and treatment cell IDs must differ")
    checked = {
        "block_id": _sha256(block["block_id"], f"{path}.block_id"),
        "baseline": baseline,
        "treatment": treatment,
    }
    expected_id = performance_block_id(checked)
    if checked["block_id"] != expected_id:
        raise ContractError(f"{path}.block_id does not match the paired block content")
    return checked


def _quantile_type7(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ContractError("cannot compute a performance quantile without blocks")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _counter_draw(seed: bytes, replicate: int, draw: int, population: int) -> int:
    digest = hashlib.sha256(
        seed + replicate.to_bytes(8, "big") + draw.to_bytes(8, "big")
    ).digest()
    return int.from_bytes(digest[:8], "big") % population


def _bootstrap_log_speedup_ci(
    values: Sequence[float], *, seed: bytes
) -> dict[str, float]:
    means: list[float] = []
    population = len(values)
    for replicate in range(BOOTSTRAP_RESAMPLES):
        total = 0.0
        for draw in range(population):
            total += values[_counter_draw(seed, replicate, draw, population)]
        means.append(total / population)
    return {
        "lower": math.exp(_quantile_type7(means, 0.025)),
        "upper": math.exp(_quantile_type7(means, 0.975)),
    }


def _validated_blocks(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ContractError("blocks must be an array")
    if len(values) < MINIMUM_BLOCK_COUNT:
        raise ContractError(
            f"at least {MINIMUM_BLOCK_COUNT} independent paired blocks are required"
        )
    blocks = [_validate_block(value, index) for index, value in enumerate(values)]
    blocks.sort(key=lambda block: block["block_id"])
    block_ids = [block["block_id"] for block in blocks]
    if len(block_ids) != len(set(block_ids)):
        raise ContractError("performance blocks contain duplicate block IDs")

    shared_across_blocks = (
        "suite_lock_sha256",
        "task_ids_sha256",
        "load_profile_sha256",
    )
    for field in shared_across_blocks:
        values_for_field = {block["treatment"][field] for block in blocks}
        if len(values_for_field) != 1:
            raise ContractError(f"performance blocks disagree on {field}")
    if len({block["treatment"]["cell_id"] for block in blocks}) != 1:
        raise ContractError("performance blocks use different treatment cell IDs")
    if len({block["baseline"]["cell_id"] for block in blocks}) != 1:
        raise ContractError("performance blocks use different baseline cell IDs")

    schedules = [block["treatment"]["schedule_manifest_sha256"] for block in blocks]
    if len(schedules) != len(set(schedules)):
        raise ContractError("independent blocks require unique schedule manifests")
    run_hashes = [
        block[arm]["run_provenance_sha256"]
        for block in blocks
        for arm in ("baseline", "treatment")
    ]
    if len(run_hashes) != len(set(run_hashes)):
        raise ContractError("each block arm requires unique run provenance")
    aggregate_hashes = [
        block[arm]["aggregate_sha256"]
        for block in blocks
        for arm in ("baseline", "treatment")
    ]
    if len(aggregate_hashes) != len(set(aggregate_hashes)):
        raise ContractError("each block arm requires a unique aggregate")
    return blocks


def build_performance_block_record(
    blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the canonical summary for independent paired run blocks."""

    checked = _validated_blocks(list(blocks))
    first = checked[0]
    suite_lock = first["treatment"]["suite_lock_sha256"]
    task_hash = first["treatment"]["task_ids_sha256"]
    load_hash = first["treatment"]["load_profile_sha256"]
    treatment_cell = first["treatment"]["cell_id"]
    baseline_cell = first["baseline"]["cell_id"]
    comparison_identity = {
        "schema_version": PERFORMANCE_BLOCK_SCHEMA_VERSION,
        "suite_lock_sha256": suite_lock,
        "task_ids_sha256": task_hash,
        "load_profile_sha256": load_hash,
        "treatment_cell_id": treatment_cell,
        "baseline_cell_id": baseline_cell,
    }
    comparison_id = sha256_hex(canonical_json_bytes(comparison_identity))
    log_speedups = [
        math.log(block["treatment"]["avs_per_second"])
        - math.log(block["baseline"]["avs_per_second"])
        for block in checked
    ]
    seed = hashlib.sha256(
        canonical_json_bytes(
            {
                "method": BOOTSTRAP_METHOD,
                "comparison_id": comparison_id,
                "blocks": checked,
            }
        )
    ).digest()
    speedup_ci = _bootstrap_log_speedup_ci(log_speedups, seed=seed)
    promotion_reasons = []
    if speedup_ci["lower"] < MINIMUM_SPEEDUP:
        promotion_reasons.append(
            "paired block-level AVS/s lower 95% bound is below 1.0"
        )
    result = {
        "schema_version": PERFORMANCE_BLOCK_SCHEMA_VERSION,
        "comparison_id": comparison_id,
        "suite_lock_sha256": suite_lock,
        "task_ids_sha256": task_hash,
        "load_profile_sha256": load_hash,
        "treatment_cell_id": treatment_cell,
        "baseline_cell_id": baseline_cell,
        "minimum_speedup": MINIMUM_SPEEDUP,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "blocks": checked,
        "statistics": {
            "block_count": len(checked),
            "baseline_avs_per_second_mean": sum(
                block["baseline"]["avs_per_second"] for block in checked
            )
            / len(checked),
            "treatment_avs_per_second_mean": sum(
                block["treatment"]["avs_per_second"] for block in checked
            )
            / len(checked),
            "geometric_mean_speedup": math.exp(sum(log_speedups) / len(log_speedups)),
            "paired_log_speedup_mean": sum(log_speedups) / len(log_speedups),
            "speedup_ci95": speedup_ci,
            "bootstrap_seed_sha256": seed.hex(),
            "method": BOOTSTRAP_METHOD,
            "quantile_method": QUANTILE_METHOD,
        },
        "promotion": {
            "status": "fail" if promotion_reasons else "pass",
            "reasons": promotion_reasons,
        },
    }
    if contains_secret(result):
        raise ContractError("performance-block record contains a credential")
    return result


def validate_performance_block_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and recompute every persisted performance-block value."""

    root = dict(_exact(record, _ROOT_FIELDS, "performance_block"))
    if root["schema_version"] != PERFORMANCE_BLOCK_SCHEMA_VERSION:
        raise ContractError(
            f"schema_version must be {PERFORMANCE_BLOCK_SCHEMA_VERSION}"
        )
    _exact(root["statistics"], _STATISTIC_FIELDS, "performance_block.statistics")
    _exact(
        root["statistics"]["speedup_ci95"],
        {"lower", "upper"},
        "performance_block.statistics.speedup_ci95",
    )
    _exact(root["promotion"], {"status", "reasons"}, "performance_block.promotion")
    if contains_secret(root):
        raise ContractError("performance-block record contains a credential")
    expected = build_performance_block_record(root["blocks"])
    if root != expected:
        raise ContractError(
            "performance-block record does not match deterministic recomputation"
        )
    return root


def performance_block_sha256(record: Mapping[str, Any]) -> str:
    """Hash a validated canonical performance-block record."""

    return sha256_hex(canonical_json_bytes(validate_performance_block_record(record)))


__all__ = [
    "BOOTSTRAP_METHOD",
    "BOOTSTRAP_RESAMPLES",
    "MINIMUM_BLOCK_COUNT",
    "MINIMUM_SPEEDUP",
    "PERFORMANCE_BLOCK_SCHEMA_VERSION",
    "QUANTILE_METHOD",
    "build_performance_block_record",
    "performance_block_id",
    "performance_block_sha256",
    "task_ids_sha256",
    "validate_performance_block_record",
]
