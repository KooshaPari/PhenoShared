"""Review-only heterogeneous model/runtime tournament validation and deltas."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

from .contracts import ContractError

TOURNAMENT_SCHEMA_VERSION = "pheno.tournament.v1"
_TIERS = {"specialist", "fast", "worker", "escalation"}
_ARCHITECTURES = {"specialist", "dense", "moe"}
_STATUSES = {"candidate", "locked_control"}
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_MOBILE_LEASE_FIELDS = {
    "job_id",
    "lease_id",
    "model_hash",
    "artifact_hash",
    "runtime_hash",
    "config_hash",
    "deadline",
    "max_context_tokens",
    "max_output_tokens",
    "nonce",
}


def _timestamp_key(value: Any) -> datetime:
    """Order contract timestamps by instant rather than ISO-8601 spelling."""

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError("registry retrieved_at must include a timezone")
    return parsed.astimezone(UTC)


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _strings(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ContractError(f"{path} must be an array")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ContractError(f"{path}[{index}] must be a non-empty string")
        result.append(item)
    return result


def validate_tournament(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a closed review-only tournament configuration."""
    root = _object(config, "tournament")
    if root.get("schema_version") != TOURNAMENT_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {TOURNAMENT_SCHEMA_VERSION}")
    try:
        date.fromisoformat(str(root.get("cutoff_date")))
    except ValueError as exc:
        raise ContractError("cutoff_date must be YYYY-MM-DD") from exc
    policy = _object(root.get("policy"), "policy")
    required_false = (
        "allow_model_artifact_download",
        "allow_server_launch",
        "allow_phone_install",
        "allow_mac_mutation",
        "allow_1080ti_install",
        "mutate_adr_locked_shortlist",
    )
    if policy.get("review_only") is not True:
        raise ContractError("policy.review_only must be true")
    for field in required_false:
        if policy.get(field) is not False:
            raise ContractError(f"policy.{field} must be false")
    ceiling = policy.get("max_total_parameters")
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 1:
        raise ContractError("policy.max_total_parameters must be positive")
    _strings(policy.get("north_star"), "policy.north_star", allow_empty=False)

    runtime_pins = _object(root.get("runtime_pins"), "runtime_pins")
    if not runtime_pins:
        raise ContractError("runtime_pins cannot be empty")
    for runtime, raw in runtime_pins.items():
        if not isinstance(runtime, str) or not runtime:
            raise ContractError("runtime pin names must be strings")
        pin = _object(raw, f"runtime_pins.{runtime}")
        _strings([pin.get("version"), pin.get("channel")], f"runtime_pins.{runtime}")
        commit = pin.get("commit")
        if commit is not None and not _COMMIT_RE.fullmatch(str(commit)):
            raise ContractError(
                f"runtime_pins.{runtime}.commit must be a full 40-hex SHA"
            )
        if "commit" in str(pin["channel"]):
            immutable = str(commit or pin["version"])
            if not _COMMIT_RE.fullmatch(immutable):
                raise ContractError(
                    f"runtime_pins.{runtime} commit channel requires a full 40-hex SHA"
                )

    kernel_pins = _object(root.get("kernel_substrate_pins"), "kernel_substrate_pins")
    for substrate, raw in kernel_pins.items():
        pin = _object(raw, f"kernel_substrate_pins.{substrate}")
        _strings(
            [pin.get("version"), pin.get("channel")],
            f"kernel_substrate_pins.{substrate}",
        )

    mobile = _object(root.get("mobile_worker_policy"), "mobile_worker_policy")
    if mobile.get("trust_class") != "untrusted_burst_worker":
        raise ContractError("mobile workers must remain untrusted burst workers")
    required_mobile_true = (
        "coordinator_authoritative",
        "foreground_visible",
        "user_initiated",
        "outbound_only",
        "no_cloud_handoff",
        "no_tool_execution",
        "no_workload_secrets",
        "external_vendor_telemetry_disabled",
        "authenticated_transport",
        "device_scoped_short_lived_transport_credentials",
        "transport_credentials_excluded_from_lease_payload",
        "replay_protected_leases",
        "content_hashed_result_bundle",
    )
    for field in required_mobile_true:
        if mobile.get(field) is not True:
            raise ContractError(f"mobile_worker_policy.{field} must be true")
    for field in ("allowed_tasks", "forbidden_inputs", "required_telemetry"):
        _strings(mobile.get(field), f"mobile_worker_policy.{field}", allow_empty=False)
    durations = mobile.get("sustained_probe_seconds")
    if durations != [300, 900, 1800]:
        raise ContractError("mobile sustained probes must be 5, 15, and 30 minutes")
    headroom = mobile.get("initial_memory_headroom_fraction")
    if not isinstance(headroom, (int, float)) or isinstance(headroom, bool):
        raise ContractError("mobile memory headroom must be numeric")
    if not 0.25 <= float(headroom) <= 0.35:
        raise ContractError(
            "mobile memory headroom must start between 25 and 35 percent"
        )
    lease = _object(mobile.get("lease"), "mobile_worker_policy.lease")
    checkpoint = lease.get("checkpoint_max_seconds")
    if (
        not isinstance(checkpoint, int)
        or isinstance(checkpoint, bool)
        or not 1 <= checkpoint <= 60
    ):
        raise ContractError("mobile checkpoint interval must be 1-60 seconds")
    lease_fields = set(
        _strings(
            lease.get("required_fields"),
            "mobile_worker_policy.lease.required_fields",
            allow_empty=False,
        )
    )
    missing_lease_fields = sorted(_MOBILE_LEASE_FIELDS - lease_fields)
    if missing_lease_fields:
        raise ContractError(
            f"mobile lease is missing mandatory fields: {missing_lease_fields}"
        )

    devices = _object(root.get("devices"), "devices")
    if set(devices) != {
        "rtx_3090_ti",
        "m1_pro_16gb",
        "galaxy_s21_ultra",
        "iphone_17_pro_max",
        "gtx_1080_ti",
    }:
        raise ContractError("device set does not match the requested fleet")
    for name, raw in devices.items():
        device = _object(raw, f"devices.{name}")
        if not isinstance(device.get("available"), bool):
            raise ContractError(f"devices.{name}.available must be boolean")
        if not isinstance(device.get("install_authorized"), bool):
            raise ContractError(f"devices.{name}.install_authorized must be boolean")
        if "probe_authorized" in device and not isinstance(
            device.get("probe_authorized"), bool
        ):
            raise ContractError(f"devices.{name}.probe_authorized must be boolean")
        runtimes = _strings(device.get("runtimes"), f"devices.{name}.runtimes")
        if not set(runtimes).issubset(runtime_pins):
            raise ContractError(f"devices.{name}.runtimes contains an unpinned runtime")
        backends = _strings(device.get("backends", []), f"devices.{name}.backends")
        if set(runtimes) & {"onnx", "vulkan", "metal", "opencl", "coreml", "wgpu"}:
            raise ContractError(
                f"devices.{name}.runtimes conflates a backend with a runtime"
            )
        if set(backends) & set(runtimes):
            raise ContractError(
                f"devices.{name} backend/runtime names must be distinct"
            )
        default = device.get("default_runtime")
        if default is not None and default not in runtimes:
            raise ContractError(f"devices.{name}.default_runtime is not in runtimes")
        _strings(
            device.get("constraints"), f"devices.{name}.constraints", allow_empty=False
        )
    if devices["m1_pro_16gb"].get("remote_mutation_authorized") is not False:
        raise ContractError("M1 Pro remote mutation must remain unauthorized")
    for name in ("m1_pro_16gb", "galaxy_s21_ultra", "iphone_17_pro_max"):
        if devices[name].get("install_authorized") is not False:
            raise ContractError(f"devices.{name}.install_authorized must remain false")
    pascal = devices["gtx_1080_ti"]
    if pascal.get("available") is True and pascal.get("probe_authorized") is not True:
        raise ContractError("available 1080 Ti requires explicit probe authorization")
    if (
        pascal.get("available") is True
        and pascal.get("install_authorized") is not False
    ):
        raise ContractError(
            "1080 Ti installation must remain separately gated during probing"
        )

    candidates = root.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ContractError("candidates must be a non-empty array")
    ids: set[str] = set()
    controls: set[str] = set()
    for index, raw in enumerate(candidates):
        item = _object(raw, f"candidates[{index}]")
        candidate_id = str(item.get("id") or "")
        if not candidate_id or candidate_id in ids:
            raise ContractError("candidate ids must be unique and non-empty")
        ids.add(candidate_id)
        status = item.get("status")
        if status not in _STATUSES:
            raise ContractError(f"candidate {candidate_id} has invalid status")
        if status == "locked_control":
            controls.add(candidate_id)
        tier = item.get("tier")
        architecture = item.get("architecture")
        if tier not in _TIERS or architecture not in _ARCHITECTURES:
            raise ContractError(
                f"candidate {candidate_id} has invalid tier/architecture"
            )
        total = item.get("total_parameters")
        active = item.get("active_parameters")
        if not isinstance(total, int) or not isinstance(active, int) or total < 1:
            raise ContractError(
                f"candidate {candidate_id} parameter counts are invalid"
            )
        if active < 1 or active > total or total > ceiling:
            raise ContractError(f"candidate {candidate_id} violates parameter bounds")
        if total < 500_000_000 and tier != "specialist":
            raise ContractError(
                f"sub-0.5B candidate {candidate_id} must be a specialist"
            )
        lanes = _strings(
            item.get("lanes"), f"candidate {candidate_id}.lanes", allow_empty=False
        )
        if not set(lanes).issubset(devices):
            raise ContractError(f"candidate {candidate_id} names an unknown device")
        candidate_runtimes = _strings(
            item.get("runtimes"),
            f"candidate {candidate_id}.runtimes",
            allow_empty=False,
        )
        if not set(candidate_runtimes).issubset(runtime_pins):
            raise ContractError(f"candidate {candidate_id} names an unpinned runtime")
        for lane in lanes:
            if not set(candidate_runtimes) & set(devices[lane]["runtimes"]):
                raise ContractError(
                    f"candidate {candidate_id} has no supported runtime for lane {lane}"
                )
        _strings(item.get("registry_keys"), f"candidate {candidate_id}.registry_keys")
        _strings(item.get("source_urls"), f"candidate {candidate_id}.source_urls")
        if status == "candidate" and item.get("execution_gate") != "blocked":
            raise ContractError(
                f"candidate {candidate_id} execution must remain blocked"
            )
        if status == "candidate" and item.get("license_gate") != "review_required":
            raise ContractError(f"candidate {candidate_id} license must require review")
        mobile_lanes = {"galaxy_s21_ultra", "iphone_17_pro_max"} & set(lanes)
        if mobile_lanes:
            if (
                item.get("mobile_support_gate")
                != "exact_artifact_runtime_probe_required"
            ):
                raise ContractError(
                    f"candidate {candidate_id} requires an exact mobile artifact/runtime gate"
                )
            phone_lane_mode = item.get("phone_lane_mode", "normal_worker")
            if phone_lane_mode not in {"normal_worker", "feasibility_only"}:
                raise ContractError(
                    f"candidate {candidate_id} has invalid phone lane mode"
                )
            if total > 4_000_000_000 and phone_lane_mode != "feasibility_only":
                raise ContractError(
                    f"candidate {candidate_id} exceeds the 4B normal phone-worker cap"
                )
    if controls != {
        "qwen35-08b-control",
        "lfm25-8b-a1b-control",
        "ornith-9b-control",
    }:
        raise ContractError("ADR 0005 control set changed")
    _strings(root.get("acceleration_order"), "acceleration_order", allow_empty=False)
    return dict(root)


def build_candidate_review(
    tournament: Mapping[str, Any],
    primary_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Join registry observations to candidates without promoting or downloading."""

    config = validate_tournament(tournament)
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for record in primary_records.values():
        name = str(record["subject"]["canonical_name"]).lower()
        by_name.setdefault(name, []).append(record)
    rows: list[dict[str, Any]] = []
    for candidate in config["candidates"]:
        matches: list[Mapping[str, Any]] = []
        for key in candidate["registry_keys"]:
            matches.extend(by_name.get(str(key).lower(), []))
        immutable = [record for record in matches if not record["resolved"]["mutable"]]
        chosen_pool = immutable or matches
        chosen = (
            max(chosen_pool, key=lambda record: _timestamp_key(record["retrieved_at"]))
            if chosen_pool
            else None
        )
        resolution = (
            "resolved_immutable"
            if immutable
            else "mutable_only"
            if matches
            else "missing"
        )
        rows.append(
            {
                "candidate_id": candidate["id"],
                "status": candidate["status"],
                "resolution": resolution,
                "record_id": chosen["record_id"] if chosen else None,
                "revision": chosen["source"]["revision"] if chosen else None,
                "retrieved_at": chosen["retrieved_at"] if chosen else None,
                "declared_licenses": chosen["license"]["declared"] if chosen else [],
                "license_verified": chosen["license"]["verified"] if chosen else False,
                "execution_gate": candidate["execution_gate"],
                "promotion_authorized": False,
            }
        )
    counts = {
        state: sum(row["resolution"] == state for row in rows)
        for state in ("resolved_immutable", "mutable_only", "missing")
    }
    return {
        "schema_version": "pheno.tournament.review.v1",
        "cutoff_date": config["cutoff_date"],
        "review_only": True,
        "counts": counts,
        "candidates": rows,
    }


__all__ = [
    "TOURNAMENT_SCHEMA_VERSION",
    "build_candidate_review",
    "validate_tournament",
]
