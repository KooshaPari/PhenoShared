from __future__ import annotations

import copy
import unittest

from pheno.evidence.benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    derive_efficiency,
    promotion_reasons,
    scoreability_reasons,
    validate_benchmark_record,
)

SHA = "b" * 64


def completed_record() -> dict:
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "run_id": "tbench21-qwen36-vllm-c1-seed0",
        "created_at": "2026-07-14T22:00:00+00:00",
        "status": "complete",
        "suite": {
            "name": "terminal-bench-2.1",
            "revision": "36d417f56c293b8271b306a0e4c566f58e98c153",
            "task_manifest_sha256": SHA,
            "task_count": 2,
            "attempts_per_task": 5,
        },
        "provenance": {
            "harness_revision": "0123456789abcdef",
            "worktree_dirty": False,
            "config_sha256": SHA,
            "tool_schema_sha256": SHA,
            "agent_config_sha256": SHA,
            "evaluator_sha256": SHA,
            "verifier_artifacts": {"reward.json": SHA, "run.log": SHA},
        },
        "factors": {
            "model_record_id": "hf:qwen/qwen3.6-35b-a3b:0123456789abcdef",
            "artifact_revision": "int4-sha256:example",
            "quantization": "awq-int4",
            "runtime": "vllm",
            "runtime_revision": "0.25.1",
            "parser_revision": "qwen3-coder@0123",
            "template_revision": "sha256:template",
            "context_tokens": 16384,
            "cache_mode": "prefix",
            "decode_mode": "autoregressive",
            "concurrency": 1,
            "role": "coding-worker",
            "seed": 0,
            "device": "rtx-3090-ti-sm86",
        },
        "integrity": {
            "no_training_on_eval_tasks": True,
            "risky_action_gate_enabled": True,
            "risky_action_bypass_count": 0,
            "verifier_untampered": True,
            "secrets_redacted": True,
            "synthetic": False,
            "tool_observation_correlation": 1.0,
            "infra_exclusion_rate": 0.0,
        },
        "metrics": {
            "quality": {
                "accepted_verified_steps": 100,
                "task_attempts": 10,
                "task_successes": 8,
                "pass_at_1": 0.8,
                "pass_at_k": 1.0,
                "ci95_lower": 0.6,
                "ci95_upper": 0.95,
            },
            "latency": {"wall_seconds": 20.0, "ttft_p95_ms": 500.0, "itl_p95_ms": 25.0},
            "resources": {"peak_active_gb": 20.0, "energy_wh": 12.0},
            "cost": {"amortized_usd": 0.50},
            "tools": {
                "schema_valid_rate": 1.0,
                "exact_rate": 1.0,
                "wrong_tool_rate": 0.0,
                "duplicate_loop_rate": 0.0,
                "recovery_rate": 1.0,
            },
            "cache": {},
            "drift": {},
            "concurrency": {
                "successful_request_rate": 1.0,
                "oom_count": 0,
                "restart_count": 0,
                "deadlock_count": 0,
            },
            "thermals": {"throttled": False, "throughput_retention_30m": 0.95},
            "speculation": {},
            "comparison": {"quality_delta_ci95_lower": -0.01},
        },
    }


class BenchmarkContractTests(unittest.TestCase):
    def test_complete_record_is_scoreable_and_promotable(self) -> None:
        payload = completed_record()
        self.assertEqual(
            validate_benchmark_record(payload)["run_id"], payload["run_id"]
        )
        self.assertEqual(scoreability_reasons(payload), [])
        self.assertEqual(promotion_reasons(payload), [])

    def test_north_star_is_a_vector_with_secondary_composite(self) -> None:
        values = derive_efficiency(completed_record())
        self.assertAlmostEqual(values["avs_per_second"], 5.0)
        self.assertAlmostEqual(values["avs_per_second_per_peak_gb"], 0.25)
        self.assertAlmostEqual(values["avs_per_dollar"], 200.0)
        self.assertAlmostEqual(values["combined_avs_per_second_gb_dollar"], 0.5)

    def test_zero_provider_cost_is_not_zero_amortized_cost(self) -> None:
        payload = completed_record()
        payload["metrics"]["cost"]["amortized_usd"] = 0.0
        self.assertIn(
            "amortized cost must be positive for the /$ comparison",
            scoreability_reasons(payload),
        )
        self.assertIsNone(derive_efficiency(payload)["avs_per_dollar"])

    def test_integrity_failure_cannot_be_hidden_by_speed(self) -> None:
        payload = completed_record()
        payload["integrity"]["risky_action_bypass_count"] = 1
        payload["metrics"]["latency"]["wall_seconds"] = 0.01
        self.assertIn("risky-action bypass observed", promotion_reasons(payload))

    def test_stability_thresholds_are_promotion_gates(self) -> None:
        payload = completed_record()
        payload["metrics"]["tools"]["wrong_tool_rate"] = 0.02
        payload["metrics"]["thermals"]["throughput_retention_30m"] = 0.85
        reasons = promotion_reasons(payload)
        self.assertIn("wrong-tool rate exceeds 1%", reasons)
        self.assertIn("30-minute throughput retention below 90%", reasons)

    def test_synthetic_data_is_diagnostic_only(self) -> None:
        payload = copy.deepcopy(completed_record())
        payload["integrity"]["synthetic"] = True
        self.assertIn("synthetic run", scoreability_reasons(payload))


if __name__ == "__main__":
    unittest.main()
