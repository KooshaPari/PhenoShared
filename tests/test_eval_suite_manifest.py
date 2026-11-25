from __future__ import annotations

import copy
import unittest

from pheno.evidence.contracts import ContractError
from pheno.evidence.suite_manifest import (
    build_suite_tree_manifest,
    validate_suite_tree_manifest,
)

COMMIT = "a" * 40
TREE = "b" * 40
TASK_ROOT = "c" * 40


def tree_payload() -> dict:
    return {
        "sha": TREE,
        "truncated": False,
        "tree": [
            {"path": "README.md", "type": "blob", "sha": "d" * 40, "size": 5},
            {"path": "tasks", "type": "tree", "sha": TASK_ROOT},
            {
                "path": "tasks/task-b/task.toml",
                "type": "blob",
                "sha": "e" * 40,
                "size": 12,
            },
            {
                "path": "tasks/task-a/task.toml",
                "type": "blob",
                "sha": "f" * 40,
                "size": 11,
            },
            {
                "path": "tasks/task-a/tests/test.sh",
                "type": "blob",
                "sha": "1" * 40,
                "size": 30,
            },
        ],
    }


class SuiteManifestTest(unittest.TestCase):
    def _manifest(self) -> dict:
        return build_suite_tree_manifest(
            suite_id="terminal-bench-2.1",
            repository_url="https://github.com/harbor-framework/terminal-bench-2-1",
            commit_sha=COMMIT,
            tree_sha=TREE,
            commit_verified=True,
            observed_at="2026-07-15T06:00:00Z",
            tree_payload=tree_payload(),
            expected_task_count=2,
        )

    def test_builds_sorted_content_addressed_metadata_only_manifest(self) -> None:
        manifest = self._manifest()
        self.assertEqual(manifest["task_ids"], ["task-a", "task-b"])
        self.assertEqual(manifest["source"]["task_root_sha"], TASK_ROOT)
        self.assertTrue(manifest["source"]["double_observed"])
        self.assertFalse(manifest["artifact_download"])
        self.assertFalse(manifest["execution_authorized"])
        self.assertEqual(len(manifest["task_ids_sha256"]), 64)
        self.assertEqual(len(manifest["task_manifest_sha256"]), 64)
        self.assertEqual(len(manifest["manifest_sha256"]), 64)

    def test_rejects_truncated_tree_and_wrong_expected_count(self) -> None:
        payload = tree_payload()
        payload["truncated"] = True
        with self.assertRaisesRegex(ContractError, "truncated"):
            build_suite_tree_manifest(
                suite_id="terminal-bench-2.1",
                repository_url="https://github.com/harbor-framework/terminal-bench-2-1",
                commit_sha=COMMIT,
                tree_sha=TREE,
                commit_verified=True,
                observed_at="2026-07-15T06:00:00Z",
                tree_payload=payload,
            )
        with self.assertRaisesRegex(ContractError, "expected lock count"):
            build_suite_tree_manifest(
                suite_id="terminal-bench-2.1",
                repository_url="https://github.com/harbor-framework/terminal-bench-2-1",
                commit_sha=COMMIT,
                tree_sha=TREE,
                commit_verified=True,
                observed_at="2026-07-15T06:00:00Z",
                tree_payload=tree_payload(),
                expected_task_count=3,
            )

    def test_rejects_nested_or_duplicate_descriptors(self) -> None:
        payload = tree_payload()
        payload["tree"].append(
            {
                "path": "tasks/task-a/task.toml",
                "type": "blob",
                "sha": "2" * 40,
                "size": 12,
            }
        )
        with self.assertRaisesRegex(ContractError, "duplicate"):
            build_suite_tree_manifest(
                suite_id="terminal-bench-2.1",
                repository_url="https://github.com/harbor-framework/terminal-bench-2-1",
                commit_sha=COMMIT,
                tree_sha=TREE,
                commit_verified=False,
                observed_at="2026-07-15T06:00:00Z",
                tree_payload=payload,
            )

    def test_recomputes_all_hashes_and_rejects_mutation(self) -> None:
        manifest = self._manifest()
        changed = copy.deepcopy(manifest)
        changed["descriptors"][0]["bytes"] += 1
        with self.assertRaisesRegex(ContractError, "task_manifest_sha256"):
            validate_suite_tree_manifest(changed)

        changed = copy.deepcopy(manifest)
        changed["task_ids_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "task_ids_sha256"):
            validate_suite_tree_manifest(changed)

        changed = copy.deepcopy(manifest)
        changed["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "manifest_sha256"):
            validate_suite_tree_manifest(changed)

    def test_rejects_execution_or_artifact_claims(self) -> None:
        for field, value in (
            ("metadata_only", False),
            ("artifact_download", True),
            ("execution_authorized", True),
        ):
            changed = copy.deepcopy(self._manifest())
            changed[field] = value
            with self.assertRaises(ContractError):
                validate_suite_tree_manifest(changed)


if __name__ == "__main__":
    unittest.main()
