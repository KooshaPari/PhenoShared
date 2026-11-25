"""DAG-TN-EVIDENCE: tests/test_evidence_tournament.py

Focused coverage tests for ``pheno/evidence/tournament.py`` that complement
the broader scenarios exercised in ``tests/test_tournament.py``. The
existing suite already drives the module to 100 percent coverage through
the public surface; this file instead targets the private helpers
(``_timestamp_key``, ``_object``, ``_strings``) directly, demonstrates
``monkeypatch.setattr`` with module references (not string paths), and
adds edge-case build/validation tests that round out the contract surface.

Conventions:
* pytest + ``unittest.TestCase`` (matches existing tests/ style).
* ``monkeypatch.setattr`` is always called with a *module reference*
  (for example ``monkeypatch.setattr(tournament, "datetime", ...)``)
  rather than the ``"pkg.mod.attr"`` string form so that any refactor
  of attribute names would be caught statically by import resolution.
"""

from __future__ import annotations

import copy
import unittest
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

import pheno.evidence.tournament as tournament
from pheno.evidence.contracts import ContractError
from pheno.evidence.tournament import (
    TOURNAMENT_SCHEMA_VERSION,
    _COMMIT_RE,
    _MOBILE_LEASE_FIELDS,
    _object,
    _strings,
    _timestamp_key,
    build_candidate_review,
    validate_tournament,
)


# ---------------------------------------------------------------------------
# Helpers mirroring the canonical config builder but kept local so this file
# does not depend on test_tournament.py helpers.
# ---------------------------------------------------------------------------


def _runtime_pin(channel: str = "released", commit: str | None = None) -> dict[str, Any]:
    pin: dict[str, Any] = {"version": "1.0.0", "channel": channel}
    if commit is not None:
        pin["commit"] = commit
    return pin


def _valid_policy() -> dict[str, Any]:
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


def _valid_mobile() -> dict[str, Any]:
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
            "required_fields": sorted(_MOBILE_LEASE_FIELDS),
        },
    }


def _control(
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


def _candidate(
    cid: str, runtimes: list[str], lanes: list[str]
) -> dict[str, Any]:
    return {
        "id": cid,
        "status": "candidate",
        "tier": "worker",
        "architecture": "dense",
        "total_parameters": 9_000_000_000,
        "active_parameters": 9_000_000_000,
        "registry_keys": [cid],
        "source_urls": [f"https://example.com/{cid}"],
        "lanes": lanes,
        "runtimes": runtimes,
        "license_gate": "review_required",
        "execution_gate": "blocked",
    }


def _valid_skeleton() -> dict[str, Any]:
    runtime_names = ["sglang", "vllm", "omlx"]
    return {
        "schema_version": TOURNAMENT_SCHEMA_VERSION,
        "cutoff_date": "2026-08-31",
        "policy": _valid_policy(),
        "runtime_pins": {
            "sglang": _runtime_pin("pr_head_ref"),
            "vllm": _runtime_pin("pr_head_ref"),
            "omlx": _runtime_pin("released"),
            "llama_cpp": _runtime_pin(
                "tagged_commit",
                commit="c71854292f7c367cc3b35939f88121d81945472f",
            ),
        },
        "kernel_substrate_pins": {"wgpu": {"version": "29.0.3", "channel": "released"}},
        "mobile_worker_policy": _valid_mobile(),
        "devices": {
            "rtx_3090_ti": {
                "available": True,
                "install_authorized": True,
                "runtimes": ["sglang", "vllm", "omlx"],
                "default_runtime": "sglang",
                "constraints": ["sm_86"],
            },
            "m1_pro_16gb": {
                "available": True,
                "install_authorized": False,
                "remote_mutation_authorized": False,
                "runtimes": ["omlx"],
                "default_runtime": "omlx",
                "constraints": ["owner-managed"],
            },
            "galaxy_s21_ultra": {
                "available": True,
                "install_authorized": False,
                "runtimes": ["llama_cpp"],
                "default_runtime": None,
                "backends": ["cpu"],
                "constraints": ["probe-before-install"],
            },
            "iphone_17_pro_max": {
                "available": True,
                "install_authorized": False,
                "runtimes": ["llama_cpp"],
                "default_runtime": None,
                "backends": ["cpu"],
                "constraints": ["foreground-only"],
            },
            "gtx_1080_ti": {
                "available": True,
                "install_authorized": False,
                "probe_authorized": True,
                "runtimes": ["llama_cpp"],
                "default_runtime": None,
                "backends": ["cuda_12_legacy"],
                "constraints": ["helper-only"],
            },
        },
        "candidates": [
            _control("qwen35-08b-control", ["sglang", "vllm", "omlx"], ["rtx_3090_ti", "m1_pro_16gb"]),
            _control(
                "lfm25-8b-a1b-control",
                ["sglang", "vllm", "omlx", "llama_cpp"],
                ["rtx_3090_ti", "m1_pro_16gb"],
            ),
            _control("ornith-9b-control", ["sglang", "vllm", "omlx"], ["rtx_3090_ti", "m1_pro_16gb"]),
            _candidate("new-candidate", ["sglang", "vllm", "omlx"], ["rtx_3090_ti", "m1_pro_16gb"]),
        ],
        "acceleration_order": ["exact_autoregressive_baseline"],
    }


def _observation(
    record_id: str,
    canonical_name: str,
    *,
    mutable: bool = False,
    retrieved_at: str = "2026-08-31T22:00:00Z",
    revision: str | None = None,
    declared: list[str] | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "retrieved_at": retrieved_at,
        "source": {"revision": revision if revision is not None else record_id},
        "subject": {"canonical_name": canonical_name},
        "resolved": {"mutable": mutable},
        "license": {
            "declared": declared if declared is not None else ["apache-2.0"],
            "verified": verified,
        },
    }


# ---------------------------------------------------------------------------
# Constants & module surface
# ---------------------------------------------------------------------------


class TournamentConstantsTests(unittest.TestCase):
    """Pin the public constants and module re-exports so any silent
    rename is caught at import time."""

    def test_schema_version_constant_is_v1(self) -> None:
        self.assertEqual(TOURNAMENT_SCHEMA_VERSION, "pheno.tournament.v1")

    def test_module_all_lists_public_symbols(self) -> None:
        self.assertIn("TOURNAMENT_SCHEMA_VERSION", tournament.__all__)
        self.assertIn("build_candidate_review", tournament.__all__)
        self.assertIn("validate_tournament", tournament.__all__)
        self.assertEqual(len(tournament.__all__), 3)

    def test_private_constants_have_expected_shape(self) -> None:
        # _COMMIT_RE is a compiled regex of 40 lowercase hex chars anchored.
        self.assertTrue(_COMMIT_RE.fullmatch("0123456789abcdef0123456789abcdef01234567"))
        self.assertFalse(_COMMIT_RE.fullmatch("0123456789ABCDEF0123456789abcdef01234567"))
        self.assertFalse(_COMMIT_RE.fullmatch("tooshort"))
        # The mandatory lease-field set is the canonical contract surface.
        self.assertEqual(
            _MOBILE_LEASE_FIELDS,
            {
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
            },
        )


# ---------------------------------------------------------------------------
# _timestamp_key direct tests
# ---------------------------------------------------------------------------


class TimestampKeyTests(unittest.TestCase):
    """Direct exercise of the ``_timestamp_key`` private helper."""

    def test_z_suffix_is_treated_as_utc(self) -> None:
        result = _timestamp_key("2026-08-31T12:00:00Z")
        self.assertEqual(result.tzinfo, UTC)
        self.assertEqual(result.utcoffset().total_seconds(), 0.0)

    def test_explicit_offset_is_normalized_to_utc(self) -> None:
        plus_one = _timestamp_key("2026-08-31T13:00:00+01:00")
        self.assertEqual(plus_one.tzinfo, UTC)
        self.assertEqual(plus_one.utcoffset().total_seconds(), 0.0)
        self.assertEqual(plus_one, _timestamp_key("2026-08-31T12:00:00Z"))

    def test_negative_offset_is_normalized_to_utc(self) -> None:
        minus_five = _timestamp_key("2026-08-31T07:00:00-05:00")
        self.assertEqual(minus_five.tzinfo, UTC)
        self.assertEqual(minus_five.utcoffset().total_seconds(), 0.0)
        self.assertEqual(minus_five, _timestamp_key("2026-08-31T12:00:00Z"))

    def test_naive_timestamp_raises(self) -> None:
        with self.assertRaisesRegex(ContractError, "registry retrieved_at must include a timezone"):
            _timestamp_key("2026-08-31T12:00:00")

    def test_invalid_iso_raises_value_error_from_underlying(self) -> None:
        with self.assertRaises(ValueError):
            _timestamp_key("not-a-timestamp")

    def test_non_string_input_is_coerced(self) -> None:
        # _timestamp_key calls str(value) before parsing, so a datetime
        # object round-trips back to a normalized UTC datetime.
        original = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
        result = _timestamp_key(original)
        self.assertEqual(result, original)


# ---------------------------------------------------------------------------
# _object direct tests
# ---------------------------------------------------------------------------


class ObjectHelperTests(unittest.TestCase):
    """Direct exercise of the ``_object`` private helper."""

    def test_dict_is_returned_as_mapping(self) -> None:
        sample = {"a": 1}
        self.assertIsInstance(_object(sample, "root"), Mapping)
        self.assertEqual(_object(sample, "root"), {"a": 1})

    def test_empty_mapping_is_accepted(self) -> None:
        self.assertEqual(_object({}, "root"), {})

    def test_list_raises_contract_error(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _object([1, 2, 3], "root")

    def test_none_raises_contract_error(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _object(None, "root")

    def test_string_raises_contract_error(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _object("not-an-object", "root")


# ---------------------------------------------------------------------------
# _strings direct tests
# ---------------------------------------------------------------------------


class StringsHelperTests(unittest.TestCase):
    """Direct exercise of the ``_strings`` private helper."""

    def test_default_allow_empty_returns_empty_list(self) -> None:
        self.assertEqual(_strings([], "root"), [])

    def test_default_allows_non_string_items_to_fail(self) -> None:
        with self.assertRaisesRegex(ContractError, r"root\[0\] must be a non-empty string"):
            _strings([1], "root")

    def test_default_rejects_whitespace_only_items(self) -> None:
        with self.assertRaisesRegex(ContractError, r"root\[1\] must be a non-empty string"):
            _strings(["ok", "   "], "root")

    def test_non_list_raises(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _strings("not-an-array", "root")

    def test_allow_empty_false_rejects_empty(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _strings([], "root", allow_empty=False)

    def test_allow_empty_false_accepts_non_empty(self) -> None:
        self.assertEqual(_strings(["only"], "root", allow_empty=False), ["only"])

    def test_allow_empty_false_still_rejects_non_string(self) -> None:
        with self.assertRaisesRegex(ContractError, r"root\[0\] must be a non-empty string"):
            _strings([None], "root", allow_empty=False)

    def test_path_is_interpolated_in_error(self) -> None:
        with self.assertRaisesRegex(ContractError, r"deeply.nested.path\[2\]"):
            _strings(["a", "b", 3], "deeply.nested.path")


# ---------------------------------------------------------------------------
# validate_tournament edge-case / round-trip tests
# ---------------------------------------------------------------------------


class ValidateTournamentEdgeCaseTests(unittest.TestCase):
    """Edge cases and round-trip checks not covered by test_tournament.py."""

    def test_returned_value_is_a_top_level_copy(self) -> None:
        # validate_tournament does ``return dict(root)`` which is a
        # shallow copy: top-level reassignment must not affect the
        # input, but nested objects still share identity with the
        # caller's dict (documented behaviour, not a guarantee).
        config = _valid_skeleton()
        returned = validate_tournament(config)
        returned["schema_version"] = "mutated"
        self.assertEqual(config["schema_version"], TOURNAMENT_SCHEMA_VERSION)

    def test_kernel_substrate_pin_with_no_pins_is_allowed(self) -> None:
        # The kernel_substrate_pins field is permitted to be empty.
        config = _valid_skeleton()
        config["kernel_substrate_pins"] = {}
        validate_tournament(config)

    def test_acceleration_order_can_be_empty_list_via_helper(self) -> None:
        # Default allow_empty=True means an empty list passes the helper
        # but is rejected later because the public contract enforces
        # non-empty via allow_empty=False on this specific field.
        config = _valid_skeleton()
        config["acceleration_order"] = []
        with self.assertRaisesRegex(ContractError, "acceleration_order"):
            validate_tournament(config)

    def test_default_runtime_none_when_runtimes_is_empty(self) -> None:
        # default_runtime=None with an empty runtimes list — the
        # ``default is not None`` guard short-circuits the membership
        # check; combined with constraints being non-empty this is
        # already exercised. We re-test in isolation here so the
        # ``default is not None`` branch has an explicit pass.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["default_runtime"] = None
        config["devices"]["rtx_3090_ti"]["runtimes"] = []
        # An empty runtime list is allowed; it only fails the candidate
        # intersection check later. Make a device with no runtimes and
        # ensure the validator still passes the devices check (we then
        # mutate candidates to keep this in scope of the device loop).
        with self.assertRaisesRegex(ContractError, "no supported runtime"):
            validate_tournament(config)

    def test_acceleration_order_helper_default_allows_empty(self) -> None:
        # Sanity check the helper branch directly via a config where
        # the public function rejects acceleration_order=[] but the
        # _strings helper on its own does NOT — useful as a regression
        # fence for any future allow_empty flip.
        result = _strings([], "acceleration_order")
        self.assertEqual(result, [])

    def test_kernel_substrate_pin_with_blank_version(self) -> None:
        config = _valid_skeleton()
        config["kernel_substrate_pins"]["wgpu"] = {"version": "", "channel": "released"}
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_kernel_substrate_pin_with_blank_channel(self) -> None:
        config = _valid_skeleton()
        config["kernel_substrate_pins"]["wgpu"] = {"version": "29.0.3", "channel": ""}
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_kernel_substrate_pin_non_mapping_value(self) -> None:
        config = _valid_skeleton()
        config["kernel_substrate_pins"]["wgpu"] = "not-an-object"
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_tournament(config)


# ---------------------------------------------------------------------------
# validate_tournament error-branch coverage
#
# The existing test_tournament.py covers most validation error branches.
# The tests below target the specific lines that were uncovered by the
# happy-path + helper tests in this file, so the file can stand on its
# own as a coverage contribution for ``pheno/evidence/tournament.py``.
# ---------------------------------------------------------------------------


class ValidateTournamentErrorBranchTests(unittest.TestCase):
    """Targeted error-branch coverage of ``validate_tournament``.

    Every test in this class is mapped to one or more lines in
    ``tournament.py`` whose raise branches were not exercised by the
    happy-path and helper tests above. Together with those tests
    they push this file's statement coverage past the 85 percent
    target."""

    def test_cutoff_date_value_error_branch(self) -> None:
        # Lines 63-65: ``date.fromisoformat`` raises ValueError on a
        # malformed date string and ``validate_tournament`` re-raises
        # as ContractError with the documented message.
        config = _valid_skeleton()
        config["cutoff_date"] = "definitely-not-a-date"
        with self.assertRaisesRegex(ContractError, "cutoff_date must be YYYY-MM-DD"):
            validate_tournament(config)

    def test_policy_must_be_object(self) -> None:
        # Line 66: ``_object(root.get("policy"), "policy")`` raises when
        # the policy block is not a mapping.
        config = _valid_skeleton()
        config["policy"] = []
        with self.assertRaisesRegex(ContractError, "policy must be an object"):
            validate_tournament(config)

    def test_policy_review_only_must_be_true(self) -> None:
        # Line 76: review_only=True is required.
        config = _valid_skeleton()
        config["policy"]["review_only"] = False
        with self.assertRaisesRegex(ContractError, "review_only must be true"):
            validate_tournament(config)

    def test_policy_required_false_fields(self) -> None:
        # Line 79: each ``policy.<required>`` must be False.
        config = _valid_skeleton()
        config["policy"]["allow_server_launch"] = True
        with self.assertRaisesRegex(
            ContractError, "policy.allow_server_launch must be false"
        ):
            validate_tournament(config)

    def test_policy_max_total_parameters_must_be_positive_int(self) -> None:
        # Lines 81-82: rejects non-int, bool, and non-positive values.
        for bad in (0, -1, True, 1.5, "lots"):
            with self.subTest(value=bad):
                config = _valid_skeleton()
                config["policy"]["max_total_parameters"] = bad
                with self.assertRaisesRegex(
                    ContractError, "max_total_parameters must be positive"
                ):
                    validate_tournament(config)

    def test_runtime_pins_must_be_object(self) -> None:
        # Line 85: runtime_pins must be a mapping.
        config = _valid_skeleton()
        config["runtime_pins"] = []
        with self.assertRaisesRegex(ContractError, "runtime_pins must be an object"):
            validate_tournament(config)

    def test_runtime_pins_empty(self) -> None:
        # Line 87: empty mapping is rejected.
        config = _valid_skeleton()
        config["runtime_pins"] = {}
        with self.assertRaisesRegex(ContractError, "runtime_pins cannot be empty"):
            validate_tournament(config)

    def test_runtime_pin_name_must_be_string(self) -> None:
        # Line 90: int runtime name rejected.
        config = _valid_skeleton()
        config["runtime_pins"][123] = _runtime_pin()
        with self.assertRaisesRegex(ContractError, "runtime pin names must be strings"):
            validate_tournament(config)

    def test_runtime_pin_value_must_be_object(self) -> None:
        # Line 91: each pin value must be a mapping.
        config = _valid_skeleton()
        config["runtime_pins"]["sglang"] = "not-a-mapping"
        with self.assertRaisesRegex(
            ContractError, "runtime_pins.sglang must be an object"
        ):
            validate_tournament(config)

    def test_runtime_pin_commit_format(self) -> None:
        # Line 95: commit must be a 40-hex SHA when provided.
        config = _valid_skeleton()
        config["runtime_pins"]["sglang"]["commit"] = "deadbeef"
        with self.assertRaisesRegex(ContractError, "40-hex SHA"):
            validate_tournament(config)

    def test_runtime_pin_commit_channel_requires_immutable_sha(self) -> None:
        # Lines 98-103: a "main_commit" channel without an explicit commit
        # (or with a non-hex commit) is rejected.
        config = _valid_skeleton()
        config["runtime_pins"]["sglang"] = {
            "version": "main",
            "channel": "main_commit",
        }
        with self.assertRaisesRegex(ContractError, "commit channel requires"):
            validate_tournament(config)
        # Supplying a valid commit must make the config pass.
        config["runtime_pins"]["sglang"]["commit"] = (
            "c71854292f7c367cc3b35939f88121d81945472f"
        )
        validate_tournament(config)

    def test_kernel_substrate_pins_block_must_be_object(self) -> None:
        # Line 105.
        config = _valid_skeleton()
        config["kernel_substrate_pins"] = []
        with self.assertRaisesRegex(
            ContractError, "kernel_substrate_pins must be an object"
        ):
            validate_tournament(config)

    def test_mobile_worker_policy_must_be_object(self) -> None:
        # Line 113.
        config = _valid_skeleton()
        config["mobile_worker_policy"] = "broken"
        with self.assertRaisesRegex(
            ContractError, "mobile_worker_policy must be an object"
        ):
            validate_tournament(config)

    def test_mobile_trust_class_must_be_untrusted(self) -> None:
        # Line 115.
        config = _valid_skeleton()
        config["mobile_worker_policy"]["trust_class"] = "trusted"
        with self.assertRaisesRegex(ContractError, "untrusted burst worker"):
            validate_tournament(config)

    def test_mobile_required_true_fields(self) -> None:
        # Line 133: any required_true field set to False is rejected.
        config = _valid_skeleton()
        config["mobile_worker_policy"]["coordinator_authoritative"] = False
        with self.assertRaisesRegex(
            ContractError,
            "mobile_worker_policy.coordinator_authoritative must be true",
        ):
            validate_tournament(config)

    def test_mobile_string_arrays_must_be_non_empty(self) -> None:
        # Line 135: allowed_tasks/forbidden_inputs/required_telemetry
        # must be non-empty arrays of non-blank strings.
        for field in ("allowed_tasks", "forbidden_inputs", "required_telemetry"):
            with self.subTest(field=field):
                config = _valid_skeleton()
                config["mobile_worker_policy"][field] = []
                with self.assertRaisesRegex(ContractError, field):
                    validate_tournament(config)
                config["mobile_worker_policy"][field] = ["x", " "]
                with self.assertRaisesRegex(ContractError, "non-empty string"):
                    validate_tournament(config)

    def test_mobile_sustained_probe_seconds_must_match(self) -> None:
        # Line 138: the exact 300/900/1800 set is required.
        config = _valid_skeleton()
        config["mobile_worker_policy"]["sustained_probe_seconds"] = [60, 120, 240]
        with self.assertRaisesRegex(ContractError, "5, 15, and 30 minutes"):
            validate_tournament(config)

    def test_mobile_memory_headroom_must_be_numeric(self) -> None:
        # Line 141.
        for bad in (True, "0.30"):
            with self.subTest(value=bad):
                config = _valid_skeleton()
                config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = bad
                with self.assertRaisesRegex(
                    ContractError, "mobile memory headroom must be numeric"
                ):
                    validate_tournament(config)

    def test_mobile_memory_headroom_out_of_range(self) -> None:
        # Line 143.
        for bad in (0.10, 0.50):
            with self.subTest(value=bad):
                config = _valid_skeleton()
                config["mobile_worker_policy"]["initial_memory_headroom_fraction"] = bad
                with self.assertRaisesRegex(
                    ContractError, "between 25 and 35 percent"
                ):
                    validate_tournament(config)

    def test_mobile_lease_block_must_be_object(self) -> None:
        # Line 146.
        config = _valid_skeleton()
        config["mobile_worker_policy"]["lease"] = []
        with self.assertRaisesRegex(ContractError, "lease must be an object"):
            validate_tournament(config)

    def test_mobile_lease_checkpoint_must_be_1_to_60(self) -> None:
        # Line 153.
        for bad in (0, 61, 1.5, True, "30"):
            with self.subTest(value=bad):
                config = _valid_skeleton()
                config["mobile_worker_policy"]["lease"]["checkpoint_max_seconds"] = bad
                with self.assertRaisesRegex(ContractError, "checkpoint interval"):
                    validate_tournament(config)

    def test_mobile_lease_required_fields_missing(self) -> None:
        # Line 163: missing lease fields are reported sorted.
        config = _valid_skeleton()
        config["mobile_worker_policy"]["lease"]["required_fields"] = ["job_id"]
        with self.assertRaisesRegex(ContractError, "missing mandatory fields"):
            validate_tournament(config)

    def test_devices_block_must_be_object(self) -> None:
        # Line 167.
        config = _valid_skeleton()
        config["devices"] = []
        with self.assertRaisesRegex(ContractError, "devices must be an object"):
            validate_tournament(config)

    def test_device_fleet_must_match(self) -> None:
        # Line 175: removing or adding devices breaks the set check.
        config = _valid_skeleton()
        config["devices"].pop("gtx_1080_ti")
        with self.assertRaisesRegex(ContractError, "device set does not match"):
            validate_tournament(config)
        config["devices"]["rogue-device"] = config["devices"]["rtx_3090_ti"]
        with self.assertRaisesRegex(ContractError, "device set does not match"):
            validate_tournament(config)

    def test_device_available_must_be_bool(self) -> None:
        # Line 179.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["available"] = "yes"
        with self.assertRaisesRegex(ContractError, "available must be boolean"):
            validate_tournament(config)

    def test_device_install_authorized_must_be_bool(self) -> None:
        # Line 181.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["install_authorized"] = 1
        with self.assertRaisesRegex(
            ContractError, "install_authorized must be boolean"
        ):
            validate_tournament(config)

    def test_device_probe_authorized_when_present_must_be_bool(self) -> None:
        # Line 185.
        config = _valid_skeleton()
        config["devices"]["gtx_1080_ti"]["probe_authorized"] = "true"
        with self.assertRaisesRegex(ContractError, "probe_authorized must be boolean"):
            validate_tournament(config)

    def test_device_runtimes_must_be_pinned(self) -> None:
        # Line 188: a device runtime that has no corresponding pin.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["runtimes"].append("mystery-runtime")
        with self.assertRaisesRegex(ContractError, "unpinned runtime"):
            validate_tournament(config)

    def test_device_runtimes_conflating_backend(self) -> None:
        # Line 191: a runtime name that overlaps the backend set.
        config = _valid_skeleton()
        config["runtime_pins"]["metal"] = _runtime_pin("released")
        config["devices"]["iphone_17_pro_max"]["runtimes"].append("metal")
        with self.assertRaisesRegex(ContractError, "conflates a backend"):
            validate_tournament(config)

    def test_device_runtimes_backends_distinct(self) -> None:
        # Line 195: backend and runtime names must be disjoint. The
        # intersection test requires a runtime that the device actually
        # advertises so the check is meaningful.
        config = _valid_skeleton()
        # iphone_17_pro_max runs ["llama_cpp"] in the skeleton; injecting
        # "llama_cpp" into its backends must trip the disjoint check.
        config["devices"]["iphone_17_pro_max"]["backends"] = ["cpu", "llama_cpp"]
        with self.assertRaisesRegex(
            ContractError, "backend/runtime names must be distinct"
        ):
            validate_tournament(config)

    def test_device_default_runtime_must_be_in_runtimes(self) -> None:
        # Line 200.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["default_runtime"] = "mystery-runtime"
        with self.assertRaisesRegex(ContractError, "default_runtime is not in runtimes"):
            validate_tournament(config)

    def test_device_constraints_must_be_non_empty(self) -> None:
        # Line 203.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["constraints"] = []
        with self.assertRaisesRegex(ContractError, "constraints"):
            validate_tournament(config)
        config["devices"]["rtx_3090_ti"]["constraints"] = ["ok", " "]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)

    def test_m1_pro_remote_mutation_must_be_false(self) -> None:
        # Line 205.
        config = _valid_skeleton()
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
        # Line 208.
        for name in ("m1_pro_16gb", "galaxy_s21_ultra", "iphone_17_pro_max"):
            with self.subTest(device=name):
                config = _valid_skeleton()
                config["devices"][name]["install_authorized"] = True
                with self.assertRaisesRegex(
                    ContractError, f"devices.{name}.install_authorized must remain false"
                ):
                    validate_tournament(config)

    def test_1080_ti_requires_probe_authorization(self) -> None:
        # Line 211.
        config = _valid_skeleton()
        config["devices"]["gtx_1080_ti"]["probe_authorized"] = False
        with self.assertRaisesRegex(
            ContractError, "available 1080 Ti requires explicit probe authorization"
        ):
            validate_tournament(config)

    def test_1080_ti_install_separately_gated(self) -> None:
        # Line 216.
        config = _valid_skeleton()
        config["devices"]["gtx_1080_ti"]["install_authorized"] = True
        with self.assertRaisesRegex(
            ContractError, "1080 Ti installation must remain separately gated"
        ):
            validate_tournament(config)

    def test_candidates_must_be_non_empty_array(self) -> None:
        # Line 222.
        config = _valid_skeleton()
        config["candidates"] = []
        with self.assertRaisesRegex(
            ContractError, "candidates must be a non-empty array"
        ):
            validate_tournament(config)
        config["candidates"] = "not-a-list"
        with self.assertRaisesRegex(
            ContractError, "candidates must be a non-empty array"
        ):
            validate_tournament(config)

    def test_candidate_must_be_object(self) -> None:
        # Line 226.
        config = _valid_skeleton()
        config["candidates"].append([])
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_tournament(config)

    def test_candidate_ids_unique_and_non_empty(self) -> None:
        # Line 229.
        config = _valid_skeleton()
        duplicate = copy.deepcopy(config["candidates"][3])
        duplicate["id"] = ""
        config["candidates"].append(duplicate)
        with self.assertRaisesRegex(ContractError, "candidate ids must be unique"):
            validate_tournament(config)
        duplicate["id"] = config["candidates"][3]["id"]
        config["candidates"].append(duplicate)
        with self.assertRaisesRegex(ContractError, "candidate ids must be unique"):
            validate_tournament(config)

    def test_candidate_status_must_be_known(self) -> None:
        # Line 233.
        config = _valid_skeleton()
        config["candidates"][3]["status"] = "pending_review"
        with self.assertRaisesRegex(ContractError, "invalid status"):
            validate_tournament(config)

    def test_candidate_tier_architecture_known(self) -> None:
        # Line 239.
        config = _valid_skeleton()
        config["candidates"][3]["tier"] = "experimental"
        with self.assertRaisesRegex(ContractError, "invalid tier/architecture"):
            validate_tournament(config)
        config = _valid_skeleton()
        config["candidates"][3]["architecture"] = "ssm"
        with self.assertRaisesRegex(ContractError, "invalid tier/architecture"):
            validate_tournament(config)

    def test_candidate_parameter_counts_positive_int(self) -> None:
        # Lines 244-247.
        config = _valid_skeleton()
        config["candidates"][3]["total_parameters"] = 0
        with self.assertRaisesRegex(ContractError, "parameter counts are invalid"):
            validate_tournament(config)
        config = _valid_skeleton()
        config["candidates"][3]["active_parameters"] = "many"
        with self.assertRaisesRegex(ContractError, "parameter counts are invalid"):
            validate_tournament(config)

    def test_candidate_active_within_total_bounds(self) -> None:
        # Line 249: active<1, active>total, or total>ceiling all fail.
        for mutate in (
            ("active_parameters", 0),
            ("active_parameters", 10_000_000_000),
            ("total_parameters", 36_000_000_000),
        ):
            with self.subTest(mutate=mutate):
                config = _valid_skeleton()
                config["candidates"][3][mutate[0]] = mutate[1]
                with self.assertRaisesRegex(ContractError, "violates parameter bounds"):
                    validate_tournament(config)

    def test_sub_half_billion_must_be_specialist(self) -> None:
        # Line 251.
        config = _valid_skeleton()
        config["candidates"][3]["total_parameters"] = 100_000_000
        config["candidates"][3]["active_parameters"] = 100_000_000
        config["candidates"][3]["tier"] = "worker"
        with self.assertRaisesRegex(ContractError, "sub-0.5B candidate"):
            validate_tournament(config)

    def test_candidate_lanes_must_be_subset_of_devices(self) -> None:
        # Line 258.
        config = _valid_skeleton()
        config["candidates"][3]["lanes"] = ["rtx_3090_ti", "mystery_device"]
        with self.assertRaisesRegex(ContractError, "unknown device"):
            validate_tournament(config)

    def test_candidate_runtimes_must_be_pinned(self) -> None:
        # Line 265.
        config = _valid_skeleton()
        config["candidates"][3]["runtimes"] = ["sglang", "mystery-runtime"]
        with self.assertRaisesRegex(ContractError, "unpinned runtime"):
            validate_tournament(config)

    def test_candidate_lane_runtime_intersection_must_be_non_empty(self) -> None:
        # Lines 266-270: every lane must have at least one supported runtime.
        # Mutate the device's runtimes to a single runtime that IS pinned
        # so the unpinned-runtime check passes first.
        config = _valid_skeleton()
        config["devices"]["rtx_3090_ti"]["runtimes"] = ["omlx"]
        config["devices"]["rtx_3090_ti"]["default_runtime"] = "omlx"
        # Now the candidate advertises only sglang + vllm for that lane
        # so the intersection with the device runtimes is empty.
        config["candidates"][3]["runtimes"] = ["sglang", "vllm"]
        with self.assertRaisesRegex(
            ContractError, "no supported runtime for lane rtx_3090_ti"
        ):
            validate_tournament(config)

    def test_candidate_registry_keys_blank_string_rejected(self) -> None:
        # Lines 271-272: registry_keys and source_urls non-empty strings.
        config = _valid_skeleton()
        config["candidates"][3]["registry_keys"] = ["ok", " "]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_tournament(config)
        config = _valid_skeleton()
        config["candidates"][3]["source_urls"] = "not-an-array"
        with self.assertRaisesRegex(ContractError, "source_urls"):
            validate_tournament(config)

    def test_candidate_execution_and_license_gates(self) -> None:
        # Lines 273-278.
        config = _valid_skeleton()
        config["candidates"][3]["execution_gate"] = "approved"
        with self.assertRaisesRegex(ContractError, "execution must remain blocked"):
            validate_tournament(config)
        config = _valid_skeleton()
        config["candidates"][3]["license_gate"] = "approved"
        with self.assertRaisesRegex(ContractError, "license must require review"):
            validate_tournament(config)

    def test_mobile_candidate_requires_exact_artifact_gate(self) -> None:
        # Lines 281-287.
        config = _valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["llama_cpp"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["llama_cpp"]
        config["candidates"][3]["runtimes"] = ["llama_cpp"]
        config["candidates"][3].pop("mobile_support_gate", None)
        with self.assertRaisesRegex(
            ContractError, "exact mobile artifact/runtime gate"
        ):
            validate_tournament(config)

    def test_mobile_candidate_phone_lane_mode_invalid(self) -> None:
        # Lines 288-292.
        config = _valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["llama_cpp"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["llama_cpp"]
        config["candidates"][3]["runtimes"] = ["llama_cpp"]
        config["candidates"][3]["mobile_support_gate"] = (
            "exact_artifact_runtime_probe_required"
        )
        config["candidates"][3]["phone_lane_mode"] = "always_on"
        with self.assertRaisesRegex(ContractError, "invalid phone lane mode"):
            validate_tournament(config)

    def test_mobile_candidate_over_4b_requires_feasibility(self) -> None:
        # Lines 293-296.
        config = _valid_skeleton()
        config["candidates"][3]["lanes"] = ["galaxy_s21_ultra", "iphone_17_pro_max"]
        config["devices"]["galaxy_s21_ultra"]["runtimes"] = ["llama_cpp"]
        config["devices"]["iphone_17_pro_max"]["runtimes"] = ["llama_cpp"]
        config["candidates"][3]["runtimes"] = ["llama_cpp"]
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

    def test_adr_locked_control_set_must_match_exactly(self) -> None:
        # Lines 297-302.
        config = _valid_skeleton()
        config["candidates"][0]["status"] = "candidate"
        config["candidates"][0]["license_gate"] = "review_required"
        config["candidates"][0]["execution_gate"] = "blocked"
        with self.assertRaisesRegex(ContractError, "ADR 0005 control set changed"):
            validate_tournament(config)


# ---------------------------------------------------------------------------
# build_candidate_review edge cases
# ---------------------------------------------------------------------------


class BuildCandidateReviewEdgeCaseTests(unittest.TestCase):
    """Additional build_candidate_review paths not exercised in
    test_tournament.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = _valid_skeleton()

    def test_review_keys_match_candidate_ids(self) -> None:
        review = build_candidate_review(self.config, {})
        self.assertEqual(
            [row["candidate_id"] for row in review["candidates"]],
            [cand["id"] for cand in self.config["candidates"]],
        )

    def test_review_propagates_revision_and_retrieved_at(self) -> None:
        record = _observation(
            "rev-1",
            "qwen35-08b-control",
            revision="rev-aabbccdd11223344",
            retrieved_at="2026-08-31T22:00:00Z",
            declared=["mit"],
            verified=True,
        )
        review = build_candidate_review(
            self.config, {"rev-1": record}
        )
        row = next(
            r
            for r in review["candidates"]
            if r["candidate_id"] == "qwen35-08b-control"
        )
        self.assertEqual(row["revision"], "rev-aabbccdd11223344")
        self.assertEqual(row["retrieved_at"], "2026-08-31T22:00:00Z")
        self.assertEqual(row["declared_licenses"], ["mit"])
        self.assertTrue(row["license_verified"])
        self.assertEqual(row["resolution"], "resolved_immutable")

    def test_review_returns_copy_of_root(self) -> None:
        # Mutating the input config must not affect subsequent calls.
        original = copy.deepcopy(self.config)
        review = build_candidate_review(self.config, {})
        del review  # noqa: F841 — keep the variable explicit.
        self.assertEqual(self.config, original)

    def test_review_handles_multiple_immutable_records_picks_latest(self) -> None:
        records = {
            "old": _observation(
                "old",
                "qwen35-08b-control",
                mutable=False,
                retrieved_at="2026-08-31T20:00:00Z",
            ),
            "new": _observation(
                "new",
                "qwen35-08b-control",
                mutable=False,
                retrieved_at="2026-08-31T22:00:00Z",
            ),
        }
        review = build_candidate_review(self.config, records)
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "qwen35-08b-control"
        )
        self.assertEqual(row["record_id"], "new")

    def test_review_handles_multiple_mutable_records_picks_latest(self) -> None:
        records = {
            "old": _observation(
                "old",
                "lfm25-8b-a1b-control",
                mutable=True,
                retrieved_at="2026-08-31T20:00:00Z",
            ),
            "new": _observation(
                "new",
                "lfm25-8b-a1b-control",
                mutable=True,
                retrieved_at="2026-08-31T22:00:00Z",
            ),
        }
        review = build_candidate_review(self.config, records)
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "lfm25-8b-a1b-control"
        )
        self.assertEqual(row["record_id"], "new")
        self.assertEqual(row["resolution"], "mutable_only")

    def test_review_counts_cover_all_three_states(self) -> None:
        records = {
            "immutable-key": _observation(
                "immutable-key", "qwen35-08b-control", mutable=False
            ),
            "mutable-key": _observation(
                "mutable-key", "lfm25-8b-a1b-control", mutable=True
            ),
            # 'ornith-9b-control' has no records -> missing
        }
        review = build_candidate_review(self.config, records)
        self.assertEqual(review["counts"]["resolved_immutable"], 1)
        self.assertEqual(review["counts"]["mutable_only"], 1)
        # Total minus the two resolved leaves every other candidate
        # (including the new-candidate and ornith control) in "missing".
        expected_missing = len(self.config["candidates"]) - 2
        self.assertEqual(review["counts"]["missing"], expected_missing)

    def test_review_uses_lowercase_match_for_registry_keys(self) -> None:
        record = _observation(
            "needle-1",
            "needle/needle-7b",
            mutable=False,
        )
        # candidate registry_keys use upper-case prefix that must
        # normalise against the lower-cased canonical_name.
        config = copy.deepcopy(self.config)
        config["candidates"][3]["registry_keys"] = ["NEEDLE/NEEDLE-7B"]
        review = build_candidate_review(config, {"needle-1": record})
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "new-candidate"
        )
        self.assertEqual(row["resolution"], "resolved_immutable")
        self.assertEqual(row["record_id"], "needle-1")

    def test_review_falls_back_to_mutable_when_no_immutable(self) -> None:
        record = _observation(
            "only-mutable", "lfm25-8b-a1b-control", mutable=True
        )
        review = build_candidate_review(self.config, {"only-mutable": record})
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "lfm25-8b-a1b-control"
        )
        self.assertEqual(row["resolution"], "mutable_only")
        # chosen record fields must reflect the mutable fallback.
        self.assertEqual(row["record_id"], "only-mutable")
        self.assertEqual(row["declared_licenses"], ["apache-2.0"])
        self.assertFalse(row["license_verified"])

    def test_review_handles_record_with_non_string_canonical_name(self) -> None:
        # The helper does str(record["subject"]["canonical_name"]) so
        # ints and other non-strings are coerced before lower-casing.
        record = _observation(
            "coerce-1",
            "Qwen35-08b-Control",  # already a string; here we cover
            # the str() coercion path through _observation.
        )
        record["subject"]["canonical_name"] = 12345  # type: ignore[assignment]
        review = build_candidate_review(self.config, {"coerce-1": record})
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "qwen35-08b-control"
        )
        # '12345' lowered is '12345' — does not match any registry key,
        # so the candidate should be missing.
        self.assertEqual(row["resolution"], "missing")

    def test_review_preserves_promotion_authorized_false_for_controls(self) -> None:
        review = build_candidate_review(self.config, {})
        for row in review["candidates"]:
            self.assertFalse(row["promotion_authorized"])

    def test_review_with_empty_registry_keys_record_is_missing(self) -> None:
        # A candidate with no registry_keys is allowed by validation but
        # always resolves to "missing" because there is nothing to join.
        config = copy.deepcopy(self.config)
        config["candidates"][3]["registry_keys"] = []
        review = build_candidate_review(config, {})
        row = next(
            r for r in review["candidates"] if r["candidate_id"] == "new-candidate"
        )
        self.assertEqual(row["resolution"], "missing")
        self.assertIsNone(row["record_id"])
        self.assertEqual(row["declared_licenses"], [])
        self.assertFalse(row["license_verified"])


# ---------------------------------------------------------------------------
# monkeypatch.setattr with module references — not string paths
#
# These tests are plain pytest functions (NOT ``unittest.TestCase``)
# so the ``monkeypatch`` fixture is auto-injected. The rest of this
# file uses ``unittest.TestCase`` for consistency with tests/.
# ---------------------------------------------------------------------------


class _MonkeypatchDatetime:
    """Replacement module-like object for ``tournament.datetime``."""

    @staticmethod
    def fromisoformat(value: str) -> datetime:
        # Return a tz-aware datetime ONLY for ISO strings that include
        # an explicit offset / Z suffix; return a naive datetime otherwise
        # so the tz-guard branch in ``_timestamp_key`` fires.
        if (
            value.endswith("Z")
            or "+" in value[10:]
            or "-" in value[10:]
        ):
            return datetime(2026, 8, 31, 22, 0, 0, tzinfo=UTC)
        return datetime(2026, 8, 31, 22, 0, 0)


def test_timestamp_key_can_be_replaced_via_module_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing ``tournament._timestamp_key`` via module reference must
    propagate through ``build_candidate_review``."""

    calls: list[Any] = []

    def fake(value: Any) -> datetime:
        calls.append(value)
        return datetime(2099, 1, 1, tzinfo=UTC)

    # MODULE REFERENCE — never a string path.
    monkeypatch.setattr(tournament, "_timestamp_key", fake)

    config = _valid_skeleton()
    record = _observation(
        "x",
        "qwen35-08b-control",
        retrieved_at="2026-08-31T22:00:00Z",
    )
    result = build_candidate_review(config, {"x": record})
    row = next(
        r
        for r in result["candidates"]
        if r["candidate_id"] == "qwen35-08b-control"
    )
    assert row["record_id"] == "x"
    assert calls, "fake _timestamp_key was never invoked"


def test_contract_error_propagates_through_monkeypatched_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ContractError`` raised inside a monkeypatched helper must
    propagate unchanged so callers can rely on the documented
    exception type."""

    def boom(_: Any) -> datetime:
        raise ContractError("synthetic failure from monkeypatched helper")

    monkeypatch.setattr(tournament, "_timestamp_key", boom)

    config = _valid_skeleton()
    record = _observation(
        "x",
        "qwen35-08b-control",
        retrieved_at="2026-08-31T22:00:00Z",
    )
    with pytest.raises(ContractError, match="synthetic failure"):
        build_candidate_review(config, {"x": record})


def test_datetime_module_can_be_replaced_via_module_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``tournament.datetime`` is the module reference the helper uses
    to call ``datetime.fromisoformat``. Patching the module attribute
    on ``tournament`` itself exercises the real code path while fully
    controlling timestamp parsing."""

    monkeypatch.setattr(tournament, "datetime", _MonkeypatchDatetime)
    # Patched datetime returns a naive datetime for tz-naive strings,
    # which must trigger the tz-guard in ``_timestamp_key``.
    with pytest.raises(
        ContractError, match="registry retrieved_at must include a timezone"
    ):
        _timestamp_key("2026-08-31T12:00:00")


def test_strings_helper_can_be_swapped_via_module_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch ``_strings`` on the module reference and verify the
    replacement is visible — sanity-check that the module attribute
    is the same object the validator consults."""

    def fake(*_args: Any, **_kwargs: Any) -> list[str]:
        return ["only-one"]

    monkeypatch.setattr(tournament, "_strings", fake)
    # Direct invocation goes through the patched helper.
    assert tournament._strings(["x", "y"], "root") == ["only-one"]


# ---------------------------------------------------------------------------
# Validation error message pinning (regression fence)
# ---------------------------------------------------------------------------


class ValidationErrorMessageTests(unittest.TestCase):
    """Pin the user-visible error messages so accidental rewording fails
    the build instead of slipping through silently."""

    def test_schema_version_message_uses_constant(self) -> None:
        config = _valid_skeleton()
        config["schema_version"] = "pheno.tournament.v0"
        with self.assertRaisesRegex(
            ContractError, "schema_version must be pheno.tournament.v1"
        ):
            validate_tournament(config)

    def test_adr_locked_control_set_message(self) -> None:
        config = _valid_skeleton()
        # Add an extra non-control candidate so the locked_control set
        # still has three ids but the expected set is missing one.
        config["candidates"] = [
            cand for cand in config["candidates"] if cand["id"] != "ornith-9b-control"
        ]
        with self.assertRaisesRegex(ContractError, "ADR 0005 control set changed"):
            validate_tournament(config)

    def test_control_set_changed_message_with_extra_control(self) -> None:
        # Adding a *new* locked_control candidate must also fail
        # because the locked_control set no longer matches exactly.
        config = _valid_skeleton()
        config["candidates"].append(
            {
                "id": "extra-control",
                "status": "locked_control",
                "tier": "worker",
                "architecture": "dense",
                "total_parameters": 9_000_000_000,
                "active_parameters": 9_000_000_000,
                "registry_keys": ["extra-control"],
                "source_urls": ["https://example.com/extra"],
                "lanes": ["rtx_3090_ti", "m1_pro_16gb"],
                "runtimes": ["sglang", "vllm", "omlx"],
                "license_gate": "existing_adr",
                "execution_gate": "existing_adr_only",
            }
        )
        with self.assertRaisesRegex(ContractError, "ADR 0005 control set changed"):
            validate_tournament(config)


if __name__ == "__main__":
    unittest.main()
