from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts import audit_eval_locks

ROOT = Path(__file__).resolve().parents[1]
LOCK_ROOT = ROOT / "config" / "eval_locks"


def run_cli(*arguments: str) -> tuple[int, dict]:
    stdout = StringIO()
    with redirect_stdout(stdout):
        returncode = audit_eval_locks.main(list(arguments))
    return returncode, json.loads(stdout.getvalue())


class EvalLockAuditTests(unittest.TestCase):
    def test_candidate_locks_are_valid_but_blocked(self) -> None:
        returncode, result = run_cli()
        second_returncode, second_result = run_cli()
        self.assertEqual(returncode, 0)
        self.assertEqual(second_returncode, 0)
        self.assertEqual(result, second_result)
        self.assertTrue(result["ok"])
        self.assertTrue(result["metadata_only"])
        self.assertFalse(result["all_scoreable"])
        self.assertEqual(
            result["counts"],
            {"blocked": 2, "errors": 0, "inputs": 2, "scoreable": 0, "valid": 2},
        )
        by_suite = {row["suite_id"]: row for row in result["locks"]}
        self.assertNotIn(
            "dataset.subset_manifest_sha256 is unresolved",
            by_suite["terminal-bench-2.0"]["blocking_reasons"],
        )
        self.assertIn(
            "source.license_spdx is unresolved",
            by_suite["deepswe-v1.1"]["blocking_reasons"],
        )
        self.assertTrue(all(len(row["lock_sha256"]) == 64 for row in result["locks"]))

    def test_require_scoreable_has_distinct_exit_code(self) -> None:
        returncode, result = run_cli("--require-scoreable")
        self.assertEqual(returncode, 3)
        self.assertTrue(result["ok"])
        self.assertFalse(result["all_scoreable"])

    def test_duplicate_keys_and_aliases_are_rejected(self) -> None:
        cases = {
            "duplicate.yaml": "schema_version: one\nschema_version: two\n",
            "alias.yaml": "root: &root {value: 1}\ncopy: *root\n",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for name, content in cases.items():
                path = Path(temp_dir) / name
                path.write_text(content, encoding="utf-8")
                paths.append(str(path))
            returncode, result = run_cli(*paths)
        self.assertEqual(returncode, 2)
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"]["errors"], 2)
        messages = {row["source"]: row["error"] for row in result["locks"]}
        self.assertIn("duplicate YAML mapping key", messages["duplicate.yaml"])
        self.assertEqual(messages["alias.yaml"], "YAML aliases are forbidden")

    def test_input_is_bounded_before_yaml_parsing(self) -> None:
        lock = LOCK_ROOT / "terminal_bench_2_0.candidate.yaml"
        returncode, result = run_cli("--max-input-bytes", "1", str(lock))
        self.assertEqual(returncode, 2)
        self.assertIn("1-byte limit", result["locks"][0]["error"])

    def test_symbolic_link_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "lock.yaml"
            try:
                link.symlink_to(LOCK_ROOT / "terminal_bench_2_0.candidate.yaml")
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            returncode, result = run_cli(str(link))
        self.assertEqual(returncode, 2)
        self.assertEqual(
            result["locks"][0]["error"],
            "lock input must not be a symbolic link",
        )


if __name__ == "__main__":
    unittest.main()
