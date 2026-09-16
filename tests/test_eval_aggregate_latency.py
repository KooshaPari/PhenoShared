from __future__ import annotations

import copy
import hashlib
import unittest
from unittest import mock

from pheno.evidence import aggregate_contracts as aggregate
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex

SHA = "a" * 64


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _tools(*, labeled: bool) -> dict:
    return {
        "emitted_candidates": 3 if labeled else 1,
        "parsed_calls": 2 if labeled else 1,
        "schema_valid_calls": 2 if labeled else 1,
        "executed_calls": 2 if labeled else 1,
        "semantically_correct_calls": 1,
        "gold_labeled_calls": 2 if labeled else None,
        "exact_tool_matches": 2 if labeled else None,
        "exact_argument_matches": 1 if labeled else None,
        "schema_valid_but_wrong": 0,
        "repair_attempts": 2 if labeled else 0,
        "fallbacks": 1,
        "duplicate_calls": 0,
        "loop_events": 0,
        "unauthorized_attempts": 0,
        "risky_action_bypasses": 0,
        "orphan_calls": 0,
        "orphan_observations": 0,
    }


def _trial(task_id: str, *, queue_ms: float, completion: int, interval_ns: int) -> dict:
    ordinal = 0
    return {
        "schema_version": aggregate.TRIAL_SCHEMA_VERSION,
        "run_id": "latency-run",
        "trial_id": f"trial-{task_id}",
        "cell_id": SHA,
        "pair_key": _digest(f"{task_id}:{ordinal}"),
        "cell": {
            "suite_lock_sha256": SHA,
            "task_id": task_id,
            "attempt_ordinal": ordinal,
            "seed": 7,
        },
        "outcome": {
            "state": "passed",
            "reason": None,
            "scoreable": True,
            "reward": 1.0,
        },
        "accepted_steps": [
            {
                "step_id": "task-pass",
                "weight": 1.0,
                "depends_on": [],
                "false_to_true_transition": True,
                "terminal_reverified": True,
            }
        ],
        "total_weight": 1.0,
        "timing": {
            "clock_id": "clock:latency-run",
            "enqueued_ns": 0,
            "first_token_ns": 1_000_000_000,
            "last_token_ns": 1_000_000_000 + interval_ns,
            "verifier_completed_ns": 4_000_000_000,
            "queue_ms": queue_ms,
            "ttft_ms": queue_ms * 10,
            "task_wall_ms": queue_ms * 100,
            "verifier_ms": queue_ms * 5,
        },
        "tokens": {"completion": completion},
        "tools": _tools(labeled=task_id == "task-alpha"),
        "cache": {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 50,
            "counter_reconciliation_error": 0.0,
            "cross_request_contamination": False,
        },
        "integrity": {
            "ooms": 0,
            "deadlocks": 0,
            "unexplained_restarts": 0,
        },
        "drift": {
            "assertion_manifest_sha256": _digest("drift-manifest"),
            "checkpoints": [
                {
                    "turn": turn,
                    "assertions_expected": 1,
                    "assertions_retained": (
                        1 if task_id == "task-alpha" or turn <= 10 else 0
                    ),
                }
                for turn in (1, 5, 10, 25, 50)
            ],
        },
    }


class AggregateLatencyAndToolSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trials = [
            _trial(
                "task-alpha",
                queue_ms=10.0,
                completion=11,
                interval_ns=1_000_000_000,
            ),
            _trial(
                "task-beta",
                queue_ms=30.0,
                completion=21,
                interval_ns=2_000_000_000,
            ),
        ]
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()

    def tearDown(self) -> None:
        self.patches.stop()

    def _aggregate(self, trials: list[dict] | None = None) -> dict:
        return aggregate.aggregate_trials(
            trials or self.trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=1,
            run_provenance=None,
            bootstrap_resamples=aggregate.DEFAULT_BOOTSTRAP_RESAMPLES,
        )

    def test_latency_block_uses_token_timestamps_and_type7_quantiles(self) -> None:
        result = self._aggregate()
        latency = result["latency"]
        self.assertEqual(latency["population"], "scoreable_trials")
        self.assertEqual(latency["scoreable_trial_count"], 2)
        self.assertEqual(latency["queue_ms"]["p50"], 20.0)
        self.assertEqual(latency["queue_ms"]["p95"], 29.0)
        self.assertEqual(latency["queue_ms"]["p99"], 29.8)

        decode = latency["true_decode_tokens_per_second"]
        self.assertEqual(decode["sample_count"], 2)
        self.assertEqual(decode["p50"], 10.0)
        self.assertEqual(decode["p95"], 10.0)
        self.assertEqual(decode["p99"], 10.0)
        self.assertEqual(decode["formula"], aggregate.TRUE_DECODE_FORMULA)
        self.assertEqual(
            decode["timestamp_source"], aggregate.TRUE_DECODE_TIMESTAMP_SOURCE
        )
        self.assertFalse(
            any("itl" in key.lower() for key in _all_keys(latency)),
            "transport chunk gaps must not be presented as inter-token latency",
        )
        self.assertEqual(aggregate.validate_aggregate_record(result), result)

        tampered = copy.deepcopy(result)
        tampered["latency"]["queue_ms"]["p50"] = 31.0
        with self.assertRaisesRegex(ContractError, "quantiles must be monotonic"):
            aggregate.validate_aggregate_record(tampered)

        tampered = copy.deepcopy(result)
        tampered["latency"]["true_decode_tokens_per_second"]["formula"] = (
            "completion_tokens / elapsed_seconds"
        )
        with self.assertRaisesRegex(ContractError, "formula is not recognized"):
            aggregate.validate_aggregate_record(tampered)

    def test_tool_rates_use_executed_and_gold_labeled_denominators(self) -> None:
        result = self._aggregate()
        tools = result["tools"]
        self.assertEqual(tools["totals"]["executed_calls"], 3)
        self.assertEqual(tools["totals"]["semantically_correct_calls"], 2)
        self.assertEqual(tools["semantic_correct_rate"], 2 / 3)
        self.assertEqual(tools["exact_tool_match_rate"], 1.0)
        self.assertEqual(tools["exact_argument_match_rate"], 0.5)
        self.assertEqual(tools["totals"]["repair_attempts"], 2)
        self.assertEqual(tools["repair_attempt_trial_count"], 1)
        self.assertEqual(tools["repair_attempt_trial_rate"], 0.5)
        self.assertEqual(tools["totals"]["fallbacks"], 2)
        self.assertEqual(tools["fallback_trial_count"], 2)
        self.assertEqual(tools["fallback_trial_rate"], 1.0)

        open_ended = copy.deepcopy(self.trials)
        open_ended[0]["tools"]["gold_labeled_calls"] = None
        open_ended[0]["tools"]["exact_tool_matches"] = None
        open_ended[0]["tools"]["exact_argument_matches"] = None
        summary = aggregate._summarize_tools(open_ended)
        self.assertNotIn("exact_tool_match_rate", summary)
        self.assertNotIn("exact_argument_match_rate", summary)

        tampered = copy.deepcopy(result)
        tampered["tools"]["semantic_correct_rate"] = 1.0
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(tampered)

    def test_admissibility_runtime_stability_and_incomplete_run_efficiency(
        self,
    ) -> None:
        with (
            mock.patch.object(
                aggregate,
                "trial_scoreability_reasons",
                return_value=["run_mode is not execute"],
            ),
            self.assertRaisesRegex(ContractError, "not evidence-admissible"),
        ):
            self._aggregate()

        unstable = copy.deepcopy(self.trials)
        unstable[0]["outcome"] = {
            "state": "model_failure",
            "reason": "oom",
            "scoreable": True,
            "reward": 0.0,
        }
        unstable[0]["accepted_steps"] = []
        unstable[0]["total_weight"] = 0.0
        unstable[0]["integrity"]["ooms"] = 1
        with mock.patch.object(
            aggregate,
            "trial_scoreability_reasons",
            return_value=["integrity.ooms is nonzero"],
        ):
            result = self._aggregate(unstable)
        self.assertEqual(result["counts"]["scored"], 2)
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertEqual(result["counts"]["excluded"], 0)
        self.assertEqual(result["runtime_stability"]["ooms"], 1)
        self.assertEqual(result["gates"]["runtime_stability"]["status"], "fail")
        self.assertIn("runtime_stability", result["promotion"]["reason_codes"])

        incomplete_run = {
            "complete": False,
            "reasons": ["memory coverage is below 95%"],
            "makespan_seconds": 1.0,
            "peak_attributable_active_memory_bytes": 2_000_000_000,
            "cost": {
                "complete": True,
                "total_amortized_usd": 1.0,
            },
        }
        efficiency = aggregate._efficiency(self.trials, incomplete_run)
        self.assertEqual(efficiency["accepted_verified_step_weight"], 2.0)
        self.assertFalse(efficiency["provenance_complete"])
        self.assertEqual(
            efficiency["provenance_reasons"],
            ["memory coverage is below 95%"],
        )
        for field in (
            "run_makespan_seconds",
            "peak_attributable_active_memory_bytes",
            "peak_attributable_active_memory_gb_si",
            "total_amortized_usd",
            "avs_per_second",
            "avs_per_second_per_gb",
            "avs_per_dollar",
            "combined_avs_per_second_gb_dollar",
        ):
            self.assertIsNone(efficiency[field], field)

    def test_drift_summary_is_strictly_validated(self) -> None:
        result = self._aggregate()
        drift = result["drift"]
        self.assertEqual(drift["assertion_manifest_sha256"], _digest("drift-manifest"))
        self.assertEqual(drift["retention_by_turn"]["1"]["retention"], 1.0)
        self.assertEqual(drift["retention_by_turn"]["50"]["retention"], 0.5)
        self.assertEqual(drift["long_turn_assertions_retained"], 8)
        self.assertEqual(drift["long_turn_assertions_expected"], 10)
        self.assertEqual(drift["long_turn_assertion_retention"], 0.8)
        tampered = copy.deepcopy(result)
        tampered["drift"]["long_turn_assertions_retained"] = 11
        with self.assertRaisesRegex(
            ContractError, "retained long-turn assertions exceed expected"
        ):
            aggregate.validate_aggregate_record(tampered)


def _all_keys(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value] + [
            child for item in value.values() for child in _all_keys(item)
        ]
    if isinstance(value, list):
        return [child for item in value for child in _all_keys(item)]
    return []


if __name__ == "__main__":
    unittest.main()
