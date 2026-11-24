from __future__ import annotations

import copy
import unittest

import yaml

from pheno.evidence.contracts import ContractError
from pheno.evidence.eval_contracts import (
    suite_lock_scoreability_reasons,
    suite_lock_sha256,
    validate_suite_lock,
)
from pheno.paths import PHENO_ROOT


class EvalSuiteLockTests(unittest.TestCase):
    def _locks(self):
        root = PHENO_ROOT / "config" / "eval_locks"
        return [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted(root.glob("*.yaml"))
        ]

    def test_candidate_locks_are_valid_but_explicitly_non_scoreable(self) -> None:
        locks = self._locks()
        self.assertEqual(len(locks), 2)
        for lock in locks:
            validated = validate_suite_lock(lock)
            self.assertFalse(validated["integrity"]["scoreable"])
            self.assertTrue(suite_lock_scoreability_reasons(validated))
            self.assertEqual(len(suite_lock_sha256(validated)), 64)

    def test_scoreable_flag_cannot_override_missing_hashes(self) -> None:
        lock = copy.deepcopy(self._locks()[0])
        lock["integrity"]["scoreable"] = True
        with self.assertRaisesRegex(ContractError, "incomplete"):
            validate_suite_lock(lock)

    def test_pins_match_researched_revisions(self) -> None:
        locks = {lock["suite_id"]: lock for lock in self._locks()}
        self.assertEqual(
            locks["terminal-bench-2.0"]["source"]["revision_sha"],
            "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c",
        )
        self.assertEqual(
            locks["deepswe-v1.1"]["runner"]["package_sha256"],
            "a8b43377774bc45fa20520d6c1aad9e244f2c6bdcd04155dddabd753fe443251",
        )

    def test_fully_pinned_lock_has_a_positive_scoreable_path(self) -> None:
        lock = copy.deepcopy(self._locks()[1])
        digest = "c" * 64
        lock["dataset"].update(
            {
                "task_ids_sha256": digest,
                "task_manifest_sha256": digest,
                "subset_ids": ["task-001"],
                "subset_manifest_sha256": digest,
                "changed_task_ids_sha256": digest,
            }
        )
        lock["runner"].update({"version": "0.6.1", "revision_sha": "d" * 40})
        lock["harness"].update(
            {
                "revision_sha": "e" * 40,
                "system_prompt_sha256": digest,
                "agent_config_sha256": digest,
                "tool_definitions_sha256": digest,
            }
        )
        lock["verifier"].update({"revision_sha": digest, "image_digests": ["f" * 64]})
        lock["integrity"].update(
            {
                "held_out_from_training": True,
                "holdout_manifest_sha256": digest,
                "scoreable": True,
                "unverified_reasons": [],
            }
        )
        validated = validate_suite_lock(lock)
        self.assertEqual(suite_lock_scoreability_reasons(validated), [])

    def test_unsafe_or_duplicate_lock_lists_are_rejected(self) -> None:
        lock = copy.deepcopy(self._locks()[0])
        lock["dataset"]["subset_ids"] = ["task-001", "task-001"]
        with self.assertRaisesRegex(ContractError, "duplicates"):
            validate_suite_lock(lock)

        lock = copy.deepcopy(self._locks()[0])
        lock["verifier"]["expected_artifacts"] = ["../reward.json"]
        with self.assertRaisesRegex(ContractError, "safe relative POSIX path"):
            validate_suite_lock(lock)

        lock = copy.deepcopy(self._locks()[0])
        lock["runner"]["versoin"] = "typo"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_suite_lock(lock)


if __name__ == "__main__":
    unittest.main()
