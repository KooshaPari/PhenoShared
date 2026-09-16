"""Offline, content-addressed heterogeneous telemetry bundle contracts.

``pheno.eval.telemetry-bundle.v1`` normalizes already-collected samples.  It
does not import a device API, start a process, or collect telemetry.  Every
derived summary and quality decision is recomputed from bounded input rows so
that a scalar peak or coverage claim cannot drift away from its time series.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .redaction import contains_secret

TELEMETRY_SCHEMA_VERSION = "pheno.eval.telemetry-bundle.v1"
MAX_TELEMETRY_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_TELEMETRY_SAMPLES = 200_000
MINIMUM_COVERAGE_FRACTION = 0.95
MAXIMUM_OVERHEAD_FRACTION = 0.05
MINIMUM_OVERHEAD_PAIRS = 3
MAXIMUM_OVERHEAD_PAIRS = 10_000
MEMORY_SCOPE = "time_aligned_peak_attributable_physical_bytes"

METRIC_NAMES = (
    "gpu_power_w",
    "system_power_w",
    "battery_power_w",
    "cumulative_energy_j",
    "gpu_memory_used_bytes",
    "process_memory_bytes",
    "unified_memory_used_bytes",
    "system_available_memory_bytes",
    "temperature_c",
    "thermal_throttle_active",
    "thermal_state",
    "lifecycle_state",
    "gpu_utilization_pct",
)

_METRIC_UNITS = {
    "gpu_power_w": "W",
    "system_power_w": "W",
    "battery_power_w": "W",
    "cumulative_energy_j": "J",
    "gpu_memory_used_bytes": "byte",
    "process_memory_bytes": "byte",
    "unified_memory_used_bytes": "byte",
    "system_available_memory_bytes": "byte",
    "temperature_c": "degC",
    "thermal_throttle_active": "boolean",
    "thermal_state": "state",
    "lifecycle_state": "state",
    "gpu_utilization_pct": "percent",
}
_INTEGER_METRICS = {
    "gpu_memory_used_bytes",
    "process_memory_bytes",
    "unified_memory_used_bytes",
    "system_available_memory_bytes",
}
_BOOLEAN_METRICS = {"thermal_throttle_active"}
_STATE_METRICS = {"thermal_state", "lifecycle_state"}
_POWER_METRICS = {
    "gpu_power_w",
    "system_power_w",
    "battery_power_w",
    "cumulative_energy_j",
}
_PROCESS_SCOPES = {"process", "process_tree", "app_process"}
_SCOPES = _PROCESS_SCOPES | {"device", "system", "sensor"}
_SCOPE_BY_METRIC = {
    "gpu_power_w": {"device", "process", "process_tree"},
    "system_power_w": {"system", "device"},
    "battery_power_w": {"device", "system"},
    "cumulative_energy_j": _SCOPES - {"sensor"},
    "gpu_memory_used_bytes": {"device", "process", "process_tree"},
    "process_memory_bytes": _PROCESS_SCOPES,
    "unified_memory_used_bytes": _PROCESS_SCOPES | {"system"},
    "system_available_memory_bytes": {"system"},
    "temperature_c": {"device", "sensor"},
    "thermal_throttle_active": {"device", "system", "app_process"},
    "thermal_state": {"device", "system", "app_process"},
    "lifecycle_state": {"system", "process", "app_process"},
    "gpu_utilization_pct": {"device", "process", "process_tree"},
}

PROFILE_REQUIRED_METRICS = {
    "rtx_3090_ti": frozenset(
        {
            "gpu_power_w",
            "cumulative_energy_j",
            "gpu_memory_used_bytes",
            "process_memory_bytes",
            "system_available_memory_bytes",
            "temperature_c",
            "thermal_throttle_active",
            "lifecycle_state",
            "gpu_utilization_pct",
        }
    ),
    "m1_pro_16gb": frozenset(
        {
            "system_power_w",
            "cumulative_energy_j",
            "process_memory_bytes",
            "unified_memory_used_bytes",
            "system_available_memory_bytes",
            "thermal_throttle_active",
            "thermal_state",
            "lifecycle_state",
        }
    ),
    "galaxy_s21_ultra": frozenset(
        {
            "battery_power_w",
            "cumulative_energy_j",
            "process_memory_bytes",
            "system_available_memory_bytes",
            "temperature_c",
            "thermal_throttle_active",
            "thermal_state",
            "lifecycle_state",
        }
    ),
    "iphone_17_pro_max": frozenset(
        {
            "battery_power_w",
            "cumulative_energy_j",
            "process_memory_bytes",
            "system_available_memory_bytes",
            "thermal_throttle_active",
            "thermal_state",
            "lifecycle_state",
        }
    ),
    "gtx_1080_ti": frozenset(
        {
            "gpu_power_w",
            "cumulative_energy_j",
            "gpu_memory_used_bytes",
            "process_memory_bytes",
            "system_available_memory_bytes",
            "temperature_c",
            "thermal_throttle_active",
            "lifecycle_state",
            "gpu_utilization_pct",
        }
    ),
}
PROFILE_NOT_APPLICABLE_METRICS = {
    "rtx_3090_ti": frozenset({"battery_power_w", "unified_memory_used_bytes"}),
    "m1_pro_16gb": frozenset({"gpu_power_w", "gpu_memory_used_bytes"}),
    "galaxy_s21_ultra": frozenset(
        {
            "gpu_power_w",
            "system_power_w",
            "gpu_memory_used_bytes",
            "unified_memory_used_bytes",
        }
    ),
    "iphone_17_pro_max": frozenset(
        {
            "gpu_power_w",
            "system_power_w",
            "gpu_memory_used_bytes",
            "unified_memory_used_bytes",
        }
    ),
    "gtx_1080_ti": frozenset({"battery_power_w", "unified_memory_used_bytes"}),
}

_PROFILE_ENVIRONMENTS = {
    "rtx_3090_ti": {"wsl2_cuda"},
    "m1_pro_16gb": {"macos_metal"},
    "galaxy_s21_ultra": {"android_native"},
    "iphone_17_pro_max": {"ios_native"},
    "gtx_1080_ti": {"wsl2_cuda_helper", "windows_cuda_helper"},
}
_PROFILE_ROLES = {
    "rtx_3090_ti": {"primary"},
    "m1_pro_16gb": {"worker"},
    "galaxy_s21_ultra": {"worker"},
    "iphone_17_pro_max": {"worker"},
    "gtx_1080_ti": {"helper"},
}
_CLOCKS_BY_ENVIRONMENT = {
    "wsl2_cuda": {"clock_monotonic", "clock_monotonic_raw"},
    "wsl2_cuda_helper": {"clock_monotonic", "clock_monotonic_raw"},
    "windows_cuda_helper": {"query_performance_counter"},
    "macos_metal": {"mach_continuous_time"},
    "android_native": {"android_elapsed_realtime_nanos"},
    "ios_native": {"mach_continuous_time"},
}
_ATTRIBUTION_BY_ENVIRONMENT = {
    "wsl2_cuda": {"nvml_pid_plus_linux_process_tree"},
    "wsl2_cuda_helper": {"nvml_pid_plus_linux_process_tree"},
    "windows_cuda_helper": {"nvml_pid_plus_windows_process_tree"},
    "macos_metal": {"darwin_process_tree"},
    "android_native": {"android_uid_process"},
    "ios_native": {"ios_app_process"},
}
_EXPECTED_LIFECYCLE = {
    "rtx_3090_ti": "active",
    "m1_pro_16gb": "active",
    "galaxy_s21_ultra": "foreground",
    "iphone_17_pro_max": "foreground",
    "gtx_1080_ti": "active",
}
_MEMORY_COMPONENTS = {
    "rtx_3090_ti": ("process_memory_bytes", "gpu_memory_used_bytes"),
    "m1_pro_16gb": ("process_memory_bytes", "unified_memory_used_bytes"),
    "galaxy_s21_ultra": ("process_memory_bytes",),
    "iphone_17_pro_max": ("process_memory_bytes",),
    "gtx_1080_ti": ("process_memory_bytes", "gpu_memory_used_bytes"),
}
_MEMORY_COMBINATION_METHOD = {
    "rtx_3090_ti": "sum_disjoint_host_and_device_physical_bytes",
    "m1_pro_16gb": "max_shared_unified_physical_bytes",
    "galaxy_s21_ultra": "process_physical_bytes",
    "iphone_17_pro_max": "process_physical_bytes",
    "gtx_1080_ti": "sum_disjoint_host_and_device_physical_bytes",
}
_THERMAL_STATES = {
    "nominal",
    "fair",
    "serious",
    "critical",
    "emergency",
    "shutdown",
    "unknown",
}
_THERMAL_ORDER = {
    "unknown": -1,
    "nominal": 0,
    "fair": 1,
    "serious": 2,
    "critical": 3,
    "emergency": 4,
    "shutdown": 5,
}
_PROHIBITED_THERMAL_STATES = {"serious", "critical", "emergency", "shutdown"}
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
_MISSING_REASONS = {
    "collector_unavailable",
    "permission_denied",
    "sensor_unavailable",
    "unsupported_runtime",
    "collection_failed",
    "no_samples_returned",
}
_OVERHEAD_MISSING_REASONS = {
    "calibration_not_run",
    "calibration_failed",
    "calibration_artifact_missing",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROOT_FIELDS = {
    "schema_version",
    "telemetry_id",
    "evidence_class",
    "identity",
    "clock",
    "isolation",
    "series",
    "overhead",
    "summary",
    "quality",
}
_IDENTITY_FIELDS = {
    "run_id",
    "run_provenance_sha256",
    "suite_lock_sha256",
    "cell_id",
    "device_profile_id",
    "device_role",
    "execution_environment",
    "device_capability_sha256",
    "hardware_identity_sha256",
    "host_software_identity_sha256",
    "guest_software_identity_sha256",
    "runtime_identity_sha256",
    "launch_config_sha256",
    "model_artifact_sha256",
    "load_profile_sha256",
    "topology_sha256",
    "collector_identity_sha256",
    "collection_config_sha256",
}
_CLOCK_FIELDS = {
    "clock_id",
    "clock_identity_sha256",
    "resolution_ns",
    "start_monotonic_ns",
    "end_monotonic_ns",
}
_ISOLATION_INPUT_FIELDS = {
    "exclusive_device_lease",
    "background_policy_sha256",
    "workload_process_set_sha256",
    "attribution_method",
    "attributable_metrics",
}
_SERIES_FIELDS = {
    "metric",
    "status",
    "unit",
    "scope",
    "interval_ns",
    "source_provenance_sha256",
    "reason_code",
    "samples",
}
_SAMPLE_FIELDS = {"slot", "monotonic_ns", "value"}
_OVERHEAD_INPUT_FIELDS = {
    "status",
    "reason_code",
    "attempt_provenance_sha256",
    "pairs",
}
_OVERHEAD_PAIR_FIELDS = {
    "schedule_sha256",
    "baseline_run_sha256",
    "instrumented_run_sha256",
    "baseline_duration_ns",
    "instrumented_duration_ns",
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


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ContractError(
            f"{path} must be a non-empty string of at most 512 characters"
        )
    return value


def _sha256(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        suffix = " or null" if nullable else ""
        raise ContractError(f"{path} must be a lowercase SHA-256 digest{suffix}")
    return value


def _integer(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = (1 << 63) - 1,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ContractError(
            f"{path} must be an integer from {minimum} through {maximum}"
        )
    return value


def _number(
    value: Any,
    path: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or result < minimum or result > maximum:
        raise ContractError(
            f"{path} must be a finite number from {minimum} through {maximum}"
        )
    return result


def _validate_identity(value: Any) -> dict[str, Any]:
    raw = _exact(value, _IDENTITY_FIELDS, "identity")
    identity: dict[str, Any] = {
        "run_id": _text(raw["run_id"], "identity.run_id"),
    }
    digest_fields = _IDENTITY_FIELDS - {
        "run_id",
        "device_profile_id",
        "device_role",
        "execution_environment",
        "guest_software_identity_sha256",
    }
    for field in sorted(digest_fields):
        identity[field] = _sha256(raw[field], f"identity.{field}")
    identity["guest_software_identity_sha256"] = _sha256(
        raw["guest_software_identity_sha256"],
        "identity.guest_software_identity_sha256",
        nullable=True,
    )
    profile = raw["device_profile_id"]
    if profile not in PROFILE_REQUIRED_METRICS:
        raise ContractError("identity.device_profile_id is not in the fleet policy")
    identity["device_profile_id"] = profile
    environment = raw["execution_environment"]
    if environment not in _PROFILE_ENVIRONMENTS[profile]:
        raise ContractError(
            "identity.execution_environment is invalid for the device profile"
        )
    identity["execution_environment"] = environment
    role = raw["device_role"]
    if role not in _PROFILE_ROLES[profile]:
        raise ContractError("identity.device_role is invalid for the device profile")
    identity["device_role"] = role
    guest = identity["guest_software_identity_sha256"]
    if environment.startswith("wsl2_") != (guest is not None):
        raise ContractError(
            "WSL environments require a guest software identity and native "
            "environments forbid one"
        )
    return {field: identity[field] for field in sorted(_IDENTITY_FIELDS)}


def _validate_clock(value: Any, identity: Mapping[str, Any]) -> dict[str, Any]:
    raw = _exact(value, _CLOCK_FIELDS, "clock")
    clock_id = raw["clock_id"]
    allowed = _CLOCKS_BY_ENVIRONMENT[identity["execution_environment"]]
    if clock_id not in allowed:
        raise ContractError("clock.clock_id is invalid for the execution environment")
    start = _integer(raw["start_monotonic_ns"], "clock.start_monotonic_ns")
    end = _integer(raw["end_monotonic_ns"], "clock.end_monotonic_ns")
    if end <= start:
        raise ContractError("clock.end_monotonic_ns must be greater than the start")
    return {
        "clock_id": clock_id,
        "clock_identity_sha256": _sha256(
            raw["clock_identity_sha256"], "clock.clock_identity_sha256"
        ),
        "resolution_ns": _integer(
            raw["resolution_ns"],
            "clock.resolution_ns",
            minimum=1,
            maximum=50_000_000,
        ),
        "start_monotonic_ns": start,
        "end_monotonic_ns": end,
    }


def _validate_isolation_input(
    value: Any, identity: Mapping[str, Any]
) -> dict[str, Any]:
    raw = _exact(value, _ISOLATION_INPUT_FIELDS, "isolation")
    exclusive = raw["exclusive_device_lease"]
    if not isinstance(exclusive, bool):
        raise ContractError("isolation.exclusive_device_lease must be boolean")
    method = raw["attribution_method"]
    allowed = _ATTRIBUTION_BY_ENVIRONMENT[identity["execution_environment"]]
    if method not in allowed:
        raise ContractError(
            "isolation.attribution_method is invalid for the execution environment"
        )
    metrics = raw["attributable_metrics"]
    if not isinstance(metrics, list):
        raise ContractError("isolation.attributable_metrics must be an array")
    checked_metrics: list[str] = []
    for index, metric in enumerate(metrics):
        if metric not in METRIC_NAMES:
            raise ContractError(
                f"isolation.attributable_metrics[{index}] is not a known metric"
            )
        checked_metrics.append(metric)
    if len(checked_metrics) != len(set(checked_metrics)):
        raise ContractError("isolation.attributable_metrics must be unique")
    if "process_memory_bytes" not in checked_metrics:
        raise ContractError(
            "isolation.attributable_metrics must include process_memory_bytes"
        )
    checked_metrics.sort(key=METRIC_NAMES.index)
    base = {
        "exclusive_device_lease": exclusive,
        "background_policy_sha256": _sha256(
            raw["background_policy_sha256"],
            "isolation.background_policy_sha256",
        ),
        "workload_process_set_sha256": _sha256(
            raw["workload_process_set_sha256"],
            "isolation.workload_process_set_sha256",
        ),
        "attribution_method": method,
        "attributable_metrics": checked_metrics,
    }
    attribution_identity = {
        "device_capability_sha256": identity["device_capability_sha256"],
        "execution_environment": identity["execution_environment"],
        "workload_process_set_sha256": base["workload_process_set_sha256"],
        "attribution_method": method,
        "attributable_metrics": checked_metrics,
        "collector_identity_sha256": identity["collector_identity_sha256"],
        "collection_config_sha256": identity["collection_config_sha256"],
    }
    return {
        **base,
        "attribution_sha256": sha256_hex(canonical_json_bytes(attribution_identity)),
    }


def _metric_value(metric: str, value: Any, path: str) -> Any:
    if metric in _INTEGER_METRICS:
        return _integer(value, path)
    if metric in _BOOLEAN_METRICS:
        if not isinstance(value, bool):
            raise ContractError(f"{path} must be boolean")
        return value
    if metric == "thermal_state":
        if value not in _THERMAL_STATES:
            raise ContractError(f"{path} is not a normalized thermal state")
        return value
    if metric == "lifecycle_state":
        if value not in _LIFECYCLE_STATES:
            raise ContractError(f"{path} is not a normalized lifecycle state")
        return value
    limits = {
        "gpu_power_w": (0.0, 10_000.0),
        "system_power_w": (0.0, 10_000.0),
        "battery_power_w": (0.0, 2_000.0),
        "cumulative_energy_j": (0.0, 1e15),
        "temperature_c": (-100.0, 500.0),
        "gpu_utilization_pct": (0.0, 100.0),
    }
    minimum, maximum = limits[metric]
    return _number(value, path, minimum=minimum, maximum=maximum)


def _expected_sample_count(clock: Mapping[str, Any], interval_ns: int) -> int:
    start_ns = int(clock["start_monotonic_ns"])
    end_ns = int(clock["end_monotonic_ns"])
    duration = end_ns - start_ns
    return (duration + interval_ns - 1) // interval_ns


def _validate_series(
    values: Any,
    identity: Mapping[str, Any],
    clock: Mapping[str, Any],
    isolation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ContractError("series must be an array")
    if len(values) != len(METRIC_NAMES):
        raise ContractError("series must contain every telemetry metric exactly once")
    profile = identity["device_profile_id"]
    not_applicable = PROFILE_NOT_APPLICABLE_METRICS[profile]
    checked_by_metric: dict[str, dict[str, Any]] = {}
    total_samples = 0
    for index, value in enumerate(values):
        path = f"series[{index}]"
        raw = _exact(value, _SERIES_FIELDS, path)
        metric = raw["metric"]
        if metric not in METRIC_NAMES:
            raise ContractError(f"{path}.metric is not a known telemetry metric")
        if metric in checked_by_metric:
            raise ContractError(f"series contains duplicate metric {metric}")
        if raw["unit"] != _METRIC_UNITS[metric]:
            raise ContractError(f"{path}.unit is invalid for {metric}")
        status = raw["status"]
        if status not in {"measured", "missing", "not_applicable"}:
            raise ContractError(f"{path}.status is invalid")
        if (metric in not_applicable) != (status == "not_applicable"):
            raise ContractError(
                f"{metric} not-applicable status contradicts the device profile"
            )
        samples = raw["samples"]
        if not isinstance(samples, list):
            raise ContractError(f"{path}.samples must be an array")
        if status == "not_applicable":
            if (
                raw["scope"] != "not_applicable"
                or raw["interval_ns"] is not None
                or raw["source_provenance_sha256"] is not None
                or raw["reason_code"] != "metric_not_applicable_to_device_profile"
                or samples
            ):
                raise ContractError(f"{path} has invalid not-applicable representation")
            checked_by_metric[metric] = dict(raw)
            continue
        if raw["scope"] not in _SCOPE_BY_METRIC[metric]:
            raise ContractError(f"{path}.scope is invalid for {metric}")
        interval = _integer(raw["interval_ns"], f"{path}.interval_ns", minimum=1)
        if interval < clock["resolution_ns"]:
            raise ContractError(
                f"{path}.interval_ns cannot be finer than the monotonic clock"
            )
        expected_count = _expected_sample_count(clock, interval)
        if expected_count > MAX_TELEMETRY_SAMPLES:
            raise ContractError(f"{path} sampling grid exceeds the sample limit")
        source_hash = _sha256(
            raw["source_provenance_sha256"],
            f"{path}.source_provenance_sha256",
        )
        if status == "missing":
            if raw["reason_code"] not in _MISSING_REASONS or samples:
                raise ContractError(f"{path} has invalid missing representation")
            checked_by_metric[metric] = {
                **dict(raw),
                "interval_ns": interval,
                "source_provenance_sha256": source_hash,
            }
            continue
        if raw["reason_code"] is not None or not samples:
            raise ContractError(
                f"{path} measured series requires samples and null reason"
            )
        normalized_samples: list[dict[str, Any]] = []
        previous_slot = -1
        previous_time = -1
        for sample_index, sample_value in enumerate(samples):
            sample_path = f"{path}.samples[{sample_index}]"
            sample = _exact(sample_value, _SAMPLE_FIELDS, sample_path)
            slot = _integer(sample["slot"], f"{sample_path}.slot")
            if slot >= expected_count or slot <= previous_slot:
                raise ContractError(
                    f"{path}.samples must use unique, strictly increasing grid slots"
                )
            timestamp = _integer(sample["monotonic_ns"], f"{sample_path}.monotonic_ns")
            slot_start = clock["start_monotonic_ns"] + slot * interval
            slot_end = min(slot_start + interval, clock["end_monotonic_ns"])
            if not slot_start <= timestamp < slot_end or timestamp <= previous_time:
                raise ContractError(
                    f"{sample_path}.monotonic_ns is outside its monotonic grid slot"
                )
            normalized_samples.append(
                {
                    "slot": slot,
                    "monotonic_ns": timestamp,
                    "value": _metric_value(
                        metric, sample["value"], f"{sample_path}.value"
                    ),
                }
            )
            previous_slot = slot
            previous_time = timestamp
        if metric == "cumulative_energy_j":
            energies = [sample["value"] for sample in normalized_samples]
            if len(energies) < 2 or any(
                latter < former for former, latter in zip(energies, energies[1:])
            ):
                raise ContractError(
                    "cumulative_energy_j needs at least two nondecreasing samples"
                )
        total_samples += len(normalized_samples)
        if total_samples > MAX_TELEMETRY_SAMPLES:
            raise ContractError("telemetry bundle exceeds the total sample limit")
        checked_by_metric[metric] = {
            "metric": metric,
            "status": status,
            "unit": raw["unit"],
            "scope": raw["scope"],
            "interval_ns": interval,
            "source_provenance_sha256": source_hash,
            "reason_code": None,
            "samples": normalized_samples,
        }
    attributable = set(isolation["attributable_metrics"])
    required_memory_components = set(_MEMORY_COMPONENTS[profile])
    if not required_memory_components.issubset(attributable):
        raise ContractError(
            "isolation.attributable_metrics omits a profile memory component"
        )
    for metric in METRIC_NAMES:
        series = checked_by_metric[metric]
        is_process_scoped = series["scope"] in _PROCESS_SCOPES
        if (metric in attributable) != is_process_scoped:
            raise ContractError(
                f"{metric} scope and isolation.attributable_metrics disagree"
            )
    return [checked_by_metric[metric] for metric in METRIC_NAMES]


def _calibration_context(identity: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "device_capability_sha256": identity["device_capability_sha256"],
                "execution_environment": identity["execution_environment"],
                "runtime_identity_sha256": identity["runtime_identity_sha256"],
                "launch_config_sha256": identity["launch_config_sha256"],
                "model_artifact_sha256": identity["model_artifact_sha256"],
                "load_profile_sha256": identity["load_profile_sha256"],
                "topology_sha256": identity["topology_sha256"],
                "collection_config_sha256": identity["collection_config_sha256"],
            }
        )
    )


def _validate_overhead_input(value: Any, identity: Mapping[str, Any]) -> dict[str, Any]:
    raw = _exact(value, _OVERHEAD_INPUT_FIELDS, "overhead")
    status = raw["status"]
    context = _calibration_context(identity)
    pairs = raw["pairs"]
    if not isinstance(pairs, list):
        raise ContractError("overhead.pairs must be an array")
    if status == "missing":
        if (
            raw["reason_code"] not in _OVERHEAD_MISSING_REASONS
            or _sha256(
                raw["attempt_provenance_sha256"],
                "overhead.attempt_provenance_sha256",
            )
            is None
            or pairs
        ):
            raise ContractError("overhead has invalid missing representation")
        return {
            "status": "missing",
            "reason_code": raw["reason_code"],
            "attempt_provenance_sha256": raw["attempt_provenance_sha256"],
            "pairs": [],
            "maximum_allowed_fraction": MAXIMUM_OVERHEAD_FRACTION,
            "estimated_overhead_fraction": None,
            "calibration_context_sha256": context,
            "calibration_sha256": None,
        }
    if status != "measured":
        raise ContractError("overhead.status must be measured or missing")
    if raw["reason_code"] is not None or raw["attempt_provenance_sha256"] is not None:
        raise ContractError("measured overhead requires null missing metadata")
    if len(pairs) < MINIMUM_OVERHEAD_PAIRS:
        raise ContractError(
            f"measured overhead requires at least {MINIMUM_OVERHEAD_PAIRS} pairs"
        )
    if len(pairs) > MAXIMUM_OVERHEAD_PAIRS:
        raise ContractError(
            f"measured overhead permits at most {MAXIMUM_OVERHEAD_PAIRS} pairs"
        )
    checked_pairs = []
    schedules: list[str] = []
    run_hashes: list[str] = []
    for index, pair_value in enumerate(pairs):
        path = f"overhead.pairs[{index}]"
        pair = _exact(pair_value, _OVERHEAD_PAIR_FIELDS, path)
        checked = {
            "schedule_sha256": _sha256(
                pair["schedule_sha256"], f"{path}.schedule_sha256"
            ),
            "baseline_run_sha256": _sha256(
                pair["baseline_run_sha256"], f"{path}.baseline_run_sha256"
            ),
            "instrumented_run_sha256": _sha256(
                pair["instrumented_run_sha256"],
                f"{path}.instrumented_run_sha256",
            ),
            "baseline_duration_ns": _integer(
                pair["baseline_duration_ns"],
                f"{path}.baseline_duration_ns",
                minimum=1,
            ),
            "instrumented_duration_ns": _integer(
                pair["instrumented_duration_ns"],
                f"{path}.instrumented_duration_ns",
                minimum=1,
            ),
        }
        schedules.append(checked["schedule_sha256"])  # type: ignore[arg-type]
        run_hashes.extend(
            [checked["baseline_run_sha256"], checked["instrumented_run_sha256"]]  # type: ignore[list-item]
        )
        checked_pairs.append(checked)
    if len(schedules) != len(set(schedules)):
        raise ContractError("overhead calibration schedules must be unique")
    if len(run_hashes) != len(set(run_hashes)):
        raise ContractError("overhead calibration run hashes must be unique")
    checked_pairs.sort(key=lambda pair: pair["schedule_sha256"])  # type: ignore[arg-type, return-value]
    log_ratios = [
        math.log(pair["instrumented_duration_ns"])  # type: ignore[arg-type]
        - math.log(pair["baseline_duration_ns"])  # type: ignore[arg-type]
        for pair in checked_pairs
    ]
    estimated = max(0.0, math.exp(math.fsum(log_ratios) / len(log_ratios)) - 1.0)
    calibration = {
        "calibration_context_sha256": context,
        "pairs": checked_pairs,
    }
    return {
        "status": "measured",
        "reason_code": None,
        "attempt_provenance_sha256": None,
        "pairs": checked_pairs,
        "maximum_allowed_fraction": MAXIMUM_OVERHEAD_FRACTION,
        "estimated_overhead_fraction": estimated,
        "calibration_context_sha256": context,
        "calibration_sha256": sha256_hex(canonical_json_bytes(calibration)),
    }


def _series_summary(
    series: Mapping[str, Any], clock: Mapping[str, Any]
) -> dict[str, Any]:
    status = series["status"]
    if status == "not_applicable":
        expected: int | None = None
        coverage: float | None = None
    else:
        expected = _expected_sample_count(clock, series["interval_ns"])
        coverage = len(series["samples"]) / expected
    values = [sample["value"] for sample in series["samples"]]
    minimum = maximum = mean = true_fraction = None
    states: list[str] = []
    if values and series["metric"] not in _STATE_METRICS | _BOOLEAN_METRICS:
        minimum = min(values)
        maximum = max(values)
        mean = math.fsum(values) / len(values)
    elif values and series["metric"] in _BOOLEAN_METRICS:
        true_fraction = sum(1 for value in values if value) / len(values)
    elif values:
        states = sorted(set(values))
    return {
        "status": status,
        "scope": series["scope"],
        "sample_count": len(values),
        "expected_sample_count": expected,
        "coverage_fraction": coverage,
        "minimum": minimum,
        "maximum": maximum,
        "mean": mean,
        "true_fraction": true_fraction,
        "observed_states": states,
    }


def _memory_summary(
    identity: Mapping[str, Any],
    isolation: Mapping[str, Any],
    by_metric: Mapping[str, Mapping[str, Any]],
    clock: Mapping[str, Any],
) -> dict[str, Any]:
    profile = identity["device_profile_id"]
    components = _MEMORY_COMPONENTS[profile]
    component_series = [by_metric[metric] for metric in components]
    measured = all(item["status"] == "measured" for item in component_series)
    intervals = {
        item["interval_ns"]
        for item in component_series
        if item["status"] != "not_applicable"
    }
    interval: int | None = next(iter(intervals)) if len(intervals) == 1 else None
    expected = _expected_sample_count(clock, interval) if interval is not None else None
    aligned_slots: set[int] = set()
    common_slots: set[int] = set()
    maximum_skew: int | None = None
    tolerance = (
        max(
            clock["resolution_ns"],
            min(50_000_000, max(1, interval // 10)),
        )
        if interval is not None
        else None
    )
    observed_peak: int | None = None
    if measured and interval is not None:
        samples_by_metric = {
            metric: {sample["slot"]: sample for sample in by_metric[metric]["samples"]}
            for metric in components
        }
        common_slots = set.intersection(
            *(set(samples_by_metric[metric]) for metric in components)
        )
        combined: list[int] = []
        observed_skews = []
        for slot in sorted(common_slots):
            rows = [samples_by_metric[metric][slot] for metric in components]
            timestamps = [row["monotonic_ns"] for row in rows]
            skew = max(timestamps) - min(timestamps)
            observed_skews.append(skew)
            assert tolerance is not None  # nosec B101
            if skew > tolerance:
                continue
            aligned_slots.add(slot)
            values = [row["value"] for row in rows]
            if profile in {"rtx_3090_ti", "gtx_1080_ti"}:
                combined.append(sum(values))
            else:
                # Apple unified-memory counters can overlap.  The larger
                # physical footprint is retained once; it is never summed.
                combined.append(max(values))
        observed_peak = max(combined) if combined else None
        maximum_skew = max(observed_skews) if observed_skews else None
    coverage = (
        len(aligned_slots) / expected if expected is not None and expected > 0 else 0.0
    )
    if not measured:
        status = "missing_stream"
    elif interval is None:
        status = "interval_mismatch"
    elif coverage < MINIMUM_COVERAGE_FRACTION:
        status = "insufficient_coverage"
    else:
        status = "complete"
    promotable_peak = observed_peak if status == "complete" else None
    memory_base = {
        "scope": MEMORY_SCOPE,
        "combination_method": _MEMORY_COMBINATION_METHOD[profile],
        "component_metrics": list(components),
        "alignment_status": status,
        "alignment_interval_ns": interval,
        "alignment_tolerance_ns": tolerance,
        "maximum_observed_alignment_skew_ns": maximum_skew,
        "expected_sample_count": expected,
        "common_sample_count": len(common_slots),
        "aligned_sample_count": len(aligned_slots),
        "skew_rejected_sample_count": len(common_slots) - len(aligned_slots),
        "coverage_fraction": coverage,
        "observed_peak_bytes": observed_peak,
        "peak_attributable_active_memory_bytes": promotable_peak,
        "unified_memory_counted_once": True,
    }
    provenance = {
        "identity": {
            "run_provenance_sha256": identity["run_provenance_sha256"],
            "device_capability_sha256": identity["device_capability_sha256"],
            "hardware_identity_sha256": identity["hardware_identity_sha256"],
            "runtime_identity_sha256": identity["runtime_identity_sha256"],
        },
        "clock": clock,
        "attribution_sha256": isolation["attribution_sha256"],
        "component_series": [by_metric[metric] for metric in components],
        "derived": memory_base,
    }
    return {
        **memory_base,
        "memory_provenance_sha256": sha256_hex(canonical_json_bytes(provenance)),
    }


def _build_summary(
    identity: Mapping[str, Any],
    isolation: Mapping[str, Any],
    series: Sequence[Mapping[str, Any]],
    clock: Mapping[str, Any],
) -> dict[str, Any]:
    by_metric = {item["metric"]: item for item in series}
    summaries = {
        metric: _series_summary(by_metric[metric], clock) for metric in METRIC_NAMES
    }

    def maximum(metric: str) -> Any:
        """Return the maximum observed value for ``metric`` (default 0)."""
        return summaries[metric]["maximum"]

    energy_samples = by_metric["cumulative_energy_j"]["samples"]
    energy_delta = (
        energy_samples[-1]["value"] - energy_samples[0]["value"]
        if energy_samples
        else None
    )
    throttle_values = [
        sample["value"] for sample in by_metric["thermal_throttle_active"]["samples"]
    ]
    thermal_states = summaries["thermal_state"]["observed_states"]
    peak_thermal = (
        max(thermal_states, key=_THERMAL_ORDER.__getitem__) if thermal_states else None
    )
    lifecycle_states = summaries["lifecycle_state"]["observed_states"]
    memory = _memory_summary(identity, isolation, by_metric, clock)
    return {
        "duration_ns": clock["end_monotonic_ns"] - clock["start_monotonic_ns"],
        "metric_summaries": summaries,
        "energy_delta_j": energy_delta,
        "memory": memory,
        "peak_attributable_active_memory_bytes": memory[
            "peak_attributable_active_memory_bytes"
        ],
        "peak_gpu_memory_bytes": maximum("gpu_memory_used_bytes"),
        "peak_unified_memory_bytes": maximum("unified_memory_used_bytes"),
        "peak_temperature_c": maximum("temperature_c"),
        "throttle_observed": any(throttle_values) if throttle_values else None,
        "thermal_state_peak": peak_thermal,
        "lifecycle_states": lifecycle_states,
    }


def _build_quality(
    identity: Mapping[str, Any],
    isolation: Mapping[str, Any],
    series: Sequence[Mapping[str, Any]],
    overhead: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    profile = identity["device_profile_id"]
    required = [
        metric for metric in METRIC_NAMES if metric in PROFILE_REQUIRED_METRICS[profile]
    ]
    by_metric = {item["metric"]: item for item in series}
    metric_summaries = summary["metric_summaries"]
    missing = [
        metric for metric in required if by_metric[metric]["status"] != "measured"
    ]
    low_coverage = [
        metric
        for metric in required
        if by_metric[metric]["status"] == "measured"
        and metric_summaries[metric]["coverage_fraction"] < MINIMUM_COVERAGE_FRACTION
    ]
    not_evaluable = [f"required metric {metric} is missing" for metric in missing]
    not_evaluable.extend(
        f"required metric {metric} coverage is below {MINIMUM_COVERAGE_FRACTION}"
        for metric in low_coverage
    )
    if overhead["status"] != "measured":
        not_evaluable.append("instrumentation overhead calibration is missing")
    if summary["energy_delta_j"] is not None and summary["energy_delta_j"] <= 0.0:
        not_evaluable.append("cumulative energy delta is not positive")
    if summary["memory"]["alignment_status"] != "complete":
        not_evaluable.append(
            "time-aligned attributable physical-memory peak is not complete"
        )
    device_scoped_energy = any(
        by_metric[metric]["status"] == "measured"
        and by_metric[metric]["scope"] in {"device", "system"}
        for metric in _POWER_METRICS
    )
    if device_scoped_energy and not isolation["exclusive_device_lease"]:
        not_evaluable.append(
            "device-scoped power or energy lacks an exclusive device lease"
        )

    failures: list[str] = []
    estimated = overhead["estimated_overhead_fraction"]
    if estimated is not None and estimated > MAXIMUM_OVERHEAD_FRACTION:
        failures.append("instrumentation overhead exceeds the 5% maximum")
    if summary["throttle_observed"] is True:
        failures.append("thermal throttling was observed")
    peak_state = summary["thermal_state_peak"]
    if peak_state in _PROHIBITED_THERMAL_STATES:
        failures.append("a prohibited thermal state was observed")
    if "unknown" in summary["metric_summaries"]["thermal_state"]["observed_states"]:
        not_evaluable.append("thermal state contains unknown observations")
    lifecycle = set(summary["lifecycle_states"])
    expected_lifecycle = _EXPECTED_LIFECYCLE[profile]
    if "unknown" in lifecycle:
        not_evaluable.append("lifecycle state contains unknown observations")
    if lifecycle and lifecycle != {expected_lifecycle}:
        failures.append(
            f"lifecycle left the required {expected_lifecycle} state during the window"
        )
    optional_missing = [
        metric
        for metric in METRIC_NAMES
        if metric not in PROFILE_REQUIRED_METRICS[profile]
        and metric not in PROFILE_NOT_APPLICABLE_METRICS[profile]
        and by_metric[metric]["status"] == "missing"
    ]
    status = "fail" if failures else "not_evaluable" if not_evaluable else "pass"
    required_coverages = [
        metric_summaries[metric]["coverage_fraction"]
        if by_metric[metric]["status"] == "measured"
        else 0.0
        for metric in required
    ]
    return {
        "status": status,
        "not_evaluable_reasons": not_evaluable,
        "failure_reasons": failures,
        "required_metrics": required,
        "missing_required_metrics": missing,
        "low_coverage_required_metrics": low_coverage,
        "optional_missing_metrics": optional_missing,
        "minimum_required_coverage_fraction": MINIMUM_COVERAGE_FRACTION,
        "minimum_required_coverage_observed": min(required_coverages),
        "maximum_overhead_fraction": MAXIMUM_OVERHEAD_FRACTION,
    }


def build_telemetry_bundle(
    *,
    identity: Mapping[str, Any],
    clock: Mapping[str, Any],
    isolation: Mapping[str, Any],
    series: Sequence[Mapping[str, Any]],
    overhead: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate raw normalized samples and build all persisted derived values."""

    checked_identity = _validate_identity(identity)
    checked_clock = _validate_clock(clock, checked_identity)
    checked_isolation = _validate_isolation_input(isolation, checked_identity)
    checked_series = _validate_series(
        list(series), checked_identity, checked_clock, checked_isolation
    )
    checked_overhead = _validate_overhead_input(overhead, checked_identity)
    base = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "evidence_class": "local_measured",
        "identity": checked_identity,
        "clock": checked_clock,
        "isolation": checked_isolation,
        "series": checked_series,
        "overhead": checked_overhead,
    }
    if contains_secret(base):
        raise ContractError("telemetry bundle contains a credential")
    telemetry_id = sha256_hex(canonical_json_bytes(base))
    summary = _build_summary(
        checked_identity, checked_isolation, checked_series, checked_clock
    )
    quality = _build_quality(
        checked_identity,
        checked_isolation,
        checked_series,
        checked_overhead,
        summary,
    )
    result = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "telemetry_id": telemetry_id,
        "evidence_class": "local_measured",
        "identity": checked_identity,
        "clock": checked_clock,
        "isolation": checked_isolation,
        "series": checked_series,
        "overhead": checked_overhead,
        "summary": summary,
        "quality": quality,
    }
    try:
        encoded = canonical_json_bytes(result)
    except (TypeError, ValueError) as exc:
        raise ContractError("telemetry bundle must contain finite JSON values") from exc
    if len(encoded) > MAX_TELEMETRY_BUNDLE_BYTES:
        raise ContractError("telemetry bundle exceeds the normalized byte limit")
    return result


def _raw_isolation(value: Any) -> dict[str, Any]:
    raw = _mapping(value, "telemetry.isolation")
    expected = _ISOLATION_INPUT_FIELDS | {"attribution_sha256"}
    _exact(raw, expected, "telemetry.isolation")
    return {field: raw[field] for field in _ISOLATION_INPUT_FIELDS}


def _raw_overhead(value: Any) -> dict[str, Any]:
    raw = _mapping(value, "telemetry.overhead")
    expected = _OVERHEAD_INPUT_FIELDS | {
        "maximum_allowed_fraction",
        "estimated_overhead_fraction",
        "calibration_context_sha256",
        "calibration_sha256",
    }
    _exact(raw, expected, "telemetry.overhead")
    return {field: raw[field] for field in _OVERHEAD_INPUT_FIELDS}


def validate_telemetry_bundle(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a persisted bundle by rebuilding every hash and summary."""

    root = _exact(record, _ROOT_FIELDS, "telemetry")
    if root["schema_version"] != TELEMETRY_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {TELEMETRY_SCHEMA_VERSION}")
    if root["evidence_class"] != "local_measured":
        raise ContractError("telemetry.evidence_class must be local_measured")
    if not isinstance(root["series"], list):
        raise ContractError("telemetry.series must be an array")
    try:
        encoded = canonical_json_bytes(root)
    except (TypeError, ValueError) as exc:
        raise ContractError("telemetry bundle must contain finite JSON values") from exc
    if len(encoded) > MAX_TELEMETRY_BUNDLE_BYTES:
        raise ContractError("telemetry bundle exceeds the normalized byte limit")
    if contains_secret(root):
        raise ContractError("telemetry bundle contains a credential")
    expected = build_telemetry_bundle(
        identity=_mapping(root["identity"], "telemetry.identity"),
        clock=_mapping(root["clock"], "telemetry.clock"),
        isolation=_raw_isolation(root["isolation"]),
        series=root["series"],
        overhead=_raw_overhead(root["overhead"]),
    )
    if canonical_json_bytes(root) != canonical_json_bytes(expected):
        raise ContractError(
            "telemetry bundle does not match deterministic recomputation"
        )
    return expected


def telemetry_bundle_sha256(record: Mapping[str, Any]) -> str:
    """Return the hash of one validated, canonical telemetry bundle."""

    return sha256_hex(canonical_json_bytes(validate_telemetry_bundle(record)))


__all__ = [
    "MAXIMUM_OVERHEAD_FRACTION",
    "MAXIMUM_OVERHEAD_PAIRS",
    "MAX_TELEMETRY_BUNDLE_BYTES",
    "MAX_TELEMETRY_SAMPLES",
    "METRIC_NAMES",
    "MEMORY_SCOPE",
    "MINIMUM_COVERAGE_FRACTION",
    "MINIMUM_OVERHEAD_PAIRS",
    "PROFILE_NOT_APPLICABLE_METRICS",
    "PROFILE_REQUIRED_METRICS",
    "TELEMETRY_SCHEMA_VERSION",
    "build_telemetry_bundle",
    "telemetry_bundle_sha256",
    "validate_telemetry_bundle",
]
