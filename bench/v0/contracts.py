"""Strict validators for pheno.bench.v0 measured-benchmark artifacts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex

OBSERVATION_SCHEMA_VERSION = "pheno.bench.v0.observation.v1"
DERIVED_SCHEMA_VERSION = "pheno.bench.v0.derived.v1"
SIMULATION_SCHEMA_VERSION = "pheno.bench.v0.simulation.v1"
HYPOTHESIS_SCHEMA_VERSION = "pheno.bench.v0.hypothesis.v1"
SLICE_SCHEMA_VERSION = "pheno.bench.v0.slice.v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GPU_UUID = re.compile(
    r"^GPU-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_CASE_OUTCOMES = frozenset({"pass", "fail", "blocked"})
_EVIDENCE_CLASSES = frozenset(
    {"local_measured", "blocked", "derived", "simulated", "hypothesis"}
)

_PROVENANCE_FIELDS = frozenset(
    {
        "config_sha256",
        "model_sha256",
        "fixture_sha256",
        "environment_sha256",
        "phenocompose_run_sha256",
        "nvms_provenance_sha256",
    }
)

_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "observation_id",
        "case_id",
        "status",
        "evidence_class",
        "provenance",
        "gpu_uuids",
        "gpu_telemetry",
        "measurements",
        "block_reason",
    }
)
_DERIVED_FIELDS = frozenset(
    {
        "schema_version",
        "derived_id",
        "case_id",
        "evidence_class",
        "provenance",
        "source_observation_ids",
        "metrics",
    }
)
_SIMULATION_FIELDS = frozenset(
    {
        "schema_version",
        "simulation_id",
        "case_id",
        "evidence_class",
        "provenance",
        "model_spec_sha256",
        "inputs_sha256",
        "outputs",
    }
)
_HYPOTHESIS_FIELDS = frozenset(
    {
        "schema_version",
        "hypothesis_id",
        "case_id",
        "claim",
        "expected_direction",
        "linked_case_ids",
        "provenance",
    }
)
_SLICE_FIELDS = frozenset(
    {
        "schema_version",
        "slice_id",
        "suite",
        "provenance",
        "gpu_uuids",
        "cases",
        "observations",
        "derived_metrics",
        "simulations",
        "hypotheses",
        "summary",
    }
)
_GPU_TELEMETRY_FIELDS = frozenset(
    {
        "utilization_percent",
        "memory_used_mib",
        "memory_total_mib",
        "power_watts",
        "temperature_c",
    }
)


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


def _text(value: Any, path: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ContractError(
            f"{path} must be a non-empty string of at most {maximum} characters"
        )
    return value.strip()


def _gpu_uuid(value: Any, path: str) -> str:
    if not isinstance(value, str) or _GPU_UUID.fullmatch(value) is None:
        raise ContractError(f"{path} must be a canonical NVIDIA GPU UUID")
    return value


def _validate_provenance(value: Any, path: str) -> dict[str, str]:
    raw = _exact(value, _PROVENANCE_FIELDS, path)  # type: ignore[arg-type]
    return {
        field: _sha256(raw[field], f"{path}.{field}")
        for field in sorted(_PROVENANCE_FIELDS)
    }


def _validate_gpu_telemetry(
    value: Any, gpu_uuids: Sequence[str], path: str
) -> dict[str, dict[str, float | None]]:
    raw = _mapping(value, path)
    if set(raw) != set(gpu_uuids):
        raise ContractError(f"{path} keys must exactly match gpu_uuids")
    checked: dict[str, dict[str, float | None]] = {}
    for uuid in gpu_uuids:
        entry_path = f"{path}.{uuid}"
        entry = _exact(raw[uuid], _GPU_TELEMETRY_FIELDS, entry_path)  # type: ignore[arg-type]
        checked[uuid] = {}
        for field in sorted(_GPU_TELEMETRY_FIELDS):
            item = entry[field]
            if item is None:
                checked[uuid][field] = None
                continue
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ContractError(
                    f"{entry_path}.{field} must be a finite number or null"
                )
            number = float(item)
            if not math.isfinite(number):
                raise ContractError(
                    f"{entry_path}.{field} must be a finite number or null"
                )
            checked[uuid][field] = number
    return checked


def validate_observation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one measured or blocked observation artifact."""

    root = _exact(record, _OBSERVATION_FIELDS, "observation")  # type: ignore[arg-type]
    if root["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {OBSERVATION_SCHEMA_VERSION}")
    status = root["status"]
    if status not in {"measured", "blocked"}:
        raise ContractError("observation.status must be measured or blocked")
    evidence = root["evidence_class"]
    if evidence not in {"local_measured", "blocked"}:
        raise ContractError(
            "observation.evidence_class must be local_measured or blocked"
        )
    if status == "blocked":
        if evidence != "blocked":
            raise ContractError("blocked observations require evidence_class blocked")
        if root["measurements"] is not None:
            raise ContractError("blocked observations must not contain measurements")
        block_reason = _text(root["block_reason"], "observation.block_reason")
    else:
        if evidence != "local_measured":
            raise ContractError(
                "measured observations require evidence_class local_measured"
            )
        if root["block_reason"] is not None:
            raise ContractError("measured observations must not contain block_reason")
        if not isinstance(root["measurements"], Mapping):
            raise ContractError(
                "observation.measurements must be an object when measured"
            )
        block_reason = None
    provenance = _validate_provenance(root["provenance"], "observation.provenance")
    gpu_uuids_raw = root["gpu_uuids"]
    if not isinstance(gpu_uuids_raw, list) or not gpu_uuids_raw:
        raise ContractError("observation.gpu_uuids must be a non-empty array")
    gpu_uuids = [
        _gpu_uuid(item, f"observation.gpu_uuids[{index}]")
        for index, item in enumerate(gpu_uuids_raw)
    ]
    if len(gpu_uuids) != len(set(gpu_uuids)):
        raise ContractError("observation.gpu_uuids must be unique")
    gpu_telemetry = _validate_gpu_telemetry(
        root["gpu_telemetry"], gpu_uuids, "observation.gpu_telemetry"
    )
    case_id = _text(root["case_id"], "observation.case_id")
    observation_id = _sha256(root["observation_id"], "observation.observation_id")
    identity = {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "case_id": case_id,
        "status": status,
        "evidence_class": evidence,
        "provenance": provenance,
        "gpu_uuids": gpu_uuids,
        "gpu_telemetry": gpu_telemetry,
        "measurements": root["measurements"] if status == "measured" else None,
        "block_reason": block_reason,
    }
    expected_id = sha256_hex(canonical_json_bytes(identity))
    if observation_id != expected_id:
        raise ContractError("observation.observation_id does not match content hash")
    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "observation_id": observation_id,
        "case_id": case_id,
        "status": status,
        "evidence_class": evidence,
        "provenance": provenance,
        "gpu_uuids": gpu_uuids,
        "gpu_telemetry": gpu_telemetry,
        "measurements": identity["measurements"],
        "block_reason": block_reason,
    }


def validate_derived_metric(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one derived metric artifact."""

    root = _exact(record, _DERIVED_FIELDS, "derived")  # type: ignore[arg-type]
    if root["schema_version"] != DERIVED_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {DERIVED_SCHEMA_VERSION}")
    if root["evidence_class"] != "derived":
        raise ContractError("derived.evidence_class must be derived")
    provenance = _validate_provenance(root["provenance"], "derived.provenance")
    source_ids = root["source_observation_ids"]
    if not isinstance(source_ids, list) or not source_ids:
        raise ContractError("derived.source_observation_ids must be a non-empty array")
    checked_sources = [
        _sha256(item, f"derived.source_observation_ids[{index}]")
        for index, item in enumerate(source_ids)
    ]
    if len(checked_sources) != len(set(checked_sources)):
        raise ContractError("derived.source_observation_ids must be unique")
    if not isinstance(root["metrics"], Mapping):
        raise ContractError("derived.metrics must be an object")
    case_id = _text(root["case_id"], "derived.case_id")
    derived_id = _sha256(root["derived_id"], "derived.derived_id")
    identity = {
        "schema_version": DERIVED_SCHEMA_VERSION,
        "case_id": case_id,
        "evidence_class": "derived",
        "provenance": provenance,
        "source_observation_ids": checked_sources,
        "metrics": dict(root["metrics"]),
    }
    expected_id = sha256_hex(canonical_json_bytes(identity))
    if derived_id != expected_id:
        raise ContractError("derived.derived_id does not match content hash")
    return {
        "schema_version": DERIVED_SCHEMA_VERSION,
        "derived_id": derived_id,
        "case_id": case_id,
        "evidence_class": "derived",
        "provenance": provenance,
        "source_observation_ids": checked_sources,
        "metrics": identity["metrics"],
    }


def validate_simulation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one simulation artifact (never promotable as measured)."""

    root = _exact(record, _SIMULATION_FIELDS, "simulation")  # type: ignore[arg-type]
    if root["schema_version"] != SIMULATION_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SIMULATION_SCHEMA_VERSION}")
    if root["evidence_class"] != "simulated":
        raise ContractError("simulation.evidence_class must be simulated")
    provenance = _validate_provenance(root["provenance"], "simulation.provenance")
    if not isinstance(root["outputs"], Mapping):
        raise ContractError("simulation.outputs must be an object")
    case_id = _text(root["case_id"], "simulation.case_id")
    simulation_id = _sha256(root["simulation_id"], "simulation.simulation_id")
    identity = {
        "schema_version": SIMULATION_SCHEMA_VERSION,
        "case_id": case_id,
        "evidence_class": "simulated",
        "provenance": provenance,
        "model_spec_sha256": _sha256(
            root["model_spec_sha256"], "simulation.model_spec_sha256"
        ),
        "inputs_sha256": _sha256(root["inputs_sha256"], "simulation.inputs_sha256"),
        "outputs": dict(root["outputs"]),
    }
    expected_id = sha256_hex(canonical_json_bytes(identity))
    if simulation_id != expected_id:
        raise ContractError("simulation.simulation_id does not match content hash")
    return {
        "schema_version": SIMULATION_SCHEMA_VERSION,
        "simulation_id": simulation_id,
        "case_id": case_id,
        "evidence_class": "simulated",
        "provenance": provenance,
        "model_spec_sha256": identity["model_spec_sha256"],
        "inputs_sha256": identity["inputs_sha256"],
        "outputs": identity["outputs"],
    }


def validate_hypothesis(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one hypothesis artifact."""

    root = _exact(record, _HYPOTHESIS_FIELDS, "hypothesis")  # type: ignore[arg-type]
    if root["schema_version"] != HYPOTHESIS_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {HYPOTHESIS_SCHEMA_VERSION}")
    direction = root["expected_direction"]
    if direction not in {"increase", "decrease", "no_change"}:
        raise ContractError("hypothesis.expected_direction is invalid")
    linked = root["linked_case_ids"]
    if not isinstance(linked, list) or not linked:
        raise ContractError("hypothesis.linked_case_ids must be a non-empty array")
    linked_cases = [
        _text(item, f"hypothesis.linked_case_ids[{index}]")
        for index, item in enumerate(linked)
    ]
    provenance = _validate_provenance(root["provenance"], "hypothesis.provenance")
    case_id = _text(root["case_id"], "hypothesis.case_id")
    claim = _text(root["claim"], "hypothesis.claim", maximum=1024)
    hypothesis_id = _sha256(root["hypothesis_id"], "hypothesis.hypothesis_id")
    identity = {
        "schema_version": HYPOTHESIS_SCHEMA_VERSION,
        "case_id": case_id,
        "claim": claim,
        "expected_direction": direction,
        "linked_case_ids": linked_cases,
        "provenance": provenance,
    }
    expected_id = sha256_hex(canonical_json_bytes(identity))
    if hypothesis_id != expected_id:
        raise ContractError("hypothesis.hypothesis_id does not match content hash")
    return {
        "schema_version": HYPOTHESIS_SCHEMA_VERSION,
        "hypothesis_id": hypothesis_id,
        "case_id": case_id,
        "claim": claim,
        "expected_direction": direction,
        "linked_case_ids": linked_cases,
        "provenance": provenance,
    }


def _validate_slice_case(
    value: Any, index: int, gpu_uuids: Sequence[str]
) -> dict[str, Any]:
    path = f"slice.cases[{index}]"
    allowed = {"case_id", "outcome", "observation_id", "derived_id", "hypothesis_id"}
    obj = _mapping(value, path)
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")
    for required in ("case_id", "outcome"):
        if required not in obj:
            raise ContractError(f"{path} is missing {required}")
    case_id = _text(obj["case_id"], f"{path}.case_id")
    outcome = obj["outcome"]
    if outcome not in _CASE_OUTCOMES:
        raise ContractError(f"{path}.outcome must be pass, fail, or blocked")
    observation_id = obj.get("observation_id")
    if outcome == "blocked":
        if observation_id is None:
            raise ContractError(
                f"{path} blocked cases require a blocked observation_id"
            )
        _sha256(observation_id, f"{path}.observation_id")
    elif observation_id is None:
        raise ContractError(f"{path} pass/fail cases require observation_id")
    else:
        _sha256(observation_id, f"{path}.observation_id")
    derived_id = obj.get("derived_id")
    if derived_id is not None:
        _sha256(derived_id, f"{path}.derived_id")
    hypothesis_id = obj.get("hypothesis_id")
    if hypothesis_id is not None:
        _sha256(hypothesis_id, f"{path}.hypothesis_id")
    return {
        "case_id": case_id,
        "outcome": outcome,
        "observation_id": observation_id,
        "derived_id": derived_id,
        "hypothesis_id": hypothesis_id,
    }


def validate_slice_artifact(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a full V0 first-slice artifact."""

    root = _exact(record, _SLICE_FIELDS, "slice")  # type: ignore[arg-type]
    if root["schema_version"] != SLICE_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SLICE_SCHEMA_VERSION}")
    suite = _mapping(root["suite"], "slice.suite")
    for field in ("name", "revision"):
        if field not in suite:
            raise ContractError(f"slice.suite is missing {field}")
    suite_name = _text(suite["name"], "slice.suite.name")
    suite_revision = _text(suite["revision"], "slice.suite.revision")
    provenance = _validate_provenance(root["provenance"], "slice.provenance")
    gpu_uuids_raw = root["gpu_uuids"]
    if not isinstance(gpu_uuids_raw, list) or not gpu_uuids_raw:
        raise ContractError("slice.gpu_uuids must be a non-empty array")
    gpu_uuids = [
        _gpu_uuid(item, f"slice.gpu_uuids[{index}]")
        for index, item in enumerate(gpu_uuids_raw)
    ]
    if len(gpu_uuids) != len(set(gpu_uuids)):
        raise ContractError("slice.gpu_uuids must be unique")
    if not isinstance(root["cases"], list) or not root["cases"]:
        raise ContractError("slice.cases must be a non-empty array")
    cases = [
        _validate_slice_case(item, index, gpu_uuids)
        for index, item in enumerate(root["cases"])
    ]
    observations = [validate_observation(item) for item in root["observations"]]
    derived_metrics = [
        validate_derived_metric(item) for item in root["derived_metrics"]
    ]
    simulations = [validate_simulation(item) for item in root["simulations"]]
    hypotheses = [validate_hypothesis(item) for item in root["hypotheses"]]
    summary = _mapping(root["summary"], "slice.summary")
    for field in ("measured_count", "blocked_count", "pass_count", "fail_count"):
        if field not in summary:
            raise ContractError(f"slice.summary is missing {field}")
    obs_by_id = {item["observation_id"]: item for item in observations}
    derived_by_id = {item["derived_id"]: item for item in derived_metrics}
    hyp_by_id = {item["hypothesis_id"]: item for item in hypotheses}
    for case in cases:
        if (
            case["observation_id"] is not None
            and case["observation_id"] not in obs_by_id
        ):
            raise ContractError(
                f"slice case {case['case_id']} references unknown observation"
            )
        if case["observation_id"] is not None:
            obs = obs_by_id[case["observation_id"]]
            if case["outcome"] == "blocked" and obs["status"] != "blocked":
                raise ContractError(
                    f"slice case {case['case_id']} is blocked but observation is not"
                )
            if case["outcome"] in {"pass", "fail"} and obs["status"] != "measured":
                raise ContractError(
                    f"slice case {case['case_id']} expects measured observation"
                )
        if case["derived_id"] is not None and case["derived_id"] not in derived_by_id:
            raise ContractError(
                f"slice case {case['case_id']} references unknown derived metric"
            )
        if case["hypothesis_id"] is not None and case["hypothesis_id"] not in hyp_by_id:
            raise ContractError(
                f"slice case {case['case_id']} references unknown hypothesis"
            )
    for obs in observations:
        if set(obs["gpu_uuids"]) != set(gpu_uuids):
            raise ContractError(
                "slice observation gpu_uuids disagree with slice gpu_uuids"
            )
        if obs["status"] == "blocked" and obs["evidence_class"] != "blocked":
            raise ContractError("blocked observations must not masquerade as measured")
    slice_id = _sha256(root["slice_id"], "slice.slice_id")
    identity = {
        "schema_version": SLICE_SCHEMA_VERSION,
        "suite": {"name": suite_name, "revision": suite_revision},
        "provenance": provenance,
        "gpu_uuids": gpu_uuids,
        "cases": cases,
        "observations": observations,
        "derived_metrics": derived_metrics,
        "simulations": simulations,
        "hypotheses": hypotheses,
        "summary": {
            "measured_count": int(summary["measured_count"]),
            "blocked_count": int(summary["blocked_count"]),
            "pass_count": int(summary["pass_count"]),
            "fail_count": int(summary["fail_count"]),
        },
    }
    expected_id = sha256_hex(canonical_json_bytes(identity))
    if slice_id != expected_id:
        raise ContractError("slice.slice_id does not match content hash")
    return {
        "schema_version": SLICE_SCHEMA_VERSION,
        "slice_id": slice_id,
        **identity,
    }


__all__ = [
    "DERIVED_SCHEMA_VERSION",
    "HYPOTHESIS_SCHEMA_VERSION",
    "OBSERVATION_SCHEMA_VERSION",
    "SIMULATION_SCHEMA_VERSION",
    "SLICE_SCHEMA_VERSION",
    "validate_derived_metric",
    "validate_hypothesis",
    "validate_observation",
    "validate_simulation",
    "validate_slice_artifact",
]
