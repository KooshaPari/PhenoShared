from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from pheno.evidence import aggregate_contracts as aggregate
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex

SHA = "a" * 64
FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "eval_contracts"
    / "aggregate_balanced_case.json"
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def pair_key(task_id: str, ordinal: int) -> str:
    return digest(f"suite:{task_id}:fixture:{ordinal}:seed:{ordinal}")


def trial(
    *,
    arm: str,
    run_id: str,
    task_id: str,
    ordinal: int,
    state: str,
) -> dict:
    passed = state == "passed"
    return {
        "schema_version": aggregate.TRIAL_SCHEMA_VERSION,
        "run_id": run_id,
        "trial_id": f"{arm}-{task_id}-{ordinal}",
        "cell_id": digest(f"cell:{arm}"),
        "pair_key": pair_key(task_id, ordinal),
        "cell": {
            "suite_lock_sha256": SHA,
            "task_id": task_id,
            "attempt_ordinal": ordinal,
            "seed": ordinal,
        },
        "outcome": {
            "state": state,
            "reason": "verified" if passed else "verifier_fail",
            "scoreable": state != "infrastructure_exclusion",
            "reward": 1.0 if passed else 0.0,
        },
        "accepted_steps": (
            [
                {
                    "step_id": "task-pass",
                    "weight": 1.0,
                    "depends_on": [],
                    "false_to_true_transition": True,
                    "terminal_reverified": True,
                }
            ]
            if passed
            else []
        ),
        "total_weight": 1.0 if passed else 0.0,
        "timing": {
            "clock_id": f"clock:{run_id}",
            "enqueued_ns": 1,
            "verifier_completed_ns": 9_000_000_000,
        },
        "tools": {
            "emitted_candidates": 1,
            "parsed_calls": 1,
            "schema_valid_calls": 1,
            "executed_calls": 1,
            "semantically_correct_calls": 0,
            "gold_labeled_calls": 0,
            "schema_valid_but_wrong": 0,
            "duplicate_calls": 0,
            "loop_events": 0,
            "unauthorized_attempts": 0,
            "risky_action_bypasses": 0,
            "orphan_calls": 0,
            "orphan_observations": 0,
        },
        "cache": {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 50,
            "counter_reconciliation_error": 0.0,
            "cross_request_contamination": False,
        },
        "drift": {},
    }


def run_provenance(run_id: str, seconds: int) -> dict:
    return {
        "schema_version": aggregate.RUN_PROVENANCE_SCHEMA_VERSION,
        "run_id": run_id,
        "clock_id": f"clock:{run_id}",
        "measurement_started_ns": 0,
        "measurement_completed_ns": seconds * 1_000_000_000,
        "instrumentation_coverage_fraction": 1.0,
        "peak_attributable_active_memory_bytes": 2_000_000_000,
        "memory_coverage_fraction": 1.0,
        "memory_provenance_sha256": digest(f"memory:{run_id}"),
        "memory_scope": aggregate.MEMORY_SCOPE,
        "unified_memory_counted_once": True,
        "cost": {
            "completeness": "complete",
            "total_amortized_usd": 2.0,
            "ledger_sha256": digest(f"cost:{run_id}"),
            "components": {
                "provider": {"status": "not_applicable", "amount_usd": 0.0},
                "electricity": {"status": "complete", "amount_usd": 0.5},
                "hardware_amortization": {"status": "complete", "amount_usd": 1.5},
            },
        },
        "concurrency": {
            "stream_goodputs": [1.0, 1.0],
            "error_rate": 0.0,
            "starvation_count": 0,
            "goodput_unit": "normalized_useful_work_per_second",
            "homogeneous_or_normalized_fixture": True,
            "provenance_sha256": digest(f"concurrency:{run_id}"),
        },
        "thermal": {
            "duration_seconds": 1800.0,
            "coverage_fraction": 1.0,
            "baseline_window_start_s": 300,
            "baseline_window_end_s": 600,
            "terminal_window_start_s": 1500,
            "terminal_window_end_s": 1800,
            "baseline_goodput": 1.0,
            "terminal_goodput": 0.95,
            "baseline_p95_latency_ms": 100.0,
            "terminal_p95_latency_ms": 110.0,
            "os_thermal_state_peak": "fair",
            "policy_violation": False,
            "telemetry_sha256": digest(f"thermal:{run_id}"),
            "load_profile_sha256": digest("load-profile"),
        },
    }


class AggregateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.tasks = self.fixture["expected_task_ids"]
        self.treatment = self._arm("treatment", "run-treatment")
        self.baseline = self._arm("baseline", "run-baseline")
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()

    def tearDown(self) -> None:
        self.patches.stop()

    def _arm(self, arm: str, run_id: str) -> list[dict]:
        return [
            trial(
                arm=arm,
                run_id=run_id,
                task_id=task_id,
                ordinal=ordinal,
                state=state,
            )
            for task_id, outcomes in self.fixture[arm].items()
            for ordinal, state in enumerate(outcomes)
        ]

    def _aggregate(self, trials: list[dict] | None = None, **kwargs: object) -> dict:
        return aggregate.aggregate_trials(
            trials or self.treatment,
            expected_task_ids=self.tasks,
            attempts_per_task=4,
            run_provenance=run_provenance("run-treatment", 10),
            baseline_trials=self.baseline,
            baseline_run_provenance=run_provenance("run-baseline", 20),
            **kwargs,
        )

    def test_balanced_fixture_metrics_and_paired_ci(self) -> None:
        result = self._aggregate()
        expected = self.fixture["expected"]
        self.assertEqual(
            result["quality"]["pass_at_1"]["estimate"], expected["treatment_pass_at_1"]
        )
        self.assertEqual(
            result["quality"]["pass_at_4"]["estimate"], expected["treatment_pass_at_4"]
        )
        self.assertEqual(
            result["quality"]["pass_all_k"]["estimate"],
            expected["treatment_pass_all_4"],
        )
        delta = result["comparison"]["pass_at_1_delta"]
        self.assertEqual(delta["estimate"], expected["paired_pass_at_1_delta"])
        self.assertEqual(delta["ci95"]["lower"], expected["paired_delta_ci95_lower"])
        self.assertEqual(delta["ci95"]["upper"], expected["paired_delta_ci95_upper"])
        for field in (
            "avs_per_second",
            "avs_per_second_per_gb",
            "avs_per_dollar",
            "combined_avs_per_second_gb_dollar",
        ):
            self.assertAlmostEqual(result["efficiency"][field], expected[field])
        self.assertEqual(len(result["provenance"]["contributing_trial_sha256"]), 8)
        self.assertEqual(result["gates"]["quality_noninferiority"]["status"], "pass")
        self.assertEqual(
            result["gates"]["performance_promotion"]["status"], "not_evaluable"
        )

    def test_quantile_type7_empty_singleton_and_interpolation(self) -> None:
        self.assertIsNone(aggregate.quantile_type7([], 0.5))
        self.assertEqual(aggregate.quantile_type7([4.0], 0.95), 4.0)
        self.assertEqual(aggregate.quantile_type7([0.0, 10.0], 0.25), 2.5)

    def test_recomputation_rejects_tampered_estimate(self) -> None:
        result = self._aggregate()
        tampered = copy.deepcopy(result)
        tampered["quality"]["pass_at_1"]["estimate"] = 0.5
        with self.assertRaisesRegex(ContractError, "does not match recomputation"):
            aggregate.validate_aggregate_against_inputs(
                tampered,
                self.treatment,
                expected_task_ids=self.tasks,
                attempts_per_task=4,
                run_provenance=run_provenance("run-treatment", 10),
                baseline_trials=self.baseline,
                baseline_run_provenance=run_provenance("run-baseline", 20),
            )

    def test_missing_attempt_is_visible_and_pass_all_ci_is_undefined(self) -> None:
        incomplete = copy.deepcopy(self.treatment[:-1])
        result = self._aggregate(incomplete)
        self.assertEqual(result["gates"]["sample_adequacy"]["status"], "fail")
        self.assertEqual(result["quality"]["pass_all_k"]["complete_task_coverage"], 0.5)
        self.assertIsNone(result["quality"]["pass_all_k"]["ci95"]["lower"])

    def test_infrastructure_exclusion_is_not_scored_or_hidden(self) -> None:
        excluded = copy.deepcopy(self.treatment)
        excluded[-1]["outcome"] = {
            "state": "infrastructure_exclusion",
            "reason": "network_error",
            "scoreable": False,
            "reward": 0.0,
        }
        excluded[-1]["accepted_steps"] = []
        excluded[-1]["total_weight"] = 0.0
        result = self._aggregate(excluded)
        self.assertEqual(result["counts"]["excluded"], 1)
        self.assertEqual(result["counts"]["scored"], 7)
        self.assertEqual(result["gates"]["infrastructure_health"]["status"], "fail")
        self.assertIsNone(result["quality"]["pass_all_k"]["ci95"]["lower"])

    def test_duplicate_trial_is_rejected(self) -> None:
        duplicate = self.treatment + [copy.deepcopy(self.treatment[0])]
        with self.assertRaisesRegex(ContractError, "duplicate canonical trial"):
            self._aggregate(duplicate)

    def test_incomplete_cost_nulls_dollar_metrics_without_hiding_reason(self) -> None:
        provenance = run_provenance("run-treatment", 10)
        provenance["cost"] = {
            "completeness": "incomplete",
            "total_amortized_usd": None,
            "ledger_sha256": digest("partial-ledger"),
            "components": {"electricity": {"status": "unknown", "amount_usd": 0.0}},
        }
        result = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=self.tasks,
            attempts_per_task=4,
            run_provenance=provenance,
        )
        self.assertIsNone(result["efficiency"]["avs_per_dollar"])
        self.assertEqual(
            result["gates"]["cost_completeness"]["status"], "not_evaluable"
        )
        self.assertEqual(result["gates"]["run_provenance"]["status"], "pass")

    def test_hash_is_canonical_and_structural_tampering_is_rejected(self) -> None:
        result = self._aggregate()
        reordered = {key: result[key] for key in reversed(list(result))}
        self.assertEqual(
            aggregate.aggregate_sha256(result), aggregate.aggregate_sha256(reordered)
        )
        tampered = copy.deepcopy(result)
        tampered["counts"]["scored"] -= 1
        with self.assertRaisesRegex(ContractError, "counts do not reconcile"):
            aggregate.validate_aggregate_record(tampered)


if __name__ == "__main__":
    unittest.main()
