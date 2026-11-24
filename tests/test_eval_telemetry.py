from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from pheno.evidence.aggregate_contracts import MEMORY_SCOPE as AGGREGATE_MEMORY_SCOPE
from pheno.evidence.contracts import ContractError, sha256_hex
from pheno.evidence.telemetry import (
    MAXIMUM_OVERHEAD_FRACTION,
    MEMORY_SCOPE,
    METRIC_NAMES,
    PROFILE_NOT_APPLICABLE_METRICS,
    PROFILE_REQUIRED_METRICS,
    TELEMETRY_SCHEMA_VERSION,
    build_telemetry_bundle,
    telemetry_bundle_sha256,
    validate_telemetry_bundle,
)
from scripts import eval_contract


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


def _inputs(profile: str = "rtx_3090_ti") -> dict:
    environment = _ENVIRONMENT[profile]
    identity = {
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
    clock = {
        "clock_id": _CLOCK[environment],
        "clock_identity_sha256": _digest(f"clock:{profile}"),
        "resolution_ns": 1,
        "start_monotonic_ns": 1_000_000_000,
        "end_monotonic_ns": 5_000_000_000,
    }
    attributable = ["process_memory_bytes"]
    if profile in {"rtx_3090_ti", "gtx_1080_ti"}:
        attributable.append("gpu_memory_used_bytes")
    if "unified_memory_used_bytes" in PROFILE_REQUIRED_METRICS[profile]:
        attributable.append("unified_memory_used_bytes")
    isolation = {
        "exclusive_device_lease": True,
        "background_policy_sha256": _digest(f"background:{profile}"),
        "workload_process_set_sha256": _digest(f"processes:{profile}"),
        "attribution_method": _ATTRIBUTION[environment],
        "attributable_metrics": attributable,
    }
    series = []
    for metric in METRIC_NAMES:
        if metric in PROFILE_NOT_APPLICABLE_METRICS[profile]:
            series.append(
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
            series.append(
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
        series.append(
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
    overhead = {
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
    return {
        "identity": identity,
        "clock": clock,
        "isolation": isolation,
        "series": series,
        "overhead": overhead,
    }


def _build(inputs: dict) -> dict:
    return build_telemetry_bundle(**inputs)


def _series(inputs: dict, metric: str) -> dict:
    return next(item for item in inputs["series"] if item["metric"] == metric)


class TelemetryContractTests(unittest.TestCase):
    def test_every_fleet_profile_builds_a_canonical_pass_bundle(self) -> None:
        for profile in PROFILE_REQUIRED_METRICS:
            with self.subTest(profile=profile):
                first = _build(_inputs(profile))
                second_inputs = _inputs(profile)
                second_inputs["series"].reverse()
                second_inputs["overhead"]["pairs"].reverse()
                second = _build(second_inputs)
                self.assertEqual(first, second)
                self.assertEqual(first["schema_version"], TELEMETRY_SCHEMA_VERSION)
                self.assertEqual(first["quality"]["status"], "pass")
                self.assertEqual(validate_telemetry_bundle(first), first)
                self.assertEqual(
                    telemetry_bundle_sha256(first), telemetry_bundle_sha256(second)
                )

    def test_summary_recomputes_energy_memory_temperature_and_coverage(self) -> None:
        bundle = _build(_inputs())
        summary = bundle["summary"]
        self.assertEqual(MEMORY_SCOPE, AGGREGATE_MEMORY_SCOPE)
        self.assertEqual(summary["duration_ns"], 4_000_000_000)
        self.assertEqual(summary["energy_delta_j"], 30.0)
        self.assertEqual(
            summary["peak_attributable_active_memory_bytes"], 2_000_006_000
        )
        self.assertEqual(summary["memory"]["alignment_status"], "complete")
        self.assertEqual(summary["memory"]["coverage_fraction"], 1.0)
        self.assertEqual(summary["memory"]["maximum_observed_alignment_skew_ns"], 0)
        self.assertEqual(summary["memory"]["skew_rejected_sample_count"], 0)
        self.assertEqual(
            summary["memory"]["combination_method"],
            "sum_disjoint_host_and_device_physical_bytes",
        )
        self.assertEqual(summary["peak_temperature_c"], 53.0)
        self.assertFalse(summary["throttle_observed"])
        self.assertEqual(
            summary["metric_summaries"]["gpu_power_w"]["coverage_fraction"],
            1.0,
        )

    def test_wsl_guest_and_profile_role_bindings_fail_closed(self) -> None:
        for field, value, message in (
            ("guest_software_identity_sha256", None, "guest software identity"),
            ("device_role", "worker", "device_role"),
            ("execution_environment", "macos_metal", "execution_environment"),
        ):
            inputs = _inputs()
            inputs["identity"][field] = value
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ContractError, message),
            ):
                _build(inputs)

    def test_monotonic_slots_are_strict_and_bounded(self) -> None:
        inputs = _inputs()
        power = _series(inputs, "gpu_power_w")
        power["samples"][1]["slot"] = 0
        with self.assertRaisesRegex(ContractError, "strictly increasing grid slots"):
            _build(inputs)

        inputs = _inputs()
        power = _series(inputs, "gpu_power_w")
        power["samples"][0]["monotonic_ns"] += 1_000_000_000
        with self.assertRaisesRegex(ContractError, "outside its monotonic grid slot"):
            _build(inputs)

    def test_required_missing_and_low_coverage_are_not_evaluable(self) -> None:
        inputs = _inputs()
        temperature = _series(inputs, "temperature_c")
        temperature.update(
            status="missing", reason_code="sensor_unavailable", samples=[]
        )
        missing = _build(inputs)
        self.assertEqual(missing["quality"]["status"], "not_evaluable")
        self.assertIn("temperature_c", missing["quality"]["missing_required_metrics"])
        self.assertEqual(
            missing["summary"]["metric_summaries"]["temperature_c"][
                "coverage_fraction"
            ],
            0.0,
        )

        inputs = _inputs()
        _series(inputs, "gpu_power_w")["samples"].pop()
        low = _build(inputs)
        self.assertEqual(low["quality"]["status"], "not_evaluable")
        self.assertIn("gpu_power_w", low["quality"]["low_coverage_required_metrics"])

    def test_not_applicable_cannot_hide_a_required_or_applicable_metric(self) -> None:
        inputs = _inputs()
        temperature = _series(inputs, "temperature_c")
        temperature.update(
            status="not_applicable",
            scope="not_applicable",
            interval_ns=None,
            source_provenance_sha256=None,
            reason_code="metric_not_applicable_to_device_profile",
            samples=[],
        )
        with self.assertRaisesRegex(ContractError, "contradicts the device profile"):
            _build(inputs)

        inputs = _inputs()
        battery = _series(inputs, "battery_power_w")
        battery.update(
            status="missing",
            scope="device",
            interval_ns=1_000_000_000,
            source_provenance_sha256=_digest("battery-attempt"),
            reason_code="sensor_unavailable",
        )
        with self.assertRaisesRegex(ContractError, "contradicts the device profile"):
            _build(inputs)

    def test_attribution_scope_and_metric_set_must_agree(self) -> None:
        inputs = _inputs()
        inputs["isolation"]["attributable_metrics"] = []
        with self.assertRaisesRegex(ContractError, "include process_memory_bytes"):
            _build(inputs)

        inputs = _inputs()
        inputs["isolation"]["attributable_metrics"].append("gpu_power_w")
        with self.assertRaisesRegex(ContractError, "scope.*disagree"):
            _build(inputs)

        inputs = _inputs()
        inputs["isolation"]["attributable_metrics"].remove("gpu_memory_used_bytes")
        with self.assertRaisesRegex(ContractError, "omits a profile memory component"):
            _build(inputs)

    def test_memory_peak_is_profile_specific_and_unified_memory_is_not_summed(
        self,
    ) -> None:
        bundle = _build(_inputs("m1_pro_16gb"))
        memory = bundle["summary"]["memory"]
        self.assertEqual(
            memory["combination_method"], "max_shared_unified_physical_bytes"
        )
        self.assertTrue(memory["unified_memory_counted_once"])
        self.assertEqual(memory["observed_peak_bytes"], 1_000_003_000)
        self.assertEqual(
            bundle["summary"]["peak_attributable_active_memory_bytes"],
            1_000_003_000,
        )

        phone = _build(_inputs("iphone_17_pro_max"))
        self.assertEqual(
            phone["summary"]["memory"]["combination_method"],
            "process_physical_bytes",
        )

    def test_device_total_vram_cannot_substitute_for_process_gpu_vram(self) -> None:
        for profile in ("rtx_3090_ti", "gtx_1080_ti"):
            inputs = _inputs(profile)
            _series(inputs, "gpu_memory_used_bytes")["scope"] = "device"
            with (
                self.subTest(profile=profile),
                self.assertRaisesRegex(
                    ContractError, "scope.*attributable_metrics disagree"
                ),
            ):
                _build(inputs)

    def test_memory_alignment_coverage_fails_closed(self) -> None:
        inputs = _inputs()
        _series(inputs, "process_memory_bytes")["samples"].pop(0)
        _series(inputs, "gpu_memory_used_bytes")["samples"].pop(1)
        bundle = _build(inputs)
        memory = bundle["summary"]["memory"]
        self.assertEqual(memory["alignment_status"], "insufficient_coverage")
        self.assertEqual(memory["aligned_sample_count"], 2)
        self.assertEqual(memory["coverage_fraction"], 0.5)
        self.assertIsNotNone(memory["observed_peak_bytes"])
        self.assertIsNone(memory["peak_attributable_active_memory_bytes"])
        self.assertEqual(bundle["quality"]["status"], "not_evaluable")
        self.assertIn(
            "time-aligned attributable physical-memory peak is not complete",
            bundle["quality"]["not_evaluable_reasons"],
        )

    def test_memory_interval_mismatch_does_not_emit_a_promotable_peak(self) -> None:
        inputs = _inputs()
        gpu_memory = _series(inputs, "gpu_memory_used_bytes")
        gpu_memory["interval_ns"] = 2_000_000_000
        gpu_memory["samples"] = [
            {
                "slot": 0,
                "monotonic_ns": 1_000_000_000,
                "value": 1_000_000_000,
            },
            {
                "slot": 1,
                "monotonic_ns": 3_000_000_000,
                "value": 1_000_001_000,
            },
        ]
        bundle = _build(inputs)
        memory = bundle["summary"]["memory"]
        self.assertEqual(memory["alignment_status"], "interval_mismatch")
        self.assertIsNone(memory["peak_attributable_active_memory_bytes"])
        self.assertEqual(bundle["quality"]["status"], "not_evaluable")

    def test_memory_alignment_rejects_same_slot_samples_with_excessive_skew(
        self,
    ) -> None:
        inputs = _inputs()
        gpu_memory = _series(inputs, "gpu_memory_used_bytes")
        gpu_memory["samples"][1]["monotonic_ns"] += 100_000_000
        bundle = _build(inputs)
        memory = bundle["summary"]["memory"]
        self.assertEqual(memory["alignment_tolerance_ns"], 50_000_000)
        self.assertEqual(memory["maximum_observed_alignment_skew_ns"], 100_000_000)
        self.assertEqual(memory["skew_rejected_sample_count"], 1)
        self.assertEqual(memory["alignment_status"], "insufficient_coverage")
        self.assertIsNone(memory["peak_attributable_active_memory_bytes"])

    def test_device_scoped_energy_without_exclusive_lease_is_not_evaluable(
        self,
    ) -> None:
        inputs = _inputs()
        inputs["isolation"]["exclusive_device_lease"] = False
        bundle = _build(inputs)
        self.assertEqual(bundle["quality"]["status"], "not_evaluable")
        self.assertIn(
            "device-scoped power or energy lacks an exclusive device lease",
            bundle["quality"]["not_evaluable_reasons"],
        )

    def test_overhead_missing_high_or_unreplicated_fails_closed(self) -> None:
        inputs = _inputs()
        inputs["overhead"] = {
            "status": "missing",
            "reason_code": "calibration_not_run",
            "attempt_provenance_sha256": _digest("calibration-attempt"),
            "pairs": [],
        }
        missing = _build(inputs)
        self.assertEqual(missing["quality"]["status"], "not_evaluable")

        inputs = _inputs()
        inputs["overhead"]["pairs"] = inputs["overhead"]["pairs"][:2]
        with self.assertRaisesRegex(ContractError, "at least 3 pairs"):
            _build(inputs)

        inputs = _inputs()
        for pair in inputs["overhead"]["pairs"]:
            pair["instrumented_duration_ns"] = 1_200_000_000
        high = _build(inputs)
        self.assertGreater(
            high["overhead"]["estimated_overhead_fraction"],
            MAXIMUM_OVERHEAD_FRACTION,
        )
        self.assertEqual(high["quality"]["status"], "fail")

        inputs = _inputs()
        schedule = inputs["overhead"]["pairs"][0]["schedule_sha256"]
        inputs["overhead"]["pairs"][1]["schedule_sha256"] = schedule
        with self.assertRaisesRegex(ContractError, "schedules must be unique"):
            _build(inputs)

        inputs = _inputs()
        inputs["overhead"]["pairs"] = inputs["overhead"]["pairs"][:1] * 10_001
        with self.assertRaisesRegex(ContractError, "at most 10000 pairs"):
            _build(inputs)

    def test_thermal_throttle_state_and_lifecycle_are_known_failures(self) -> None:
        inputs = _inputs("galaxy_s21_ultra")
        _series(inputs, "thermal_throttle_active")["samples"][2]["value"] = True
        _series(inputs, "thermal_state")["samples"][2]["value"] = "serious"
        _series(inputs, "lifecycle_state")["samples"][2]["value"] = "background"
        bundle = _build(inputs)
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertEqual(len(bundle["quality"]["failure_reasons"]), 3)

    def test_unknown_thermal_or_lifecycle_state_is_not_evaluable(self) -> None:
        inputs = _inputs("iphone_17_pro_max")
        _series(inputs, "thermal_state")["samples"][1]["value"] = "unknown"
        _series(inputs, "lifecycle_state")["samples"][1]["value"] = "unknown"
        bundle = _build(inputs)
        self.assertEqual(bundle["quality"]["status"], "fail")
        self.assertEqual(len(bundle["quality"]["not_evaluable_reasons"]), 2)
        self.assertEqual(len(bundle["quality"]["failure_reasons"]), 1)

    def test_cumulative_energy_must_be_nondecreasing_and_positive_for_quality(
        self,
    ) -> None:
        inputs = _inputs()
        energy = _series(inputs, "cumulative_energy_j")
        energy["samples"][2]["value"] = 5.0
        with self.assertRaisesRegex(ContractError, "nondecreasing"):
            _build(inputs)

        inputs = _inputs()
        for sample in _series(inputs, "cumulative_energy_j")["samples"]:
            sample["value"] = 0.0
        bundle = _build(inputs)
        self.assertEqual(bundle["quality"]["status"], "not_evaluable")

    def test_persisted_hash_summary_and_quality_cannot_be_forged(self) -> None:
        for path in ("telemetry_id", "summary", "quality"):
            bundle = _build(_inputs())
            if path == "telemetry_id":
                bundle[path] = "f" * 64
            elif path == "summary":
                bundle[path]["energy_delta_j"] = 999.0
            else:
                bundle[path]["status"] = "fail"
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ContractError, "deterministic recomputation"),
            ):
                validate_telemetry_bundle(bundle)

    def test_unknown_fields_duplicate_metrics_and_nonfinite_values_are_rejected(
        self,
    ) -> None:
        inputs = _inputs()
        inputs["identity"]["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            _build(inputs)

        inputs = _inputs()
        inputs["series"][1]["metric"] = inputs["series"][0]["metric"]
        with self.assertRaisesRegex(ContractError, "duplicate metric"):
            _build(inputs)

        inputs = _inputs()
        _series(inputs, "gpu_power_w")["samples"][0]["value"] = float("nan")
        with self.assertRaisesRegex(ContractError, "finite number"):
            _build(inputs)

    def test_sampling_grid_is_bounded_before_rows_are_allocated(self) -> None:
        inputs = _inputs()
        _series(inputs, "gpu_power_w")["interval_ns"] = 1
        with self.assertRaisesRegex(ContractError, "sampling grid exceeds"):
            _build(inputs)

    def test_offline_cli_validates_and_hashes_bundle(self) -> None:
        bundle = _build(_inputs())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "telemetry.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                returncode = eval_contract.main(["validate-telemetry", str(path)])
        self.assertEqual(returncode, 0, stderr.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        output = json.loads(stdout.getvalue())
        self.assertTrue(output["ok"])
        self.assertEqual(output["quality_status"], "pass")
        self.assertEqual(output["memory_alignment_status"], "complete")
        self.assertEqual(
            output["telemetry_bundle_sha256"], telemetry_bundle_sha256(bundle)
        )


if __name__ == "__main__":
    unittest.main()
