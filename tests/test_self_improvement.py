import unittest

from harness.self_improvement.gates import evaluate_gates
from harness.self_improvement.signals import aggregate_rows

POLICY = {
    "gates": {
        "holdout": {"required": True, "min_delta_vs_baseline": 0.0},
        "regression": {"required": True, "max_allowed_new_regressions": 0},
        "safety": {"required": True, "max_high_severity_violations": 0},
        "budget": {"required": True, "max_alert_level": "yellow"},
        "reproducibility": {"required": True, "min_replay_equivalence": 0.9},
        "serving_stability": {
            "required": True,
            "max_crash_count": 0,
            "max_p95_ttft_regression_pct": 10,
        },
    }
}


class SelfImprovementTests(unittest.TestCase):
    def test_signal_aggregation_groups_numeric_metrics(self):
        result = aggregate_rows(
            [
                {"role": "reviewer", "metrics": {"tokens": 10}},
                {"role": "reviewer", "metrics": {"tokens": 20}},
            ],
            group_by="role",
        )
        self.assertEqual(result["reviewer"]["tokens"]["mean"], 15.0)

    def test_all_required_gates_green(self):
        metrics = {
            "holdout_score": 0.9,
            "new_regressions": 0,
            "high_severity_violations": 0,
            "budget_alert_level": "green",
            "replay_equivalence": 0.95,
            "crash_count": 0,
            "p95_ttft_regression_pct": 2,
        }
        result = evaluate_gates(metrics, {"holdout_score": 0.9}, POLICY)
        self.assertEqual(result["status"], "green")

    def test_missing_required_signal_fails_closed(self):
        result = evaluate_gates({}, {}, POLICY)
        self.assertEqual(result["status"], "red")
        self.assertIn("holdout", result["required_failures"])


if __name__ == "__main__":
    unittest.main()
