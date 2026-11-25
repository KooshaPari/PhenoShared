import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.self_improvement.artifacts import observation_from_artifact


class GardenArtifactTests(unittest.TestCase):
    def test_completed_perf_artifact_is_scoreable(self):
        row = observation_from_artifact(
            {
                "status": "pass",
                "model_alias": "local/qwen35-08b",
                "aggregate_tokens_per_s": 23.2,
                "total_requests": 8,
                "successes": 8,
            },
            artifact=Path("state/example.json"),
            git_sha="abc",
        )
        self.assertTrue(row["scoreable"])
        self.assertEqual(row["metrics"]["success_rate"], 1.0)

    def test_non_scoreable_artifact_cannot_enter_as_a_pass(self):
        row = observation_from_artifact(
            {"suite_status": "availability_unverified"},
            artifact=Path("x.json"),
            git_sha="abc",
        )
        self.assertFalse(row["scoreable"])
        self.assertEqual(row["result"], "non_scoreable")

    def test_shared_artifact_is_kept_out_of_clean_baseline(self):
        row = observation_from_artifact(
            {
                "schema_version": "pheno.heterogeneous_perf.v1",
                "model": "local/qwen35-08b",
                "result": {
                    "request_count": 2,
                    "success_count": 2,
                    "error_count": 0,
                    "aggregate_tokens_per_s": 20,
                },
            },
            artifact=Path("shared_perf.json"),
            git_sha="abc",
        )
        self.assertTrue(row["contended"])
        self.assertFalse(row["scoreable"])

    def test_runtime_manifest_metrics_are_ingested(self):
        row = observation_from_artifact(
            {
                "model_alias": "local/ornith-8b",
                "runtime_validation": {"status": "pass", "generation_tok_s": 25.3},
            },
            artifact=Path("ornith_mtp_q4_manifest.json"),
            git_sha="abc",
        )
        self.assertTrue(row["scoreable"])
        self.assertEqual(row["metrics"]["generation_tok_s"], 25.3)

    def test_perf_levels_are_aggregated(self):
        row = observation_from_artifact(
            {
                "schema_version": "pheno.perf.v1",
                "model": "local/qwen35-08b",
                "levels": [
                    {
                        "request_count": 3,
                        "success_count": 3,
                        "error_count": 0,
                        "aggregate_tokens_per_s": 23.2,
                        "latency_ms_p95": 260,
                    }
                ],
            },
            artifact=Path("qwen1080_perf_real.json"),
            git_sha="abc",
        )
        self.assertTrue(row["scoreable"])
        self.assertEqual(row["metrics"]["success_rate"], 1.0)

    def test_variant_bakeoff_is_diagnostic_and_retains_metrics(self):
        row = observation_from_artifact(
            {
                "schema_version": "phenolm.quantization_bakeoff.v1",
                "model": "local/qwen35-08b",
                "variants": [{"generation_tok_s": 20}, {"generation_tok_s": 30}],
            },
            artifact=Path("quantization_bakeoff.json"),
            git_sha="abc",
        )
        self.assertFalse(row["scoreable"])
        self.assertEqual(row["artifact_status"], "diagnostic_only")
        self.assertEqual(row["metrics"]["variant_count"], 2.0)
        self.assertEqual(row["metrics"]["max_generation_tok_s"], 30.0)

    def test_negative_spec_control_is_diagnostic_and_retains_speedup(self):
        row = observation_from_artifact(
            {
                "schema_version": "phenolm.speculative_probe.v1",
                "model": "local/qwen35-08b",
                "medians": {
                    "baseline": {"median_tok_s": 100},
                    "ngram-simple": {"median_tok_s": 95},
                },
                "decision": {"status": "negative_control", "promote": False},
            },
            artifact=Path("spec_probe.json"),
            git_sha="abc",
        )
        self.assertFalse(row["scoreable"])
        self.assertEqual(row["artifact_status"], "negative_control")
        self.assertEqual(row["metrics"]["candidate_speedup"], 0.95)

    def test_harbor_zero_reward_with_verifier_is_scoreable_baseline(self):
        row = observation_from_artifact(
            {
                "schema_version": "phenolm.harbor_trial.v1",
                "status": "completed",
                "model_id": "local/lfm25-8b-a1b",
                "metrics": {"reward": 0.0, "trial_count": 1, "error_count": 0},
                "verifier": {"present": True},
            },
            artifact=Path("lfm25.json"),
            git_sha="abc",
        )
        self.assertTrue(row["scoreable"])
        self.assertEqual(row["metrics"]["reward"], 0.0)

    def test_cli_dry_run_does_not_append(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "perf.json"
            artifact.write_text(
                json.dumps({"status": "pass", "aggregate_tokens_per_s": 10}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/ingest_garden_observation.py"),
                    str(artifact),
                    "--dry-run",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["scoreable"])


if __name__ == "__main__":
    unittest.main()
