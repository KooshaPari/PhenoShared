"""Offline, fail-closed readiness contracts for the heterogeneous device fleet.

This module deliberately has no process, network, package-manager, model-loader,
or device-control imports.  It validates user-supplied observations, produces
non-authorizing templates, and evaluates an interval-only GTX 1080 Ti helper
simulation.  It never probes or mutates a device.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from yaml.tokens import AliasToken, AnchorToken

POLICY_SCHEMA_VERSION = "pheno.fleet-readiness-policy.v1"
CAPABILITY_SCHEMA_VERSION = "pheno.fleet.device-capability.v1"
CAPABILITY_VALIDATION_SCHEMA_VERSION = "pheno.fleet.device-capability-validation.v1"
HELPER_INPUT_SCHEMA_VERSION = "pheno.fleet.gtx1080-helper-input.v1"
HELPER_RESULT_SCHEMA_VERSION = "pheno.fleet.gtx1080-helper-result.v1"

REQUESTED_DEVICE_PROFILES = {
    "rtx_3090_ti",
    "m1_pro_16gb",
    "galaxy_s21_ultra",
    "iphone_17_pro_max",
    "gtx_1080_ti",
}
REMOTE_TEMPLATE_PROFILES = {
    "m1_pro_16gb",
    "galaxy_s21_ultra",
    "iphone_17_pro_max",
}
PHYSICAL_GATE_FIELDS = {
    "psu_capacity",
    "slot_available",
    "power_connector_available",
    "case_clearance",
    "thermal_budget",
}
AUTHORIZATION_FIELDS = {
    "remote_probe_authorized",
    "mutation_authorized",
    "install_authorized",
    "server_launch_authorized",
    "benchmark_execution_authorized",
}
POLICY_ALLOW_FIELDS = {
    "allow_local_mutation",
    "allow_remote_mutation",
    "allow_remote_probe",
    "allow_ssh",
    "allow_install",
    "allow_download",
    "allow_server_launch",
    "allow_phone_mutation",
    "allow_mac_mutation",
    "allow_1080ti_install",
}
INTERVAL_FIELDS = {
    "baseline_avs_per_s",
    "primary_power_w",
    "helper_candidate_avs_per_s",
    "coordination_rounds_per_s",
    "helper_latency_ms",
    "ipc_latency_ms",
    "acceptance_fraction",
    "helper_power_w",
}
_SHA256_LENGTH = 64
_MAX_POLICY_BYTES = 1024 * 1024
_CAPABILITY_ROOT_FIELDS = {
    "schema_version",
    "capture_state",
    "captured_at",
    "device",
    "runtime",
    "backend",
    "build",
    "telemetry",
    "memory",
    "thermal",
    "lifecycle",
    "owner_handoff",
    "authorization",
    "manifest_sha256",
}
_THERMAL_STATES = {"nominal", "fair", "serious", "critical", "unknown"}
_LIFECYCLE_STATES = {
    "active",
    "idle",
    "foreground",
    "inactive",
    "background",
    "terminated",
    "unavailable",
    "unknown",
}
_MEMORY_BASES = {
    "system_available",
    "process_limit",
    "metal_recommended_working_set",
    "os_available_to_process",
    "unknown",
}


class FleetReadinessError(ValueError):
    """Raised when a readiness policy or artifact fails closed validation."""


class _StrictPolicyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Safe policy loader that rejects duplicate mapping keys."""

    def construct_mapping(
        self, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        """Build the mapping and reject duplicate keys with a FleetReadinessError."""

        self.flatten_mapping(node)
        keys: set[Any] = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=False)
            try:
                duplicate = key in keys
            except TypeError as exc:
                raise FleetReadinessError("policy mapping keys must be scalar") from exc
            if duplicate:
                raise FleetReadinessError(
                    f"duplicate policy mapping key {key!r} is forbidden"
                )
            keys.add(key)
        mapping: dict[Any, Any] = dict(super().construct_mapping(node, deep=deep))
        return mapping


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FleetReadinessError(f"{path} must be an object")
    return value


def _exact(value: Any, fields: set[str], path: str) -> Mapping[str, Any]:
    obj = _object(value, path)
    actual = set(obj)
    missing = sorted(fields - actual)
    unknown = sorted(actual - fields)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unknown:
            details.append(f"unknown={unknown}")
        raise FleetReadinessError(f"{path} has invalid fields ({', '.join(details)})")
    return obj


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise FleetReadinessError(f"{path} must be boolean")
    return value


def _text(value: Any, path: str, *, allow_unmeasured: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FleetReadinessError(f"{path} must be a non-empty string")
    result = value.strip()
    if not allow_unmeasured and (result == "unmeasured" or result.startswith("<fill-")):
        raise FleetReadinessError(f"{path} still contains a template placeholder")
    return result


def _optional_text(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _text(value, path)


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
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise FleetReadinessError(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise FleetReadinessError(f"{path} must be finite")
    if minimum is not None and result < minimum:
        raise FleetReadinessError(f"{path} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise FleetReadinessError(f"{path} must be <= {maximum}")
    return result


def _integer(
    value: Any,
    path: str,
    *,
    minimum: int | None = None,
    nullable: bool = False,
) -> int | None:
    if value is None and nullable:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise FleetReadinessError(f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise FleetReadinessError(f"{path} must be >= {minimum}")
    return value


def _strings(value: Any, path: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise FleetReadinessError(f"{path} must be an array")
    checked = [_text(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if len(set(checked)) != len(checked):
        raise FleetReadinessError(f"{path} must not contain duplicates")
    return checked


def _sha256(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    text = _text(value, path).lower()
    if len(text) != _SHA256_LENGTH or any(ch not in "0123456789abcdef" for ch in text):
        raise FleetReadinessError(f"{path} must be a 64-character SHA-256")
    return text


def _timestamp(value: Any, path: str) -> str:
    text = _text(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FleetReadinessError(f"{path} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FleetReadinessError(f"{path} must include a timezone")
    return text


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON and reject non-finite values."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise FleetReadinessError(f"artifact is not canonical JSON: {exc}") from exc
    return encoded.encode("utf-8")


def _content_sha256(value: Mapping[str, Any], hash_field: str) -> str:
    payload = {key: deepcopy(item) for key, item in value.items() if key != hash_field}
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def capability_manifest_sha256(value: Mapping[str, Any]) -> str:
    """Hash every capability field except the self-referential digest."""

    return _content_sha256(value, "manifest_sha256")


def helper_input_sha256(value: Mapping[str, Any]) -> str:
    """Hash every helper-input field except the self-referential input_sha256."""

    return _content_sha256(value, "input_sha256")


def helper_result_sha256(value: Mapping[str, Any]) -> str:
    """Hash every helper-result field except the self-referential result_sha256."""

    return _content_sha256(value, "result_sha256")


def _validate_policy_profile(value: Any, path: str) -> dict[str, Any]:
    fields = {
        "device_class",
        "remote",
        "mobile",
        "owner_handoff_required",
        "min_memory_headroom_fraction",
        "allowed_runtimes",
        "allowed_backends",
        "required_lifecycle_states",
        "required_thermal_stop_states",
    }
    profile = dict(_exact(value, fields, path))
    _text(profile["device_class"], f"{path}.device_class")
    for field in ("remote", "mobile", "owner_handoff_required"):
        _boolean(profile[field], f"{path}.{field}")
    _number(
        profile["min_memory_headroom_fraction"],
        f"{path}.min_memory_headroom_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    for field in (
        "allowed_runtimes",
        "allowed_backends",
        "required_lifecycle_states",
        "required_thermal_stop_states",
    ):
        values = _strings(profile[field], f"{path}.{field}")
        if field == "required_lifecycle_states" and not set(values).issubset(
            _LIFECYCLE_STATES
        ):
            raise FleetReadinessError(f"{path}.{field} contains an invalid state")
        if field == "required_thermal_stop_states" and not set(values).issubset(
            _THERMAL_STATES
        ):
            raise FleetReadinessError(f"{path}.{field} contains an invalid state")
    return profile


def validate_policy(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the closed, non-authorizing fleet-readiness policy."""

    root = dict(
        _exact(
            value,
            {"schema_version", "policy", "device_profiles", "helper_simulation"},
            "fleet_readiness",
        )
    )
    if root["schema_version"] != POLICY_SCHEMA_VERSION:
        raise FleetReadinessError(f"schema_version must be {POLICY_SCHEMA_VERSION}")
    policy = _exact(root["policy"], POLICY_ALLOW_FIELDS, "policy")
    for field in sorted(POLICY_ALLOW_FIELDS):
        if _boolean(policy[field], f"policy.{field}"):
            raise FleetReadinessError(f"policy.{field} must remain false")

    profiles = _object(root["device_profiles"], "device_profiles")
    if set(profiles) != REQUESTED_DEVICE_PROFILES:
        raise FleetReadinessError("device_profiles must match the requested fleet")
    for name, raw in profiles.items():
        profile = _validate_policy_profile(raw, f"device_profiles.{name}")
        if name in REMOTE_TEMPLATE_PROFILES and profile["remote"] is not True:
            raise FleetReadinessError(f"device_profiles.{name}.remote must be true")
        if (
            name in {"galaxy_s21_ultra", "iphone_17_pro_max"}
            and profile["mobile"] is not True
        ):
            raise FleetReadinessError(f"device_profiles.{name}.mobile must be true")
        if profile["mobile"] and profile["required_lifecycle_states"] != ["foreground"]:
            raise FleetReadinessError(
                f"device_profiles.{name} must require foreground lifecycle"
            )
        if profile["mobile"] and not {"serious", "critical"}.issubset(
            profile["required_thermal_stop_states"]
        ):
            raise FleetReadinessError(
                f"device_profiles.{name} must stop at serious and critical thermals"
            )

    helper = _exact(
        root["helper_simulation"],
        {"method", "physical_gate_fields", "positive_epsilon"},
        "helper_simulation",
    )
    if helper["method"] != "conservative_interval_v1":
        raise FleetReadinessError(
            "helper_simulation.method must be conservative_interval_v1"
        )
    physical_fields = set(
        _strings(
            helper["physical_gate_fields"],
            "helper_simulation.physical_gate_fields",
        )
    )
    if physical_fields != PHYSICAL_GATE_FIELDS:
        raise FleetReadinessError(
            "helper_simulation.physical_gate_fields do not match the physical gates"
        )
    epsilon = _number(
        helper["positive_epsilon"],
        "helper_simulation.positive_epsilon",
        minimum=0.0,
    )
    if epsilon != 0.0:
        raise FleetReadinessError(
            "helper_simulation.positive_epsilon must be 0.0 for conservative_interval_v1"
        )
    return root


def load_policy(path: str | Path) -> dict[str, Any]:
    """Load a YAML fleet-readiness policy from disk and validate it closed."""

    policy_path = Path(path)
    if policy_path.is_symlink():
        raise FleetReadinessError("fleet policy must not be a symbolic link")
    try:
        with policy_path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise FleetReadinessError("fleet policy must be a regular file")
            if metadata.st_size > _MAX_POLICY_BYTES:
                raise FleetReadinessError("fleet policy exceeds the 1 MiB limit")
            payload = stream.read(_MAX_POLICY_BYTES + 1)
    except FleetReadinessError:
        raise
    except OSError as exc:
        raise FleetReadinessError("fleet policy cannot be read") from exc
    if len(payload) > _MAX_POLICY_BYTES:
        raise FleetReadinessError("fleet policy exceeds the 1 MiB limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FleetReadinessError("fleet policy must be UTF-8 YAML") from exc
    try:
        if any(
            isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)
        ):
            raise FleetReadinessError("fleet policy YAML aliases are forbidden")
        # bandit: aliases are rejected above via yaml.scan(); _StrictPolicyLoader
        # is a custom SafeLoader-derived Loader that disables Python/object
        # construction. safe_load would not enforce our domain-specific
        # policy (e.g. tag whitelist).
        raw = yaml.load(text, Loader=_StrictPolicyLoader)  # nosec B506
    except FleetReadinessError:
        raise
    except yaml.YAMLError as exc:
        raise FleetReadinessError("fleet policy is invalid YAML") from exc
    return validate_policy(_object(raw, "fleet_readiness"))


def _validate_authorization(value: Any, path: str = "authorization") -> dict[str, bool]:
    authorization = dict(_exact(value, AUTHORIZATION_FIELDS, path))
    for field in sorted(AUTHORIZATION_FIELDS):
        if _boolean(authorization[field], f"{path}.{field}"):
            raise FleetReadinessError(f"{path}.{field} must remain false")
    return authorization


def validate_capability_manifest(
    value: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate a closed capability artifact and its content hash.

    A valid capability is descriptive only.  Its authorization fields are
    required to remain false, including when every capability is present.
    """

    policy_root = validate_policy(policy)
    root = dict(_exact(value, _CAPABILITY_ROOT_FIELDS, "capability"))
    if root["schema_version"] != CAPABILITY_SCHEMA_VERSION:
        raise FleetReadinessError(
            f"capability.schema_version must be {CAPABILITY_SCHEMA_VERSION}"
        )
    capture_state = root["capture_state"]
    if capture_state not in {"template", "observed"}:
        raise FleetReadinessError(
            "capability.capture_state must be template or observed"
        )
    if capture_state == "template":
        if root["captured_at"] is not None:
            raise FleetReadinessError("template capability.captured_at must be null")
    else:
        _timestamp(root["captured_at"], "capability.captured_at")

    observed = capture_state == "observed"
    device = _exact(
        root["device"],
        {
            "profile_id",
            "instance_id",
            "device_class",
            "manufacturer",
            "model",
            "architecture",
            "os_name",
            "os_version",
            "os_build",
        },
        "capability.device",
    )
    profile_id = _text(device["profile_id"], "capability.device.profile_id")
    if profile_id not in REQUESTED_DEVICE_PROFILES:
        raise FleetReadinessError("capability.device.profile_id is not in the fleet")
    profile = policy_root["device_profiles"][profile_id]
    for field in (
        "instance_id",
        "device_class",
        "manufacturer",
        "model",
        "architecture",
        "os_name",
        "os_version",
        "os_build",
    ):
        _text(
            device[field],
            f"capability.device.{field}",
            allow_unmeasured=not observed,
        )
    if device["device_class"] != profile["device_class"]:
        raise FleetReadinessError(
            "capability.device.device_class does not match the policy profile"
        )

    runtime = _exact(
        root["runtime"],
        {"name", "version", "revision", "binary_sha256", "installed"},
        "capability.runtime",
    )
    runtime_name = _text(
        runtime["name"], "capability.runtime.name", allow_unmeasured=not observed
    )
    _text(
        runtime["version"],
        "capability.runtime.version",
        allow_unmeasured=not observed,
    )
    _text(
        runtime["revision"],
        "capability.runtime.revision",
        allow_unmeasured=not observed,
    )
    installed = _boolean(runtime["installed"], "capability.runtime.installed")
    binary_sha = _sha256(
        runtime["binary_sha256"], "capability.runtime.binary_sha256", nullable=True
    )
    if installed != (binary_sha is not None):
        raise FleetReadinessError(
            "capability.runtime installed state must agree with binary_sha256"
        )
    if observed and runtime_name not in profile["allowed_runtimes"]:
        raise FleetReadinessError(
            "capability.runtime.name is not allowed for this device"
        )

    backend = _exact(
        root["backend"],
        {"name", "version", "revision", "available", "capabilities"},
        "capability.backend",
    )
    backend_name = _text(
        backend["name"], "capability.backend.name", allow_unmeasured=not observed
    )
    _text(
        backend["version"],
        "capability.backend.version",
        allow_unmeasured=not observed,
    )
    _text(
        backend["revision"],
        "capability.backend.revision",
        allow_unmeasured=not observed,
    )
    _boolean(backend["available"], "capability.backend.available")
    _strings(
        backend["capabilities"],
        "capability.backend.capabilities",
        allow_empty=True,
    )
    if observed and backend_name not in profile["allowed_backends"]:
        raise FleetReadinessError(
            "capability.backend.name is not allowed for this device"
        )

    build = _exact(
        root["build"],
        {"app_id", "version", "revision", "build_sha256"},
        "capability.build",
    )
    for field in ("app_id", "version", "revision"):
        _text(
            build[field],
            f"capability.build.{field}",
            allow_unmeasured=not observed,
        )
    _sha256(build["build_sha256"], "capability.build.build_sha256", nullable=True)

    telemetry = _exact(
        root["telemetry"],
        {
            "memory_available",
            "thermal_available",
            "lifecycle_available",
            "battery_available",
            "monotonic_clock_available",
            "sampling_interval_ms",
        },
        "capability.telemetry",
    )
    telemetry_flags = []
    for field in (
        "memory_available",
        "thermal_available",
        "lifecycle_available",
        "battery_available",
        "monotonic_clock_available",
    ):
        telemetry_flags.append(
            _boolean(telemetry[field], f"capability.telemetry.{field}")
        )
    sampling_interval = _number(
        telemetry["sampling_interval_ms"],
        "capability.telemetry.sampling_interval_ms",
        minimum=1e-15,
        nullable=True,
    )
    if any(telemetry_flags) != (sampling_interval is not None):
        raise FleetReadinessError(
            "telemetry availability must agree with sampling_interval_ms"
        )

    memory = _exact(
        root["memory"],
        {"budget_bytes", "available_bytes", "headroom_fraction", "basis"},
        "capability.memory",
    )
    budget = _integer(
        memory["budget_bytes"],
        "capability.memory.budget_bytes",
        minimum=1,
        nullable=True,
    )
    available = _integer(
        memory["available_bytes"],
        "capability.memory.available_bytes",
        minimum=0,
        nullable=True,
    )
    headroom = _number(
        memory["headroom_fraction"],
        "capability.memory.headroom_fraction",
        minimum=0.0,
        maximum=1.0,
        nullable=True,
    )
    if memory["basis"] not in _MEMORY_BASES:
        raise FleetReadinessError("capability.memory.basis is invalid")
    memory_values_present = [item is not None for item in (budget, available, headroom)]
    if any(memory_values_present) and not all(memory_values_present):
        raise FleetReadinessError(
            "capability.memory measurements must be all present or all null"
        )
    if budget is not None and available is not None and headroom is not None:
        if available > budget:
            raise FleetReadinessError(
                "capability.memory.available_bytes cannot exceed budget_bytes"
            )
        expected = available / budget
        if not math.isclose(headroom, expected, rel_tol=1e-9, abs_tol=1e-12):
            raise FleetReadinessError(
                "capability.memory.headroom_fraction does not match available/budget"
            )
        if memory["basis"] == "unknown":
            raise FleetReadinessError(
                "measured capability.memory requires a known basis"
            )
    elif memory["basis"] != "unknown":
        raise FleetReadinessError("unmeasured capability.memory must use unknown basis")
    if telemetry["memory_available"] != all(memory_values_present):
        raise FleetReadinessError(
            "telemetry.memory_available must agree with memory measurements"
        )

    thermal = _exact(
        root["thermal"],
        {"observable", "state", "stop_states"},
        "capability.thermal",
    )
    thermal_observable = _boolean(
        thermal["observable"], "capability.thermal.observable"
    )
    if thermal["state"] not in _THERMAL_STATES:
        raise FleetReadinessError("capability.thermal.state is invalid")
    stop_states = _strings(thermal["stop_states"], "capability.thermal.stop_states")
    if not set(stop_states).issubset(_THERMAL_STATES):
        raise FleetReadinessError(
            "capability.thermal.stop_states contains an invalid state"
        )
    if not thermal_observable and thermal["state"] != "unknown":
        raise FleetReadinessError("unobservable thermal state must be unknown")
    if telemetry["thermal_available"] != thermal_observable:
        raise FleetReadinessError(
            "telemetry.thermal_available must agree with thermal.observable"
        )
    if not set(profile["required_thermal_stop_states"]).issubset(stop_states):
        raise FleetReadinessError(
            "capability.thermal.stop_states omits a policy-required stop state"
        )

    lifecycle = _exact(
        root["lifecycle"],
        {
            "observable",
            "state",
            "foreground_visible",
            "cancellation_tested",
            "checkpoint_recovery_tested",
        },
        "capability.lifecycle",
    )
    lifecycle_observable = _boolean(
        lifecycle["observable"], "capability.lifecycle.observable"
    )
    if lifecycle["state"] not in _LIFECYCLE_STATES:
        raise FleetReadinessError("capability.lifecycle.state is invalid")
    for field in (
        "foreground_visible",
        "cancellation_tested",
        "checkpoint_recovery_tested",
    ):
        _boolean(lifecycle[field], f"capability.lifecycle.{field}")
    if not lifecycle_observable and lifecycle["state"] != "unknown":
        raise FleetReadinessError("unobservable lifecycle state must be unknown")
    if telemetry["lifecycle_available"] != lifecycle_observable:
        raise FleetReadinessError(
            "telemetry.lifecycle_available must agree with lifecycle.observable"
        )

    owner = _exact(
        root["owner_handoff"],
        {"required", "status", "record_sha256"},
        "capability.owner_handoff",
    )
    owner_required = _boolean(owner["required"], "capability.owner_handoff.required")
    if owner_required != profile["owner_handoff_required"]:
        raise FleetReadinessError(
            "capability.owner_handoff.required does not match the device policy"
        )
    if owner["status"] not in {"not_required", "pending", "approved", "revoked"}:
        raise FleetReadinessError("capability.owner_handoff.status is invalid")
    owner_hash = _sha256(
        owner["record_sha256"],
        "capability.owner_handoff.record_sha256",
        nullable=True,
    )
    if not owner_required and (
        owner["status"] != "not_required" or owner_hash is not None
    ):
        raise FleetReadinessError(
            "non-required owner handoff must be not_required without a record"
        )
    if owner_required and (owner["status"] == "approved") != (owner_hash is not None):
        raise FleetReadinessError(
            "approved owner handoff must have a record hash, and only approved handoff may have one"
        )
    if owner_required and owner["status"] == "not_required":
        raise FleetReadinessError("required owner handoff cannot be not_required")

    _validate_authorization(root["authorization"], "capability.authorization")
    declared_hash = _sha256(root["manifest_sha256"], "capability.manifest_sha256")
    expected_hash = capability_manifest_sha256(root)
    if declared_hash != expected_hash:
        raise FleetReadinessError(
            "capability.manifest_sha256 does not match its content"
        )
    return root


def capability_readiness(
    value: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Return capability readiness without ever granting execution authority."""

    manifest = validate_capability_manifest(value, policy)
    profile_id = manifest["device"]["profile_id"]
    profile = policy["device_profiles"][profile_id]
    reasons: list[str] = []
    if manifest["capture_state"] != "observed":
        reasons.append("capability is an unmeasured template")
    if not manifest["runtime"]["installed"]:
        reasons.append("runtime is not observed as installed")
    if not manifest["backend"]["available"]:
        reasons.append("backend is not observed as available")
    if manifest["build"]["build_sha256"] is None:
        reasons.append("app or collector build hash is missing")
    telemetry = manifest["telemetry"]
    for field in (
        "memory_available",
        "thermal_available",
        "lifecycle_available",
        "monotonic_clock_available",
    ):
        if not telemetry[field]:
            reasons.append(f"telemetry capability {field} is unavailable")
    if profile["mobile"] and not telemetry["battery_available"]:
        reasons.append("mobile battery telemetry is unavailable")
    headroom = manifest["memory"]["headroom_fraction"]
    if headroom is None:
        reasons.append("memory headroom is unavailable")
    elif headroom < profile["min_memory_headroom_fraction"]:
        reasons.append("memory headroom is below the device policy")
    thermal = manifest["thermal"]
    if thermal["state"] in set(thermal["stop_states"]) | {"unknown"}:
        reasons.append("thermal state is unknown or prohibited")
    lifecycle = manifest["lifecycle"]
    if lifecycle["state"] not in profile["required_lifecycle_states"]:
        reasons.append("lifecycle state is not permitted for this device")
    if profile["mobile"]:
        if not lifecycle["foreground_visible"]:
            reasons.append("mobile worker is not foreground-visible")
        if not lifecycle["cancellation_tested"]:
            reasons.append("mobile lifecycle cancellation has not been tested")
        if not lifecycle["checkpoint_recovery_tested"]:
            reasons.append("mobile checkpoint recovery has not been tested")
    owner = manifest["owner_handoff"]
    if owner["required"] and owner["status"] != "approved":
        reasons.append("owner handoff is not approved")
    return {
        "schema_version": CAPABILITY_VALIDATION_SCHEMA_VERSION,
        "valid": True,
        "profile_id": profile_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "benchmark_capability_ready": not reasons,
        "reasons": reasons,
        "remote_probe_authorized": False,
        "mutation_authorized": False,
        "install_authorized": False,
        "server_launch_authorized": False,
        "benchmark_execution_authorized": False,
    }


def build_remote_capability_template(
    profile_id: str, policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Build a deterministic, non-authorizing template for a remote owner."""

    policy_root = validate_policy(policy)
    if profile_id not in REMOTE_TEMPLATE_PROFILES:
        raise FleetReadinessError(
            "remote templates are limited to the M1 Pro and the two phones"
        )
    profile = policy_root["device_profiles"][profile_id]
    template: dict[str, Any] = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "capture_state": "template",
        "captured_at": None,
        "device": {
            "profile_id": profile_id,
            "instance_id": "<fill-device-instance-id>",
            "device_class": profile["device_class"],
            "manufacturer": "<fill-manufacturer>",
            "model": "<fill-exact-model>",
            "architecture": "<fill-architecture-or-soc>",
            "os_name": "<fill-os-name>",
            "os_version": "<fill-os-version>",
            "os_build": "<fill-os-build>",
        },
        "runtime": {
            "name": "unmeasured",
            "version": "unmeasured",
            "revision": "unmeasured",
            "binary_sha256": None,
            "installed": False,
        },
        "backend": {
            "name": "unmeasured",
            "version": "unmeasured",
            "revision": "unmeasured",
            "available": False,
            "capabilities": [],
        },
        "build": {
            "app_id": "unmeasured",
            "version": "unmeasured",
            "revision": "unmeasured",
            "build_sha256": None,
        },
        "telemetry": {
            "memory_available": False,
            "thermal_available": False,
            "lifecycle_available": False,
            "battery_available": False,
            "monotonic_clock_available": False,
            "sampling_interval_ms": None,
        },
        "memory": {
            "budget_bytes": None,
            "available_bytes": None,
            "headroom_fraction": None,
            "basis": "unknown",
        },
        "thermal": {
            "observable": False,
            "state": "unknown",
            "stop_states": list(profile["required_thermal_stop_states"]),
        },
        "lifecycle": {
            "observable": False,
            "state": "unknown",
            "foreground_visible": False,
            "cancellation_tested": False,
            "checkpoint_recovery_tested": False,
        },
        "owner_handoff": {
            "required": profile["owner_handoff_required"],
            "status": "pending"
            if profile["owner_handoff_required"]
            else "not_required",
            "record_sha256": None,
        },
        "authorization": dict.fromkeys(sorted(AUTHORIZATION_FIELDS), False),
        "manifest_sha256": "0" * _SHA256_LENGTH,
    }
    template["manifest_sha256"] = capability_manifest_sha256(template)
    validate_capability_manifest(template, policy_root)
    return template


def _validate_interval(
    value: Any,
    path: str,
    *,
    minimum: float = 0.0,
    maximum: float | None = None,
    strictly_positive: bool = False,
) -> tuple[float, float]:
    interval = _exact(value, {"lower", "upper"}, path)
    lower = _number(
        interval["lower"], f"{path}.lower", minimum=minimum, maximum=maximum
    )
    upper = _number(
        interval["upper"], f"{path}.upper", minimum=minimum, maximum=maximum
    )
    assert lower is not None and upper is not None  # nosec B101
    if lower > upper:
        raise FleetReadinessError(f"{path}.lower cannot exceed upper")
    if strictly_positive and lower <= 0:
        raise FleetReadinessError(f"{path}.lower must be greater than zero")
    return lower, upper


def validate_helper_input(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a closed GTX 1080 Ti helper-simulation input artifact."""
    root = dict(
        _exact(
            value,
            {
                "schema_version",
                "simulation_id",
                "intervals",
                "physical_gates",
                "input_sha256",
            },
            "helper_input",
        )
    )
    if root["schema_version"] != HELPER_INPUT_SCHEMA_VERSION:
        raise FleetReadinessError(
            f"helper_input.schema_version must be {HELPER_INPUT_SCHEMA_VERSION}"
        )
    _text(root["simulation_id"], "helper_input.simulation_id")
    intervals = _exact(root["intervals"], INTERVAL_FIELDS, "helper_input.intervals")
    for field in sorted(INTERVAL_FIELDS):
        _validate_interval(
            intervals[field],
            f"helper_input.intervals.{field}",
            maximum=1.0 if field == "acceptance_fraction" else None,
            strictly_positive=field
            in {
                "baseline_avs_per_s",
                "primary_power_w",
                "helper_power_w",
            },
        )
    gates = _exact(
        root["physical_gates"], PHYSICAL_GATE_FIELDS, "helper_input.physical_gates"
    )
    for field in sorted(PHYSICAL_GATE_FIELDS):
        _boolean(gates[field], f"helper_input.physical_gates.{field}")
    declared = _sha256(root["input_sha256"], "helper_input.input_sha256")
    expected = helper_input_sha256(root)
    if declared != expected:
        raise FleetReadinessError(
            "helper_input.input_sha256 does not match its content"
        )
    return root


def _interval_dict(lower: float, upper: float) -> dict[str, float]:
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise FleetReadinessError("simulation produced a non-finite bound")
    return {"lower": lower, "upper": upper}


def simulate_gtx1080_helper(
    value: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate conservative interval bounds without touching the optional GPU."""

    policy_root = validate_policy(policy)
    simulation = validate_helper_input(value)
    raw = simulation["intervals"]

    def interval(name: str) -> tuple[float, float]:
        """Resolve one interval field by name, applying per-field bounds."""

        maximum = 1.0 if name == "acceptance_fraction" else None
        return _validate_interval(
            raw[name],
            f"helper_input.intervals.{name}",
            maximum=maximum,
            strictly_positive=name
            in {"baseline_avs_per_s", "primary_power_w", "helper_power_w"},
        )

    baseline = interval("baseline_avs_per_s")
    primary_power = interval("primary_power_w")
    helper_rate = interval("helper_candidate_avs_per_s")
    round_rate = interval("coordination_rounds_per_s")
    helper_latency = interval("helper_latency_ms")
    ipc_latency = interval("ipc_latency_ms")
    acceptance = interval("acceptance_fraction")
    helper_power = interval("helper_power_w")

    blocked_lower = min(
        1.0,
        round_rate[0] * (helper_latency[0] + ipc_latency[0]) / 1000.0,
    )
    blocked_upper = min(
        1.0,
        round_rate[1] * (helper_latency[1] + ipc_latency[1]) / 1000.0,
    )
    accepted_lower = helper_rate[0] * acceptance[0]
    accepted_upper = helper_rate[1] * acceptance[1]
    assisted_lower = baseline[0] * (1.0 - blocked_upper) + accepted_lower
    assisted_upper = baseline[1] * (1.0 - blocked_lower) + accepted_upper
    gain_lower = assisted_lower - baseline[1]
    gain_upper = assisted_upper - baseline[0]
    baseline_eff_lower = baseline[0] / primary_power[1]
    baseline_eff_upper = baseline[1] / primary_power[0]
    assisted_eff_lower = assisted_lower / (primary_power[1] + helper_power[1])
    assisted_eff_upper = assisted_upper / (primary_power[0] + helper_power[0])
    efficiency_gain_lower = assisted_eff_lower - baseline_eff_upper
    efficiency_gain_upper = assisted_eff_upper - baseline_eff_lower

    physical_gates = dict(simulation["physical_gates"])
    failed_gates = [
        field
        for field in sorted(PHYSICAL_GATE_FIELDS)
        if physical_gates[field] is not True
    ]
    epsilon = float(policy_root["helper_simulation"]["positive_epsilon"])
    reasons = [f"physical gate failed: {field}" for field in failed_gates]
    if gain_lower <= epsilon:
        reasons.append("lower-bound net AVS goodput gain is not positive")
    if efficiency_gain_lower <= epsilon:
        reasons.append("lower-bound energy-efficiency gain is not positive")
    decision = "candidate_for_user_review" if not reasons else "not_justified"

    result: dict[str, Any] = {
        "schema_version": HELPER_RESULT_SCHEMA_VERSION,
        "input_sha256": simulation["input_sha256"],
        "method": "conservative_interval_v1",
        "bounds": {
            "blocked_fraction": _interval_dict(blocked_lower, blocked_upper),
            "accepted_helper_avs_per_s": _interval_dict(accepted_lower, accepted_upper),
            "net_assisted_avs_goodput_per_s": _interval_dict(
                assisted_lower, assisted_upper
            ),
            "net_avs_goodput_gain_per_s": _interval_dict(gain_lower, gain_upper),
            "baseline_energy_efficiency_avs_per_joule": _interval_dict(
                baseline_eff_lower, baseline_eff_upper
            ),
            "assisted_energy_efficiency_avs_per_joule": _interval_dict(
                assisted_eff_lower, assisted_eff_upper
            ),
            "energy_efficiency_gain_avs_per_joule": _interval_dict(
                efficiency_gain_lower, efficiency_gain_upper
            ),
        },
        "physical_gates": physical_gates,
        "physical_gates_passed": not failed_gates,
        "decision": decision,
        "reasons": reasons,
        "install_authorized": False,
        "execution_authorized": False,
        "result_sha256": "0" * _SHA256_LENGTH,
    }
    result["result_sha256"] = helper_result_sha256(result)
    validate_helper_result(result)
    return result


def validate_helper_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a closed GTX 1080 Ti helper-simulation result artifact."""

    root = dict(
        _exact(
            value,
            {
                "schema_version",
                "input_sha256",
                "method",
                "bounds",
                "physical_gates",
                "physical_gates_passed",
                "decision",
                "reasons",
                "install_authorized",
                "execution_authorized",
                "result_sha256",
            },
            "helper_result",
        )
    )
    if root["schema_version"] != HELPER_RESULT_SCHEMA_VERSION:
        raise FleetReadinessError(
            f"helper_result.schema_version must be {HELPER_RESULT_SCHEMA_VERSION}"
        )
    _sha256(root["input_sha256"], "helper_result.input_sha256")
    if root["method"] != "conservative_interval_v1":
        raise FleetReadinessError("helper_result.method is invalid")
    bound_fields = {
        "blocked_fraction",
        "accepted_helper_avs_per_s",
        "net_assisted_avs_goodput_per_s",
        "net_avs_goodput_gain_per_s",
        "baseline_energy_efficiency_avs_per_joule",
        "assisted_energy_efficiency_avs_per_joule",
        "energy_efficiency_gain_avs_per_joule",
    }
    bounds = _exact(root["bounds"], bound_fields, "helper_result.bounds")
    checked_bounds: dict[str, tuple[float, float]] = {}
    for field in sorted(bound_fields):
        lower, upper = _validate_interval(
            bounds[field],
            f"helper_result.bounds.{field}",
            minimum=-math.inf,
        )
        checked_bounds[field] = (lower, upper)
        if field == "blocked_fraction" and (lower < 0 or upper > 1):
            raise FleetReadinessError(
                "helper_result blocked fraction must be in [0, 1]"
            )
    gates = _exact(
        root["physical_gates"], PHYSICAL_GATE_FIELDS, "helper_result.physical_gates"
    )
    checked_gates = {
        field: _boolean(gates[field], f"helper_result.physical_gates.{field}")
        for field in sorted(PHYSICAL_GATE_FIELDS)
    }
    gate_summary = _boolean(
        root["physical_gates_passed"], "helper_result.physical_gates_passed"
    )
    if gate_summary != all(checked_gates.values()):
        raise FleetReadinessError("helper_result physical gate summary is inconsistent")
    if root["decision"] not in {"not_justified", "candidate_for_user_review"}:
        raise FleetReadinessError("helper_result.decision is invalid")
    reasons = _strings(root["reasons"], "helper_result.reasons", allow_empty=True)
    if (root["decision"] == "candidate_for_user_review") != (not reasons):
        raise FleetReadinessError("helper_result decision and reasons are inconsistent")
    positive_candidate = (
        all(checked_gates.values())
        and checked_bounds["net_avs_goodput_gain_per_s"][0] > 0
        and checked_bounds["energy_efficiency_gain_avs_per_joule"][0] > 0
    )
    if (root["decision"] == "candidate_for_user_review") != positive_candidate:
        raise FleetReadinessError(
            "helper_result candidate decision is not supported by conservative bounds"
        )
    for field in ("install_authorized", "execution_authorized"):
        if _boolean(root[field], f"helper_result.{field}"):
            raise FleetReadinessError(f"helper_result.{field} must remain false")
    declared = _sha256(root["result_sha256"], "helper_result.result_sha256")
    if declared != helper_result_sha256(root):
        raise FleetReadinessError(
            "helper_result.result_sha256 does not match its content"
        )
    return root


def add_helper_input_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with its deterministic input digest populated."""

    result = deepcopy(dict(value))
    result["input_sha256"] = "0" * _SHA256_LENGTH
    result["input_sha256"] = helper_input_sha256(result)
    return result


__all__ = [
    "AUTHORIZATION_FIELDS",
    "CAPABILITY_SCHEMA_VERSION",
    "CAPABILITY_VALIDATION_SCHEMA_VERSION",
    "FleetReadinessError",
    "HELPER_INPUT_SCHEMA_VERSION",
    "HELPER_RESULT_SCHEMA_VERSION",
    "PHYSICAL_GATE_FIELDS",
    "POLICY_SCHEMA_VERSION",
    "REMOTE_TEMPLATE_PROFILES",
    "add_helper_input_hash",
    "build_remote_capability_template",
    "canonical_json_bytes",
    "capability_manifest_sha256",
    "capability_readiness",
    "helper_input_sha256",
    "helper_result_sha256",
    "load_policy",
    "simulate_gtx1080_helper",
    "validate_capability_manifest",
    "validate_helper_input",
    "validate_helper_result",
    "validate_policy",
]
