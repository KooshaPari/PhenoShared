from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts import eval_contract


def _harbor_runtime_installed() -> bool:
    """Return True iff the `harbor.models.trajectories` import works.

    Several ``validate-trial`` tests require the full Harbor runtime
    (``from harbor.models.trajectories import Trajectory``). A bare
    namespace-package ``import harbor`` succeeds when the repo's local
    ``harbor/`` directory is on the path, so it isn't a sufficient
    predicate. We probe the actual submodule import.
    """
    import importlib

    try:
        importlib.import_module("harbor.models.trajectories")
    except ImportError:
        return False
    return True


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "eval_contracts"
BUNDLE = FIXTURES / "trial_bundle"
BUNDLE_RECORD = BUNDLE / "trial_bundle_record.json"


@dataclass(frozen=True)
class CliResult:
    returncode: int
    stdout: str
    stderr: str


def run_cli(*arguments: str) -> CliResult:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        returncode = eval_contract.main(list(arguments))
    return CliResult(returncode, stdout.getvalue(), stderr.getvalue())


class EvalContractCliTests(unittest.TestCase):
    def test_validate_atif_emits_deterministic_json(self) -> None:
        fixture = FIXTURES / "atif_valid_nested.json"
        first = run_cli("validate-atif", str(fixture))
        second = run_cli("validate-atif", str(fixture))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, "")
        result = json.loads(first.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "validate-atif")
        self.assertEqual(result["validation_scope"], "pheno_atif_integrity_overlay")
        self.assertEqual(result["summary"]["trajectory_count"], 2)
        self.assertEqual(result["summary"]["tool_call_count"], 2)
        self.assertEqual(result["summary"]["tool_observation_correlation"], 1.0)

    def test_validate_atif_contract_error_is_json_and_nonzero(self) -> None:
        fixture = FIXTURES / "atif_invalid_orphan_tool_call.json"
        result = run_cli("validate-atif", str(fixture))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertFalse(error["ok"])
        self.assertEqual(error["command"], "validate-atif")
        self.assertEqual(error["error"]["kind"], "input_or_contract")

    def test_validate_trial_without_artifact_root_is_not_scoreable(self) -> None:
        from pheno.evidence.trial_contracts import trial_sha256

        payload = json.loads(BUNDLE_RECORD.read_text(encoding="utf-8"))
        first = run_cli("validate-trial", str(BUNDLE_RECORD))
        second = run_cli("validate-trial", str(BUNDLE_RECORD))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        output = json.loads(first.stdout)
        self.assertFalse(output["scoreable"])
        self.assertFalse(output["artifact_bundle_verified"])
        self.assertIsNone(output["artifact_bundle_summary"])
        self.assertEqual(output["record_scoreability_reasons"], [])
        self.assertEqual(
            output["scoreability_reasons"],
            ["artifact bytes were not verified in this invocation"],
        )
        self.assertEqual(output["trial_sha256"], trial_sha256(payload))

    def test_validate_trial_with_artifact_root_verifies_bytes(self) -> None:
        if not _harbor_runtime_installed():
            self.skipTest(
                "harbor.models.trajectories not installed; "
                "requires the full Harbor runtime"
            )
        from pheno.evidence.trial_contracts import (
            trial_sha256,
            validate_trial_artifact_bundle,
        )

        payload = json.loads(BUNDLE_RECORD.read_text(encoding="utf-8"))
        first = run_cli(
            "validate-trial",
            str(BUNDLE_RECORD),
            "--artifact-root",
            str(BUNDLE),
        )
        second = run_cli(
            "validate-trial",
            str(BUNDLE_RECORD),
            "--artifact-root",
            str(BUNDLE),
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        output = json.loads(first.stdout)
        self.assertTrue(output["scoreable"])
        self.assertTrue(output["artifact_bundle_verified"])
        self.assertEqual(output["record_scoreability_reasons"], [])
        self.assertEqual(output["scoreability_reasons"], [])
        self.assertEqual(
            output["artifact_bundle_summary"],
            validate_trial_artifact_bundle(payload, BUNDLE),
        )
        self.assertEqual(output["trial_sha256"], trial_sha256(payload))

    def test_valid_diagnostic_trial_reports_non_scoreability_without_error(
        self,
    ) -> None:
        if not _harbor_runtime_installed():
            self.skipTest(
                "harbor.models.trajectories not installed; "
                "requires the full Harbor runtime"
            )
        payload = json.loads(BUNDLE_RECORD.read_text(encoding="utf-8"))
        payload["evidence_class"] = "synthetic"
        payload["run_mode"] = "dry_run"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "diagnostic-trial.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = run_cli(
                "validate-trial",
                str(path),
                "--artifact-root",
                str(BUNDLE),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertFalse(output["scoreable"])
        self.assertTrue(output["artifact_bundle_verified"])
        self.assertEqual(
            output["record_scoreability_reasons"],
            [
                "evidence_class is not local_measured",
                "run_mode is not execute",
            ],
        )
        self.assertEqual(
            output["scoreability_reasons"],
            output["record_scoreability_reasons"],
        )

    def test_validate_aggregate_is_validation_and_hash_only(self) -> None:
        from pheno.evidence.aggregate_contracts import (
            aggregate_sha256,
            aggregate_trials,
        )

        trial = json.loads(BUNDLE_RECORD.read_text(encoding="utf-8"))
        payload = aggregate_trials(
            [trial],
            expected_task_ids=[trial["cell"]["task_id"]],
            attempts_per_task=1,
            run_provenance=None,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aggregate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = run_cli("validate-aggregate", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["aggregate_sha256"], aggregate_sha256(payload))
        self.assertEqual(output["record_schema_version"], payload["schema_version"])
        self.assertEqual(
            set(output),
            {
                "aggregate_sha256",
                "command",
                "ok",
                "record_schema_version",
                "schema_version",
            },
        )

    def test_validate_performance_block_is_hash_and_gate_only(self) -> None:
        from pheno.evidence.performance_blocks import (
            build_performance_block_record,
            performance_block_sha256,
        )
        from tests.test_eval_performance_blocks import _blocks

        payload = build_performance_block_record(_blocks())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "performance-block.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = run_cli("validate-performance-block", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["command"], "validate-performance-block")
        self.assertEqual(output["promotion_status"], "pass")
        self.assertEqual(
            output["performance_block_sha256"], performance_block_sha256(payload)
        )
        self.assertEqual(output["record_schema_version"], payload["schema_version"])

    def test_validate_replay_stability_is_hash_and_gate_only(self) -> None:
        from pheno.evidence.replay_stability import (
            build_replay_stability_record,
            replay_stability_sha256,
        )
        from tests.test_eval_replay_stability import _greedy_rows

        payload = build_replay_stability_record(_greedy_rows())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "replay-stability.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            first = run_cli("validate-replay-stability", str(path))
            second = run_cli("validate-replay-stability", str(path))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        output = json.loads(first.stdout)
        self.assertEqual(output["command"], "validate-replay-stability")
        self.assertEqual(output["promotion_status"], "pass")
        self.assertEqual(output["promotion_reason_codes"], [])
        self.assertEqual(output["mode"], "greedy")
        self.assertEqual(output["block_id"], payload["block_id"])
        self.assertEqual(
            output["replay_stability_sha256"], replay_stability_sha256(payload)
        )
        self.assertEqual(output["record_schema_version"], payload["schema_version"])

    def test_trial_artifact_root_must_be_a_directory(self) -> None:
        result = run_cli(
            "validate-trial",
            str(BUNDLE_RECORD),
            "--artifact-root",
            str(BUNDLE_RECORD),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertEqual(error["error"]["kind"], "input_or_contract")
        self.assertIn("artifact_root must be a directory", error["error"]["message"])

    def test_trial_artifact_root_symlink_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "artifact-root"
            try:
                link.symlink_to(BUNDLE, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            result = run_cli(
                "validate-trial",
                str(BUNDLE_RECORD),
                "--artifact-root",
                str(link),
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            json.loads(result.stderr)["error"]["message"],
            "artifact_root must not be a symbolic link",
        )

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self) -> None:
        cases = (
            '{"schema_version":"ATIF-v1.7","schema_version":"ATIF-v1.7"}',
            '{"schema_version":"ATIF-v1.7","value":NaN}',
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, raw in enumerate(cases):
                with self.subTest(raw=raw):
                    path = Path(temp_dir) / f"invalid-{index}.json"
                    path.write_text(raw, encoding="utf-8")
                    result = run_cli("validate-atif", str(path))
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(
                        json.loads(result.stderr)["error"]["kind"],
                        "input_or_contract",
                    )

    def test_input_size_is_bounded_before_validation(self) -> None:
        self.assertEqual(eval_contract.DEFAULT_MAX_INPUT_BYTES, 16 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "too-large.json"
            path.write_text("{}\n", encoding="utf-8")
            result = run_cli(
                "--max-input-bytes",
                "1",
                "validate-atif",
                str(path),
            )
        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stderr)
        self.assertIn("1-byte limit", error["error"]["message"])

    def test_input_path_errors_do_not_echo_the_path(self) -> None:
        secret_path = ROOT / "missing-Bearer-abcdefghijklmnopqrstuvwxyz123456.json"
        result = run_cli("validate-trial", str(secret_path))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Bearer", result.stderr)
        self.assertEqual(
            json.loads(result.stderr)["error"]["message"],
            "input file does not exist",
        )

    def test_symbolic_link_input_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "trajectory.json"
            try:
                link.symlink_to(FIXTURES / "atif_valid_nested.json")
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            result = run_cli("validate-atif", str(link))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stderr)["error"]["message"],
            "input must not be a symbolic link",
        )

    def test_unexpected_error_is_generic_json_with_exit_one(self) -> None:
        fixture = FIXTURES / "atif_valid_nested.json"
        with patch.object(
            eval_contract,
            "validate_atif",
            side_effect=RuntimeError("Bearer " + "abcdefghijklmnopqrstuvwxyz123456"),
        ):
            result = run_cli("validate-atif", str(fixture))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertEqual(error["error"]["kind"], "internal")
        self.assertNotIn("Bearer", result.stderr)


if __name__ == "__main__":
    unittest.main()
