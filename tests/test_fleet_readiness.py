from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from pheno.fleet_readiness import (
    CAPABILITY_SCHEMA_VERSION,
    HELPER_INPUT_SCHEMA_VERSION,
    FleetReadinessError,
    add_helper_input_hash,
    build_remote_capability_template,
    canonical_json_bytes,
    capability_manifest_sha256,
    capability_readiness,
    helper_input_sha256,
    helper_result_sha256,
    load_policy,
    simulate_gtx1080_helper,
    validate_capability_manifest,
    validate_helper_input,
    validate_helper_result,
    validate_policy,
)
from pheno.paths import PHENO_ROOT
from scripts.fleet_readiness import main as cli_main

POLICY_PATH = PHENO_ROOT / "config" / "fleet_readiness.yaml"


def _observed_phone(policy: dict) -> dict:
    manifest = build_remote_capability_template("galaxy_s21_ultra", policy)
    manifest["capture_state"] = "observed"
    manifest["captured_at"] = "2026-07-14T22:00:00Z"
    manifest["device"].update(
        {
            "instance_id": "phone-fixture-1",
            "manufacturer": "Samsung",
            "model": "Galaxy S21 Ultra fixture",
            "architecture": "arm64-fixture",
            "os_name": "Android",
            "os_version": "fixture-version",
            "os_build": "fixture-build",
        }
    )
    manifest["runtime"].update(
        {
            "name": "cactus",
            "version": "2.0.1",
            "revision": "fixture-runtime-revision",
            "binary_sha256": "1" * 64,
            "installed": True,
        }
    )
    manifest["backend"].update(
        {
            "name": "cpu",
            "version": "fixture-backend-version",
            "revision": "fixture-backend-revision",
            "available": True,
            "capabilities": ["arm64"],
        }
    )
    manifest["build"].update(
        {
            "app_id": "pheno.fixture.collector",
            "version": "1",
            "revision": "fixture-build-revision",
            "build_sha256": "2" * 64,
        }
    )
    manifest["telemetry"].update(
        {
            "memory_available": True,
            "thermal_available": True,
            "lifecycle_available": True,
            "battery_available": True,
            "monotonic_clock_available": True,
            "sampling_interval_ms": 500.0,
        }
    )
    manifest["memory"].update(
        {
            "budget_bytes": 1_000_000_000,
            "available_bytes": 400_000_000,
            "headroom_fraction": 0.4,
            "basis": "os_available_to_process",
        }
    )
    manifest["thermal"].update({"observable": True, "state": "nominal"})
    manifest["lifecycle"].update(
        {
            "observable": True,
            "state": "foreground",
            "foreground_visible": True,
            "cancellation_tested": True,
            "checkpoint_recovery_tested": True,
        }
    )
    manifest["owner_handoff"].update({"status": "approved", "record_sha256": "3" * 64})
    manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
    return manifest


def _helper_input(*, all_gates: bool = True, productive: bool = True) -> dict:
    helper_rate = (
        {"lower": 30.0, "upper": 30.0}
        if productive
        else {
            "lower": 0.1,
            "upper": 1.0,
        }
    )
    acceptance = (
        {"lower": 1.0, "upper": 1.0}
        if productive
        else {
            "lower": 0.1,
            "upper": 0.2,
        }
    )
    value = {
        "schema_version": HELPER_INPUT_SCHEMA_VERSION,
        "simulation_id": "fixture-simulation",
        "intervals": {
            "baseline_avs_per_s": {"lower": 10.0, "upper": 10.0},
            "primary_power_w": {"lower": 400.0, "upper": 400.0},
            "helper_candidate_avs_per_s": helper_rate,
            "coordination_rounds_per_s": {"lower": 0.0, "upper": 0.0},
            "helper_latency_ms": {"lower": 0.0, "upper": 0.0},
            "ipc_latency_ms": {"lower": 0.0, "upper": 0.0},
            "acceptance_fraction": acceptance,
            "helper_power_w": {"lower": 50.0, "upper": 50.0},
        },
        "physical_gates": {
            "psu_capacity": all_gates,
            "slot_available": all_gates,
            "power_connector_available": all_gates,
            "case_clearance": all_gates,
            "thermal_budget": all_gates,
        },
        "input_sha256": "0" * 64,
    }
    return add_helper_input_hash(value)


class FleetReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        validate_policy(cls.policy)

    def test_policy_is_closed_and_every_mutation_install_gate_is_false(self) -> None:
        checked = validate_policy(self.policy)
        self.assertTrue(checked["policy"])
        self.assertTrue(all(value is False for value in checked["policy"].values()))
        relaxed = deepcopy(self.policy)
        relaxed["policy"]["allow_phone_mutation"] = True
        with self.assertRaisesRegex(FleetReadinessError, "must remain false"):
            validate_policy(relaxed)
        unknown = deepcopy(self.policy)
        unknown["policy"]["future_escape_hatch"] = False
        with self.assertRaisesRegex(FleetReadinessError, "unknown"):
            validate_policy(unknown)
        nonzero_epsilon = deepcopy(self.policy)
        nonzero_epsilon["helper_simulation"]["positive_epsilon"] = 0.01
        with self.assertRaisesRegex(FleetReadinessError, "must be 0.0"):
            validate_policy(nonzero_epsilon)

    def test_policy_loader_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            duplicate = Path(temp_dir) / "duplicate.yaml"
            duplicate.write_text(
                "schema_version: first\nschema_version: second\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(FleetReadinessError, "duplicate"):
                load_policy(duplicate)

    def test_policy_loader_rejects_links_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "policy-link.yaml"
            try:
                link.symlink_to(POLICY_PATH)
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            with self.assertRaisesRegex(FleetReadinessError, "symbolic link"):
                load_policy(link)

    def test_remote_template_is_deterministic_valid_and_non_authorizing(self) -> None:
        first = build_remote_capability_template("iphone_17_pro_max", self.policy)
        second = build_remote_capability_template("iphone_17_pro_max", self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], CAPABILITY_SCHEMA_VERSION)
        validate_capability_manifest(first, self.policy)
        self.assertTrue(
            all(value is False for value in first["authorization"].values())
        )
        readiness = capability_readiness(first, self.policy)
        self.assertFalse(readiness["benchmark_capability_ready"])
        self.assertFalse(readiness["benchmark_execution_authorized"])

    def test_capability_hash_binds_every_nested_observation(self) -> None:
        manifest = _observed_phone(self.policy)
        validate_capability_manifest(manifest, self.policy)
        manifest["lifecycle"]["checkpoint_recovery_tested"] = False
        with self.assertRaisesRegex(FleetReadinessError, "does not match its content"):
            validate_capability_manifest(manifest, self.policy)

    def test_observed_phone_can_be_capability_ready_but_never_authorized(self) -> None:
        manifest = _observed_phone(self.policy)
        result = capability_readiness(manifest, self.policy)
        self.assertTrue(result["benchmark_capability_ready"])
        self.assertFalse(result["remote_probe_authorized"])
        self.assertFalse(result["mutation_authorized"])
        self.assertFalse(result["install_authorized"])
        self.assertFalse(result["server_launch_authorized"])
        self.assertFalse(result["benchmark_execution_authorized"])
        manifest["authorization"]["install_authorized"] = True
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        with self.assertRaisesRegex(FleetReadinessError, "must remain false"):
            validate_capability_manifest(manifest, self.policy)

    def test_low_headroom_and_prohibited_thermal_state_fail_readiness(self) -> None:
        manifest = _observed_phone(self.policy)
        manifest["memory"].update(
            {
                "available_bytes": 200_000_000,
                "headroom_fraction": 0.2,
            }
        )
        manifest["thermal"]["state"] = "serious"
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        result = capability_readiness(manifest, self.policy)
        self.assertFalse(result["benchmark_capability_ready"])
        self.assertIn("memory headroom is below the device policy", result["reasons"])
        self.assertIn("thermal state is unknown or prohibited", result["reasons"])

    def test_capability_rejects_unknown_fields_and_nonfinite_numbers(self) -> None:
        unknown = _observed_phone(self.policy)
        unknown["surprise"] = True
        unknown["manifest_sha256"] = capability_manifest_sha256(unknown)
        with self.assertRaisesRegex(FleetReadinessError, "unknown"):
            validate_capability_manifest(unknown, self.policy)
        nonfinite = _observed_phone(self.policy)
        nonfinite["memory"]["headroom_fraction"] = float("nan")
        with self.assertRaisesRegex(FleetReadinessError, "finite"):
            validate_capability_manifest(nonfinite, self.policy)

    def test_helper_input_is_closed_hash_bound_and_finite(self) -> None:
        value = _helper_input()
        validate_helper_input(value)
        unknown = deepcopy(value)
        unknown["intervals"]["mystery"] = {"lower": 0.0, "upper": 0.0}
        unknown = add_helper_input_hash(unknown)
        with self.assertRaisesRegex(FleetReadinessError, "unknown"):
            validate_helper_input(unknown)
        nonfinite = deepcopy(value)
        nonfinite["intervals"]["ipc_latency_ms"]["upper"] = float("inf")
        with self.assertRaisesRegex(FleetReadinessError, "finite"):
            validate_helper_input(nonfinite)

    def test_helper_simulation_requires_positive_lower_bounds_and_every_gate(
        self,
    ) -> None:
        positive = simulate_gtx1080_helper(_helper_input(), self.policy)
        self.assertEqual(positive["decision"], "candidate_for_user_review")
        self.assertGreater(positive["bounds"]["net_avs_goodput_gain_per_s"]["lower"], 0)
        self.assertGreater(
            positive["bounds"]["energy_efficiency_gain_avs_per_joule"]["lower"],
            0,
        )
        self.assertFalse(positive["install_authorized"])
        self.assertFalse(positive["execution_authorized"])

        weak = simulate_gtx1080_helper(_helper_input(productive=False), self.policy)
        self.assertEqual(weak["decision"], "not_justified")
        gated = simulate_gtx1080_helper(_helper_input(all_gates=False), self.policy)
        self.assertEqual(gated["decision"], "not_justified")
        self.assertFalse(gated["physical_gates_passed"])
        self.assertFalse(gated["install_authorized"])

    def test_helper_result_is_deterministic_closed_and_hash_bound(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        second = simulate_gtx1080_helper(_helper_input(), self.policy)
        self.assertEqual(first, second)
        validate_helper_result(first)
        unknown = deepcopy(first)
        unknown["authorization"] = True
        with self.assertRaisesRegex(FleetReadinessError, "unknown"):
            validate_helper_result(unknown)
        forged = simulate_gtx1080_helper(_helper_input(productive=False), self.policy)
        forged["decision"] = "candidate_for_user_review"
        forged["reasons"] = []
        forged["result_sha256"] = helper_result_sha256(forged)
        with self.assertRaisesRegex(FleetReadinessError, "conservative bounds"):
            validate_helper_result(forged)

    def test_cli_template_writes_only_deterministic_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original = os.getcwd()
            try:
                os.chdir(temp_dir)
                outputs = []
                for _ in range(2):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        code = cli_main(
                            [
                                "--config",
                                str(POLICY_PATH),
                                "template-remote",
                                "--device",
                                "m1_pro_16gb",
                            ]
                        )
                    self.assertEqual(code, 0)
                    outputs.append(stdout.getvalue())
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(list(Path(temp_dir).iterdir()), [])
                payload = json.loads(outputs[0])
                self.assertTrue(
                    all(value is False for value in payload["authorization"].values())
                )
            finally:
                os.chdir(original)

    def test_cli_rejects_nonfinite_json_without_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "bad.json"
            source.write_text('{"schema_version": NaN}', encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli_main(
                    ["--config", str(POLICY_PATH), "validate-capability", str(source)]
                )
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("non-finite", stderr.getvalue())
            self.assertEqual(set(Path(temp_dir).iterdir()), {source})

    def test_cli_rejects_linked_json_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = Path(temp_dir) / "input.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli_main(
                    ["--config", str(POLICY_PATH), "validate-capability", str(link)]
                )
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("symbolic link", stderr.getvalue())

    # ------------------------------------------------------------------
    # Policy validation edges
    # ------------------------------------------------------------------

    def test_validate_policy_rejects_unknown_root_fields(self) -> None:
        extra = deepcopy(self.policy)
        extra["future_root_field"] = False
        with self.assertRaisesRegex(FleetReadinessError, "invalid fields"):
            validate_policy(extra)

    def test_validate_policy_rejects_wrong_schema_version(self) -> None:
        bad = deepcopy(self.policy)
        bad["schema_version"] = "pheno.fleet-readiness-policy.v0"
        with self.assertRaisesRegex(FleetReadinessError, "schema_version"):
            validate_policy(bad)

    def test_validate_policy_rejects_unknown_profile_set(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"].pop("rtx_3090_ti")
        with self.assertRaisesRegex(FleetReadinessError, "must match the requested fleet"):
            validate_policy(bad)

    def test_validate_policy_rejects_non_object_device_profiles(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"] = ["not", "a", "mapping"]
        with self.assertRaisesRegex(FleetReadinessError, "must be an object"):
            validate_policy(bad)

    def test_validate_policy_rejects_device_profiles_blocking_remote(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["m1_pro_16gb"]["remote"] = False
        with self.assertRaisesRegex(FleetReadinessError, "remote must be true"):
            validate_policy(bad)

    def test_validate_policy_rejects_device_profiles_blocking_mobile(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["galaxy_s21_ultra"]["mobile"] = False
        with self.assertRaisesRegex(FleetReadinessError, "mobile must be true"):
            validate_policy(bad)

    def test_validate_policy_requires_foreground_for_mobile_profiles(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["iphone_17_pro_max"]["required_lifecycle_states"] = [
            "active"
        ]
        with self.assertRaisesRegex(FleetReadinessError, "foreground lifecycle"):
            validate_policy(bad)

    def test_validate_policy_requires_serious_and_critical_thermal_states(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["galaxy_s21_ultra"]["required_thermal_stop_states"] = [
            "critical"
        ]
        with self.assertRaisesRegex(FleetReadinessError, "serious and critical"):
            validate_policy(bad)

    def test_validate_policy_rejects_unknown_profile_field(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["rtx_3090_ti"]["escape_hatch"] = False
        with self.assertRaisesRegex(FleetReadinessError, "invalid fields"):
            validate_policy(bad)

    def test_validate_policy_rejects_invalid_lifecycle_state(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["rtx_3090_ti"]["required_lifecycle_states"] = ["made_up"]
        with self.assertRaisesRegex(FleetReadinessError, "invalid state"):
            validate_policy(bad)

    def test_validate_policy_rejects_invalid_thermal_state(self) -> None:
        bad = deepcopy(self.policy)
        bad["device_profiles"]["rtx_3090_ti"]["required_thermal_stop_states"] = ["hot"]
        with self.assertRaisesRegex(FleetReadinessError, "invalid state"):
            validate_policy(bad)

    def test_validate_policy_rejects_wrong_helper_method(self) -> None:
        bad = deepcopy(self.policy)
        bad["helper_simulation"]["method"] = "aggressive_v1"
        with self.assertRaisesRegex(FleetReadinessError, "conservative_interval_v1"):
            validate_policy(bad)

    def test_validate_policy_rejects_wrong_helper_physical_gate_set(self) -> None:
        bad = deepcopy(self.policy)
        bad["helper_simulation"]["physical_gate_fields"] = ["psu_capacity"]
        with self.assertRaisesRegex(
            FleetReadinessError, "physical_gate_fields do not match"
        ):
            validate_policy(bad)

    def test_validate_policy_rejects_negative_epsilon_via_minimum(self) -> None:
        bad = deepcopy(self.policy)
        bad["helper_simulation"]["positive_epsilon"] = -0.1
        with self.assertRaisesRegex(FleetReadinessError, "must be >= 0"):
            validate_policy(bad)

    def test_validate_policy_rejects_non_numeric_epsilon(self) -> None:
        bad = deepcopy(self.policy)
        bad["helper_simulation"]["positive_epsilon"] = "0.0"
        with self.assertRaisesRegex(FleetReadinessError, "must be numeric"):
            validate_policy(bad)

    # ------------------------------------------------------------------
    # Policy loader (filesystem / IO) edges
    # ------------------------------------------------------------------

    def test_policy_loader_rejects_directory(self) -> None:
        # On POSIX systems, ``open(path, "rb")`` on a directory raises
        # ``IsADirectoryError``; on Windows it raises ``PermissionError``.
        # Either path bubbles up as the generic "fleet policy cannot be read"
        # message. We accept that outcome and additionally exercise the
        # "regular file" branch by pointing at a directory through a wrapper.
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(FleetReadinessError):
                load_policy(Path(temp_dir))

    def test_policy_loader_rejects_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            oversized = Path(temp_dir) / "huge.yaml"
            oversized.write_bytes(b"a" * (1024 * 1024 + 1))
            with self.assertRaisesRegex(FleetReadinessError, "1 MiB limit"):
                load_policy(oversized)

    def test_policy_loader_rejects_non_utf8_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad = Path(temp_dir) / "binary.yaml"
            bad.write_bytes(b"\xff\xfe\x00\x00")
            with self.assertRaisesRegex(FleetReadinessError, "UTF-8"):
                load_policy(bad)

    def test_policy_loader_rejects_yaml_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            aliased = Path(temp_dir) / "aliases.yaml"
            aliased.write_text(
                "schema_version: &v pheno.fleet-readiness-policy.v1\npolicy: *v\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FleetReadinessError, "aliases"):
                load_policy(aliased)

    def test_policy_loader_rejects_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            broken = Path(temp_dir) / "broken.yaml"
            broken.write_text("schema_version: 'unterminated\n", encoding="utf-8")
            with self.assertRaisesRegex(FleetReadinessError, "invalid YAML"):
                load_policy(broken)

    def test_policy_loader_rejects_non_scalar_keys(self) -> None:
        # Tuple/list keys trip the unhashable-key branch in construct_mapping.
        with tempfile.TemporaryDirectory() as temp_dir:
            weird = Path(temp_dir) / "weird.yaml"
            weird.write_text(
                "[1, 2]: a\nschema_version: pheno.fleet-readiness-policy.v1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FleetReadinessError, "scalar"):
                load_policy(weird)

    # ------------------------------------------------------------------
    # Capability manifest edges
    # ------------------------------------------------------------------

    def _observed_with_overrides(
        self, **overrides: Any
    ) -> dict:
        """Build a fully-hashed observed phone manifest with optional overrides.

        ``overrides`` accepts dotted paths (e.g. ``"backend.name"``) that are
        applied to the manifest before the content hash is computed.
        """

        manifest = _observed_phone(self.policy)
        for path, change in overrides.items():
            target = manifest
            parts = path.split(".")
            for key in parts[:-1]:
                target = target[key]
            target[parts[-1]] = change
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        return manifest

    def _patch_manifest(self, manifest: dict, **overrides: Any) -> dict:
        """Mutate ``manifest`` and re-hash so validators see a valid content hash."""

        for path, change in overrides.items():
            target = manifest
            parts = path.split(".")
            for key in parts[:-1]:
                target = target[key]
            target[parts[-1]] = change
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        return manifest

    def test_validate_capability_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FleetReadinessError, "must be an object"):
            validate_capability_manifest([], self.policy)  # type: ignore[arg-type]

    def test_validate_capability_rejects_wrong_schema_version(self) -> None:
        manifest = self._observed_with_overrides(
            **{"schema_version": "pheno.fleet.device-capability.v0"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "capability.schema_version"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_capture_state(self) -> None:
        manifest = self._observed_with_overrides(**{"capture_state": "in_progress"})
        with self.assertRaisesRegex(FleetReadinessError, "capture_state"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_template_must_have_null_captured_at(self) -> None:
        template = build_remote_capability_template("iphone_17_pro_max", self.policy)
        template["captured_at"] = "2026-07-14T22:00:00Z"
        with self.assertRaisesRegex(FleetReadinessError, "captured_at must be null"):
            validate_capability_manifest(template, self.policy)

    def test_validate_capability_rejects_unknown_profile_id(self) -> None:
        manifest = self._observed_with_overrides(
            **{"device.profile_id": "rogue_laptop"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "not in the fleet"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_mismatched_device_class(self) -> None:
        manifest = self._observed_with_overrides(
            **{"device.device_class": "rogue_class"}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "device_class does not match the policy profile"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_runtime_install_state_mismatch(self) -> None:
        manifest = self._observed_with_overrides(**{"runtime.installed": False})
        with self.assertRaisesRegex(
            FleetReadinessError, "installed state must agree"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_runtime_name_outside_policy(self) -> None:
        manifest = self._observed_with_overrides(
            **{"runtime.name": "vllm"}  # not in galaxy allowed runtimes
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "runtime.name is not allowed"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_backend_name_outside_policy(self) -> None:
        manifest = self._observed_with_overrides(
            **{"backend.name": "cuda"}  # not in galaxy allowed backends
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "backend.name is not allowed"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_observed_template_placeholder(self) -> None:
        manifest = self._observed_with_overrides(
            **{"runtime.version": "<fill-version>"}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "template placeholder"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_timestamp(self) -> None:
        manifest = self._observed_with_overrides(
            **{"captured_at": "not-a-timestamp"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "RFC3339"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_naive_timestamp(self) -> None:
        manifest = self._observed_with_overrides(
            **{"captured_at": "2026-07-14T22:00:00"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "timezone"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_sha256(self) -> None:
        manifest = self._observed_with_overrides(
            **{"build.build_sha256": "abcdef"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "64-character SHA-256"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_sha_with_uppercase_chars(self) -> None:
        # Use a non-hex character so the lowered SHA still fails the hex check.
        manifest = self._observed_with_overrides(
            **{"build.build_sha256": "Z" * 64}
        )
        with self.assertRaisesRegex(FleetReadinessError, "64-character SHA-256"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_telemetry_sampling_mismatch(self) -> None:
        # Drop the sampling interval to None while every telemetry flag stays True
        # so the "telemetry availability must agree with sampling_interval_ms"
        # branch fires before any memory agreement check.
        manifest = self._observed_with_overrides(
            **{"telemetry.sampling_interval_ms": None}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "telemetry availability must agree"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_partial_memory_measurements(self) -> None:
        manifest = self._observed_with_overrides(
            **{"memory.available_bytes": None}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "all present or all null"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_available_exceeding_budget(self) -> None:
        # The "available > budget" branch is logically unreachable because the
        # headroom = available/budget invariant forces headroom > 1.0, which
        # trips the [0, 1] maximum check first. We exercise the surrounding
        # memory checks via a sibling rule to keep coverage honest.
        manifest = self._observed_with_overrides(
            **{"memory.headroom_fraction": 0.5}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "headroom_fraction does not match"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_mismatched_headroom_fraction(self) -> None:
        manifest = self._observed_with_overrides(
            **{"memory.headroom_fraction": 0.5}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "headroom_fraction does not match"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_measured_memory_with_unknown_basis(self) -> None:
        manifest = self._observed_with_overrides(**{"memory.basis": "unknown"})
        with self.assertRaisesRegex(
            FleetReadinessError, "requires a known basis"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_unmeasured_memory_with_known_basis(self) -> None:
        manifest = build_remote_capability_template(
            "iphone_17_pro_max", self.policy
        )
        manifest["memory"]["basis"] = "system_available"
        with self.assertRaisesRegex(
            FleetReadinessError, "must use unknown basis"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_memory_basis(self) -> None:
        manifest = self._observed_with_overrides(
            **{"memory.basis": "made_up_basis"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "memory.basis is invalid"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_thermal_state(self) -> None:
        manifest = self._observed_with_overrides(**{"thermal.state": "scalding"})
        with self.assertRaisesRegex(FleetReadinessError, "thermal.state is invalid"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_thermal_stop_state(self) -> None:
        manifest = self._observed_with_overrides(
            **{"thermal.stop_states": ["critical", "extreme"]}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "stop_states contains an invalid state"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_unobservable_thermal_state(self) -> None:
        manifest = self._observed_with_overrides(**{"thermal.observable": False})
        with self.assertRaisesRegex(
            FleetReadinessError, "unobservable thermal state must be unknown"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_thermal_observable_mismatch(self) -> None:
        manifest = self._observed_with_overrides(
            **{
                "telemetry.thermal_available": False,
                "thermal.observable": True,
            }
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "thermal_available must agree"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_missing_required_thermal_stop(self) -> None:
        manifest = self._observed_with_overrides(
            **{"thermal.stop_states": ["critical"]}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "omits a policy-required stop state"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_lifecycle_state(self) -> None:
        manifest = self._observed_with_overrides(
            **{"lifecycle.state": "backgroundish"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "lifecycle.state is invalid"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_unobservable_lifecycle_state(self) -> None:
        manifest = self._observed_with_overrides(
            **{"lifecycle.observable": False}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "unobservable lifecycle state must be unknown"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_lifecycle_observable_mismatch(self) -> None:
        manifest = self._observed_with_overrides(
            **{"telemetry.lifecycle_available": False}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "lifecycle_available must agree"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_owner_required_mismatch(self) -> None:
        manifest = self._observed_with_overrides(
            **{"owner_handoff.required": False}
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "owner_handoff.required does not match"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_invalid_owner_status(self) -> None:
        manifest = self._observed_with_overrides(
            **{"owner_handoff.status": "unapproved"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "owner_handoff.status is invalid"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_non_required_owner_handoff(self) -> None:
        # Build a template for a non-remote device (rtx_3090_ti) which has
        # owner_handoff_required=False. We hand-build the manifest because
        # build_remote_capability_template refuses non-remote profiles, but the
        # closed validator path is identical.
        manifest = build_remote_capability_template(
            "iphone_17_pro_max", self.policy
        )
        manifest["device"]["profile_id"] = "rtx_3090_ti"
        manifest["device"]["device_class"] = self.policy["device_profiles"][
            "rtx_3090_ti"
        ]["device_class"]
        manifest["owner_handoff"]["required"] = False
        manifest["owner_handoff"]["status"] = "approved"
        manifest["owner_handoff"]["record_sha256"] = "3" * 64
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        with self.assertRaisesRegex(
            FleetReadinessError, "must be not_required without a record"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_approved_owner_without_record(self) -> None:
        manifest = self._observed_with_overrides(
            **{"owner_handoff.record_sha256": None}
        )
        with self.assertRaisesRegex(
            FleetReadinessError,
            "approved owner handoff must have a record hash",
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_required_owner_marked_not_required(self) -> None:
        # Clear the record hash too, otherwise line 757 fires first.
        manifest = self._observed_with_overrides(
            **{
                "owner_handoff.status": "not_required",
                "owner_handoff.record_sha256": None,
            }
        )
        with self.assertRaisesRegex(
            FleetReadinessError, "required owner handoff cannot be not_required"
        ):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_non_boolean_authorization_field(self) -> None:
        manifest = self._observed_with_overrides(
            **{"authorization.install_authorized": "yes"}
        )
        with self.assertRaisesRegex(FleetReadinessError, "must be boolean"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_unknown_authorization_field(self) -> None:
        manifest = self._observed_with_overrides(
            **{"authorization.extra_field": False}
        )
        with self.assertRaisesRegex(FleetReadinessError, "unknown"):
            validate_capability_manifest(manifest, self.policy)

    def test_validate_capability_rejects_mismatched_manifest_sha(self) -> None:
        manifest = self._observed_with_overrides()
        manifest["manifest_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            FleetReadinessError, "manifest_sha256 does not match"
        ):
            validate_capability_manifest(manifest, self.policy)

    # ------------------------------------------------------------------
    # Capability readiness edges
    # ------------------------------------------------------------------

    def test_readiness_rejects_template_runtime_unavailable(self) -> None:
        template = build_remote_capability_template(
            "iphone_17_pro_max", self.policy
        )
        result = capability_readiness(template, self.policy)
        self.assertFalse(result["benchmark_capability_ready"])
        self.assertIn("capability is an unmeasured template", result["reasons"])
        self.assertIn("runtime is not observed as installed", result["reasons"])
        self.assertIn("backend is not observed as available", result["reasons"])
        self.assertIn("app or collector build hash is missing", result["reasons"])
        for field in (
            "memory_available",
            "thermal_available",
            "lifecycle_available",
            "monotonic_clock_available",
        ):
            self.assertIn(
                f"telemetry capability {field} is unavailable",
                result["reasons"],
            )
        self.assertIn("memory headroom is unavailable", result["reasons"])

    def test_readiness_flags_non_foreground_lifecycle_for_mobile(self) -> None:
        manifest = _observed_phone(self.policy)
        manifest["lifecycle"]["state"] = "background"
        manifest["lifecycle"]["cancellation_tested"] = False
        manifest["lifecycle"]["checkpoint_recovery_tested"] = False
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        result = capability_readiness(manifest, self.policy)
        self.assertIn(
            "lifecycle state is not permitted for this device", result["reasons"]
        )
        self.assertIn(
            "mobile lifecycle cancellation has not been tested", result["reasons"]
        )
        self.assertIn(
            "mobile checkpoint recovery has not been tested", result["reasons"]
        )

    def test_readiness_flags_non_approved_owner_handoff(self) -> None:
        manifest = _observed_phone(self.policy)
        manifest["owner_handoff"]["status"] = "pending"
        manifest["owner_handoff"]["record_sha256"] = None
        manifest["manifest_sha256"] = capability_manifest_sha256(manifest)
        result = capability_readiness(manifest, self.policy)
        self.assertIn("owner handoff is not approved", result["reasons"])

    # ------------------------------------------------------------------
    # Remote capability template edges
    # ------------------------------------------------------------------

    def test_remote_template_rejects_non_remote_profile(self) -> None:
        with self.assertRaisesRegex(
            FleetReadinessError,
            "limited to the M1 Pro and the two phones",
        ):
            build_remote_capability_template("rtx_3090_ti", self.policy)

    # ------------------------------------------------------------------
    # Helper input / simulation / result edges
    # ------------------------------------------------------------------

    def test_helper_input_rejects_wrong_schema_version(self) -> None:
        value = _helper_input()
        value["schema_version"] = "pheno.fleet.gtx1080-helper-input.v0"
        with self.assertRaisesRegex(FleetReadinessError, "schema_version"):
            validate_helper_input(value)

    def test_helper_input_rejects_blank_simulation_id(self) -> None:
        value = _helper_input()
        value["simulation_id"] = "  "
        value = add_helper_input_hash(value)
        with self.assertRaisesRegex(FleetReadinessError, "non-empty string"):
            validate_helper_input(value)

    def test_helper_input_rejects_interval_with_lower_exceeding_upper(self) -> None:
        value = _helper_input()
        value["intervals"]["ipc_latency_ms"]["lower"] = 5.0
        value = add_helper_input_hash(value)
        with self.assertRaisesRegex(FleetReadinessError, "cannot exceed upper"):
            validate_helper_input(value)

    def test_helper_input_rejects_non_strictly_positive_lower_bound(self) -> None:
        value = _helper_input()
        value["intervals"]["baseline_avs_per_s"]["lower"] = 0.0
        value = add_helper_input_hash(value)
        with self.assertRaisesRegex(
            FleetReadinessError, "must be greater than zero"
        ):
            validate_helper_input(value)

    def test_helper_input_rejects_acceptance_fraction_above_one(self) -> None:
        value = _helper_input()
        value["intervals"]["acceptance_fraction"]["upper"] = 1.5
        value = add_helper_input_hash(value)
        with self.assertRaisesRegex(FleetReadinessError, "must be <= 1.0"):
            validate_helper_input(value)

    def test_helper_input_rejects_non_boolean_gate(self) -> None:
        value = _helper_input()
        value["physical_gates"]["psu_capacity"] = "yes"
        value = add_helper_input_hash(value)
        with self.assertRaisesRegex(FleetReadinessError, "must be boolean"):
            validate_helper_input(value)

    def test_helper_input_rejects_bad_sha(self) -> None:
        value = _helper_input()
        value["input_sha256"] = "not-a-sha"
        with self.assertRaisesRegex(
            FleetReadinessError, "64-character SHA-256"
        ):
            validate_helper_input(value)

    def test_helper_input_rejects_recomputed_sha_mismatch(self) -> None:
        value = _helper_input()
        value["simulation_id"] = "tampered-id"
        with self.assertRaisesRegex(
            FleetReadinessError, "input_sha256 does not match"
        ):
            validate_helper_input(value)

    def test_canonical_json_bytes_rejects_non_serializable(self) -> None:
        with self.assertRaisesRegex(FleetReadinessError, "canonical JSON"):
            canonical_json_bytes({"oops": {1, 2, 3}})

    def test_canonical_json_bytes_emits_stable_bytes(self) -> None:
        first = canonical_json_bytes({"b": 1, "a": 2})
        second = canonical_json_bytes({"a": 2, "b": 1})
        self.assertEqual(first, second)

    def test_simulate_helper_with_zero_helper_rate_is_not_justified(self) -> None:
        # gain_lower <= 0 triggers the not-positive reason branch.
        weak = _helper_input(productive=False)
        weak["intervals"]["helper_candidate_avs_per_s"] = {
            "lower": 0.0,
            "upper": 0.0,
        }
        weak["intervals"]["acceptance_fraction"] = {"lower": 1.0, "upper": 1.0}
        weak = add_helper_input_hash(weak)
        result = simulate_gtx1080_helper(weak, self.policy)
        self.assertEqual(result["decision"], "not_justified")
        self.assertIn(
            "lower-bound net AVS goodput gain is not positive", result["reasons"]
        )

    def test_validate_helper_result_rejects_wrong_schema_version(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["schema_version"] = "pheno.fleet.gtx1080-helper-result.v0"
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(FleetReadinessError, "schema_version"):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_wrong_method(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["method"] = "aggressive_interval_v1"
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(FleetReadinessError, "method is invalid"):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_blocked_fraction_out_of_range(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["bounds"]["blocked_fraction"] = {"lower": -0.1, "upper": 0.9}
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(
            FleetReadinessError, "blocked fraction must be in"
        ):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_gate_summary_mismatch(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(all_gates=False), self.policy)
        first["physical_gates_passed"] = True
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(
            FleetReadinessError, "physical gate summary is inconsistent"
        ):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_invalid_decision(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["decision"] = "undecided"
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(FleetReadinessError, "decision is invalid"):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_reason_decision_mismatch(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["reasons"].append("bogus reason")
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(
            FleetReadinessError, "decision and reasons are inconsistent"
        ):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_non_boolean_gate(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["physical_gates"]["psu_capacity"] = 1
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(FleetReadinessError, "must be boolean"):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_install_authorized_true(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["install_authorized"] = True
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(
            FleetReadinessError, "install_authorized must remain false"
        ):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_execution_authorized_true(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["execution_authorized"] = True
        first["result_sha256"] = helper_result_sha256(first)
        with self.assertRaisesRegex(
            FleetReadinessError, "execution_authorized must remain false"
        ):
            validate_helper_result(first)

    def test_validate_helper_result_rejects_recomputed_sha_mismatch(self) -> None:
        first = simulate_gtx1080_helper(_helper_input(), self.policy)
        first["result_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            FleetReadinessError, "result_sha256 does not match"
        ):
            validate_helper_result(first)

    def test_helper_input_sha_is_deterministic(self) -> None:
        value = _helper_input()
        first = helper_input_sha256(value)
        second = helper_input_sha256(deepcopy(value))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
