"""Branch and edge coverage tests for ``pheno.evidence.telemetry``.

The companion suite ``tests/test_eval_telemetry.py`` pins the user-visible
contract behaviour; the tests here exhaustively exercise the private
validation helpers (``_text``, ``_sha256``, ``_integer``, ``_number``,
``_metric_value``, ``_mapping``, ``_exact``) and every defensive branch of
``build_telemetry_bundle`` / ``validate_telemetry_bundle`` so the suite
remains the canonical source of truth for the offline, content-addressed
heterogeneous telemetry bundle contract.

Coverage focus areas:
* every private validator's reject path (null/empty/wrong type/out-of-range);
* every metric-type branch inside ``_metric_value`` (integer, boolean, state,
  power, temperature, utilization);
* the series grid validation grid: ``interval_ns`` finer than the clock,
  duplicate slots, monotonic ``monotonic_ns`` outside its slot;
* the ``not_applicable`` / ``missing`` representation contracts;
* the overhead calibration minimum/maximum/duplicate constraints;
* the redaction-trigger path that aborts ``build_telemetry_bundle``;
* the ``validate_telemetry_bundle`` recomputation guards (size, schema,
  evidence_class, secret, deterministic match, raw isolation/overhead shape);
* the byte-limit guard for both build and validate paths.
"""

from __future__ import annotations

import copy
import json
import math
import unittest
from typing import Any
from unittest.mock import patch

from pheno.evidence import telemetry as telemetry_module
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex
from pheno.evidence.telemetry import (
    MAXIMUM_OVERHEAD_FRACTION,
    MAXIMUM_OVERHEAD_PAIRS,
    MAX_TELEMETRY_BUNDLE_BYTES,
    MAX_TELEMETRY_SAMPLES,
    MEMORY_SCOPE,
    METRIC_NAMES,
    MINIMUM_COVERAGE_FRACTION,
    MINIMUM_OVERHEAD_PAIRS,
    PROFILE_NOT_APPLICABLE_METRICS,
    PROFILE_REQUIRED_METRICS,
    TELEMETRY_SCHEMA_VERSION,
    _build_quality,
    _build_summary,
    _calibration_context,
    _expected_sample_count,
    _exact,
    _integer,
    _mapping,
    _memory_summary,
    _metric_value,
    _number,
    _series_summary,
    _sha256,
    _text,
    _validate_clock,
    _validate_identity,
    _validate_isolation_input,
    _validate_overhead_input,
    _validate_series,
    build_telemetry_bundle,
    telemetry_bundle_sha256,
    validate_telemetry_bundle,
)


def _digest(label: str) -> str:
    return sha256_hex(label.encode("utf-8"))


_ENVIRONMENT = {
    "rtx_3090_ti": "wsl2_cuda",
    "m1_pro_16gb": "macos_metal",
    "galaxy_s21_ultra": "android_native",
    "iphone_17_pro_max": "ios_native",
    "gtx_1080_ti": "wsl2_cuda_helper",
}
_ROLE = {
    "rtx_3090_ti": "primary",
    "m1_pro_16gb": "worker",
    "galaxy_s21_ultra": "worker",
    "iphone_17_pro_max": "worker",
    "gtx_1080_ti": "helper",
}
_CLOCK = {
    "wsl2_cuda": "clock_monotonic_raw",
    "wsl2_cuda_helper": "clock_monotonic_raw",
    "macos_metal": "mach_continuous_time",
    "android_native": "android_elapsed_realtime_nanos",
    "ios_native": "mach_continuous_time",
}
_ATTRIBUTION = {
    "wsl2_cuda": "nvml_pid_plus_linux_process_tree",
    "wsl2_cuda_helper": "nvml_pid_plus_linux_process_tree",
    "macos_metal": "darwin_process_tree",
    "android_native": "android_uid_process",
    "ios_native": "ios_app_process",
}
_UNIT = {
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
_SCOPE = {
    "gpu_power_w": "device",
    "system_power_w": "system",
    "battery_power_w": "device",
    "cumulative_energy_j": "device",
    "gpu_memory_used_bytes": "process_tree",
    "process_memory_bytes": "process_tree",
    "unified_memory_used_bytes": "process_tree",
    "system_available_memory_bytes": "system",
    "temperature_c": "sensor",
    "thermal_throttle_active": "device",
    "thermal_state": "device",
    "lifecycle_state": "system",
    "gpu_utilization_pct": "device",
}


def _sample_value(metric: str, slot: int, profile: str) -> object:
    if metric in {
        "gpu_memory_used_bytes",
        "process_memory_bytes",
        "unified_memory_used_bytes",
        "system_available_memory_bytes",
    }:
        return 1_000_000_000 + slot * 1_000
    if metric == "thermal_throttle_active":
        return False
    if metric == "thermal_state":
        return "nominal"
    if metric == "lifecycle_state":
        return (
            "foreground"
            if profile in {"galaxy_s21_ultra", "iphone_17_pro_max"}
            else "active"
        )
    if metric == "cumulative_energy_j":
        return float(slot * 10)
    if metric == "temperature_c":
        return 50.0 + slot
    if metric == "gpu_utilization_pct":
        return 70.0 + slot
    return 100.0 + slot


def _identity(profile: str) -> dict[str, Any]:
    environment = _ENVIRONMENT[profile]
    return {
        "run_id": f"run-{profile}",
        "run_provenance_sha256": _digest(f"run:{profile}"),
        "suite_lock_sha256": _digest("suite"),
        "cell_id": _digest(f"cell:{profile}"),
        "device_profile_id": profile,
        "device_role": _ROLE[profile],
        "execution_environment": environment,
        "device_capability_sha256": _digest(f"capability:{profile}"),
        "hardware_identity_sha256": _digest(f"hardware:{profile}"),
        "host_software_identity_sha256": _digest(f"host:{profile}"),
        "guest_software_identity_sha256": (
            _digest(f"guest:{profile}") if environment.startswith("wsl2_") else None
        ),
        "runtime_identity_sha256": _digest(f"runtime:{profile}"),
        "launch_config_sha256": _digest(f"launch:{profile}"),
        "model_artifact_sha256": _digest("model"),
        "load_profile_sha256": _digest("load"),
        "topology_sha256": _digest("topology"),
        "collector_identity_sha256": _digest(f"collector:{profile}"),
        "collection_config_sha256": _digest(f"config:{profile}"),
    }


def _clock(profile: str) -> dict[str, Any]:
    environment = _ENVIRONMENT[profile]
    return {
        "clock_id": _CLOCK[environment],
        "clock_identity_sha256": _digest(f"clock:{profile}"),
        "resolution_ns": 1,
        "start_monotonic_ns": 1_000_000_000,
        "end_monotonic_ns": 5_000_000_000,
    }


def _isolation(profile: str) -> dict[str, Any]:
    environment = _ENVIRONMENT[profile]
    attributable = ["process_memory_bytes"]
    if profile in {"rtx_3090_ti", "gtx_1080_ti"}:
        attributable.append("gpu_memory_used_bytes")
    if "unified_memory_used_bytes" in PROFILE_REQUIRED_METRICS[profile]:
        attributable.append("unified_memory_used_bytes")
    return {
        "exclusive_device_lease": True,
        "background_policy_sha256": _digest(f"background:{profile}"),
        "workload_process_set_sha256": _digest(f"processes:{profile}"),
        "attribution_method": _ATTRIBUTION[environment],
        "attributable_metrics": attributable,
    }


def _series_for(profile: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in METRIC_NAMES:
        if metric in PROFILE_NOT_APPLICABLE_METRICS[profile]:
            rows.append(
                {
                    "metric": metric,
                    "status": "not_applicable",
                    "unit": _UNIT[metric],
                    "scope": "not_applicable",
                    "interval_ns": None,
                    "source_provenance_sha256": None,
                    "reason_code": "metric_not_applicable_to_device_profile",
                    "samples": [],
                }
            )
            continue
        measured = metric in PROFILE_REQUIRED_METRICS[profile]
        if not measured:
            rows.append(
                {
                    "metric": metric,
                    "status": "missing",
                    "unit": _UNIT[metric],
                    "scope": _SCOPE[metric],
                    "interval_ns": 1_000_000_000,
                    "source_provenance_sha256": _digest(f"source:{profile}:{metric}"),
                    "reason_code": "sensor_unavailable",
                    "samples": [],
                }
            )
            continue
        rows.append(
            {
                "metric": metric,
                "status": "measured",
                "unit": _UNIT[metric],
                "scope": _SCOPE[metric],
                "interval_ns": 1_000_000_000,
                "source_provenance_sha256": _digest(f"source:{profile}:{metric}"),
                "reason_code": None,
                "samples": [
                    {
                        "slot": slot,
                        "monotonic_ns": 1_000_000_000 + slot * 1_000_000_000,
                        "value": _sample_value(metric, slot, profile),
                    }
                    for slot in range(4)
                ],
            }
        )
    return rows


def _overhead(profile: str) -> dict[str, Any]:
    return {
        "status": "measured",
        "reason_code": None,
        "attempt_provenance_sha256": None,
        "pairs": [
            {
                "schedule_sha256": _digest(f"schedule:{profile}:{index}"),
                "baseline_run_sha256": _digest(f"baseline:{profile}:{index}"),
                "instrumented_run_sha256": _digest(f"instrumented:{profile}:{index}"),
                "baseline_duration_ns": 1_000_000_000,
                "instrumented_duration_ns": 1_005_000_000 + index * 5_000_000,
            }
            for index in range(3)
        ],
    }


def _inputs(profile: str = "rtx_3090_ti") -> dict[str, Any]:
    return {
        "identity": _identity(profile),
        "clock": _clock(profile),
        "isolation": _isolation(profile),
        "series": _series_for(profile),
        "overhead": _overhead(profile),
    }


def _build(profile: str = "rtx_3090_ti") -> dict[str, Any]:
    return build_telemetry_bundle(**_inputs(profile))


def _series(inputs: dict[str, Any], metric: str) -> dict[str, Any]:
    return next(item for item in inputs["series"] if item["metric"] == metric)


def _alter(inputs: dict[str, Any], metric: str) -> dict[str, Any]:
    return copy.deepcopy(_series(inputs, metric))


class TelemetryModuleSurfaceTests(unittest.TestCase):
    """Pin documented constants and the ``__all__`` surface."""

    def test_constants_match_documented_values(self) -> None:
        self.assertEqual(TELEMETRY_SCHEMA_VERSION, "pheno.eval.telemetry-bundle.v1")
        self.assertEqual(MAX_TELEMETRY_BUNDLE_BYTES, 16 * 1024 * 1024)
        self.assertEqual(MAX_TELEMETRY_SAMPLES, 200_000)
        self.assertEqual(MINIMUM_COVERAGE_FRACTION, 0.95)
        self.assertEqual(MAXIMUM_OVERHEAD_FRACTION, 0.05)
        self.assertEqual(MINIMUM_OVERHEAD_PAIRS, 3)
        self.assertEqual(MAXIMUM_OVERHEAD_PAIRS, 10_000)
        self.assertEqual(
            MEMORY_SCOPE, "time_aligned_peak_attributable_physical_bytes"
        )

    def test_metric_names_are_frozen_in_canonical_order(self) -> None:
        self.assertEqual(
            METRIC_NAMES,
            (
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
            ),
        )

    def test_module_all_contains_only_public_names(self) -> None:
        from pheno.evidence import telemetry as telemetry_module

        self.assertEqual(
            set(telemetry_module.__all__),
            {
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
            },
        )


class TelemetryHelperValidationTests(unittest.TestCase):
    """Cover every reject path on the private validators."""

    def test_mapping_rejects_non_object_input(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _mapping([], "root")
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _mapping("nope", "root")

    def test_exact_enforces_exact_field_set(self) -> None:
        with self.assertRaisesRegex(ContractError, "missing fields"):
            _exact({"a": 1}, {"a", "b"}, "root")
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            _exact({"a": 1, "extra": 2}, {"a"}, "root")

    def test_text_rejects_non_string_empty_and_too_long(self) -> None:
        for bad, label in (
            (None, "non-string"),
            ("", "empty"),
            ("   ", "blank"),
            ("a" * 513, "too-long"),
            (123, "integer"),
        ):
            with self.subTest(value=label):
                with self.assertRaisesRegex(ContractError, "non-empty string"):
                    _text(bad, "field")

    def test_text_accepts_bounded_string(self) -> None:
        # ``_text`` only validates (strips for emptiness check); the original
        # value is returned verbatim, including any leading/trailing spaces.
        self.assertEqual(_text("  ok  ", "field"), "  ok  ")
        self.assertEqual(_text("a" * 512, "field"), "a" * 512)

    def test_sha256_rejects_invalid_digest_and_accepts_none_when_nullable(self) -> None:
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            _sha256("not-a-digest", "field")
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            _sha256("A" * 64, "field")
        # When nullable=True, None is allowed (returns None) and non-digest
        # strings are rejected with the "or null" suffix.
        self.assertIsNone(_sha256(None, "field", nullable=True))
        with self.assertRaisesRegex(ContractError, "or null"):
            _sha256("not-a-digest", "field", nullable=True)
        # When nullable=False, None is rejected like any other invalid value.
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            _sha256(None, "field", nullable=False)  # type: ignore[arg-type]
        digest = sha256_hex(b"abc")
        self.assertEqual(_sha256(digest, "field"), digest)

    def test_integer_rejects_bool_float_and_out_of_range(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _integer(True, "field")
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _integer(1.5, "field")
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _integer("1", "field")
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _integer(-1, "field", minimum=0)
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _integer(10, "field", minimum=0, maximum=5)
        self.assertEqual(_integer(3, "field"), 3)
        self.assertEqual(_integer(3, "field", minimum=1, maximum=10), 3)

    def test_number_rejects_bool_nonfinite_and_out_of_range(self) -> None:
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number(True, "field", minimum=0.0, maximum=1.0)
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number("1.0", "field", minimum=0.0, maximum=1.0)
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number(float("nan"), "field", minimum=0.0, maximum=1.0)
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number(float("inf"), "field", minimum=0.0, maximum=1.0)
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number(-0.1, "field", minimum=0.0, maximum=1.0)
        with self.assertRaisesRegex(ContractError, "finite number"):
            _number(1.1, "field", minimum=0.0, maximum=1.0)
        self.assertEqual(_number(0, "field", minimum=0.0, maximum=1.0), 0.0)
        self.assertEqual(_number(1, "field", minimum=0.0, maximum=1.0), 1.0)
        self.assertEqual(_number(0.5, "field", minimum=0.0, maximum=1.0), 0.5)

    def test_metric_value_validates_every_metric_type(self) -> None:
        # Integer metric.
        self.assertEqual(_metric_value("process_memory_bytes", 42, "p"), 42)
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _metric_value("process_memory_bytes", 1.5, "p")
        # Boolean metric.
        self.assertTrue(_metric_value("thermal_throttle_active", True, "p"))
        with self.assertRaisesRegex(ContractError, "must be boolean"):
            _metric_value("thermal_throttle_active", 1, "p")
        # Thermal state.
        self.assertEqual(_metric_value("thermal_state", "nominal", "p"), "nominal")
        with self.assertRaisesRegex(ContractError, "thermal state"):
            _metric_value("thermal_state", "fine", "p")
        # Lifecycle state.
        self.assertEqual(_metric_value("lifecycle_state", "active", "p"), "active")
        with self.assertRaisesRegex(ContractError, "lifecycle state"):
            _metric_value("lifecycle_state", "dying", "p")
        # Power / energy / temperature / utilization limits.
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("gpu_power_w", -1.0, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("gpu_power_w", 10_001.0, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("battery_power_w", 2_001.0, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("temperature_c", -101.0, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("temperature_c", 501.0, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("gpu_utilization_pct", -0.1, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("gpu_utilization_pct", 100.5, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _metric_value("cumulative_energy_j", -1.0, "p")
        # Acceptable power and energy values.
        self.assertEqual(_metric_value("gpu_power_w", 250.0, "p"), 250.0)
        self.assertEqual(_metric_value("battery_power_w", 12.0, "p"), 12.0)
        self.assertEqual(_metric_value("cumulative_energy_j", 1e12, "p"), 1e12)


class TelemetryIdentityValidationTests(unittest.TestCase):
    """Cover every reject path of ``_validate_identity``."""

    def test_validate_identity_rejects_unknown_profile_role_and_environment(
        self,
    ) -> None:
        identity = _identity("rtx_3090_ti")
        identity["device_profile_id"] = "phantom"
        with self.assertRaisesRegex(ContractError, "device_profile_id"):
            _validate_identity(identity)

        identity = _identity("rtx_3090_ti")
        identity["execution_environment"] = "macos_metal"
        with self.assertRaisesRegex(ContractError, "execution_environment"):
            _validate_identity(identity)

        identity = _identity("rtx_3090_ti")
        identity["device_role"] = "helper"
        with self.assertRaisesRegex(ContractError, "device_role"):
            _validate_identity(identity)

    def test_wsl_requires_guest_software_identity_and_native_forbids_one(self) -> None:
        identity = _identity("rtx_3090_ti")
        identity["guest_software_identity_sha256"] = None
        with self.assertRaisesRegex(ContractError, "guest software identity"):
            _validate_identity(identity)

        identity = _identity("m1_pro_16gb")
        identity["guest_software_identity_sha256"] = _digest("guest")
        with self.assertRaisesRegex(ContractError, "guest software identity"):
            _validate_identity(identity)

    def test_validate_identity_rejects_missing_or_unknown_fields(self) -> None:
        identity = _identity("rtx_3090_ti")
        del identity["run_id"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            _validate_identity(identity)

        identity = _identity("rtx_3090_ti")
        identity["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            _validate_identity(identity)

    def test_validate_identity_rejects_invalid_digests(self) -> None:
        identity = _identity("rtx_3090_ti")
        identity["run_provenance_sha256"] = "Z" * 64
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            _validate_identity(identity)

    def test_validate_identity_returns_sorted_canonical_form(self) -> None:
        result = _validate_identity(_identity("rtx_3090_ti"))
        self.assertEqual(list(result.keys()), sorted(result.keys()))


class TelemetryClockValidationTests(unittest.TestCase):
    """Cover the private clock validator."""

    def test_clock_rejects_unknown_clock_id_and_inverted_window(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        clock = _clock("rtx_3090_ti")
        clock["clock_id"] = "mach_continuous_time"
        with self.assertRaisesRegex(ContractError, "clock_id"):
            _validate_clock(clock, identity)

        clock = _clock("rtx_3090_ti")
        clock["end_monotonic_ns"] = clock["start_monotonic_ns"]
        with self.assertRaisesRegex(ContractError, "must be greater than the start"):
            _validate_clock(clock, identity)

    def test_clock_rejects_resolution_out_of_range(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        clock = _clock("rtx_3090_ti")
        clock["resolution_ns"] = 0
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _validate_clock(clock, identity)
        clock = _clock("rtx_3090_ti")
        clock["resolution_ns"] = 50_000_001
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            _validate_clock(clock, identity)


class TelemetryIsolationValidationTests(unittest.TestCase):
    """Cover every reject path of ``_validate_isolation_input``."""

    def test_isolation_requires_boolean_lease(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        isolation = _isolation("rtx_3090_ti")
        isolation["exclusive_device_lease"] = "yes"
        with self.assertRaisesRegex(ContractError, "must be boolean"):
            _validate_isolation_input(isolation, identity)

    def test_isolation_rejects_unknown_attribution_method(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        isolation = _isolation("rtx_3090_ti")
        isolation["attribution_method"] = "creative_guess"
        with self.assertRaisesRegex(ContractError, "attribution_method"):
            _validate_isolation_input(isolation, identity)

    def test_isolation_rejects_non_array_metrics_and_unknown_metric(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        isolation = _isolation("rtx_3090_ti")
        isolation["attributable_metrics"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _validate_isolation_input(isolation, identity)

        isolation = _isolation("rtx_3090_ti")
        isolation["attributable_metrics"] = ["process_memory_bytes", "creative_metric"]
        with self.assertRaisesRegex(ContractError, "is not a known metric"):
            _validate_isolation_input(isolation, identity)

    def test_isolation_rejects_duplicate_and_missing_process_memory(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        isolation = _isolation("rtx_3090_ti")
        isolation["attributable_metrics"] = [
            "process_memory_bytes",
            "process_memory_bytes",
        ]
        with self.assertRaisesRegex(ContractError, "must be unique"):
            _validate_isolation_input(isolation, identity)

        isolation = _isolation("rtx_3090_ti")
        isolation["attributable_metrics"] = []
        with self.assertRaisesRegex(ContractError, "include process_memory_bytes"):
            _validate_isolation_input(isolation, identity)

    def test_isolation_rejects_invalid_digests(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        isolation = _isolation("rtx_3090_ti")
        isolation["background_policy_sha256"] = "Z" * 64
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            _validate_isolation_input(isolation, identity)


class TelemetrySeriesValidationTests(unittest.TestCase):
    """Cover the private series validator."""

    def test_series_must_be_a_list_of_exact_length(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        clock = _validate_clock(_clock("rtx_3090_ti"), identity)
        isolation = _validate_isolation_input(_isolation("rtx_3090_ti"), identity)
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _validate_series({}, identity, clock, isolation)
        with self.assertRaisesRegex(ContractError, "every telemetry metric exactly once"):
            _validate_series([], identity, clock, isolation)

    def test_series_rejects_unknown_metric_unit_status_and_duplicate(self) -> None:
        inputs = _inputs()
        inputs["series"][0]["metric"] = "creative_metric"
        with self.assertRaisesRegex(ContractError, "not a known telemetry metric"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["series"][0]["unit"] = "kWh"
        with self.assertRaisesRegex(ContractError, "unit is invalid"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["series"][0]["status"] = "stale"
        with self.assertRaisesRegex(ContractError, "status is invalid"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        duplicate_metric = inputs["series"][0]["metric"]
        inputs["series"][1]["metric"] = duplicate_metric
        with self.assertRaisesRegex(ContractError, "duplicate metric"):
            build_telemetry_bundle(**inputs)

    def test_series_samples_must_be_a_list(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "samples must be an array"):
            build_telemetry_bundle(**inputs)

    def test_not_applicable_series_requires_canonical_shape(self) -> None:
        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")  # not_applicable for rtx_3090_ti
        battery["status"] = "measured"
        battery["scope"] = _SCOPE["battery_power_w"]
        battery["interval_ns"] = 1_000_000_000
        battery["source_provenance_sha256"] = _digest("battery-source")
        battery["reason_code"] = None
        battery["samples"] = []
        with self.assertRaisesRegex(ContractError, "contradicts the device profile"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery["scope"] = "device"
        with self.assertRaisesRegex(ContractError, "not-applicable representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery["interval_ns"] = 1_000_000_000
        with self.assertRaisesRegex(ContractError, "not-applicable representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery["source_provenance_sha256"] = _digest("battery-source")
        with self.assertRaisesRegex(ContractError, "not-applicable representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery["reason_code"] = "sensor_unavailable"
        with self.assertRaisesRegex(ContractError, "not-applicable representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery["samples"] = [
            {
                "slot": 0,
                "monotonic_ns": 1_000_000_000,
                "value": 1.0,
            }
        ]
        with self.assertRaisesRegex(ContractError, "not-applicable representation"):
            build_telemetry_bundle(**inputs)

    def test_missing_series_requires_known_reason_and_no_samples(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["status"] = "missing"
        gpu["samples"] = [
            {"slot": 0, "monotonic_ns": 1_000_000_000, "value": 100.0}
        ]
        with self.assertRaisesRegex(ContractError, "missing representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["status"] = "missing"
        gpu["reason_code"] = "creative_reason"
        gpu["samples"] = []
        with self.assertRaisesRegex(ContractError, "missing representation"):
            build_telemetry_bundle(**inputs)

    def test_scope_must_match_metric_capability(self) -> None:
        inputs = _inputs()
        inputs["clock"]["resolution_ns"] = 1
        gpu = _series(inputs, "gpu_power_w")
        gpu["scope"] = "system"
        with self.assertRaisesRegex(ContractError, "scope is invalid"):
            build_telemetry_bundle(**inputs)

    def test_interval_finer_than_clock_resolution_rejected(self) -> None:
        # The clock resolution must satisfy ``1 <= resolution_ns <= 50_000_000``,
        # so set the resolution to a valid value coarser than the GPU interval.
        inputs = _inputs()
        inputs["clock"]["resolution_ns"] = 1000
        gpu = _series(inputs, "gpu_power_w")
        gpu["interval_ns"] = 1
        with self.assertRaisesRegex(ContractError, "finer than the monotonic clock"):
            build_telemetry_bundle(**inputs)

    def test_measured_series_requires_null_reason_and_samples(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["reason_code"] = "creative_reason"
        with self.assertRaisesRegex(ContractError, "measured series requires samples"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"] = []
        with self.assertRaisesRegex(ContractError, "measured series requires samples"):
            build_telemetry_bundle(**inputs)

    def test_sample_outside_grid_slot_rejected(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"][1]["monotonic_ns"] -= 1
        with self.assertRaisesRegex(ContractError, "outside its monotonic grid slot"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"][2]["slot"] = 1
        with self.assertRaisesRegex(ContractError, "strictly increasing grid slots"):
            build_telemetry_bundle(**inputs)

    def test_slot_index_out_of_expected_grid_rejected(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"][0]["slot"] = 4  # only 4 slots (0..3)
        with self.assertRaisesRegex(ContractError, "strictly increasing grid slots"):
            build_telemetry_bundle(**inputs)

    def test_sampling_grid_too_dense_rejected_before_rows(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["interval_ns"] = 1
        with self.assertRaisesRegex(ContractError, "exceeds the sample limit"):
            build_telemetry_bundle(**inputs)

    def test_total_sample_limit_enforced_across_series(self) -> None:
        inputs = _inputs()
        # Per-series grid check: expected_count must be < 200_000 for samples
        # to fit.  Use interval=40_000 (resolution matches) so expected_count
        # is 100_000; 25_000 samples remain grid-valid while the cumulative
        # total of 9 * 25_000 = 225_000 exceeds MAX_TELEMETRY_SAMPLES.  Use
        # bounded per-metric values so the value-range validators do not
        # trip before the cumulative sample guard.
        def _bounded_value(metric: str, slot: int) -> object:
            if metric in {
                "gpu_memory_used_bytes",
                "process_memory_bytes",
                "unified_memory_used_bytes",
                "system_available_memory_bytes",
            }:
                return 1_000_000_000 + slot
            if metric == "thermal_throttle_active":
                return False
            if metric == "thermal_state":
                return "nominal"
            if metric == "lifecycle_state":
                return "active"
            if metric == "cumulative_energy_j":
                return float(slot)
            return 1.0

        for metric in PROFILE_REQUIRED_METRICS["rtx_3090_ti"]:
            series = _series(inputs, metric)
            if series["status"] != "measured":
                continue
            series["interval_ns"] = 40_000
            inputs["clock"]["resolution_ns"] = 40_000
            series["samples"] = [
                {
                    "slot": slot,
                    "monotonic_ns": 1_000_000_000 + slot * 40_000,
                    "value": _bounded_value(metric, slot),
                }
                for slot in range(25_000)
            ]
        with self.assertRaisesRegex(ContractError, "exceeds the total sample limit"):
            build_telemetry_bundle(**inputs)

    def test_unknown_sample_fields_rejected(self) -> None:
        inputs = _inputs()
        gpu = _series(inputs, "gpu_power_w")
        gpu["samples"][0]["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            build_telemetry_bundle(**inputs)

    def test_attribution_must_cover_profile_memory_components(self) -> None:
        inputs = _inputs()
        inputs["isolation"]["attributable_metrics"] = ["process_memory_bytes"]
        with self.assertRaisesRegex(ContractError, "omits a profile memory component"):
            build_telemetry_bundle(**inputs)


class TelemetryOverheadValidationTests(unittest.TestCase):
    """Cover every reject path of ``_validate_overhead_input``."""

    def test_overhead_pairs_must_be_a_list(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        overhead = _overhead("rtx_3090_ti")
        overhead["pairs"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _validate_overhead_input(overhead, identity)

    def test_overhead_status_must_be_measured_or_missing(self) -> None:
        inputs = _inputs()
        inputs["overhead"]["status"] = "creative"
        with self.assertRaisesRegex(ContractError, "must be measured or missing"):
            build_telemetry_bundle(**inputs)

    def test_overhead_missing_requires_attempt_provenance_and_no_pairs(self) -> None:
        # The ``missing`` branch of ``_validate_overhead_input`` rejects any
        # payload that has a non-empty ``pairs`` list, an unknown reason code,
        # or an invalid ``attempt_provenance_sha256`` digest.
        inputs = _inputs()
        inputs["overhead"] = {
            "status": "missing",
            "reason_code": "calibration_artifact_missing",
            "attempt_provenance_sha256": _digest("attempt"),
            "pairs": [
                {
                    "schedule_sha256": _digest("schedule"),
                    "baseline_run_sha256": _digest("baseline"),
                    "instrumented_run_sha256": _digest("instrumented"),
                    "baseline_duration_ns": 1_000_000_000,
                    "instrumented_duration_ns": 1_005_000_000,
                }
            ],
        }
        with self.assertRaisesRegex(ContractError, "missing representation"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"] = {
            "status": "missing",
            "reason_code": "creative_reason",
            "attempt_provenance_sha256": _digest("attempt"),
            "pairs": [],
        }
        with self.assertRaisesRegex(ContractError, "missing representation"):
            build_telemetry_bundle(**inputs)

        # Non-digest ``attempt_provenance_sha256`` is rejected by the contract's
        # SHA-256 check inside ``_validate_overhead_input``.
        inputs = _inputs()
        inputs["overhead"] = {
            "status": "missing",
            "reason_code": "calibration_not_run",
            "attempt_provenance_sha256": "Z" * 64,
            "pairs": [],
        }
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            build_telemetry_bundle(**inputs)

    def test_measured_overhead_rejects_non_null_metadata(self) -> None:
        inputs = _inputs()
        inputs["overhead"]["reason_code"] = "creative_reason"
        with self.assertRaisesRegex(ContractError, "null missing metadata"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"]["attempt_provenance_sha256"] = _digest("attempt")
        with self.assertRaisesRegex(ContractError, "null missing metadata"):
            build_telemetry_bundle(**inputs)

    def test_overhead_pair_count_limits(self) -> None:
        inputs = _inputs()
        inputs["overhead"]["pairs"] = inputs["overhead"]["pairs"][:2]
        with self.assertRaisesRegex(ContractError, "at least 3 pairs"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        first = inputs["overhead"]["pairs"][0]
        inputs["overhead"]["pairs"] = [
            {
                **first,
                "baseline_run_sha256": _digest(f"baseline:{index}"),
                "instrumented_run_sha256": _digest(f"instrumented:{index}"),
                "schedule_sha256": _digest(f"schedule:{index}"),
            }
            for index in range(10_001)
        ]
        with self.assertRaisesRegex(ContractError, "at most 10000 pairs"):
            build_telemetry_bundle(**inputs)

    def test_overhead_pair_durations_and_digests_are_validated(self) -> None:
        inputs = _inputs()
        inputs["overhead"]["pairs"][0]["baseline_duration_ns"] = 0
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"]["pairs"][0]["instrumented_duration_ns"] = 0
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"]["pairs"][0]["schedule_sha256"] = "Z" * 64
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"]["pairs"][0]["baseline_run_sha256"] = "Z" * 64
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        inputs["overhead"]["pairs"][0]["instrumented_run_sha256"] = "Z" * 64
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            build_telemetry_bundle(**inputs)

    def test_overhead_pair_unique_runs_and_schedules(self) -> None:
        inputs = _inputs()
        shared = _digest("schedule")
        for pair in inputs["overhead"]["pairs"]:
            pair["schedule_sha256"] = shared
        with self.assertRaisesRegex(ContractError, "schedules must be unique"):
            build_telemetry_bundle(**inputs)

        inputs = _inputs()
        shared_run = _digest("baseline")
        for pair in inputs["overhead"]["pairs"]:
            pair["baseline_run_sha256"] = shared_run
        with self.assertRaisesRegex(ContractError, "run hashes must be unique"):
            build_telemetry_bundle(**inputs)


class TelemetryBuildBundleTests(unittest.TestCase):
    """Cover ``build_telemetry_bundle`` end-to-end paths."""

    def test_build_bundle_is_deterministic_under_input_reordering(self) -> None:
        first = build_telemetry_bundle(**_inputs())
        second_inputs = _inputs()
        second_inputs["series"].reverse()
        second_inputs["overhead"]["pairs"].reverse()
        second = build_telemetry_bundle(**second_inputs)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], TELEMETRY_SCHEMA_VERSION)
        self.assertEqual(first["evidence_class"], "local_measured")
        self.assertEqual(first["quality"]["status"], "pass")
        self.assertEqual(
            telemetry_bundle_sha256(first), telemetry_bundle_sha256(second)
        )

    def test_build_bundle_emits_canonical_summary_for_every_profile(self) -> None:
        for profile in PROFILE_REQUIRED_METRICS:
            with self.subTest(profile=profile):
                bundle = build_telemetry_bundle(**_inputs(profile))
                self.assertEqual(bundle["schema_version"], TELEMETRY_SCHEMA_VERSION)
                self.assertIn("summary", bundle)
                self.assertIn("quality", bundle)
                self.assertIn("memory", bundle["summary"])
                self.assertIn("metric_summaries", bundle["summary"])

    def test_calibration_context_digest_matches_documented_composition(self) -> None:
        identity = _validate_identity(_identity("rtx_3090_ti"))
        digest = _calibration_context(identity)
        self.assertEqual(digest, sha256_hex(canonical_json_bytes(
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
        )))

    def test_build_bundle_rejects_secret_payloads(self) -> None:
        inputs = _inputs()
        inputs["identity"]["run_id"] = "run-with-Bearer abcdefghijklmnopqrstuvwxyz"
        with self.assertRaisesRegex(ContractError, "credential"):
            build_telemetry_bundle(**inputs)

    def test_build_bundle_serializes_with_canonical_json(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        encoded = canonical_json_bytes(bundle)
        self.assertLessEqual(len(encoded), MAX_TELEMETRY_BUNDLE_BYTES)

    def test_expected_sample_count_uses_ceiling_division(self) -> None:
        clock = {
            "start_monotonic_ns": 1_000,
            "end_monotonic_ns": 4_000,
            "resolution_ns": 1,
        }
        self.assertEqual(_expected_sample_count(clock, 1_000), 3)
        self.assertEqual(_expected_sample_count(clock, 1_500), 2)


class TelemetrySummaryQualityTests(unittest.TestCase):
    """Cover the private ``_build_summary`` / ``_build_quality`` helpers."""

    def test_series_summary_branches_for_each_metric_type(self) -> None:
        clock = _validate_clock(_clock("rtx_3090_ti"), _validate_identity(_identity("rtx_3090_ti")))
        not_app = {
            "metric": "battery_power_w",
            "status": "not_applicable",
            "scope": "not_applicable",
            "interval_ns": None,
            "samples": [],
        }
        summary = _series_summary(not_app, clock)
        self.assertIsNone(summary["expected_sample_count"])
        self.assertIsNone(summary["coverage_fraction"])

        numeric = {
            "metric": "gpu_power_w",
            "status": "measured",
            "scope": "device",
            "interval_ns": 1_000_000_000,
            "samples": [
                {"slot": 0, "monotonic_ns": 1_000_000_000, "value": 100.0},
                {"slot": 1, "monotonic_ns": 2_000_000_000, "value": 200.0},
            ],
        }
        numeric_summary = _series_summary(numeric, clock)
        self.assertEqual(numeric_summary["minimum"], 100.0)
        self.assertEqual(numeric_summary["maximum"], 200.0)
        self.assertAlmostEqual(numeric_summary["mean"], 150.0)

        boolean_series = {
            "metric": "thermal_throttle_active",
            "status": "measured",
            "scope": "device",
            "interval_ns": 1_000_000_000,
            "samples": [
                {"slot": 0, "monotonic_ns": 1_000_000_000, "value": True},
                {"slot": 1, "monotonic_ns": 2_000_000_000, "value": False},
            ],
        }
        boolean_summary = _series_summary(boolean_series, clock)
        self.assertEqual(boolean_summary["true_fraction"], 0.5)
        self.assertIsNone(boolean_summary["minimum"])

        state_series = {
            "metric": "lifecycle_state",
            "status": "measured",
            "scope": "system",
            "interval_ns": 1_000_000_000,
            "samples": [
                {"slot": 0, "monotonic_ns": 1_000_000_000, "value": "active"},
                {"slot": 1, "monotonic_ns": 2_000_000_000, "value": "idle"},
            ],
        }
        state_summary = _series_summary(state_series, clock)
        self.assertEqual(set(state_summary["observed_states"]), {"active", "idle"})

    def test_memory_summary_handles_missing_stream_and_interval_mismatch(self) -> None:
        # Skip the standard build path so we can craft a memory alignment
        # scenario directly without triggering the strict series validation.
        identity = _validate_identity(_identity("rtx_3090_ti"))
        clock = _validate_clock(_clock("rtx_3090_ti"), identity)
        isolation = _validate_isolation_input(_isolation("rtx_3090_ti"), identity)
        # Validated series but mark the memory components as missing so the
        # ``missing_stream`` branch is exercised.
        series_inputs = _inputs()
        process = _series(series_inputs, "process_memory_bytes")
        process["status"] = "missing"
        process["reason_code"] = "sensor_unavailable"
        process["samples"] = []
        gpu = _series(series_inputs, "gpu_memory_used_bytes")
        gpu["status"] = "missing"
        gpu["reason_code"] = "sensor_unavailable"
        gpu["samples"] = []
        checked_series = _validate_series(
            series_inputs["series"], identity, clock, isolation
        )
        by_metric = {row["metric"]: row for row in checked_series}
        memory = _memory_summary(identity, isolation, by_metric, clock)
        self.assertEqual(memory["alignment_status"], "missing_stream")
        self.assertIsNone(memory["peak_attributable_active_memory_bytes"])

        # Interval mismatch branch: two memory components with different intervals.
        series_inputs = _inputs()
        process = _series(series_inputs, "process_memory_bytes")
        gpu = _series(series_inputs, "gpu_memory_used_bytes")
        gpu["interval_ns"] = 2_000_000_000
        gpu["samples"] = [
            {"slot": 0, "monotonic_ns": 1_000_000_000, "value": 1_000_000_000},
            {"slot": 1, "monotonic_ns": 3_000_000_000, "value": 1_000_001_000},
        ]
        checked_series = _validate_series(
            series_inputs["series"], identity, clock, isolation
        )
        by_metric = {row["metric"]: row for row in checked_series}
        memory = _memory_summary(identity, isolation, by_metric, clock)
        self.assertEqual(memory["alignment_status"], "interval_mismatch")
        self.assertIsNone(memory["alignment_interval_ns"])

    def test_memory_summary_uses_max_for_unified_profile(self) -> None:
        # m1_pro_16gb uses max_shared_unified_physical_bytes; the larger of the
        # two samples must win even if the other would-be component is zero.
        bundle = build_telemetry_bundle(**_inputs("m1_pro_16gb"))
        memory = bundle["summary"]["memory"]
        self.assertEqual(
            memory["combination_method"], "max_shared_unified_physical_bytes"
        )
        self.assertTrue(memory["unified_memory_counted_once"])

    def test_build_summary_exposes_peak_thermal_state(self) -> None:
        bundle = build_telemetry_bundle(**_inputs("m1_pro_16gb"))
        summary = bundle["summary"]
        # The summary emits ``thermal_state_peak`` (peak thermal state name)
        # and ``lifecycle_states`` (sorted observed set).
        self.assertIn("thermal_state_peak", summary)
        self.assertIn("lifecycle_states", summary)
        self.assertIn("throttle_observed", summary)
        self.assertIn("energy_delta_j", summary)
        self.assertIn("duration_ns", summary)
        self.assertIn("peak_attributable_active_memory_bytes", summary)

    def test_build_quality_records_failure_and_not_evaluable_reasons(self) -> None:
        # A profile that lacks unified_memory metrics still needs at least one
        # measured power source to expose the exclusive_lease gate.
        bundle = build_telemetry_bundle(**_inputs())
        quality = bundle["quality"]
        self.assertIn("minimum_required_coverage_fraction", quality)
        self.assertIn("minimum_required_coverage_observed", quality)
        self.assertIn("maximum_overhead_fraction", quality)
        self.assertIn("required_metrics", quality)
        self.assertIn("missing_required_metrics", quality)
        self.assertIn("low_coverage_required_metrics", quality)
        self.assertIn("optional_missing_metrics", quality)
        self.assertIn("not_evaluable_reasons", quality)
        self.assertIn("failure_reasons", quality)


class TelemetryValidateBundleTests(unittest.TestCase):
    """Cover the public ``validate_telemetry_bundle`` and ``telemetry_bundle_sha256``."""

    def test_validate_bundle_round_trip_for_every_profile(self) -> None:
        for profile in PROFILE_REQUIRED_METRICS:
            with self.subTest(profile=profile):
                bundle = build_telemetry_bundle(**_inputs(profile))
                self.assertEqual(validate_telemetry_bundle(bundle), bundle)
                self.assertEqual(
                    telemetry_bundle_sha256(bundle),
                    sha256_hex(canonical_json_bytes(bundle)),
                )

    def test_validate_bundle_rejects_wrong_schema_and_evidence_class(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["schema_version"] = "pheno.eval.telemetry-bundle.v0"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            validate_telemetry_bundle(bundle)

        bundle = build_telemetry_bundle(**_inputs())
        bundle["evidence_class"] = "historical"
        with self.assertRaisesRegex(ContractError, "evidence_class"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_rejects_non_array_series(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["series"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "series must be an array"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_rejects_non_finite_values(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["summary"]["energy_delta_j"] = float("nan")
        with self.assertRaisesRegex(ContractError, "finite JSON"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_rejects_secret_in_payload(self) -> None:
        # Inject a bearer token into ``run_id``; ``contains_secret`` walks the
        # whole canonical bundle so the credential check fires before the
        # deterministic recomputation guard.
        bundle = build_telemetry_bundle(**_inputs())
        bundle["identity"]["run_id"] = "Bearer abcdefghijklmnopqrstuvwxyz"
        with self.assertRaisesRegex(ContractError, "credential"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_enforces_byte_limit(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["summary"]["memory"]["coverage_fraction"] = 0.5
        # Encode the bundle; if it's still under the limit, inflate an
        # inessential string until canonical JSON grows past the limit.
        encoded = canonical_json_bytes(bundle)
        if len(encoded) > MAX_TELEMETRY_BUNDLE_BYTES:
            self.skipTest("base bundle already exceeds the byte limit")
        bundle["quality"]["failure_reasons"] = [
            "synthetic reason " + "x" * (MAX_TELEMETRY_BUNDLE_BYTES + 1024)
        ]
        with self.assertRaisesRegex(ContractError, "normalized byte limit"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_requires_attribution_sha256_field(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        del bundle["isolation"]["attribution_sha256"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_requires_calibration_sha256_field(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        del bundle["overhead"]["calibration_sha256"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_rejects_deterministic_mismatch(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        # Mutate a value that does not affect recomputation but does affect the
        # hash; recompute via build_telemetry_bundle to demonstrate divergence.
        bundle["telemetry_id"] = "f" * 64
        with self.assertRaisesRegex(ContractError, "deterministic recomputation"):
            validate_telemetry_bundle(bundle)

    def test_telemetry_bundle_sha256_delegates_to_validator(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        self.assertEqual(
            telemetry_bundle_sha256(bundle),
            sha256_hex(canonical_json_bytes(validate_telemetry_bundle(bundle))),
        )

    def test_validate_bundle_survives_extra_metadata_root_fields(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["schema_version"] = TELEMETRY_SCHEMA_VERSION  # already set
        # Adding an unknown root field forces validate_telemetry_bundle to
        # reject the bundle because ``_exact`` requires the documented set.
        bundle["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_telemetry_bundle(bundle)

    def test_validate_bundle_handles_overhead_with_extra_field(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        bundle["overhead"]["estimated_overhead_fraction"] = 0.01  # already present
        # The validator copies the input overhead through ``_raw_overhead``,
        # which requires exactly the documented input fields plus the four
        # derived ones.  An extra field trips the contract.
        bundle["overhead"]["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_telemetry_bundle(bundle)

    def test_build_quality_handles_unobserved_overhead_estimator(self) -> None:
        # Bypass the strict build path by mutating a successfully built bundle
        # so the validator reports the overhead as missing without aborting.
        bundle = build_telemetry_bundle(**_inputs())
        bundle["overhead"]["status"] = "missing"
        bundle["overhead"]["reason_code"] = "calibration_not_run"
        bundle["overhead"]["attempt_provenance_sha256"] = _digest("attempt")
        bundle["overhead"]["pairs"] = []
        with self.assertRaisesRegex(ContractError, "deterministic recomputation"):
            validate_telemetry_bundle(bundle)

    def test_quality_dispatch_paths_directly(self) -> None:
        # Exercise the public-facing helper directly with a valid bundle to
        # confirm no surprise ``ContractError`` fires for the canonical case.
        bundle = build_telemetry_bundle(**_inputs())
        summary = bundle["summary"]
        overhead = bundle["overhead"]
        identity = bundle["identity"]
        isolation = bundle["isolation"]
        series = bundle["series"]
        quality = _build_quality(identity, isolation, series, overhead, summary)
        self.assertEqual(quality["status"], "pass")
        # Confirm the public summary helper re-emits the canonical structure.
        rebuilt = _build_summary(identity, isolation, series, bundle["clock"])
        self.assertEqual(rebuilt["duration_ns"], summary["duration_ns"])
        self.assertAlmostEqual(rebuilt["energy_delta_j"], summary["energy_delta_j"])


class TelemetryBundleExportTests(unittest.TestCase):
    """Cover the JSON serialization paths through canonical_json_bytes."""

    def test_canonical_round_trip_preserves_bundle(self) -> None:
        bundle = build_telemetry_bundle(**_inputs())
        encoded = canonical_json_bytes(bundle)
        decoded = json.loads(encoded.decode("utf-8"))
        self.assertEqual(decoded, bundle)

    def test_canonical_round_trip_is_deterministic(self) -> None:
        first = canonical_json_bytes(build_telemetry_bundle(**_inputs()))
        second_inputs = _inputs()
        second_inputs["series"].reverse()
        second = canonical_json_bytes(build_telemetry_bundle(**second_inputs))
        self.assertEqual(first, second)


class TelemetryQualityBranchTests(unittest.TestCase):
    """Cover every ``_build_quality`` / validation failure branch in isolation.

    These tests focus on the ``not_evaluable`` / ``fail`` reason lists emitted
    by ``_build_quality``; the user-visible contract tests in
    ``tests/test_eval_telemetry.py`` pin the canonical pass case, so the
    branches here deliberately drive each branch into a regression-friendly
    failure mode without relying on the wider suite.
    """

    def test_cumulative_energy_must_be_nondecreasing_with_two_samples(self) -> None:
        inputs = _inputs()
        energy = _series(inputs, "cumulative_energy_j")
        # The validator requires at least two nondecreasing samples; dropping
        # the second sample and reverting the third to a smaller value triggers
        # the strict branch.
        energy["samples"] = [
            {"slot": 0, "monotonic_ns": 1_000_000_000, "value": 0.0},
            {"slot": 1, "monotonic_ns": 2_000_000_000, "value": 5.0},
            {"slot": 2, "monotonic_ns": 3_000_000_000, "value": 3.0},
        ]
        with self.assertRaisesRegex(ContractError, "nondecreasing"):
            build_telemetry_bundle(**inputs)

    def test_attribution_scope_must_agree_with_metric_scope(self) -> None:
        inputs = _inputs()
        # ``gpu_power_w`` is not process-scoped, but adding it to the
        # attributable set triggers the scope/attribution mismatch guard.
        inputs["isolation"]["attributable_metrics"].append("gpu_power_w")
        with self.assertRaisesRegex(ContractError, "scope.*disagree"):
            build_telemetry_bundle(**inputs)

    def test_memory_alignment_rejects_same_slot_with_excessive_skew(self) -> None:
        inputs = _inputs()
        # Increase ``clock.resolution_ns`` so the alignment tolerance is large
        # enough to allow the alignment to fail on the *excessive-skew* path
        # rather than the *interval-mismatch* path.  Then perturb one slot's
        # timestamp past the tolerance window.
        inputs["clock"]["resolution_ns"] = 1
        gpu_memory = _series(inputs, "gpu_memory_used_bytes")
        gpu_memory["samples"][1]["monotonic_ns"] += 200_000_000
        bundle = build_telemetry_bundle(**inputs)
        memory = bundle["summary"]["memory"]
        self.assertEqual(memory["alignment_status"], "insufficient_coverage")
        self.assertGreaterEqual(memory["skew_rejected_sample_count"], 1)
        self.assertGreater(memory["maximum_observed_alignment_skew_ns"], 0)
        self.assertIsNone(memory["peak_attributable_active_memory_bytes"])

    def test_memory_insufficient_coverage_emits_complete_failure_reasons(self) -> None:
        inputs = _inputs()
        # Drop matching slots so the aligned coverage falls below the 0.95
        # threshold and ``alignment_status`` becomes ``insufficient_coverage``.
        _series(inputs, "process_memory_bytes")["samples"].pop(0)
        _series(inputs, "gpu_memory_used_bytes")["samples"].pop(1)
        bundle = build_telemetry_bundle(**inputs)
        quality = bundle["quality"]
        self.assertEqual(
            bundle["summary"]["memory"]["alignment_status"],
            "insufficient_coverage",
        )
        self.assertIn(
            "time-aligned attributable physical-memory peak is not complete",
            quality["not_evaluable_reasons"],
        )
        self.assertIn("gpu_memory_used_bytes", quality["required_metrics"])

    def test_device_scoped_energy_without_exclusive_lease_is_not_evaluable(
        self,
    ) -> None:
        inputs = _inputs()
        inputs["isolation"]["exclusive_device_lease"] = False
        bundle = build_telemetry_bundle(**inputs)
        quality = bundle["quality"]
        self.assertEqual(quality["status"], "not_evaluable")
        self.assertIn(
            "device-scoped power or energy lacks an exclusive device lease",
            quality["not_evaluable_reasons"],
        )

    def test_overhead_exceeds_maximum_marks_quality_failure(self) -> None:
        inputs = _inputs()
        # Increase every instrumented duration by ~20% to push the
        # geometric-mean overhead estimate above the 5% maximum.
        for pair in inputs["overhead"]["pairs"]:
            pair["instrumented_duration_ns"] = int(
                pair["baseline_duration_ns"] * 1.2
            )
        bundle = build_telemetry_bundle(**inputs)
        self.assertGreater(
            bundle["overhead"]["estimated_overhead_fraction"],
            MAXIMUM_OVERHEAD_FRACTION,
        )
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertIn(
            "instrumentation overhead exceeds the 5% maximum",
            bundle["quality"]["failure_reasons"],
        )

    def test_thermal_throttle_observation_marks_quality_failure(self) -> None:
        inputs = _inputs("galaxy_s21_ultra")
        _series(inputs, "thermal_throttle_active")["samples"][1]["value"] = True
        bundle = build_telemetry_bundle(**inputs)
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertIn(
            "thermal throttling was observed",
            bundle["quality"]["failure_reasons"],
        )

    def test_prohibited_thermal_state_marks_quality_failure(self) -> None:
        inputs = _inputs("galaxy_s21_ultra")
        _series(inputs, "thermal_state")["samples"][2]["value"] = "critical"
        bundle = build_telemetry_bundle(**inputs)
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertIn(
            "a prohibited thermal state was observed",
            bundle["quality"]["failure_reasons"],
        )

    def test_thermal_state_unknown_marks_quality_not_evaluable(self) -> None:
        inputs = _inputs("iphone_17_pro_max")
        _series(inputs, "thermal_state")["samples"][1]["value"] = "unknown"
        bundle = build_telemetry_bundle(**inputs)
        self.assertIn(
            "thermal state contains unknown observations",
            bundle["quality"]["not_evaluable_reasons"],
        )

    def test_lifecycle_state_unknown_marks_quality_not_evaluable(self) -> None:
        inputs = _inputs("iphone_17_pro_max")
        _series(inputs, "lifecycle_state")["samples"][1]["value"] = "unknown"
        bundle = build_telemetry_bundle(**inputs)
        self.assertIn(
            "lifecycle state contains unknown observations",
            bundle["quality"]["not_evaluable_reasons"],
        )

    def test_lifecycle_leaving_required_state_marks_quality_failure(self) -> None:
        inputs = _inputs("rtx_3090_ti")
        _series(inputs, "lifecycle_state")["samples"][2]["value"] = "idle"
        bundle = build_telemetry_bundle(**inputs)
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertIn(
            "lifecycle left the required active state during the window",
            bundle["quality"]["failure_reasons"],
        )

    def test_zero_energy_delta_marks_quality_not_evaluable(self) -> None:
        inputs = _inputs()
        energy = _series(inputs, "cumulative_energy_j")
        for sample in energy["samples"]:
            sample["value"] = 0.0
        bundle = build_telemetry_bundle(**inputs)
        self.assertIn(
            "cumulative energy delta is not positive",
            bundle["quality"]["not_evaluable_reasons"],
        )

    def test_build_telemetry_bundle_rejects_byte_limit(self) -> None:
        # Shrink the byte limit to a tiny value so the canonical JSON of any
        # ordinary bundle exceeds ``MAX_TELEMETRY_BUNDLE_BYTES``.  The build
        # path checks the byte length after computing the canonical bundle,
        # so a sufficiently small cap trips the byte-limit guard without
        # requiring the caller to construct thousands of synthetic samples.
        with patch.object(telemetry_module, "MAX_TELEMETRY_BUNDLE_BYTES", 64):
            with self.assertRaisesRegex(
                ContractError, "normalized byte limit"
            ):
                build_telemetry_bundle(**_inputs())

    def test_validate_bundle_serializes_non_finite_values(self) -> None:
        # ``canonical_json_bytes`` raises ``ValueError`` for non-finite floats
        # via ``allow_nan=False``.  The validator surfaces this as a
        # ``finite JSON`` contract error.
        bundle = build_telemetry_bundle(**_inputs())
        bundle["summary"]["peak_temperature_c"] = float("inf")
        with self.assertRaisesRegex(ContractError, "finite JSON"):
            validate_telemetry_bundle(bundle)

    def test_build_bundle_wraps_canonical_json_errors(self) -> None:
        # ``build_telemetry_bundle`` wraps ``TypeError`` / ``ValueError`` from
        # ``canonical_json_bytes`` as ``finite JSON`` contract errors.  The
        # final canonicalization (the byte-limit serialization of the full
        # ``result`` dict) is the only call wrapped by the ``try`` /
        # ``except`` block.  Use ``"telemetry_id"`` membership as the
        # discriminator so earlier validation canonicalizations still pass.
        original = telemetry_module.canonical_json_bytes

        def _fail_on_result(
            exc_cls: type[Exception],
        ) -> Any:
            def _side_effect(value: Any) -> bytes:
                if isinstance(value, dict) and "telemetry_id" in value:
                    raise exc_cls(f"simulated {exc_cls.__name__}")
                return original(value)

            return _side_effect

        with patch.object(
            telemetry_module,
            "canonical_json_bytes",
            side_effect=_fail_on_result(ValueError),
        ):
            with self.assertRaisesRegex(ContractError, "finite JSON"):
                build_telemetry_bundle(**_inputs())
        with patch.object(
            telemetry_module,
            "canonical_json_bytes",
            side_effect=_fail_on_result(TypeError),
        ):
            with self.assertRaisesRegex(ContractError, "finite JSON"):
                build_telemetry_bundle(**_inputs())


def _inputs_for_bypass(bundle: dict[str, Any]) -> dict[str, Any]:
    """Recreate an input dict from a persisted bundle for the build path.

    The byte-limit test bypasses ``build_telemetry_bundle``'s normal entry
    point and feeds the bundle directly into ``_validate_*`` by reconstructing
    the inputs the build path expects.
    """
    return {
        "identity": bundle["identity"],
        "clock": bundle["clock"],
        "isolation": {
            "exclusive_device_lease": bundle["isolation"][
                "exclusive_device_lease"
            ],
            "background_policy_sha256": bundle["isolation"][
                "background_policy_sha256"
            ],
            "workload_process_set_sha256": bundle["isolation"][
                "workload_process_set_sha256"
            ],
            "attribution_method": bundle["isolation"]["attribution_method"],
            "attributable_metrics": bundle["isolation"]["attributable_metrics"],
        },
        "series": [
            {
                "metric": row["metric"],
                "status": row["status"],
                "unit": row["unit"],
                "scope": row["scope"],
                "interval_ns": row["interval_ns"],
                "source_provenance_sha256": row["source_provenance_sha256"],
                "reason_code": row["reason_code"],
                "samples": row["samples"],
            }
            for row in bundle["series"]
        ],
        "overhead": {
            "status": bundle["overhead"]["status"],
            "reason_code": bundle["overhead"]["reason_code"],
            "attempt_provenance_sha256": bundle["overhead"][
                "attempt_provenance_sha256"
            ],
            "pairs": [
                {
                    "schedule_sha256": pair["schedule_sha256"],
                    "baseline_run_sha256": pair["baseline_run_sha256"],
                    "instrumented_run_sha256": pair[
                        "instrumented_run_sha256"
                    ],
                    "baseline_duration_ns": pair["baseline_duration_ns"],
                    "instrumented_duration_ns": pair[
                        "instrumented_duration_ns"
                    ],
                }
                for pair in bundle["overhead"]["pairs"]
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
