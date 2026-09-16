from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from pheno.evidence import aggregate_contracts, trial_contracts
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex

TRIAL_FIXTURE = (
    Path(__file__).parent / "fixtures" / "eval_contracts" / "trial_valid.json"
)
TASK_IDS = ("task-alpha", "task-beta")


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical_ids(record: dict) -> None:
    cell = record["cell"]
    cell_identity = {
        "suite_lock_sha256": cell["suite_lock_sha256"],
        "model": cell["model"],
        "runtime": cell["runtime"],
        "harness": cell["harness"],
        "device": cell["device"],
        "treatment": cell["treatment"],
        "sampling": cell["sampling"],
    }
    pair_identity = {
        "suite_lock_sha256": cell["suite_lock_sha256"],
        "task_id": cell["task_id"],
        "attempt_ordinal": cell["attempt_ordinal"],
        "seed": cell["seed"],
    }
    record["cell_id"] = sha256_hex(canonical_json_bytes(cell_identity))
    record["pair_key"] = sha256_hex(canonical_json_bytes(pair_identity))


def _trial(
    template: dict,
    *,
    arm: str,
    run_id: str,
    task_id: str,
    ordinal: int,
    state: str,
) -> dict:
    record = copy.deepcopy(template)
    record["run_id"] = run_id
    record["trial_id"] = f"{arm}-{task_id}-{ordinal}"
    cell = record["cell"]
    cell["task_id"] = task_id
    cell["attempt_ordinal"] = ordinal
    cell["seed"] = 100 + ordinal
    cell["treatment"]["role"] = arm

    record["timing"]["clock_id"] = f"clock:{run_id}"
    if state == "passed":
        record["outcome"] = {
            "state": "passed",
            "reason": None,
            "scoreable": True,
            "reward": 1.0,
            "verifier_components": {"task_pass": 1.0},
        }
    elif state == "model_failure":
        record["outcome"] = {
            "state": "model_failure",
            "reason": "verifier_fail",
            "scoreable": True,
            "reward": 0.0,
            "verifier_components": {"task_pass": 0.0},
        }
        record["accepted_steps"] = []
        record["total_weight"] = 0.0
    elif state == "infrastructure_exclusion":
        record["outcome"] = {
            "state": "infrastructure_exclusion",
            "reason": "network_error",
            "scoreable": False,
            "reward": None,
            "verifier_components": {},
        }
        record["accepted_steps"] = []
        record["total_weight"] = 0.0
    else:  # pragma: no cover - test construction guard
        raise ValueError(state)

    artifact_root = f"artifacts/{arm}/{task_id}/{ordinal}"
    record["artifacts"] = {
        "atif_trajectory": {
            "path": f"{artifact_root}/trajectory.atif.json",
            "sha256": _digest(f"{record['trial_id']}:atif"),
        },
        "intent_graph": {
            "path": f"{artifact_root}/intent-graph.json",
            "sha256": _digest(f"{record['trial_id']}:intent"),
        },
        "verifier_outputs": [
            {
                "path": f"{artifact_root}/verifier/reward.json",
                "sha256": _digest(f"{record['trial_id']}:verifier"),
            }
        ],
        "patch": {
            "path": f"{artifact_root}/changes.patch",
            "sha256": _digest(f"{record['trial_id']}:patch"),
        },
    }
    record["cost"]["ledger_sha256"] = _digest(f"{record['trial_id']}:cost")
    _canonical_ids(record)
    return trial_contracts.validate_trial_record(record)


def _arm(
    template: dict, arm: str, run_id: str, states: tuple[tuple[str, str], ...]
) -> list[dict]:
    return [
        _trial(
            template,
            arm=arm,
            run_id=run_id,
            task_id=task_id,
            ordinal=ordinal,
            state=state,
        )
        for task_id, task_states in zip(TASK_IDS, states, strict=True)
        for ordinal, state in enumerate(task_states)
    ]


def _run_provenance(run_id: str, *, seconds: int, cost_usd: float) -> dict:
    return {
        "schema_version": aggregate_contracts.RUN_PROVENANCE_SCHEMA_VERSION,
        "run_id": run_id,
        "clock_id": f"clock:{run_id}",
        "measurement_started_ns": 0,
        "measurement_completed_ns": seconds * 1_000_000_000,
        "instrumentation_coverage_fraction": 1.0,
        "peak_attributable_active_memory_bytes": 2_000_000_000,
        "memory_coverage_fraction": 1.0,
        "memory_provenance_sha256": _digest(f"{run_id}:memory"),
        "memory_scope": aggregate_contracts.MEMORY_SCOPE,
        "unified_memory_counted_once": True,
        "cost": {
            "completeness": "complete",
            "total_amortized_usd": cost_usd,
            "ledger_sha256": _digest(f"{run_id}:cost"),
            "components": {
                "electricity": {
                    "status": "complete",
                    "amount_usd": cost_usd * 0.25,
                },
                "hardware_amortization": {
                    "status": "complete",
                    "amount_usd": cost_usd * 0.75,
                },
            },
        },
        "concurrency": {
            "stream_goodputs": [1.0, 1.0],
            "error_rate": 0.0,
            "starvation_count": 0,
            "goodput_unit": "normalized_useful_work_per_second",
            "homogeneous_or_normalized_fixture": True,
            "provenance_sha256": _digest(f"{run_id}:concurrency"),
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
            "os_thermal_state_peak": "nominal",
            "policy_violation": False,
            "telemetry_sha256": _digest(f"{run_id}:thermal"),
            "load_profile_sha256": _digest("integration-load-profile"),
        },
    }


class AggregateRealTrialIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        cls.treatment = _arm(
            cls.template,
            "treatment",
            "run-treatment-integration",
            (
                ("passed", "infrastructure_exclusion"),
                ("model_failure", "passed"),
            ),
        )
        cls.baseline = _arm(
            cls.template,
            "baseline",
            "run-baseline-integration",
            (
                ("model_failure", "passed"),
                ("model_failure", "passed"),
            ),
        )
        cls.treatment_run = _run_provenance(
            "run-treatment-integration", seconds=4, cost_usd=1.0
        )
        cls.baseline_run = _run_provenance(
            "run-baseline-integration", seconds=8, cost_usd=2.0
        )

    def _aggregate(self) -> dict:
        return aggregate_contracts.aggregate_trials(
            self.treatment,
            expected_task_ids=TASK_IDS,
            attempts_per_task=2,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            bootstrap_resamples=aggregate_contracts.DEFAULT_BOOTSTRAP_RESAMPLES,
        )

    def test_real_trial_validation_aggregation_and_recomputation(self) -> None:
        for record in self.treatment + self.baseline:
            self.assertEqual(
                trial_contracts.validate_trial_record(record),
                record,
            )
        self.assertEqual(
            trial_contracts.trial_scoreability_reasons(self.treatment[1]),
            ["outcome is an infrastructure exclusion"],
        )

        result = self._aggregate()
        self.assertEqual(
            result["counts"],
            {
                "attempted": 4,
                "scored": 3,
                "passed": 2,
                "failed": 1,
                "excluded": 1,
                "excluded_by_reason": {"network_error": 1},
                "infrastructure_exclusion_rate": 0.25,
            },
        )
        self.assertEqual(result["quality"]["pass_at_1"]["estimate"], 0.75)
        self.assertEqual(result["quality"]["pass_at_4"]["estimate"], 1.0)
        self.assertEqual(result["accepted_verified_steps"]["total_weight"], 2.0)
        self.assertEqual(result["efficiency"]["avs_per_second"], 0.5)
        self.assertEqual(result["efficiency"]["avs_per_second_per_gb"], 0.25)
        self.assertEqual(result["efficiency"]["avs_per_dollar"], 2.0)
        self.assertEqual(result["comparison"]["pair_key_count"], 4)
        self.assertEqual(result["comparison"]["discordant_exclusion_count"], 1)

        self.assertEqual(
            aggregate_contracts.validate_aggregate_against_inputs(
                result,
                self.treatment,
                expected_task_ids=TASK_IDS,
                attempts_per_task=2,
                run_provenance=self.treatment_run,
                baseline_trials=self.baseline,
                baseline_run_provenance=self.baseline_run,
                bootstrap_resamples=aggregate_contracts.DEFAULT_BOOTSTRAP_RESAMPLES,
            ),
            result,
        )

    def test_recomputation_rejects_tampered_real_aggregate(self) -> None:
        tampered = copy.deepcopy(self._aggregate())
        tampered["quality"]["pass_at_1"]["estimate"] = 0.5
        with self.assertRaisesRegex(ContractError, "does not match recomputation"):
            aggregate_contracts.validate_aggregate_against_inputs(
                tampered,
                self.treatment,
                expected_task_ids=TASK_IDS,
                attempts_per_task=2,
                run_provenance=self.treatment_run,
                baseline_trials=self.baseline,
                baseline_run_provenance=self.baseline_run,
                bootstrap_resamples=aggregate_contracts.DEFAULT_BOOTSTRAP_RESAMPLES,
            )


if __name__ == "__main__":
    unittest.main()
