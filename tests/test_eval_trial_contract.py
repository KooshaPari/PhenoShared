from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from pheno.evidence.contracts import ContractError
from pheno.evidence.trial_contracts import (
    TRIAL_SCHEMA_VERSION,
    trial_scoreability_reasons,
    trial_sha256,
    validate_trial_record,
)

FIXTURES = Path(__file__).parent / "fixtures" / "eval_contracts"
VALID = FIXTURES / "trial_valid.json"
INVALID = FIXTURES / "trial_invalid.json"


class TrialContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(VALID.read_text(encoding="utf-8"))

    def test_valid_measured_fixture_is_scoreable_and_hash_is_canonical(self) -> None:
        validated = validate_trial_record(self.record)
        self.assertEqual(validated["schema_version"], TRIAL_SCHEMA_VERSION)
        self.assertEqual(trial_scoreability_reasons(validated), [])
        reordered = {key: self.record[key] for key in reversed(self.record)}
        self.assertEqual(trial_sha256(self.record), trial_sha256(reordered))
        self.assertEqual(
            trial_sha256(self.record),
            "2f9e6c483d3a3f1bfb4d887f61fec5b0263052387de55f5058ee2a55a9948961",
        )

    def test_invalid_fixture_and_unknown_root_field_are_rejected(self) -> None:
        invalid = json.loads(INVALID.read_text(encoding="utf-8"))
        with self.assertRaises(ContractError):
            validate_trial_record(invalid)
        tampered = copy.deepcopy(self.record)
        tampered["extra"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_trial_record(tampered)

    def test_cell_id_and_pair_key_are_recomputed(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["cell"]["runtime"]["version"] = "2.0.0"
        with self.assertRaisesRegex(ContractError, "cell_id"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["cell"]["seed"] += 1
        with self.assertRaisesRegex(ContractError, "pair_key"):
            validate_trial_record(tampered)

    def test_outcome_state_reason_and_scoreable_are_consistent(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["outcome"]["reason"] = "verifier_fail"
        with self.assertRaisesRegex(ContractError, "null reason"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["outcome"]["scoreable"] = False
        with self.assertRaisesRegex(ContractError, "contradicts"):
            validate_trial_record(tampered)

    def test_infrastructure_exclusion_is_valid_but_not_scoreable(self) -> None:
        excluded = copy.deepcopy(self.record)
        excluded["outcome"] = {
            "state": "infrastructure_exclusion",
            "reason": "network_error",
            "scoreable": False,
            "reward": None,
            "verifier_components": {},
        }
        excluded["accepted_steps"] = []
        excluded["total_weight"] = 0.0
        validate_trial_record(excluded)
        self.assertIn(
            "outcome is an infrastructure exclusion",
            trial_scoreability_reasons(excluded),
        )

    def test_model_timeout_is_a_scored_failure_not_an_exclusion(self) -> None:
        failed = copy.deepcopy(self.record)
        failed["outcome"] = {
            "state": "model_failure",
            "reason": "timeout",
            "scoreable": True,
            "reward": 0.0,
            "verifier_components": {"task_pass": 0.0},
        }
        failed["accepted_steps"] = []
        failed["total_weight"] = 0.0
        self.assertEqual(trial_scoreability_reasons(failed), [])

    def test_oom_is_scored_and_structurally_cross_checked(self) -> None:
        failed = copy.deepcopy(self.record)
        failed["outcome"] = {
            "state": "model_failure",
            "reason": "oom",
            "scoreable": True,
            "reward": 0.0,
            "verifier_components": {"task_pass": 0.0},
        }
        failed["accepted_steps"] = []
        failed["total_weight"] = 0.0
        failed["integrity"]["ooms"] = 1
        self.assertEqual(trial_scoreability_reasons(failed), [])
        failed["integrity"]["ooms"] = 0
        with self.assertRaisesRegex(ContractError, "ooms does not match"):
            validate_trial_record(failed)

    def test_accepted_steps_reconcile_weight_and_dependencies(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["total_weight"] = 2.0
        with self.assertRaisesRegex(ContractError, "total_weight"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["accepted_steps"][0]["depends_on"] = ["missing"]
        with self.assertRaisesRegex(ContractError, "missing dependencies"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["accepted_steps"][0]["terminal_reverified"] = False
        with self.assertRaisesRegex(ContractError, "terminally reverified"):
            validate_trial_record(tampered)

    def test_timing_must_be_monotonic_and_derived_latencies_reconcile(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["timing"]["last_token_ns"] = 1200000000
        with self.assertRaisesRegex(ContractError, "outside"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["timing"]["queue_ms"] = 101.0
        with self.assertRaisesRegex(ContractError, "reconcile"):
            validate_trial_record(tampered)

    def test_token_tool_and_cache_counters_reconcile(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["tools"]["executed_calls"] = 2
        with self.assertRaisesRegex(ContractError, "counts do not reconcile"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["tokens"]["draft_proposed"] = 2
        tampered["tokens"]["draft_accepted"] = 3
        with self.assertRaisesRegex(ContractError, "draft_accepted"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["cache"]["hit_tokens"] = 101
        with self.assertRaisesRegex(ContractError, "hit_tokens"):
            validate_trial_record(tampered)

    def test_complete_cost_requires_a_reconciled_hashed_ledger(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["cost"]["total_amortized_usd"] = 0.04
        with self.assertRaisesRegex(ContractError, "do not sum"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["cost"]["ledger_sha256"] = None
        with self.assertRaisesRegex(ContractError, "complete cost"):
            validate_trial_record(tampered)
        incomplete = copy.deepcopy(self.record)
        incomplete["cost"] = {
            "completeness": "incomplete",
            "provider_usd": None,
            "sandbox_usd": None,
            "electricity_usd": None,
            "hardware_amortization_usd": None,
            "total_amortized_usd": None,
            "ledger_sha256": None,
        }
        validate_trial_record(incomplete)

    def test_integrity_counters_cross_check_instrumentation(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["integrity"]["orphan_calls"] = 1
        with self.assertRaisesRegex(ContractError, "orphan-call"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["integrity"]["cross_request_contamination"] = True
        with self.assertRaisesRegex(ContractError, "contamination"):
            validate_trial_record(tampered)

    def test_scoreability_reports_integrity_and_coverage_failures(self) -> None:
        diagnostic = copy.deepcopy(self.record)
        diagnostic["evidence_class"] = "synthetic"
        diagnostic["run_mode"] = "replay"
        diagnostic["integrity"]["atif_valid"] = False
        diagnostic["integrity"]["harness_worktree_dirty"] = True
        diagnostic["integrity"]["deadlocks"] = 1
        diagnostic["resources"]["coverage_fraction"] = 0.9
        reasons = trial_scoreability_reasons(diagnostic)
        self.assertIn("evidence_class is not local_measured", reasons)
        self.assertIn("run_mode is not execute", reasons)
        self.assertIn("ATIF trajectory is invalid", reasons)
        self.assertIn("harness worktree was dirty", reasons)
        self.assertNotIn("integrity.deadlocks is nonzero", reasons)
        self.assertIn("resource instrumentation coverage is below 0.95", reasons)

    def test_drift_checkpoints_are_strict_sorted_and_bounded(self) -> None:
        validated = validate_trial_record(self.record)
        self.assertEqual(
            [item["turn"] for item in validated["drift"]["checkpoints"]],
            [1, 5, 10, 25, 50],
        )
        unsorted = copy.deepcopy(self.record)
        unsorted["drift"]["checkpoints"][0], unsorted["drift"]["checkpoints"][1] = (
            unsorted["drift"]["checkpoints"][1],
            unsorted["drift"]["checkpoints"][0],
        )
        with self.assertRaisesRegex(ContractError, "ascending order"):
            validate_trial_record(unsorted)
        invalid_turn = copy.deepcopy(self.record)
        invalid_turn["drift"]["checkpoints"][1]["turn"] = 2
        with self.assertRaisesRegex(ContractError, "one of 1, 5, 10, 25, or 50"):
            validate_trial_record(invalid_turn)
        overclaimed = copy.deepcopy(self.record)
        overclaimed["drift"]["checkpoints"][0]["assertions_retained"] = 2
        with self.assertRaisesRegex(ContractError, "cannot exceed"):
            validate_trial_record(overclaimed)

    def test_drift_manifest_presence_matches_checkpoint_presence(self) -> None:
        missing_manifest = copy.deepcopy(self.record)
        missing_manifest["drift"]["assertion_manifest_sha256"] = None
        with self.assertRaisesRegex(ContractError, "required when checkpoints exist"):
            validate_trial_record(missing_manifest)
        empty = copy.deepcopy(self.record)
        empty["drift"] = {
            "assertion_manifest_sha256": None,
            "checkpoints": [],
        }
        validate_trial_record(empty)
        empty["drift"]["assertion_manifest_sha256"] = "9" * 64
        with self.assertRaisesRegex(ContractError, "must be null"):
            validate_trial_record(empty)

    def test_drift_is_required_and_rejects_unknown_fields(self) -> None:
        missing = copy.deepcopy(self.record)
        del missing["drift"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            validate_trial_record(missing)
        unknown = copy.deepcopy(self.record)
        unknown["drift"]["total"] = 5
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_trial_record(unknown)

    def test_artifact_hashes_and_paths_are_strict(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["artifacts"]["atif_trajectory"]["sha256"] = "bad"
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            validate_trial_record(tampered)
        tampered = copy.deepcopy(self.record)
        tampered["artifacts"]["patch"]["path"] = "../escape.patch"
        with self.assertRaisesRegex(ContractError, "safe relative"):
            validate_trial_record(tampered)

    def test_secret_material_is_never_persistable(self) -> None:
        tampered = copy.deepcopy(self.record)
        tampered["trial_id"] = "Bearer " + "abcdefghijklmnopqrstuvwxyz"
        with self.assertRaisesRegex(ContractError, "credential"):
            validate_trial_record(tampered)


if __name__ == "__main__":
    unittest.main()
