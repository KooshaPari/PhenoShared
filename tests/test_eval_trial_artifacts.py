from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pheno.evidence.contracts import ContractError
from pheno.evidence.trial_contracts import (
    ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION,
    validate_trial_artifact_bundle,
    validate_trial_record,
)


def _harbor_runtime_installed() -> bool:
    """Return True iff ``harbor.models.trajectories`` is importable.

    ATIF validation requires the full Harbor runtime; a bare namespace
    ``import harbor`` is not enough.
    """
    import importlib

    try:
        importlib.import_module("harbor.models.trajectories")
    except ImportError:
        return False
    return True


BUNDLE = Path(__file__).parent / "fixtures" / "eval_contracts" / "trial_bundle"


def load_record() -> dict:
    return json.loads((BUNDLE / "trial_bundle_record.json").read_text(encoding="utf-8"))


def copied_bundle(parent: Path) -> Path:
    destination = parent / "bundle"
    shutil.copytree(BUNDLE, destination)
    return destination


class TrialArtifactBundleTests(unittest.TestCase):
    def test_actual_bundle_is_byte_verified_and_deterministic(self) -> None:
        if not _harbor_runtime_installed():
            self.skipTest(
                "harbor.models.trajectories not installed; "
                "requires the full Harbor runtime"
            )
        record = load_record()
        first = validate_trial_artifact_bundle(record, BUNDLE)
        second = validate_trial_artifact_bundle(record, BUNDLE)
        self.assertEqual(first, second)
        self.assertEqual(
            first["schema_version"], ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION
        )
        self.assertEqual(first["artifact_count"], 3)
        self.assertEqual(first["verifier_output_count"], 1)
        self.assertEqual(
            first["total_bytes"],
            sum(
                (BUNDLE / path).stat().st_size
                for path in (
                    "trajectory.atif.json",
                    "intent-graph.json",
                    "verifier/reward.json",
                )
            ),
        )
        self.assertEqual(
            first["atif"]["root_trajectory_id"], "trajectory-fixture-bundle"
        )
        self.assertEqual(first["atif"]["tool_observation_correlation"], 1.0)
        self.assertEqual(first["intent_graph"]["run_id"], "run-fixture-bundle")
        self.assertEqual(first["intent_graph"]["node_count"], 2)
        self.assertEqual(first["intent_graph"]["edge_count"], 1)

    def test_tampered_bytes_are_rejected_even_when_integrity_flags_are_true(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copied_bundle(Path(temporary))
            (root / "verifier" / "reward.json").write_text(
                '{"reward":0.0}\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(ContractError, "SHA-256 mismatch"):
                validate_trial_artifact_bundle(load_record(), root)

    def test_json_verifier_output_secret_key_is_rejected_after_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copied_bundle(Path(temporary))
            leaked = b'{"reward":1.0,"token":"fixture-placeholder"}\n'
            (root / "verifier" / "reward.json").write_bytes(leaked)
            record = load_record()
            record["artifacts"]["verifier_outputs"][0]["sha256"] = hashlib.sha256(
                leaked
            ).hexdigest()
            with self.assertRaisesRegex(ContractError, "contains a credential"):
                validate_trial_artifact_bundle(record, root)

    def test_traversal_is_rejected_before_file_access(self) -> None:
        record = load_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "../outside.json"
        with self.assertRaisesRegex(ContractError, "safe relative POSIX path"):
            validate_trial_artifact_bundle(record, BUNDLE)

    def test_windows_drive_relative_spelling_is_not_a_safe_posix_path(self) -> None:
        record = load_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "C:outside.json"
        with self.assertRaisesRegex(ContractError, "safe relative POSIX path"):
            validate_trial_artifact_bundle(record, BUNDLE)

    def test_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            root = copied_bundle(temporary_root)
            outside = temporary_root / "outside.json"
            outside.write_bytes((root / "verifier" / "reward.json").read_bytes())
            link = root / "escape.json"
            try:
                link.symlink_to(outside)
            except OSError as exc:  # pragma: no cover - host privilege gate
                self.skipTest(f"host cannot create symlinks: {exc}")
            record = load_record()
            record["artifacts"]["verifier_outputs"][0]["path"] = "escape.json"
            with self.assertRaisesRegex(ContractError, "escapes artifact_root"):
                validate_trial_artifact_bundle(record, root)

    def test_symlinked_artifact_root_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            root = copied_bundle(temporary_root)
            link = temporary_root / "bundle-link"
            try:
                link.symlink_to(root, target_is_directory=True)
            except OSError as exc:  # pragma: no cover - host privilege gate
                self.skipTest(f"host cannot create directory symlinks: {exc}")
            with self.assertRaisesRegex(
                ContractError, "artifact_root must not be a symlink"
            ):
                validate_trial_artifact_bundle(load_record(), link)

    def test_non_regular_artifact_is_rejected(self) -> None:
        record = load_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "verifier"
        with self.assertRaisesRegex(ContractError, "not a regular file"):
            validate_trial_artifact_bundle(record, BUNDLE)

    def test_total_bytes_are_bounded(self) -> None:
        with (
            mock.patch("pheno.evidence.trial_contracts.MAX_ARTIFACT_BUNDLE_BYTES", 1),
            self.assertRaisesRegex(ContractError, "maximum total byte count"),
        ):
            validate_trial_artifact_bundle(load_record(), BUNDLE)

    def test_duplicate_json_keys_are_rejected_after_matching_raw_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copied_bundle(Path(temporary))
            duplicate = b'{"schema_version":1,"schema_version":1}'
            (root / "intent-graph.json").write_bytes(duplicate)
            record = load_record()
            record["artifacts"]["intent_graph"]["sha256"] = hashlib.sha256(
                duplicate
            ).hexdigest()
            with self.assertRaisesRegex(ContractError, "duplicate object key"):
                validate_trial_artifact_bundle(record, root)

    def test_intent_graph_must_match_trial_identity_and_be_acyclic(self) -> None:
        if not _harbor_runtime_installed():
            self.skipTest(
                "harbor.models.trajectories not installed; "
                "requires the full Harbor runtime"
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = copied_bundle(Path(temporary))
            graph_path = root / "intent-graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["edges"].append(
                {
                    "source": "verifier-1",
                    "target": "run-fixture-bundle",
                    "kind": "depends_on",
                }
            )
            raw = (json.dumps(graph, sort_keys=True) + "\n").encode("utf-8")
            graph_path.write_bytes(raw)
            record = load_record()
            record["artifacts"]["intent_graph"]["sha256"] = hashlib.sha256(
                raw
            ).hexdigest()
            with self.assertRaisesRegex(ContractError, "contains a cycle"):
                validate_trial_artifact_bundle(record, root)

        with tempfile.TemporaryDirectory() as temporary:
            root = copied_bundle(Path(temporary))
            graph_path = root / "intent-graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["run_id"] = "another-run"
            raw = (json.dumps(graph, sort_keys=True) + "\n").encode("utf-8")
            graph_path.write_bytes(raw)
            record = load_record()
            record["artifacts"]["intent_graph"]["sha256"] = hashlib.sha256(
                raw
            ).hexdigest()
            with self.assertRaisesRegex(ContractError, "does not match"):
                validate_trial_artifact_bundle(record, root)


class TrialInvariantGapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = load_record()

    def test_evidence_class_is_closed(self) -> None:
        self.record["evidence_class"] = "claimed_local"
        with self.assertRaisesRegex(ContractError, "evidence_class must"):
            validate_trial_record(self.record)

    def test_outcome_reward_and_exclusion_payload_are_state_consistent(self) -> None:
        no_reward = copy.deepcopy(self.record)
        no_reward["outcome"]["reward"] = None
        with self.assertRaisesRegex(ContractError, "require a finite reward"):
            validate_trial_record(no_reward)

        exclusion = copy.deepcopy(self.record)
        exclusion["outcome"] = {
            "state": "infrastructure_exclusion",
            "reason": "provider_error",
            "scoreable": False,
            "reward": 0.0,
            "verifier_components": {"apparent_quality": 1.0},
        }
        exclusion["accepted_steps"] = []
        exclusion["total_weight"] = 0.0
        with self.assertRaisesRegex(ContractError, "null reward and empty"):
            validate_trial_record(exclusion)

    def test_accepted_step_predicate_is_hashed(self) -> None:
        del self.record["accepted_steps"][0]["predicate_sha256"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            validate_trial_record(self.record)

    def test_single_task_fallback_requires_one_unit_step(self) -> None:
        self.record["accepted_steps"][0]["weight"] = 0.5
        self.record["total_weight"] = 0.5
        with self.assertRaisesRegex(ContractError, "exactly one accepted step"):
            validate_trial_record(self.record)

    def test_gold_match_counts_are_all_null_or_ordered(self) -> None:
        without_gold = copy.deepcopy(self.record)
        without_gold["tools"]["exact_tool_matches"] = 1
        with self.assertRaisesRegex(ContractError, "must be null without gold"):
            validate_trial_record(without_gold)

        with_gold = copy.deepcopy(self.record)
        with_gold["tools"]["gold_labeled_calls"] = 1
        with_gold["tools"]["exact_tool_matches"] = 0
        with_gold["tools"]["exact_argument_matches"] = 1
        with self.assertRaisesRegex(ContractError, "exact match counts must satisfy"):
            validate_trial_record(with_gold)

    def test_incomplete_cost_cannot_claim_a_total_or_ledger(self) -> None:
        self.record["cost"]["completeness"] = "incomplete"
        with self.assertRaisesRegex(ContractError, "incomplete cost requires null"):
            validate_trial_record(self.record)
        self.record["cost"]["total_amortized_usd"] = None
        self.record["cost"]["ledger_sha256"] = None
        validate_trial_record(self.record)


if __name__ == "__main__":
    unittest.main()
