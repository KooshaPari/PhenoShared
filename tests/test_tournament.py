from __future__ import annotations

import copy
import unittest
from collections.abc import Mapping
from typing import Any

import yaml

from pheno.evidence.contracts import ContractError
from pheno.evidence.tournament import (
    TOURNAMENT_SCHEMA_VERSION,
    build_candidate_review,
    validate_tournament,
)
from pheno.paths import PHENO_ROOT


def _make_valid_config() -> dict[str, Any]:
    """Return a deep copy of the canonical heterogeneous tournament config."""

    config = yaml.safe_load(
        (PHENO_ROOT / "config" / "heterogeneous_tournament.yaml").read_text(
            encoding="utf-8"
        )
    )
    return copy.deepcopy(config)


def _runtime_pin(channel: str = "released", commit: str | None = None) -> dict[str, Any]:
    pin: dict[str, Any] = {"version": "1.0.0", "channel": channel}
    if commit is not None:
        pin["commit"] = commit
    return pin


def _make_valid_policy_block() -> dict[str, Any]:
    return {
        "review_only": True,
        "allow_model_artifact_download": False,
        "allow_server_launch": False,
        "allow_phone_install": False,
        "allow_mac_mutation": False,
        "allow_1080ti_install": False,
        "mutate_adr_locked_shortlist": False,
        "max_total_parameters": 35_000_000_000,
        "north_star": ["avs_per_second"],
    }


def _make_valid_mobile_policy() -> dict[str, Any]:
    return {
        "trust_class": "untrusted_burst_worker",
        "coordinator_authoritative": True,
        "foreground_visible": True,
        "user_initiated": True,
        "outbound_only": True,
        "no_cloud_handoff": True,
        "no_tool_execution": True,
        "no_workload_secrets": True,
        "external_vendor_telemetry_disabled": True,
        "authenticated_transport": True,
        "device_scoped_short_lived_transport_credentials": True,
        "transport_credentials_excluded_from_lease_payload": True,
        "replay_protected_leases": True,
        "content_hashed_result_bundle": True,
        "allowed_tasks": ["needle_function_routing"],
        "forbidden_inputs": ["workload_credentials_or_tokens"],
        "required_telemetry": ["ttft_and_decode_rate"],
        "sustained_probe_seconds": [300, 900, 1800],
        "initial_memory_headroom_fraction": 0.30,
        "lease": {
            "checkpoint_max_seconds": 30,
            "required_fields": [
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
            ],
        },
    }


def _make_valid_device(name: str, runtimes: list[str]) -> dict[str, Any]:
    if name == "rtx_3090_ti":
        return {
            "available": True,
            "install_authorized": True,
            "memory_gb": 24,
            "architecture": "sm_86",
            "runtimes": runtimes,
            "default_runtime": runtimes[0] if runtimes else None,
            "constraints": ["no native FP8"],
        }
    if name == "m1_pro_16gb":
        return {
            "available": True,
            "install_authorized": False,
            "remote_mutation_authorized": False,
            "memory_gb": 16,
            "architecture": "apple_m1_pro",
            "runtimes": runtimes,
            "default_runtime": runtimes[0] if runtimes else None,
            "constraints": ["Existing workspace is owner-managed."],
        }
    if name == "galaxy_s21_ultra":
        return {
            "available": True,
            "install_authorized": False,
            "memory_gb": None,
            "architecture": "probe_required",
            "runtimes": runtimes,
            "backends": ["cpu"],
            "default_runtime": None,
            "constraints": ["Probe before installation."],
        }
    if name == "iphone_17_pro_max":
        return {
            "available": True,
            "install_authorized": False,
            "memory_gb": None,
            "architecture": "apple_mobile_probe_required",
            "runtimes": runtimes,
            "backends": ["cpu", "metal"],
            "default_runtime": None,
            "constraints": ["Foreground work only."],
        }
    if name == "gtx_1080_ti":
        return {
            "available": True,
            "install_authorized": False,
            "probe_authorized": True,
            "memory_gb": 11,
            "architecture": "sm_61",
            "runtimes": runtimes,
            "backends": ["cuda_12_legacy"],
            "default_runtime": None,
            "constraints": ["Helper only."],
        }
    raise ValueError(name)


def _make_valid_runtime_pins() -> dict[str, dict[str, Any]]:
    return {
        "sglang": _runtime_pin("pr_head_ref"),
        "vllm": _runtime_pin("pr_head_ref"),
        "tensorrt_llm": _runtime_pin("stable"),
        "tensorrt_llm_dflash": _runtime_pin("prerelease"),
        "mlx": _runtime_pin("released"),
        "mlx_lm": _runtime_pin("released"),
        "omlx": _runtime_pin("released"),
        "llama_cpp": _runtime_pin(
            "tagged_commit",
            commit="c71854292f7c367cc3b35939f88121d81945472f",
        ),
        "cactus": _runtime_pin("released"),
        "mnn": _runtime_pin("released"),
        "executorch": _runtime_pin("released"),
        "mlx_swift": _runtime_pin("released"),
        "mlx_swift_lm": _runtime_pin("released"),
        "mlc_llm": _runtime_pin(
            "main_commit",
            commit="a2bcc5c86678b72a86b7aadc29b643a5ce63c747",
        ),
        "litert_lm": _runtime_pin(
            "released",
            commit="80f301ff9a3b02c2c1e7be2dd1a567752f7b51b6",
        ),
    }


def _make_valid_devices(
    runtime_names: list[str],
) -> dict[str, dict[str, Any]]:
    return {
        "rtx_3090_ti": _make_valid_device("rtx_3090_ti", runtime_names),
        "m1_pro_16gb": _make_valid_device("m1_pro_16gb", runtime_names),
        "galaxy_s21_ultra": _make_valid_device("galaxy_s21_ultra", runtime_names),
        "iphone_17_pro_max": _make_valid_device("iphone_17_pro_max", runtime_names),
        "gtx_1080_ti": _make_valid_device("gtx_1080_ti", ["llama_cpp"]),
    }


def _control_candidate(
    cid: str, runtimes: list[str], lanes: list[str]
) -> dict[str, Any]:
    return {
        "id": cid,
        "status": "locked_control",
        "tier": "worker",
        "architecture": "dense",
        "total_parameters": 9_000_000_000,
        "active_parameters": 9_000_000_000,
        "registry_keys": [cid],
        "source_urls": [f"https://example.com/{cid}"],
        "lanes": lanes,
        "runtimes": runtimes,
        "license_gate": "existing_adr",
        "execution_gate": "existing_adr_only",
    }


def _make_valid_candidate(
    runtimes: list[str], lanes: list[str]
) -> dict[str, Any]:
    return {
        "id": "test-candidate",
        "status": "candidate",
        "tier": "worker",
        "architecture": "dense",
        "total_parameters": 9_000_000_000,
        "active_parameters": 9_000_000_000,
        "registry_keys": ["test-candidate"],
        "source_urls": ["https://example.com/test"],
        "lanes": lanes,
        "runtimes": runtimes,
        "license_gate": "review_required",
        "execution_gate": "blocked",
    }


def _make_valid_skeleton() -> dict[str, Any]:
    runtime_names = ["sglang", "vllm", "omlx"]
    return {
        "schema_version": TOURNAMENT_SCHEMA_VERSION,
        "cutoff_date": "2026-07-14",
        "policy": _make_valid_policy_block(),
        "runtime_pins": _make_valid_runtime_pins(),
        "kernel_substrate_pins": {"wgpu": {"version": "29.0.3", "channel": "released"}},
        "mobile_worker_policy": _make_valid_mobile_policy(),
        "devices": _make_valid_devices(runtime_names),
        "candidates": [
            _control_candidate("qwen35-08b-control", ["sglang", "vllm", "omlx"], ["rtx_3090_ti", "m1_pro_16gb"]),
            _control_candidate(
                "lfm25-8b-a1b-control",
                ["sglang", "vllm", "omlx", "llama_cpp"],
                ["rtx_3090_ti", "m1_pro_16gb"],
            ),
            _control_candidate(
                "ornith-9b-control",
                ["sglang", "vllm", "omlx"],
                ["rtx_3090_ti", "m1_pro_16gb"],
            ),
            _make_valid_candidate(runtime_names, ["rtx_3090_ti", "m1_pro_16gb"]),
        ],
        "acceleration_order": ["exact_autoregressive_baseline"],
    }


def _observation(
    record_id: str,
    canonical_name: str,
    *,
    mutable: bool = False,
    retrieved_at: str = "2026-07-14T22:00:00Z",
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "retrieved_at": retrieved_at,
        "source": {"revision": record_id},
        "subject": {"canonical_name": canonical_name},
        "resolved": {"mutable": mutable},
        "license": {"declared": ["apache-2.0"], "verified": False},
    }


class TournamentValidationTests(unittest.TestCase):
    """Exercise the closed, review-only tournament validator."""

    def test_canonical_config_validates_and_returns_copy(self) -> None:
        config = _make_valid_config()
        returned = validate_tournament(config)
        self.assertIsInstance(returned, dict)
        self.assertEqual(returned["schema_version"], TOURNAMENT_SCHEMA_VERSION)
        self.assertIsNot(returned, config)
        self.assertEqual(returned["cutoff_date"], config["cutoff_date"])

    def test_root_must_be_object(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_tournament([])  # type: ignore[arg-type]

    def test_schema_version_must_match(self) -> None:
        config = _make_valid_skeleton()
        config["schema_version"] = "pheno.tournament.v0"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            validate_tournament(config)

    def test_cutoff_date_must_be_iso_date(self) -> None:
        config = _make_valid_skeleton()
        config["cutoff_date"] = "not-a-date"
        with self.assertRaisesRegex(ContractError, "cutoff_date"):
            validate_tournament(config)

    def test_policy_block_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["policy"] = []
        with self.assertRaisesRegex(ContractError, "policy must be an object"):
            validate_tournament(config)

    def test_policy_review_only_must_be_true(self) -> None:
        config = _make_valid_skeleton()
        config["policy"]["review_only"] = False
        with self.assertRaisesRegex(ContractError, "review_only must be true"):
            validate_tournament(config)

    def test_each_required_false_policy_field_is_enforced(self) -> None:
        for field in (
            "allow_model_artifact_download",
            "allow_server_launch",
            "allow_phone_install",
            "allow_mac_mutation",
            "allow_1080ti_install",
            "mutate_adr_locked_shortlist",
        ):
            with self.subTest(field=field):
                config = _make_valid_skeleton()
                config["policy"][field] = True
                with self.assertRaisesRegex(ContractError, f"policy.{field} must be false"):
                    validate_tournament(config)

    def test_policy_max_total_parameters_rejects_non_positive_or_bool(self) -> None:
        for bad in (0, -1, True, 1.5, "lots"):
            with self.subTest(value=bad):
                config = _make_valid_skeleton()
                config["policy"]["max_total_parameters"] = bad
                with self.assertRaisesRegex(
                    ContractError, "max_total_parameters must be positive"
                ):
                    validate_tournament(config)

    def test_policy_north_star_must_be_non_empty_array(self) -> None:
        config = _make_valid_skeleton()
        config["policy"]["north_star"] = []
        with self.assertRaisesRegex(ContractError, "north_star"):
            validate_tournament(config)
        config["policy"]["north_star"] = [""]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)
        config["policy"]["north_star"] = "not-an-array"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            validate_tournament(config)

    def test_runtime_pins_block_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"] = []
        with self.assertRaisesRegex(ContractError, "runtime_pins must be an object"):
            validate_tournament(config)

    def test_runtime_pins_must_be_non_empty(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"] = {}
        with self.assertRaisesRegex(ContractError, "runtime_pins cannot be empty"):
            validate_tournament(config)

    def test_runtime_pins_rejects_non_string_pin_names(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"][123] = _runtime_pin()
        with self.assertRaisesRegex(ContractError, "runtime pin names must be strings"):
            validate_tournament(config)

    def test_runtime_pin_version_or_channel_must_be_non_empty_string(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"]["sglang"]["version"] = ""
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["runtime_pins"]["sglang"]["channel"] = "  "
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_runtime_pin_commit_must_be_40_hex_when_provided(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"]["sglang"]["commit"] = "deadbeef"
        with self.assertRaisesRegex(ContractError, "40-hex SHA"):
            validate_tournament(config)

    def test_runtime_pin_commit_channel_requires_immutable_sha(self) -> None:
        config = _make_valid_skeleton()
        config["runtime_pins"]["sglang"] = {
            "version": "main",
            "channel": "main_commit",
        }
        with self.assertRaisesRegex(ContractError, "commit channel requires"):
            validate_tournament(config)
        config["runtime_pins"]["sglang"]["commit"] = "c71854292f7c367cc3b35939f88121d81945472f"
        validate_tournament(config)

    def test_kernel_substrate_pin_must_be_object_with_strings(self) -> None:
        config = _make_valid_skeleton()
        config["kernel_substrate_pins"] = {"wgpu": "not-a-mapping"}
        with self.assertRaisesRegex(ContractError, "kernel_substrate_pins.wgpu must be an object"):
            validate_tournament(config)
        config["kernel_substrate_pins"] = {"wgpu": {"version": "", "channel": "released"}}
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_mobile_worker_policy_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"] = "broken"
        with self.assertRaisesRegex(ContractError, "mobile_worker_policy must be an object"):
            validate_tournament(config)

    def test_mobile_trust_class_must_be_untrusted_burst_worker(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["trust_class"] = "trusted"
        with self.assertRaisesRegex(ContractError, "untrusted burst worker"):
            validate_tournament(config)

    def test_each_required_mobile_true_field_is_enforced(self) -> None:
        for field in (
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
        ):
            with self.subTest(field=field):
                config = _make_valid_skeleton()
                config["mobile_worker_policy"][field] = False
                with self.assertRaisesRegex(
                    ContractError, f"mobile_worker_policy.{field} must be true"
                ):
                    validate_tournament(config)

    def test_mobile_string_fields_must_be_non_empty(self) -> None:
        for field in ("allowed_tasks", "forbidden_inputs", "required_telemetry"):
            with self.subTest(field=field):
                config = _make_valid_skeleton()
                config["mobile_worker_policy"][field] = []
                with self.assertRaisesRegex(ContractError, field):
                    validate_tournament(config)
                config["mobile_worker_policy"][field] = [" ", "x"]
                with self.assertRaisesRegex(ContractError, "non-empty string"):
                    validate_tournament(config)

    def test_mobile_sustained_probe_seconds_must_match_exact_set(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["sustained_probe_seconds"] = [60, 120, 240]
        with self.assertRaisesRegex(ContractError, "5, 15, and 30 minutes"):
            validate_tournament(config)

    def test_mobile_memory_headroom_must_be_in_range_and_numeric(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = 0.10
        with self.assertRaisesRegex(ContractError, "between 25 and 35"):
            validate_tournament(config)
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = 0.50
        with self.assertRaisesRegex(ContractError, "between 25 and 35"):
            validate_tournament(config)
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = True
        with self.assertRaisesRegex(ContractError, "mobile memory headroom must be numeric"):
            validate_tournament(config)
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = "0.30"
        with self.assertRaisesRegex(ContractError, "mobile memory headroom must be numeric"):
            validate_tournament(config)
        # 0.25 and 0.35 are inclusive bounds.
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = 0.25
        validate_tournament(config)
        config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = 0.35
        validate_tournament(config)

    def test_mobile_lease_block_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["lease"] = []
        with self.assertRaisesRegex(ContractError, "lease must be an object"):
            validate_tournament(config)

    def test_mobile_lease_checkpoint_interval_must_be_1_to_60(self) -> None:
        for bad in (0, 61, 1.5, True, "30"):
            with self.subTest(value=bad):
                config = _make_valid_skeleton()
                config["mobile_worker_policy"]["lease"]["checkpoint_max_seconds"] = bad
                with self.assertRaisesRegex(ContractError, "checkpoint interval"):
                    validate_tournament(config)

    def test_mobile_lease_required_fields_must_include_mandatory_set(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["lease"]["required_fields"] = ["job_id"]
        with self.assertRaisesRegex(ContractError, "missing mandatory fields"):
            validate_tournament(config)

    def test_devices_block_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["devices"] = []
        with self.assertRaisesRegex(ContractError, "devices must be an object"):
            validate_tournament(config)

    def test_devices_must_match_exact_fleet_set(self) -> None:
        config = _make_valid_skeleton()
        config["devices"].pop("gtx_1080_ti")
        with self.assertRaisesRegex(ContractError, "device set does not match"):
            validate_tournament(config)
        config["devices"]["rogue-device"] = _make_valid_device(
            "gtx_1080_ti", ["llama_cpp"]
        )
        with self.assertRaisesRegex(ContractError, "device set does not match"):
            validate_tournament(config)

    def test_device_available_and_install_authorized_must_be_boolean(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["available"] = "yes"
        with self.assertRaisesRegex(ContractError, "available must be boolean"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["install_authorized"] = 1
        with self.assertRaisesRegex(ContractError, "install_authorized must be boolean"):
            validate_tournament(config)

    def test_device_probe_authorized_when_present_must_be_boolean(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["gtx_1080_ti"]["probe_authorized"] = "true"
        with self.assertRaisesRegex(ContractError, "probe_authorized must be boolean"):
            validate_tournament(config)

    def test_device_runtimes_must_be_pinned(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["runtimes"].append("mystery-runtime")
        with self.assertRaisesRegex(ContractError, "unpinned runtime"):
            validate_tournament(config)

    def test_device_runtimes_and_backends_must_be_disjoint(self) -> None:
        config = _make_valid_skeleton()
        # Pin "metal" first so the unpinned-runtime check passes and we reach
        # the conflates-a-backend-with-a-runtime branch.
        config["runtime_pins"]["metal"] = _runtime_pin("released")
        config["devices"]["iphone_17_pro_max"]["runtimes"].append("metal")
        with self.assertRaisesRegex(ContractError, "conflates a backend"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["sglang"]
        config["devices"]["iphone_17_pro_max"]["backends"] = ["sglang"]
        with self.assertRaisesRegex(ContractError, "backend/runtime names must be distinct"):
            validate_tournament(config)

    def test_device_default_runtime_must_be_in_runtimes(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["default_runtime"] = "mystery-runtime"
        with self.assertRaisesRegex(ContractError, "default_runtime is not in runtimes"):
            validate_tournament(config)

    def test_device_constraints_must_be_non_empty_string_list(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["constraints"] = []
        with self.assertRaisesRegex(ContractError, "constraints"):
            validate_tournament(config)
        config["devices"]["rtx_3090_ti"]["constraints"] = ["valid", " "]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_m1_pro_remote_mutation_must_remain_unauthorized(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["m1_pro_16gb"]["remote_mutation_authorized"] = True
        with self.assertRaisesRegex(
            ContractError, "M1 Pro remote mutation must remain unauthorized"
        ):
            validate_tournament(config)
        config["devices"]["m1_pro_16gb"].pop("remote_mutation_authorized")
        with self.assertRaisesRegex(
            ContractError, "M1 Pro remote mutation must remain unauthorized"
        ):
            validate_tournament(config)

    def test_install_authorized_must_remain_false_for_protected_devices(self) -> None:
        for name in ("m1_pro_16gb", "galaxy_s21_ultra", "iphone_17_pro_max"):
            with self.subTest(device=name):
                config = _make_valid_skeleton()
                config["devices"][name]["install_authorized"] = True
                with self.assertRaisesRegex(
                    ContractError, f"devices.{name}.install_authorized must remain false"
                ):
                    validate_tournament(config)

    def test_1080_ti_available_requires_probe_authorization(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["gtx_1080_ti"]["probe_authorized"] = False
        with self.assertRaisesRegex(
            ContractError, "available 1080 Ti requires explicit probe authorization"
        ):
            validate_tournament(config)

    def test_1080_ti_available_keeps_install_separately_gated(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["gtx_1080_ti"]["install_authorized"] = True
        with self.assertRaisesRegex(
            ContractError, "1080 Ti installation must remain separately gated"
        ):
            validate_tournament(config)

    def test_1080_ti_unavailable_bypasses_probe_and_install_gates(self) -> None:
        # When the 1080 Ti is unavailable, both probe and install gates are
        # skipped entirely, so we can drop probe_authorized and keep install
        # authorized disabled without error.
        config = _make_valid_skeleton()
        config["devices"]["gtx_1080_ti"]["available"] = False
        config["devices"]["gtx_1080_ti"].pop("probe_authorized", None)
        config["devices"]["gtx_1080_ti"]["install_authorized"] = False
        validate_tournament(config)

    def test_candidates_must_be_non_empty_array(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"] = []
        with self.assertRaisesRegex(ContractError, "candidates must be a non-empty array"):
            validate_tournament(config)
        config["candidates"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "candidates must be a non-empty array"):
            validate_tournament(config)

    def test_candidate_must_be_object(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"].append([])
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_tournament(config)

    def test_candidate_ids_must_be_unique_and_non_empty(self) -> None:
        config = _make_valid_skeleton()
        duplicate = copy.deepcopy(config["candidates"][3])
        duplicate["id"] = ""
        config["candidates"].append(duplicate)
        with self.assertRaisesRegex(ContractError, "candidate ids must be unique"):
            validate_tournament(config)
        duplicate["id"] = config["candidates"][3]["id"]
        config["candidates"].append(duplicate)
        with self.assertRaisesRegex(ContractError, "candidate ids must be unique"):
            validate_tournament(config)

    def test_candidate_status_must_be_in_known_set(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["status"] = "pending_review"
        with self.assertRaisesRegex(ContractError, "invalid status"):
            validate_tournament(config)

    def test_candidate_tier_and_architecture_must_be_in_known_sets(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["tier"] = "experimental"
        with self.assertRaisesRegex(ContractError, "invalid tier/architecture"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["architecture"] = "ssm"
        with self.assertRaisesRegex(ContractError, "invalid tier/architecture"):
            validate_tournament(config)

    def test_candidate_parameter_counts_must_be_positive_ints(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["total_parameters"] = 0
        with self.assertRaisesRegex(ContractError, "parameter counts are invalid"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["active_parameters"] = "many"
        with self.assertRaisesRegex(ContractError, "parameter counts are invalid"):
            validate_tournament(config)

    def test_candidate_active_must_be_in_bounds_and_total_under_ceiling(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["active_parameters"] = 0
        with self.assertRaisesRegex(ContractError, "violates parameter bounds"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["active_parameters"] = 10_000_000_000
        with self.assertRaisesRegex(ContractError, "violates parameter bounds"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["total_parameters"] = 36_000_000_000
        with self.assertRaisesRegex(ContractError, "violates parameter bounds"):
            validate_tournament(config)

    def test_sub_half_billion_candidate_must_be_specialist(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["total_parameters"] = 100_000_000
        config["candidates"][3]["active_parameters"] = 100_000_000
        config["candidates"][3]["tier"] = "worker"
        with self.assertRaisesRegex(ContractError, "sub-0.5B candidate"):
            validate_tournament(config)

    def test_candidate_lanes_must_be_subset_of_devices(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["lanes"] = ["rtx_3090_ti", "mystery_device"]
        with self.assertRaisesRegex(ContractError, "unknown device"):
            validate_tournament(config)

    def test_candidate_runtimes_must_be_pinned(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["runtimes"] = ["sglang", "mystery-runtime"]
        with self.assertRaisesRegex(ContractError, "unpinned runtime"):
            validate_tournament(config)

    def test_candidate_lane_runtime_intersection_must_be_non_empty(self) -> None:
        config = _make_valid_skeleton()
        config["devices"]["rtx_3090_ti"]["runtimes"] = ["tensorrt_llm"]
        config["devices"]["rtx_3090_ti"]["default_runtime"] = "tensorrt_llm"
        with self.assertRaisesRegex(
            ContractError, "no supported runtime for lane rtx_3090_ti"
        ):
            validate_tournament(config)

    def test_candidate_registry_keys_and_source_urls_validation(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["registry_keys"] = []
        validate_tournament(config)  # empty registry_keys is allowed.
        config["candidates"][3]["registry_keys"] = ["ok", " "]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["source_urls"] = "not-an-array"
        with self.assertRaisesRegex(ContractError, "source_urls"):
            validate_tournament(config)

    def test_candidate_execution_and_license_gates_are_enforced(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["execution_gate"] = "approved"
        with self.assertRaisesRegex(ContractError, "execution must remain blocked"):
            validate_tournament(config)
        config = _make_valid_skeleton()
        config["candidates"][3]["license_gate"] = "approved"
        with self.assertRaisesRegex(ContractError, "license must require review"):
            validate_tournament(config)

    def test_mobile_candidate_requires_exact_artifact_runtime_gate(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["candidates"][3]["runtimes"] = ["sglang"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["sglang"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["sglang"]
        config["candidates"][3].pop("mobile_support_gate", None)
        with self.assertRaisesRegex(
            ContractError, "exact mobile artifact/runtime gate"
        ):
            validate_tournament(config)

    def test_mobile_candidate_phone_lane_mode_validates_options(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["sglang"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["sglang"]
        config["candidates"][3]["runtimes"] = ["sglang"]
        config["candidates"][3]["mobile_support_gate"] = (
            "exact_artifact_runtime_probe_required"
        )
        config["candidates"][3]["phone_lane_mode"] = "always_on"
        with self.assertRaisesRegex(ContractError, "invalid phone lane mode"):
            validate_tournament(config)

    def test_over_4b_mobile_candidate_requires_feasibility_only(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["sglang"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["sglang"]
        config["candidates"][3]["runtimes"] = ["sglang"]
        config["candidates"][3]["mobile_support_gate"] = (
            "exact_artifact_runtime_probe_required"
        )
        config["candidates"][3]["total_parameters"] = 4_500_000_000
        config["candidates"][3]["active_parameters"] = 4_500_000_000
        # Default phone_lane_mode is "normal_worker" -> must fail.
        with self.assertRaisesRegex(ContractError, "4B normal phone-worker cap"):
            validate_tournament(config)
        config["candidates"][3]["phone_lane_mode"] = "feasibility_only"
        validate_tournament(config)

    def test_advertised_adr_locked_control_set_must_remain_unchanged(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"][0]["status"] = "candidate"
        config["candidates"][0]["license_gate"] = "review_required"
        config["candidates"][0]["execution_gate"] = "blocked"
        with self.assertRaisesRegex(ContractError, "ADR 0005 control set changed"):
            validate_tournament(config)

    def test_missing_control_candidate_fails_adr_check(self) -> None:
        config = _make_valid_skeleton()
        config["candidates"] = [
            cand for cand in config["candidates"] if cand["id"] != "ornith-9b-control"
        ]
        with self.assertRaisesRegex(ContractError, "ADR 0005 control set changed"):
            validate_tournament(config)

    def test_acceleration_order_must_be_non_empty_array(self) -> None:
        config = _make_valid_skeleton()
        config["acceleration_order"] = []
        with self.assertRaisesRegex(ContractError, "acceleration_order"):
            validate_tournament(config)
        config["acceleration_order"] = ["ok", ""]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)


class CandidateReviewBuildTests(unittest.TestCase):
    """Exercise build_candidate_review and its review-only invariants."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = _make_valid_config()

    def test_review_marks_every_candidate_non_authorizing(self) -> None:
        review = build_candidate_review(self.config, {})
        self.assertEqual(
            review["schema_version"], "pheno.tournament.review.v1"
        )
        self.assertTrue(review["review_only"])
        self.assertEqual(review["cutoff_date"], self.config["cutoff_date"])
        self.assertEqual(len(review["candidates"]), len(self.config["candidates"]))
        self.assertTrue(
            all(row["promotion_authorized"] is False for row in review["candidates"])
        )

    def test_missing_observation_yields_missing_resolution(self) -> None:
        review = build_candidate_review(self.config, {})
        row = review["candidates"][0]
        self.assertEqual(row["resolution"], "missing")
        self.assertIsNone(row["record_id"])
        self.assertEqual(row["declared_licenses"], [])
        self.assertFalse(row["license_verified"])

    def test_immutable_observation_resolves_with_details(self) -> None:
        record = _observation("immutable-1", "Qwen/Qwen3.6-27B")
        review = build_candidate_review(self.config, {"immutable-1": record})
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["resolution"], "resolved_immutable")
        self.assertEqual(row["record_id"], "immutable-1")
        self.assertEqual(row["declared_licenses"], ["apache-2.0"])

    def test_mutable_only_observation_is_not_promoted(self) -> None:
        record = _observation("mutable-1", "Qwen/Qwen3.6-27B", mutable=True)
        review = build_candidate_review(self.config, {"mutable-1": record})
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["resolution"], "mutable_only")
        self.assertEqual(row["record_id"], "mutable-1")

    def test_review_prefers_immutable_detail_over_newer_mutable_search(self) -> None:
        records = {
            "immutable-detail": _observation(
                "immutable-detail",
                "Qwen/Qwen3.6-27B",
                mutable=False,
                retrieved_at="2026-07-14T22:00:00Z",
            ),
            "newer-search": _observation(
                "newer-search",
                "Qwen/Qwen3.6-27B",
                mutable=True,
                retrieved_at="2026-07-14T23:00:00Z",
            ),
        }
        review = build_candidate_review(self.config, records)
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["resolution"], "resolved_immutable")
        self.assertEqual(row["record_id"], "immutable-detail")

    def test_review_orders_records_by_instant_not_iso_spelling(self) -> None:
        records = {
            "lexically-later": _observation(
                "lexically-later",
                "Qwen/Qwen3.6-27B",
                retrieved_at="2026-07-14T22:00:00+00:00",
            ),
            "chronologically-later": _observation(
                "chronologically-later",
                "Qwen/Qwen3.6-27B",
                retrieved_at="2026-07-14T21:30:00-02:00",
            ),
        }
        review = build_candidate_review(self.config, records)
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["record_id"], "chronologically-later")

    def test_review_counts_resolution_states(self) -> None:
        records = {
            "needle-immutable": _observation(
                "needle-immutable", "Cactus-Compute/needle", mutable=False
            ),
            "qwen-mutable": _observation(
                "qwen-mutable", "Qwen/Qwen3.6-27B", mutable=True
            ),
        }
        review = build_candidate_review(self.config, records)
        self.assertEqual(review["counts"]["resolved_immutable"], 1)
        self.assertEqual(review["counts"]["mutable_only"], 1)
        self.assertGreater(review["counts"]["missing"], 0)
        # All counts sum to the candidate count.
        self.assertEqual(
            sum(review["counts"].values()),
            len(self.config["candidates"]),
        )

    def test_review_propagates_status_and_execution_gate(self) -> None:
        review = build_candidate_review(self.config, {})
        for row, candidate in zip(review["candidates"], self.config["candidates"]):
            self.assertEqual(row["candidate_id"], candidate["id"])
            self.assertEqual(row["status"], candidate["status"])
            self.assertEqual(row["execution_gate"], candidate["execution_gate"])

    def test_review_rejects_tz_naive_retrieved_at(self) -> None:
        bad = _observation("bad", "Qwen/Qwen3.6-27B", retrieved_at="2026-07-14T22:00:00")
        with self.assertRaisesRegex(
            ContractError, "registry retrieved_at must include a timezone"
        ):
            build_candidate_review(self.config, {"bad": bad})

    def test_build_candidate_review_requires_valid_tournament(self) -> None:
        bad_config = copy.deepcopy(self.config)
        bad_config["policy"]["review_only"] = False
        with self.assertRaisesRegex(ContractError, "review_only"):
            build_candidate_review(bad_config, {})


class TournamentHelpersTests(unittest.TestCase):
    """Exercise the private helpers via the public surface."""

    def test_strings_helper_via_north_star(self) -> None:
        config = _make_valid_skeleton()
        config["policy"]["north_star"] = [1, "ok"]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_object_helper_via_policy(self) -> None:
        config = _make_valid_skeleton()
        config["mobile_worker_policy"]["lease"] = "not-mapping"
        with self.assertRaisesRegex(ContractError, "lease must be an object"):
            validate_tournament(config)


if __name__ == "__main__":
    unittest.main()
