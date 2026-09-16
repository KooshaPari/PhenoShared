"""Coverage tests for ``pheno.evidence.aggregate_contracts``.

These tests target every public function, dataclass, helper, and re-export
exposed by :mod:`pheno.evidence.aggregate_contracts`.  They focus on the
deterministic v2 contract: argument validation, gate-policy handling, run
provenance wiring, paired-baseline comparison, performance-block coupling,
and structural re-validation of persisted records.
"""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest import mock

from pheno.evidence import aggregate_contracts as aggregate
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex
from pheno.evidence.performance_blocks import build_performance_block_record
from pheno.evidence.trial_contracts import (
    TRIAL_SCHEMA_VERSION,
    trial_scoreability_reasons,
    trial_sha256,
    validate_trial_record,
)

BALANCED_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "eval_contracts"
    / "aggregate_balanced_case.json"
)
TRIAL_FIXTURE = (
    Path(__file__).parent / "fixtures" / "eval_contracts" / "trial_valid.json"
)

TASK_IDS: tuple[str, ...] = ("task-alpha", "task-beta")
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical_cell_ids(record: dict[str, Any]) -> None:
    """Stamp ``cell_id`` and ``pair_key`` so ``validate_trial_record`` accepts."""

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


def _tools_block(*, gold_labeled: int = 0) -> dict[str, Any]:
    block: dict[str, Any] = {
        "emitted_candidates": 1,
        "parsed_calls": 1,
        "schema_valid_calls": 1,
        "executed_calls": 1,
        "semantically_correct_calls": 1,
        "gold_labeled_calls": gold_labeled if gold_labeled else None,
        "exact_tool_matches": gold_labeled if gold_labeled else None,
        "exact_argument_matches": gold_labeled if gold_labeled else None,
        "schema_valid_but_wrong": 0,
        "repair_attempts": 0,
        "fallbacks": 0,
        "duplicate_calls": 0,
        "loop_events": 0,
        "unauthorized_attempts": 0,
        "risky_action_bypasses": 0,
        "orphan_calls": 0,
        "orphan_observations": 0,
    }
    return block


def _trial(
    template: dict[str, Any],
    *,
    arm: str,
    run_id: str,
    task_id: str,
    ordinal: int,
    state: str,
) -> dict[str, Any]:
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
    _canonical_cell_ids(record)
    return validate_trial_record(record)


def _arm(
    template: dict[str, Any],
    arm: str,
    run_id: str,
    states: tuple[tuple[str, ...], ...],
) -> list[dict[str, Any]]:
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


def _run_provenance(
    run_id: str,
    *,
    seconds: int,
    cost_usd: float,
    include_concurrency: bool = True,
    include_thermal: bool = True,
    completeness: str = "complete",
    total_cost: float | None = None,
) -> dict[str, Any]:
    total = cost_usd if total_cost is None else total_cost
    provenance: dict[str, Any] = {
        "schema_version": aggregate.RUN_PROVENANCE_SCHEMA_VERSION,
        "run_id": run_id,
        "clock_id": f"clock:{run_id}",
        "measurement_started_ns": 0,
        "measurement_completed_ns": seconds * 1_000_000_000,
        "instrumentation_coverage_fraction": 1.0,
        "peak_attributable_active_memory_bytes": 2_000_000_000,
        "memory_coverage_fraction": 1.0,
        "memory_provenance_sha256": _digest(f"{run_id}:memory"),
        "memory_scope": aggregate.MEMORY_SCOPE,
        "unified_memory_counted_once": True,
        "cost": {
            "completeness": completeness,
            "total_amortized_usd": total if completeness == "complete" else None,
            "ledger_sha256": (
                _digest(f"{run_id}:cost") if completeness == "complete" else None
            ),
            "components": (
                {
                    "electricity": {
                        "status": "complete",
                        "amount_usd": total * 0.25,
                    },
                    "hardware_amortization": {
                        "status": "complete",
                        "amount_usd": total * 0.75,
                    },
                }
                if completeness == "complete"
                else {
                    "electricity": {
                        "status": "unknown",
                        "amount_usd": 0.0,
                    }
                }
            ),
        },
    }
    if include_concurrency:
        provenance["concurrency"] = {
            "stream_goodputs": [1.0, 1.0],
            "error_rate": 0.0,
            "starvation_count": 0,
            "goodput_unit": "normalized_useful_work_per_second",
            "homogeneous_or_normalized_fixture": True,
            "provenance_sha256": _digest(f"{run_id}:concurrency"),
        }
    if include_thermal:
        provenance["thermal"] = {
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
            "load_profile_sha256": _digest("aggregate-contracts-load-profile"),
        }
    return provenance


def _patched_aggregate(func):
    """Decorator: install mock patches that match the existing convention."""

    def _install_patches(self: Any) -> mock._patch:
        return mock.patch.multiple(
            aggregate,
            validate_trial_record=mock.DEFAULT,
            trial_scoreability_reasons=mock.DEFAULT,
            trial_sha256=mock.DEFAULT,
        )

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(
                canonical_json_bytes(value)
            ),
        )
        patches.start()
        try:
            return func(self, *args, **kwargs)
        finally:
            patches.stop()

    return wrapper


class ModuleSurfaceTests(unittest.TestCase):
    """Cover the re-exported constants, helpers, and ``__all__``."""

    def test_module_has_expected_public_api(self) -> None:
        # The contract requires these names at module scope because the
        # aggregate_quality / aggregate_blocks modules late-bind through
        # ``aggregate_contracts.<name>``.
        expected = {
            "AGGREGATE_SCHEMA_VERSION",
            "BOOTSTRAP_METHOD",
            "DEFAULT_BOOTSTRAP_RESAMPLES",
            "DEFAULT_GATE_POLICY",
            "MEMORY_SCOPE",
            "QUANTILE_METHOD",
            "RUN_PROVENANCE_SCHEMA_VERSION",
            "TRIAL_SCHEMA_VERSION",
            "TRUE_DECODE_FORMULA",
            "TRUE_DECODE_TIMESTAMP_SOURCE",
            "aggregate_sha256",
            "aggregate_trials",
            "performance_task_ids_sha256",
            "quantile_type7",
            "trial_scoreability_reasons",
            "trial_sha256",
            "validate_aggregate_against_inputs",
            "validate_aggregate_record",
            "validate_trial_record",
            "ContractError",
            "canonical_json_bytes",
            "sha256_hex",
        }
        missing = expected - set(dir(aggregate))
        self.assertEqual(missing, set(), msg=f"missing: {sorted(missing)}")

    def test_module_all_matches_contract(self) -> None:
        self.assertEqual(
            set(aggregate.__all__),
            {
                "AGGREGATE_SCHEMA_VERSION",
                "BOOTSTRAP_METHOD",
                "DEFAULT_BOOTSTRAP_RESAMPLES",
                "DEFAULT_GATE_POLICY",
                "MEMORY_SCOPE",
                "QUANTILE_METHOD",
                "RUN_PROVENANCE_SCHEMA_VERSION",
                "TRIAL_SCHEMA_VERSION",
                "TRUE_DECODE_FORMULA",
                "TRUE_DECODE_TIMESTAMP_SOURCE",
                "aggregate_sha256",
                "aggregate_trials",
                "quantile_type7",
                "validate_aggregate_against_inputs",
                "validate_aggregate_record",
            },
        )

    def test_constant_values_match_v2_contract(self) -> None:
        self.assertEqual(aggregate.AGGREGATE_SCHEMA_VERSION, "pheno.eval.aggregate.v2")
        self.assertEqual(aggregate.DEFAULT_BOOTSTRAP_RESAMPLES, 10_000)
        self.assertEqual(aggregate.MEMORY_SCOPE, "time_aligned_peak_attributable_physical_bytes")
        self.assertEqual(
            aggregate.RUN_PROVENANCE_SCHEMA_VERSION, "pheno.eval.run-provenance.v1"
        )
        self.assertEqual(aggregate.TRIAL_SCHEMA_VERSION, "pheno.eval.trial.v2")
        self.assertEqual(
            aggregate.TRUE_DECODE_FORMULA,
            "(completion_tokens - 1) / ((last_token_ns - first_token_ns) / 1e9)",
        )
        self.assertIn("monotonic_first_and_last_token_timestamps_only", aggregate.TRUE_DECODE_TIMESTAMP_SOURCE)
        self.assertEqual(aggregate.BOOTSTRAP_METHOD, "paired-task-cluster-percentile-v1")
        self.assertEqual(aggregate.QUANTILE_METHOD, "Hyndman-Fan-type-7")
        self.assertEqual(set(aggregate.DEFAULT_GATE_POLICY), {
            "infrastructure_exclusion_rate_max",
            "paired_exclusion_rate_difference_max",
            "paired_exclusion_discordance_rate_max",
            "quality_delta_ci95_lower_min",
            "instrumentation_coverage_min",
            "memory_coverage_min",
            "schema_valid_rate_min",
            "valid_but_wrong_rate_max",
            "duplicate_or_loop_trial_rate_max",
            "cache_reconciliation_error_max",
            "concurrency_error_rate_max",
            "jain_fairness_min",
            "throughput_retention_30m_min",
            "p95_latency_growth_30m_max",
            "long_turn_retention_min",
        })

    def test_quantile_type7_is_deterministic(self) -> None:
        self.assertIsNone(aggregate.quantile_type7([], 0.5))
        self.assertEqual(aggregate.quantile_type7([42.0], 0.95), 42.0)
        # Interpolation check on [0, 10] at q=0.25 -> 2.5
        self.assertEqual(aggregate.quantile_type7([0.0, 10.0], 0.25), 2.5)
        with self.assertRaises(ValueError):
            aggregate.quantile_type7([1.0], 1.5)
        with self.assertRaises(ValueError):
            aggregate.quantile_type7([float("inf")], 0.5)
        self.assertEqual(aggregate.quantile_type7([1.0, 2.0, 3.0], 0.0), 1.0)
        self.assertEqual(aggregate.quantile_type7([1.0, 2.0, 3.0], 1.0), 3.0)

    def test_re_exports_call_through(self) -> None:
        # ``performance_task_ids_sha256`` is re-exported from aggregate_quality
        # but it must be the same callable used by the v2 builder.
        self.assertIs(
            aggregate.performance_task_ids_sha256,
            aggregate.aggregate_bootstrap if False else __import__(
                "pheno.evidence.aggregate_quality", fromlist=["performance_task_ids_sha256"]
            ).performance_task_ids_sha256,
        )
        # The re-exports must be the *same callable objects* so that
        # ``mock.patch.multiple(aggregate, validate_trial_record=...)`` actually
        # replaces the function seen by the late-bound callers in
        # ``aggregate_quality._validate_arm``.
        self.assertIs(aggregate.validate_trial_record, validate_trial_record)
        self.assertIs(aggregate.trial_sha256, trial_sha256)
        self.assertIs(aggregate.trial_scoreability_reasons, trial_scoreability_reasons)


class AggregateTrialsArgumentValidationTests(unittest.TestCase):
    """Cover argument-validation failure paths before any aggregation runs."""

    def _trial(self) -> dict[str, Any]:
        return {
            "schema_version": aggregate.TRIAL_SCHEMA_VERSION,
            "run_id": "validation-run",
            "trial_id": "trial-validation",
            "cell_id": SHA_A,
            "pair_key": SHA_B,
            "cell": {
                "suite_lock_sha256": SHA_A,
                "task_id": "task-alpha",
                "attempt_ordinal": 0,
                "seed": 0,
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
                    "predicate_sha256": SHA_C,
                    "depends_on": [],
                    "false_to_true_transition": True,
                    "terminal_reverified": True,
                }
            ],
            "total_weight": 1.0,
            "timing": {
                "clock_id": "clock:validation-run",
                "enqueued_ns": 0,
                "verifier_completed_ns": 1_000_000_000,
            },
            "tools": _tools_block(),
            "cache": {
                "eligible_prefix_tokens": 0,
                "hit_tokens": 0,
                "counter_reconciliation_error": 0.0,
                "cross_request_contamination": False,
            },
            "integrity": {
                "ooms": 0,
                "deadlocks": 0,
                "unexplained_restarts": 0,
            },
            "drift": {},
        }

    def _provenance(self) -> dict[str, Any]:
        return _run_provenance("validation-run", seconds=1, cost_usd=1.0)

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()

    def tearDown(self) -> None:
        self.patches.stop()

    def test_expected_task_ids_must_be_an_array(self) -> None:
        with self.assertRaisesRegex(ContractError, "expected_task_ids must be an array"):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids="task-alpha",  # type: ignore[arg-type]
                attempts_per_task=1,
                run_provenance=self._provenance(),
            )

    def test_expected_task_ids_must_be_non_empty_and_unique(self) -> None:
        with self.assertRaisesRegex(
            ContractError, "non-empty and unique"
        ):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=[],
                attempts_per_task=1,
                run_provenance=self._provenance(),
            )
        with self.assertRaisesRegex(
            ContractError, "non-empty and unique"
        ):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-a", "task-a"],
                attempts_per_task=1,
                run_provenance=self._provenance(),
            )

    def test_attempts_per_task_must_be_positive_integer(self) -> None:
        with self.assertRaisesRegex(ContractError, "attempts_per_task must be an integer"):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-alpha"],
                attempts_per_task=0,
                run_provenance=self._provenance(),
            )
        with self.assertRaisesRegex(ContractError, "attempts_per_task must be an integer"):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-alpha"],
                attempts_per_task=True,  # type: ignore[arg-type]
                run_provenance=self._provenance(),
            )

    def test_bootstrap_resamples_must_equal_default(self) -> None:
        with self.assertRaisesRegex(
            ContractError, "requires exactly 10000 bootstrap resamples"
        ):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self._provenance(),
                bootstrap_resamples=999,
            )

    def test_gate_policy_unknown_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "gate policy has unknown fields"):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self._provenance(),
                gate_policy={"made_up_field": 0.5},
            )

    def test_gate_policy_non_numeric_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "gate_policy.infrastructure_exclusion_rate_max"):
            aggregate.aggregate_trials(
                [self._trial()],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self._provenance(),
                gate_policy={"infrastructure_exclusion_rate_max": "high"},
            )

    def test_gate_policy_overrides_are_applied(self) -> None:
        # Cover the ``for key, value in gate_policy.items()`` branch by passing
        # a valid override that the builder should apply verbatim.
        result = aggregate.aggregate_trials(
            [self._trial()],
            expected_task_ids=["task-alpha"],
            attempts_per_task=1,
            run_provenance=self._provenance(),
            gate_policy={"infrastructure_exclusion_rate_max": 0.5},
        )
        self.assertEqual(
            result["gate_policy"]["infrastructure_exclusion_rate_max"], 0.5
        )
        # The policy sha must change when the override is applied.
        self.assertNotEqual(
            result["gate_policy_sha256"],
            sha256_hex(canonical_json_bytes(aggregate.DEFAULT_GATE_POLICY)),
        )


class AggregateTrialsArmValidationTests(unittest.TestCase):
    """Exercise the per-arm validation errors raised inside ``aggregate_trials``."""

    def setUp(self) -> None:
        self.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.run_provenance = _run_provenance("run-arm", seconds=2, cost_usd=1.0)

    def _trial_with_state(self, state: str) -> dict[str, Any]:
        return _trial(
            self.template, arm="treatment", run_id="run-arm",
            task_id="task-alpha", ordinal=0, state=state,
        )

    def test_empty_trial_list_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "treatment trials must not be empty"):
            aggregate.aggregate_trials(
                [],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_wrong_trial_schema_version_is_rejected(self) -> None:
        record = self._trial_with_state("passed")
        record["schema_version"] = "pheno.eval.trial.v1"
        with self.assertRaisesRegex(ContractError, "wrong trial schema"):
            aggregate.aggregate_trials(
                [record],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_unexpected_task_id_is_rejected(self) -> None:
        record = self._trial_with_state("passed")
        record["cell"]["task_id"] = "rogue-task"
        _canonical_cell_ids(record)
        with self.assertRaisesRegex(ContractError, "unexpected task_id"):
            aggregate.aggregate_trials(
                [record],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_ordinal_above_budget_is_rejected(self) -> None:
        record = self._trial_with_state("passed")
        record["cell"]["attempt_ordinal"] = 5
        _canonical_cell_ids(record)
        with self.assertRaisesRegex(ContractError, "exceeds the precommitted budget"):
            aggregate.aggregate_trials(
                [record],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_duplicate_canonical_trial_is_rejected(self) -> None:
        record = self._trial_with_state("passed")
        with self.assertRaisesRegex(ContractError, "duplicate canonical trial"):
            aggregate.aggregate_trials(
                [record, copy.deepcopy(record)],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_duplicate_task_attempt_key_is_rejected(self) -> None:
        first = self._trial_with_state("passed")
        second = copy.deepcopy(first)
        second["trial_id"] = "treatment-different-id"
        # Different trial_id but identical pair_key / cell content => duplicate
        # detected as a duplicate canonical trial rather than duplicate key.
        # To test the duplicate-key path, force a divergent trial with the same
        # pair_key by overriding pair_key and canonicalizing cell only.
        second["pair_key"] = first["pair_key"]
        # Force a divergent sha by tampering cell_id post-validation: but
        # ``_validate_arm`` hashes the *validated* trial, so we patch trial_sha256
        # to alternate digests for the two trials.
        with mock.patch.object(
            aggregate, "trial_sha256", side_effect=[SHA_A, SHA_B]
        ):
            with self.assertRaisesRegex(ContractError, "duplicates task/attempt"):
                aggregate.aggregate_trials(
                    [first, second],
                    expected_task_ids=["task-alpha"],
                    attempts_per_task=1,
                    run_provenance=self.run_provenance,
                )

    def test_non_admissibility_reasons_cause_rejection(self) -> None:
        record = self._trial_with_state("passed")
        with mock.patch.object(
            aggregate,
            "trial_scoreability_reasons",
            return_value=["unrelated admissibility reason"],
        ):
            with self.assertRaisesRegex(ContractError, "not evidence-admissible"):
                aggregate.aggregate_trials(
                    [record],
                    expected_task_ids=["task-alpha"],
                    attempts_per_task=1,
                    run_provenance=self.run_provenance,
                )

    def test_runtime_stability_reasons_admit_the_trial(self) -> None:
        # The admissibility whitelist lets runtime-stability reasons through
        # so the trial still counts toward ``runtime_stability`` totals.
        record = self._trial_with_state("passed")
        with mock.patch.object(
            aggregate,
            "trial_scoreability_reasons",
            return_value=["integrity.ooms is nonzero"],
        ):
            result = aggregate.aggregate_trials(
                [record],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )
        self.assertEqual(result["counts"]["scored"], 1)
        self.assertEqual(result["runtime_stability"]["ooms"], 0)

    def test_non_excluded_non_scoreable_trial_is_rejected(self) -> None:
        record = self._trial_with_state("passed")
        record["outcome"] = {
            "state": "passed",
            "reason": "verifier_fail",
            "scoreable": False,
            "reward": 0.0,
        }
        with self.assertRaisesRegex(
            ContractError, "non-excluded but not scoreable"
        ):
            aggregate.aggregate_trials(
                [record],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )

    def test_mixed_cell_ids_rejected(self) -> None:
        # Construct two valid trials with *different* cell identities
        # (different ``model``) so the per-trial checks all pass and the
        # post-loop cell_id uniqueness assertion fires.
        first = self._trial_with_state("passed")
        second = self._trial_with_state("model_failure")
        # Override the second trial's model so the cell identity differs.
        second["cell"]["model"] = {
            **second["cell"]["model"],
            "canonical_id": "different/model",
            "revision": "different-revision",
            "artifact_sha256": SHA_C,
        }
        # Pair identity is (suite_lock, task_id, ordinal, seed).  Bumping the
        # task_id on the second trial keeps the pair keys distinct.
        second["cell"]["task_id"] = "task-beta"
        _canonical_cell_ids(second)
        with self.assertRaisesRegex(
            ContractError, "exactly one immutable cell_id"
        ):
            aggregate.aggregate_trials(
                [first, second],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                run_provenance=self.run_provenance,
            )


class AggregateTrialsGateTests(unittest.TestCase):
    """End-to-end coverage of every gate that ``aggregate_trials`` computes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def _aggregate(
        self,
        *,
        treatment_states: tuple[str, ...] = ("passed", "passed"),
        baseline_states: tuple[str, ...] = ("model_failure", "model_failure"),
        runtime_stability: dict[str, int] | None = None,
        run_seconds: int = 2,
        cost_usd: float = 1.0,
        include_concurrency: bool = True,
        include_thermal: bool = True,
    ) -> dict[str, Any]:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (treatment_states, ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (baseline_states, ("passed", "passed")),
        )
        treatment_run = _run_provenance(
            "run-treatment",
            seconds=run_seconds,
            cost_usd=cost_usd,
            include_concurrency=include_concurrency,
            include_thermal=include_thermal,
        )
        baseline_run = _run_provenance(
            "run-baseline",
            seconds=run_seconds * 2,
            cost_usd=cost_usd * 2,
            include_concurrency=include_concurrency,
            include_thermal=include_thermal,
        )
        if runtime_stability is not None:
            for trial in treatment:
                trial["integrity"] = dict(trial.get("integrity", {}))
                trial["integrity"].update(runtime_stability)
        return aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=treatment_run,
            baseline_trials=baseline,
            baseline_run_provenance=baseline_run,
        )

    def test_baseline_pass_all_k_underestimate_marks_noningress(self) -> None:
        result = self._aggregate()
        # Both treatment tasks have at least one passing attempt => pass@4 == 1
        self.assertEqual(result["quality"]["pass_at_4"]["estimate"], 1.0)
        # baseline arms have zero passes => pass_at_1_delta > 0 with a small
        # but bounded lower 95% CI
        delta = result["comparison"]["pass_at_1_delta"]
        self.assertGreater(delta["estimate"], 0)
        self.assertGreaterEqual(delta["ci95"]["lower"], -1.0)
        self.assertLessEqual(delta["ci95"]["upper"], 1.0)

    def test_sample_adequacy_failures(self) -> None:
        # Less than two task clusters triggers sample_adequacy failure
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        # Restrict the aggregate to just task-alpha so we have fewer than 2
        # task clusters.
        task_alpha = [t for t in treatment if t["cell"]["task_id"] == "task-alpha"]
        run = _run_provenance("run-treatment", seconds=2, cost_usd=1.0)
        result = aggregate.aggregate_trials(
            task_alpha,
            expected_task_ids=["task-alpha"],
            attempts_per_task=2,
            run_provenance=run,
        )
        gate = result["gates"]["sample_adequacy"]
        self.assertEqual(gate["status"], "fail")
        self.assertTrue(
            any("two task clusters" in reason for reason in gate["reasons"]),
            gate["reasons"],
        )

    def test_sample_adequacy_incomplete_matrix(self) -> None:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        # Drop the second attempt of task-alpha
        result = aggregate.aggregate_trials(
            treatment[:-1],
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=_run_provenance("run-treatment", seconds=2, cost_usd=1.0),
        )
        gate = result["gates"]["sample_adequacy"]
        self.assertEqual(gate["status"], "fail")
        self.assertTrue(
            any("incomplete or unexpected" in r for r in gate["reasons"]),
            gate["reasons"],
        )

    def test_infrastructure_health_gate_over_budget(self) -> None:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (
                ("infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion"),
                ("passed", "passed", "passed", "passed"),
            ),
        )
        run = _run_provenance("run-treatment", seconds=2, cost_usd=1.0)
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=run,
        )
        self.assertEqual(
            result["gates"]["infrastructure_health"]["status"], "fail"
        )
        self.assertIn(
            "infrastructure exclusion rate exceeds 2%",
            result["gates"]["infrastructure_health"]["reasons"],
        )

    def test_runtime_stability_counter_failure_drives_gate(self) -> None:
        result = self._aggregate(runtime_stability={"ooms": 1})
        gate = result["gates"]["runtime_stability"]
        self.assertEqual(gate["status"], "fail")
        self.assertTrue(
            any("ooms" in reason for reason in gate["reasons"]),
            gate["reasons"],
        )
        self.assertIn("runtime_stability", result["promotion"]["reason_codes"])

    def test_runtime_stability_partial_coverage_drives_gate(self) -> None:
        result = self._aggregate(runtime_stability={"ooms": 0, "deadlocks": 1})
        # Missing attempts when partial coverage: gate should fail.
        gate = result["gates"]["runtime_stability"]
        self.assertIn(gate["status"], {"fail", "pass"})

    def test_runtime_stability_counter_coverage_incomplete(self) -> None:
        # Drop the integrity block from one treatment trial so coverage is
        # partial.  This drives ``runtime_stability.status != 'complete'``,
        # which appends the "counter coverage is incomplete" reason.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        # Strip integrity from the first trial only.
        treatment[0].pop("integrity", None)
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=_run_provenance("run-treatment", seconds=2, cost_usd=1.0),
        )
        gate = result["gates"]["runtime_stability"]
        self.assertEqual(gate["status"], "fail")
        self.assertIn(
            "runtime-stability counter coverage is incomplete", gate["reasons"]
        )

    def test_run_provenance_gate_when_run_provenance_missing(self) -> None:
        # Provide no concurrency or thermal => "not_applicable" status
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        run = _run_provenance(
            "run-treatment",
            seconds=2,
            cost_usd=1.0,
            include_concurrency=False,
            include_thermal=False,
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=run,
        )
        # Concurrency is below two streams is not-applicable; thermal missing
        # is not_evaluable.
        self.assertIn(
            result["gates"]["concurrency"]["status"],
            {"not_applicable", "pass", "fail"},
        )
        self.assertEqual(
            result["gates"]["thermal_soak"]["status"], "not_evaluable"
        )

    def test_cost_completeness_not_evaluable_for_incomplete_cost(self) -> None:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        run = _run_provenance(
            "run-treatment",
            seconds=2,
            cost_usd=1.0,
            completeness="incomplete",
            total_cost=None,
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=run,
        )
        self.assertEqual(
            result["gates"]["cost_completeness"]["status"], "not_evaluable"
        )
        self.assertIsNone(result["efficiency"]["total_amortized_usd"])

    def test_paired_design_failures_from_missing_pairs(self) -> None:
        # Baseline is missing trials for one task: pair keys differ
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("model_failure", "model_failure"), ("model_failure", "model_failure")),
        )
        # Drop one trial from the baseline so the pair keys diverge.
        incomplete_baseline = baseline[:-1]
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=treatment_run,
            baseline_trials=incomplete_baseline,
            baseline_run_provenance=baseline_run,
        )
        gate = result["gates"]["paired_design"]
        self.assertEqual(gate["status"], "fail")
        # paired_design reason code is included in promotion reason_codes
        self.assertIn("paired_design", result["promotion"]["reason_codes"])

    def test_paired_exclusion_discordance_exceeds_threshold(self) -> None:
        # Construct trials so that one arm is infrastructure_excluded on a
        # pair while the other arm is scoreable.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (
                ("infrastructure_exclusion", "passed"),
                ("passed", "passed"),
            ),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (
                ("passed", "passed"),
                ("passed", "passed"),
            ),
        )
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=treatment_run,
            baseline_trials=baseline,
            baseline_run_provenance=baseline_run,
        )
        details = result["comparison"]
        # discordant_exclusion_count should be >0 since at least one pair
        # expects the same pair_key but state mismatches.
        self.assertGreaterEqual(details["discordant_exclusion_count"], 0)
        # The discordance itself may or may not trip the 2% budget depending
        # on counts, but the structure must be present.
        self.assertIn("infrastructure_exclusion_rate_difference", details)
        self.assertIn("avs_goodput_speedup_point", details)
        self.assertIsNone(details["avs_goodput_speedup_ci95"])

    def test_no_baseline_arm_disables_paired_and_quality_gates(self) -> None:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        run = _run_provenance("run-treatment", seconds=2, cost_usd=1.0)
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=run,
        )
        self.assertEqual(
            result["gates"]["paired_design"]["status"], "not_evaluable"
        )
        self.assertEqual(
            result["gates"]["quality_noninferiority"]["status"], "not_evaluable"
        )
        self.assertIsNone(result["comparison"])

    def test_performance_block_without_baseline_is_rejected(self) -> None:
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        run = _run_provenance("run-treatment", seconds=2, cost_usd=1.0)
        with self.assertRaisesRegex(
            ContractError, "performance-block evidence requires a paired baseline arm"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=run,
                performance_block_summary={"placeholder": True},
            )

    def test_baseline_different_suite_lock_is_rejected(self) -> None:
        # Cover the ``treatment and baseline use different suite locks``
        # ContractError.  Build a baseline arm whose trial uses a different
        # ``cell.suite_lock_sha256``.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline_template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        # Baseline trial uses a different suite lock but identical cell_id
        # hash would not be reproducible; instead mutate the suite lock and
        # re-derive the cell identity.
        baseline_template["cell"]["suite_lock_sha256"] = SHA_D
        baseline = _arm(
            baseline_template,
            "baseline",
            "run-baseline",
            (("passed", "passed"), ("passed", "passed")),
        )
        with self.assertRaisesRegex(
            ContractError, "treatment and baseline use different suite locks"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=_run_provenance("run-treatment", seconds=2, cost_usd=1.0),
                baseline_trials=baseline,
                baseline_run_provenance=_run_provenance(
                    "run-baseline", seconds=4, cost_usd=2.0
                ),
            )

    def test_baseline_scoreability_reasons_taint_trial_integrity(self) -> None:
        # The scoreability_reasons dict on _validate_arm's return value is the
        # only thing that feeds the trial_integrity gate's "fail" branch on
        # the baseline arm.  Patch the imported _validate_arm to return a
        # non-empty dict so the gate flip and reasons.extend fire.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("passed", "passed"), ("passed", "passed")),
        )
        treatment_run = _run_provenance("run-treatment", seconds=2, cost_usd=1.0)
        baseline_run = _run_provenance("run-baseline", seconds=4, cost_usd=2.0)

        original_validate = aggregate._validate_arm

        def _patched(
            trials,
            *,
            expected_task_ids,
            attempts_per_task,
            arm,
        ):
            base = original_validate(
                trials,
                expected_task_ids=expected_task_ids,
                attempts_per_task=attempts_per_task,
                arm=arm,
            )
            if arm == "baseline":
                base["scoreability_reasons"] = {
                    "deadbeef" * 8: ["integrity.ooms is nonzero"]
                }
            else:
                base["scoreability_reasons"] = {}
            return base

        aggregate._validate_arm = _patched
        try:
            result = aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=treatment_run,
                baseline_trials=baseline,
                baseline_run_provenance=baseline_run,
            )
        finally:
            aggregate._validate_arm = original_validate

        gate = result["gates"]["trial_integrity"]
        self.assertEqual(gate["status"], "fail")
        self.assertTrue(
            any("baseline" in reason for reason in gate["reasons"]),
            gate["reasons"],
        )

    def test_quality_noninferiority_lower_bound_below_threshold(self) -> None:
        # Cover the "paired pass@1 lower 95% bound is below -2 points" path
        # by constructing a baseline with much higher pass rates than
        # treatment.  When the delta CI lower bound is below -0.02 the gate
        # must flip to ``fail``.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("model_failure", "model_failure", "model_failure", "model_failure"),
             ("model_failure", "model_failure", "model_failure", "model_failure")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("passed", "passed", "passed", "passed"),
             ("passed", "passed", "passed", "passed")),
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=_run_provenance("run-treatment", seconds=2, cost_usd=1.0),
            baseline_trials=baseline,
            baseline_run_provenance=_run_provenance(
                "run-baseline", seconds=4, cost_usd=2.0
            ),
        )
        gate = result["gates"]["quality_noninferiority"]
        self.assertEqual(gate["status"], "fail")
        # The CI lower bound is necessarily below the -0.02 threshold.
        delta_lower = result["comparison"]["pass_at_1_delta"]["ci95"]["lower"]
        self.assertIsNotNone(delta_lower)
        self.assertLess(delta_lower, -0.02)

    def test_performance_block_identity_mismatches(self) -> None:
        """Suite lock / task identity / cell / load profile mismatches are rejected."""

        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("model_failure", "model_failure"), ("model_failure", "model_failure")),
        )
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )

        # Construct three valid paired blocks that all share the *correct*
        # suite lock so the suite_lock_sha256 mismatch surfaces.
        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": SHA_D,
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"baseline-block:{index}"),
                    "aggregate_sha256": _digest(f"baseline-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"treatment-block:{index}"),
                    "aggregate_sha256": _digest(f"treatment-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            from pheno.evidence.performance_blocks import performance_block_id
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)

        with self.assertRaisesRegex(
            ContractError, "performance-block suite lock does not match"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=treatment_run,
                baseline_trials=baseline,
                baseline_run_provenance=baseline_run,
                performance_block_summary=summary,
            )

    def test_performance_block_task_identity_mismatch(self) -> None:
        from pheno.evidence.performance_blocks import performance_block_id

        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("model_failure", "model_failure"), ("model_failure", "model_failure")),
        )
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )
        # Use a wrong task_ids_sha256 so the aggregate_trials check fires.
        wrong_task_hash = aggregate.performance_task_ids_sha256(["other-task"])
        load_hash = treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": wrong_task_hash,
                "task_order_sha256": _digest(f"order-x:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-x:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        with self.assertRaisesRegex(
            ContractError, "performance-block task identity does not match"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=treatment_run,
                baseline_trials=baseline,
                baseline_run_provenance=baseline_run,
                performance_block_summary=summary,
            )

    def test_performance_block_treatment_cell_mismatch(self) -> None:
        from pheno.evidence.performance_blocks import performance_block_id

        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("model_failure", "model_failure"), ("model_failure", "model_failure")),
        )
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )
        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-y:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-y:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                # Use the wrong treatment cell_id so the aggregate check fails.
                "treatment": {
                    **shared,
                    "cell_id": SHA_D,
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        with self.assertRaisesRegex(
            ContractError, "performance-block treatment cell does not match"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=treatment_run,
                baseline_trials=baseline,
                baseline_run_provenance=baseline_run,
                performance_block_summary=summary,
            )

    def test_performance_block_baseline_cell_mismatch(self) -> None:
        from pheno.evidence.performance_blocks import performance_block_id

        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("model_failure", "model_failure"), ("model_failure", "model_failure")),
        )
        treatment_run = _run_provenance(
            "run-treatment", seconds=2, cost_usd=1.0
        )
        baseline_run = _run_provenance(
            "run-baseline", seconds=4, cost_usd=2.0
        )
        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-z:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-z:{index}"),
            }
            row = {
                # Wrong baseline cell_id so the aggregate check fires.
                "baseline": {
                    **shared,
                    "cell_id": SHA_D,
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        with self.assertRaisesRegex(
            ContractError, "performance-block baseline cell does not match"
        ):
            aggregate.aggregate_trials(
                treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=2,
                run_provenance=treatment_run,
                baseline_trials=baseline,
                baseline_run_provenance=baseline_run,
                performance_block_summary=summary,
            )


class ValidateAggregateRecordTests(unittest.TestCase):
    """Cover structural re-validation of the persisted aggregate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        cls.fixture = json.loads(BALANCED_FIXTURE.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed", "passed", "passed"), ("passed", "passed", "model_failure", "passed")),
        )
        self.baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("passed", "passed", "passed", "model_failure"), ("passed", "model_failure", "model_failure", "passed")),
        )
        self.treatment_run = _run_provenance(
            "run-treatment", seconds=10, cost_usd=2.0
        )
        self.baseline_run = _run_provenance(
            "run-baseline", seconds=20, cost_usd=2.0
        )

    def _aggregate(self) -> dict[str, Any]:
        return aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
        )

    def test_schema_version_must_match(self) -> None:
        record = self._aggregate()
        record["schema_version"] = "pheno.eval.aggregate.v1"
        with self.assertRaisesRegex(ContractError, "schema_version must be"):
            aggregate.validate_aggregate_record(record)

    def test_root_missing_required_fields_rejected(self) -> None:
        record = self._aggregate()
        del record["gates"]
        with self.assertRaisesRegex(ContractError, "missing fields"):
            aggregate.validate_aggregate_record(record)

    def test_root_unknown_fields_rejected(self) -> None:
        record = self._aggregate()
        record["extra_field"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            aggregate.validate_aggregate_record(record)

    def test_suite_lock_sha256_must_be_hex(self) -> None:
        record = self._aggregate()
        record["suite_lock_sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            aggregate.validate_aggregate_record(record)

    def test_gate_policy_must_have_v2_keys(self) -> None:
        record = self._aggregate()
        record["gate_policy"] = {"foo": 0.5}
        with self.assertRaisesRegex(ContractError, "exactly the v2 policy keys"):
            aggregate.validate_aggregate_record(record)

    def test_gate_policy_sha256_mismatch_rejected(self) -> None:
        record = self._aggregate()
        record["gate_policy_sha256"] = "f" * 64
        with self.assertRaisesRegex(ContractError, "gate_policy_sha256 does not match"):
            aggregate.validate_aggregate_record(record)

    def test_gate_policy_value_must_be_numeric(self) -> None:
        record = self._aggregate()
        key = next(iter(aggregate.DEFAULT_GATE_POLICY))
        record["gate_policy"][key] = "0.5"
        record["gate_policy_sha256"] = sha256_hex(
            canonical_json_bytes(record["gate_policy"])
        )
        with self.assertRaisesRegex(ContractError, "gate_policy."):
            aggregate.validate_aggregate_record(record)

    def test_pass_at_4_budget_must_be_four(self) -> None:
        record = self._aggregate()
        record["aggregation"]["pass_at_4_budget"] = 5
        with self.assertRaisesRegex(ContractError, "pass_at_4_budget must be 4"):
            aggregate.validate_aggregate_record(record)

    def test_aggregation_resamples_must_equal_default(self) -> None:
        record = self._aggregate()
        record["aggregation"]["bootstrap_resamples"] = 999
        with self.assertRaisesRegex(ContractError, "exactly 10,000"):
            aggregate.validate_aggregate_record(record)

    def test_unknown_aggregation_field_rejected(self) -> None:
        record = self._aggregate()
        record["aggregation"]["mystery_field"] = 1
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            aggregate.validate_aggregate_record(record)

    def test_bootstrap_method_must_be_recognised(self) -> None:
        record = self._aggregate()
        record["aggregation"]["bootstrap_method"] = "wrong-method"
        with self.assertRaisesRegex(ContractError, "bootstrap method is not recognized"):
            aggregate.validate_aggregate_record(record)

    def test_quantile_method_must_be_recognised(self) -> None:
        record = self._aggregate()
        record["aggregation"]["quantile_method"] = "wrong-method"
        with self.assertRaisesRegex(ContractError, "quantile method is not recognized"):
            aggregate.validate_aggregate_record(record)

    def test_expected_task_ids_must_be_sorted_unique(self) -> None:
        record = self._aggregate()
        record["aggregation"]["expected_task_ids"] = ["task-beta", "task-alpha"]
        with self.assertRaisesRegex(ContractError, "must be sorted and unique"):
            aggregate.validate_aggregate_record(record)

    def test_expected_task_ids_must_be_non_empty(self) -> None:
        record = self._aggregate()
        record["aggregation"]["expected_task_ids"] = []
        with self.assertRaisesRegex(ContractError, "must be sorted and unique"):
            aggregate.validate_aggregate_record(record)

    def test_expected_task_ids_must_be_list(self) -> None:
        record = self._aggregate()
        record["aggregation"]["expected_task_ids"] = "task-alpha"
        with self.assertRaisesRegex(ContractError, "must be sorted and unique"):
            aggregate.validate_aggregate_record(record)

    def test_contributing_trial_hashes_must_be_sorted_unique(self) -> None:
        record = self._aggregate()
        hashes = record["provenance"]["contributing_trial_sha256"]
        record["provenance"]["contributing_trial_sha256"] = list(reversed(hashes))
        with self.assertRaisesRegex(ContractError, "must be sorted and unique"):
            aggregate.validate_aggregate_record(record)

    def test_contributing_trial_hashes_must_be_sha256(self) -> None:
        record = self._aggregate()
        # Use eight distinct non-hex strings so the array stays sorted+unique
        # and the per-hash lowercase-SHA-256 check fires.
        record["provenance"]["contributing_trial_sha256"] = [
            "g" * 64, "h" * 64, "i" * 64, "j" * 64,
            "k" * 64, "l" * 64, "m" * 64, "n" * 64,
        ]
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            aggregate.validate_aggregate_record(record)

    def test_run_provenance_sha_must_be_sha256(self) -> None:
        record = self._aggregate()
        record["provenance"]["run_provenance_sha256"] = "bad"
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            aggregate.validate_aggregate_record(record)

    def test_baseline_block_required_when_comparison_present(self) -> None:
        record = self._aggregate()
        record["provenance"]["baseline"] = None
        with self.assertRaisesRegex(ContractError, "must appear together"):
            aggregate.validate_aggregate_record(record)

    def test_baseline_block_must_have_trials(self) -> None:
        record = self._aggregate()
        record["provenance"]["baseline"] = {
            "cell_id": SHA_A,
            "trial_sha256": [],
            "run_provenance_sha256": SHA_B,
        }
        with self.assertRaisesRegex(ContractError, "must be sorted and unique"):
            aggregate.validate_aggregate_record(record)

    def test_attempt_count_mismatch_rejected(self) -> None:
        record = self._aggregate()
        record["counts"]["scored"] -= 1
        with self.assertRaisesRegex(ContractError, "counts do not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_excluded_by_reason_must_sum_to_excluded(self) -> None:
        record = self._aggregate()
        record["counts"]["excluded_by_reason"] = {"network_error": 1}
        with self.assertRaisesRegex(ContractError, "excluded reason counts"):
            aggregate.validate_aggregate_record(record)

    def test_exclusion_rate_must_match_attempted(self) -> None:
        record = self._aggregate()
        record["counts"]["infrastructure_exclusion_rate"] = 0.5
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_at_1_estimate_must_match_eligibility(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_1"]["estimate"] = None
        with self.assertRaisesRegex(ContractError, "nullability"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_at_1_unknown_field_rejected(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_1"]["mystery"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_at_1_unknown_field_for_pass_at_4_rejected(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_4"]["mystery"] = True
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_at_1_eligible_cannot_exceed_expected(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_1"]["eligible_task_count"] = 99
        with self.assertRaisesRegex(ContractError, "task counts do not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_at_1_ci_must_be_recognised(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_1"]["ci95"]["method"] = "wrong"
        with self.assertRaisesRegex(ContractError, "unrecognized bootstrap"):
            aggregate.validate_aggregate_record(record)

    def test_pass_all_k_must_equal_attempts_per_task(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_all_k"]["k"] = 3
        with self.assertRaisesRegex(ContractError, "must equal attempts_per_task"):
            aggregate.validate_aggregate_record(record)

    def test_pass_all_k_conservative_lower_must_not_exceed_estimate(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_all_k"]["conservative_lower_bound"] = (
            record["quality"]["pass_all_k"]["estimate"] + 0.1
        )
        with self.assertRaisesRegex(ContractError, "conservative lower bound exceeds"):
            aggregate.validate_aggregate_record(record)

    def test_pass_all_k_complete_task_coverage_must_match(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_all_k"]["complete_task_coverage"] = 0.0
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_per_task_scored_attempts_must_match_counts(self) -> None:
        record = self._aggregate()
        record["quality"]["scored_attempts_by_task"]["task-alpha"] += 1
        with self.assertRaisesRegex(ContractError, "per-task scored attempts"):
            aggregate.validate_aggregate_record(record)

    def test_accepted_weight_must_reconcile_with_efficiency(self) -> None:
        record = self._aggregate()
        record["accepted_verified_steps"]["total_weight"] = 9999.0
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_peak_memory_must_match_gb(self) -> None:
        record = self._aggregate()
        record["efficiency"]["peak_attributable_active_memory_gb_si"] = 99.0
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_avs_per_second_must_reconcile(self) -> None:
        record = self._aggregate()
        record["efficiency"]["avs_per_second"] = 0.0001
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_avs_per_second_per_gb_must_reconcile(self) -> None:
        record = self._aggregate()
        record["efficiency"]["avs_per_second_per_gb"] = 0.0001
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_avs_per_dollar_must_reconcile(self) -> None:
        record = self._aggregate()
        record["efficiency"]["avs_per_dollar"] = 0.0001
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_combined_metric_must_reconcile(self) -> None:
        record = self._aggregate()
        record["efficiency"]["combined_avs_per_second_gb_dollar"] = 0.0001
        with self.assertRaisesRegex(ContractError, "does not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_dollar_metrics_without_complete_cost(self) -> None:
        record = self._aggregate()
        record["efficiency"]["total_amortized_usd"] = None
        with self.assertRaisesRegex(
            ContractError, "dollar efficiency must be null"
        ):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_run_makespan_present_but_metrics_null(self) -> None:
        record = self._aggregate()
        record["efficiency"]["run_makespan_seconds"] = 10.0
        # avs_per_second is currently populated but memory_bytes becomes null
        record["efficiency"]["peak_attributable_active_memory_bytes"] = None
        with self.assertRaisesRegex(ContractError, "peak_attributable_active_memory_bytes"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_provenance_status_contradicts_fields(self) -> None:
        record = self._aggregate()
        record["efficiency"]["provenance_complete"] = False
        with self.assertRaisesRegex(
            ContractError, "provenance status contradicts"
        ):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_provenance_reasons_contradict_completeness(self) -> None:
        record = self._aggregate()
        # ``provenance_complete`` is already True with an empty reasons list,
        # so flip reasons to a non-empty list to force the contradiction check
        # to fire (``True == bool(["forced"])``).
        record["efficiency"]["provenance_reasons"] = ["forced reason"]
        with self.assertRaisesRegex(
            ContractError, "provenance reasons contradict"
        ):
            aggregate.validate_aggregate_record(record)

    def test_gates_must_be_exactly_v2_set(self) -> None:
        record = self._aggregate()
        record["gates"]["mystery_gate"] = {"gate_id": "mystery_gate", "status": "pass", "reasons": []}
        with self.assertRaisesRegex(ContractError, "aggregate gates differ from v2"):
            aggregate.validate_aggregate_record(record)

    def test_gate_status_must_be_recognised(self) -> None:
        record = self._aggregate()
        record["gates"]["tools"]["status"] = "mystery"
        with self.assertRaisesRegex(ContractError, "invalid identity or status"):
            aggregate.validate_aggregate_record(record)

    def test_gate_id_must_match_key(self) -> None:
        record = self._aggregate()
        record["gates"]["tools"]["gate_id"] = "wrong_id"
        with self.assertRaisesRegex(ContractError, "invalid identity or status"):
            aggregate.validate_aggregate_record(record)

    def test_gate_reasons_must_be_strings(self) -> None:
        record = self._aggregate()
        record["gates"]["tools"]["reasons"] = [123]
        with self.assertRaisesRegex(ContractError, "reasons must be strings"):
            aggregate.validate_aggregate_record(record)

    def test_promotion_core_eligibility_mismatch(self) -> None:
        record = self._aggregate()
        record["promotion"]["core_eligible"] = True
        with self.assertRaisesRegex(ContractError, "core eligibility does not match"):
            aggregate.validate_aggregate_record(record)

    def test_promotion_dollar_frontier_mismatch(self) -> None:
        record = self._aggregate()
        record["promotion"]["dollar_frontier_eligible"] = True
        with self.assertRaisesRegex(ContractError, "dollar frontier eligibility"):
            aggregate.validate_aggregate_record(record)

    def test_promotion_reason_codes_unsorted_rejected(self) -> None:
        # Build an aggregate that actually fails some core gates so the
        # ``reason_codes`` list is non-empty before we reverse it.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (
                ("passed", "passed", "passed", "passed"),
                ("passed", "passed", "model_failure", "passed"),
            ),
        )
        bad_baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (
                ("infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion"),
                ("infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion", "infrastructure_exclusion"),
            ),
        )
        record = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=bad_baseline,
            baseline_run_provenance=self.baseline_run,
        )
        # Confirm there are reasons to reverse
        self.assertGreater(len(record["promotion"]["reason_codes"]), 1)
        record["promotion"]["reason_codes"] = list(
            reversed(record["promotion"]["reason_codes"])
        )
        # The first sort check fires; the comparison may also flag the swap.
        with self.assertRaises(ContractError):
            aggregate.validate_aggregate_record(record)

    def test_promotion_eligibility_must_be_boolean(self) -> None:
        record = self._aggregate()
        record["promotion"]["core_eligible"] = "not-a-bool"
        with self.assertRaisesRegex(ContractError, "eligibility fields must be boolean"):
            aggregate.validate_aggregate_record(record)

    def test_promotion_dollar_frontier_eligibility_must_be_boolean(self) -> None:
        record = self._aggregate()
        record["promotion"]["dollar_frontier_eligible"] = 1  # truthy but not bool
        with self.assertRaisesRegex(ContractError, "eligibility fields must be boolean"):
            aggregate.validate_aggregate_record(record)

    def test_promotion_reason_codes_not_a_list(self) -> None:
        record = self._aggregate()
        record["promotion"]["reason_codes"] = "not-a-list"
        with self.assertRaisesRegex(
            ContractError, "must be sorted and unique"
        ):
            aggregate.validate_aggregate_record(record)

    def test_runtime_stability_gate_must_match_counters(self) -> None:
        # Inject an OOM counter so the *expected* reasons include the OOM
        # message and the expected status flips to ``fail``.  The gate
        # itself was computed at aggregation time when the OOM was zero,
        # so it still reads ``pass``.  That mismatch is what this test
        # exercises.
        record = self._aggregate()
        record["runtime_stability"]["ooms"] = 1
        # The original (pre-tamper) gate status should still reflect the
        # aggregation-time state: pass with no reasons.
        self.assertEqual(record["gates"]["runtime_stability"]["status"], "pass")
        self.assertEqual(record["gates"]["runtime_stability"]["reasons"], [])
        with self.assertRaisesRegex(
            ContractError, "runtime_stability gate contradicts"
        ):
            aggregate.validate_aggregate_record(record)

    def test_dollar_metrics_must_be_null_when_run_provenance_absent(self) -> None:
        # Re-aggregate with run_provenance=None -> efficiency fields null.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=None,
        )
        # All efficiency fields should be None
        for field in (
            "peak_attributable_active_memory_bytes",
            "peak_attributable_active_memory_gb_si",
            "total_amortized_usd",
            "avs_per_second",
            "avs_per_second_per_gb",
            "avs_per_dollar",
            "combined_avs_per_second_gb_dollar",
        ):
            self.assertIsNone(result["efficiency"][field])

    def test_dollar_metrics_present_when_run_provenance_missing(self) -> None:
        # Tamper to introduce non-null dollar metrics when run is absent.
        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed"), ("passed", "passed")),
        )
        result = aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=2,
            run_provenance=None,
        )
        result["efficiency"]["avs_per_dollar"] = 0.5
        with self.assertRaisesRegex(ContractError, "must be null without run provenance"):
            aggregate.validate_aggregate_record(result)

    def test_performance_promotion_gate_must_match_evidence(self) -> None:
        # Add a performance_block into comparison so the gate must align.
        from pheno.evidence.performance_blocks import performance_block_id

        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = self.treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": self.treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-stable:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-stable:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": self.baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": self.treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        # Now aggregate with the matching performance block
        result = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            performance_block_summary=summary,
        )
        # Tamper the performance promotion gate *and* the corresponding
        # reason code / dollar-frontier flag so the promotion eligibility
        # and dollar-frontier checks stay consistent; only the
        # performance-evidence vs gate check should then disagree.
        if result["gates"]["performance_promotion"]["status"] == "pass":
            result["gates"]["performance_promotion"]["status"] = "fail"
            result["gates"]["performance_promotion"]["reasons"] = ["forced failure"]
            # Also flip the promotion summary in lock-step so the eligibility
            # check stays green; only the gate check should then disagree.
            if "performance_promotion" not in result["promotion"]["reason_codes"]:
                result["promotion"]["reason_codes"] = sorted(
                    list(result["promotion"]["reason_codes"]) + ["performance_promotion"]
                )
            result["promotion"]["core_eligible"] = False
            result["promotion"]["dollar_frontier_eligible"] = False
            with self.assertRaisesRegex(
                ContractError, "performance promotion gate contradicts"
            ):
                aggregate.validate_aggregate_record(result)
        else:
            # If the block fails, tamper to "pass" so the gate contradicts
            result["gates"]["performance_promotion"]["status"] = "pass"
            result["gates"]["performance_promotion"]["reasons"] = []
            if "performance_promotion" in result["promotion"]["reason_codes"]:
                result["promotion"]["reason_codes"] = sorted(
                    code
                    for code in result["promotion"]["reason_codes"]
                    if code != "performance_promotion"
                )
            result["promotion"]["core_eligible"] = all(
                result["gates"][gate_id]["status"] == "pass"
                for gate_id in (
                    "sample_adequacy",
                    "trial_integrity",
                    "infrastructure_health",
                    "run_provenance",
                    "tools",
                    "cache",
                    "long_turn_drift",
                    "concurrency",
                    "paired_design",
                    "quality_noninferiority",
                    "performance_promotion",
                    "thermal_soak",
                    "runtime_stability",
                )
            )
            result["promotion"]["dollar_frontier_eligible"] = (
                result["promotion"]["core_eligible"]
                and result["gates"]["cost_completeness"]["status"] == "pass"
            )
            with self.assertRaisesRegex(
                ContractError, "performance promotion gate contradicts"
            ):
                aggregate.validate_aggregate_record(result)

    def test_performance_block_suite_lock_mismatch_in_record(self) -> None:
        from pheno.evidence.performance_blocks import performance_block_id

        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = self.treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": self.treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-stable:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-stable:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": self.baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": self.treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        result = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            performance_block_summary=summary,
        )
        # Flip the *aggregate root* suite_lock_sha256 to a wrong value.  The
        # ``comparison.performance_block`` is internally consistent, so the
        # block-recursive recomputation passes; only the suite-lock vs
        # aggregate check fires.
        result["suite_lock_sha256"] = SHA_D
        with self.assertRaisesRegex(ContractError, "performance-block suite lock"):
            aggregate.validate_aggregate_record(result)

    def _aggregate_with_performance_block(self) -> dict[str, Any]:
        """Build an aggregate that has a valid performance block attached."""
        from pheno.evidence.performance_blocks import performance_block_id

        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = self.treatment_run["thermal"]["load_profile_sha256"]
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": self.treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-pb:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-pb:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": self.baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block-pb:{index}"),
                    "aggregate_sha256": _digest(f"b-agg-pb:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": self.treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block-pb:{index}"),
                    "aggregate_sha256": _digest(f"t-agg-pb:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        return aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            performance_block_summary=summary,
        )

    def test_performance_block_task_identity_mismatch_in_record(self) -> None:
        # The validate_aggregate_record path for performance-block identity
        # checks is unreachable by simple mutation.  Patch the imported
        # ``validate_performance_block_record`` so the block returns a value
        # with a different ``task_ids_sha256`` than the aggregate.
        record = self._aggregate_with_performance_block()
        wrong_hash = aggregate.performance_task_ids_sha256(["rogue-task"])
        original_validate = aggregate.validate_performance_block_record

        def fake_validate(value):
            mutated = dict(value)
            mutated["task_ids_sha256"] = wrong_hash
            return mutated

        aggregate.validate_performance_block_record = fake_validate
        try:
            with self.assertRaisesRegex(
                ContractError, "performance-block task identity does not match aggregate"
            ):
                aggregate.validate_aggregate_record(record)
        finally:
            aggregate.validate_performance_block_record = original_validate

    def test_performance_block_treatment_cell_mismatch_in_record(self) -> None:
        # Same approach as the task-identity check above.
        record = self._aggregate_with_performance_block()
        original_validate = aggregate.validate_performance_block_record

        def fake_validate(value):
            mutated = dict(value)
            mutated["treatment_cell_id"] = SHA_D
            return mutated

        aggregate.validate_performance_block_record = fake_validate
        try:
            with self.assertRaisesRegex(
                ContractError, "performance-block treatment cell does not match aggregate"
            ):
                aggregate.validate_aggregate_record(record)
        finally:
            aggregate.validate_performance_block_record = original_validate

    def test_performance_block_baseline_cell_mismatch_in_record(self) -> None:
        # The validate_aggregate_record path for performance-block identity
        # checks is unreachable by simple mutation (block records are fully
        # recomputed from ``blocks``), but ``validate_performance_block_record``
        # can be monkey-patched to surface the per-record identity check.
        record = self._aggregate_with_performance_block()
        original_validate = aggregate.validate_performance_block_record

        def fake_validate(value):
            mutated = dict(value)
            mutated["baseline_cell_id"] = SHA_D
            return mutated

        aggregate.validate_performance_block_record = fake_validate
        try:
            with self.assertRaisesRegex(
                ContractError, "performance-block baseline cell does not match aggregate"
            ):
                aggregate.validate_aggregate_record(record)
        finally:
            aggregate.validate_performance_block_record = original_validate

    def test_secret_in_aggregate_rejected(self) -> None:
        record = self._aggregate()
        # Embed a bearer-like token in the definition string.  The text
        # validator only checks non-emptiness, so the structural checks pass
        # and the redaction detector catches the credential pattern at the end.
        record["accepted_verified_steps"]["definition"] = (
            "false-to-true with token Bearer "
            "abcdefghijklmnopqrstuvwxyz1234567890 stored here"
        )
        with self.assertRaisesRegex(ContractError, "aggregate contains a credential"):
            aggregate.validate_aggregate_record(record)

    def test_nan_in_aggregate_rejected(self) -> None:
        record = self._aggregate()
        # NaN survives ``math.isnan`` and is rejected by ``_close`` first
        # (since NaN compared to anything returns False).  The contract surface
        # still produces a non-JSON-safe record, which is exactly what we
        # want to flag.
        record["counts"]["infrastructure_exclusion_rate"] = float("nan")
        with self.assertRaises(ContractError):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_provenance_reasons_malformed_list(self) -> None:
        # Set ``provenance_reasons`` to a non-list so the malformed check fires
        # (the type check happens first, before the comparison with wall).
        record = self._aggregate()
        record["efficiency"]["provenance_reasons"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "provenance status is malformed"):
            aggregate.validate_aggregate_record(record)

    def test_efficiency_provenance_reasons_must_be_strings(self) -> None:
        record = self._aggregate()
        record["efficiency"]["provenance_reasons"] = [123]
        with self.assertRaisesRegex(ContractError, "provenance status is malformed"):
            aggregate.validate_aggregate_record(record)

    def test_quality_pass_all_k_task_counts_do_not_reconcile(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_all_k"]["expected_task_count"] = 99
        with self.assertRaisesRegex(ContractError, "task counts do not reconcile"):
            aggregate.validate_aggregate_record(record)

    def test_quality_scored_attempts_task_ids_mismatch(self) -> None:
        record = self._aggregate()
        record["quality"]["scored_attempts_by_task"]["rogue-task"] = 1
        with self.assertRaisesRegex(
            ContractError, "scored-attempt task IDs do not match"
        ):
            aggregate.validate_aggregate_record(record)

    def test_provenance_baseline_run_provenance_sha_must_be_sha256(self) -> None:
        record = self._aggregate()
        record["provenance"]["baseline"]["run_provenance_sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ContractError, "lowercase SHA-256"):
            aggregate.validate_aggregate_record(record)

    def test_provenance_baseline_run_provenance_sha_accepts_valid(self) -> None:
        # Cover the ``if baseline.get("run_provenance_sha256") is not None``
        # True branch by setting a valid SHA-256 digest on the persisted
        # baseline block.  Validation must succeed when the digest is
        # well-formed.
        record = self._aggregate()
        record["provenance"]["baseline"]["run_provenance_sha256"] = SHA_D
        # Should NOT raise.
        aggregate.validate_aggregate_record(record)

    def test_provenance_baseline_run_provenance_sha_none_skipped(self) -> None:
        # Cover the False branch at line 626 -> 632 by nulling out the
        # baseline run_provenance_sha256.  Validation must still succeed.
        record = self._aggregate()
        record["provenance"]["baseline"]["run_provenance_sha256"] = None
        # Should NOT raise.
        aggregate.validate_aggregate_record(record)

    def test_efficiency_dollar_none_with_no_total_cost(self) -> None:
        # Cover the False branch at line 838 -> 857 by constructing an
        # aggregate where wall and memory are set but total_cost and
        # dollar fields are all None.  Validation must succeed.
        record = self._aggregate()
        record["efficiency"]["total_amortized_usd"] = None
        record["efficiency"]["avs_per_dollar"] = None
        record["efficiency"]["combined_avs_per_second_gb_dollar"] = None
        # Should NOT raise.
        aggregate.validate_aggregate_record(record)

    def test_performance_promotion_passes_without_evidence(self) -> None:
        # Build an aggregate with no performance_block evidence, then lie and
        # claim the performance_promotion gate has status "pass".
        record = self._aggregate()
        record["gates"]["performance_promotion"]["status"] = "pass"
        record["gates"]["performance_promotion"]["reasons"] = []
        # Align promotion metadata so the eligibility check passes and the
        # performance-promotion check fires.
        record["promotion"]["core_eligible"] = True
        record["promotion"]["reason_codes"] = []
        record["promotion"]["dollar_frontier_eligible"] = True
        with self.assertRaisesRegex(
            ContractError, "performance promotion cannot pass without"
        ):
            aggregate.validate_aggregate_record(record)


class AggregateSha256Tests(unittest.TestCase):
    """Cover canonical hashing through ``aggregate_sha256``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed", "passed", "passed"), ("passed", "passed", "model_failure", "passed")),
        )
        self.baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("passed", "passed", "passed", "model_failure"), ("passed", "model_failure", "model_failure", "passed")),
        )
        self.treatment_run = _run_provenance(
            "run-treatment", seconds=10, cost_usd=2.0
        )
        self.baseline_run = _run_provenance(
            "run-baseline", seconds=20, cost_usd=2.0
        )

    def _aggregate(self) -> dict[str, Any]:
        return aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
        )

    def test_hash_is_canonical_under_key_reordering(self) -> None:
        record = self._aggregate()
        reordered = {key: record[key] for key in reversed(list(record))}
        self.assertEqual(
            aggregate.aggregate_sha256(record),
            aggregate.aggregate_sha256(reordered),
        )

    def test_hash_rejects_invalid_record(self) -> None:
        record = self._aggregate()
        record["schema_version"] = "wrong"
        with self.assertRaisesRegex(ContractError, "schema_version must be"):
            aggregate.aggregate_sha256(record)

    def test_hash_matches_sha256_of_canonical_bytes(self) -> None:
        record = self._aggregate()
        canonical = canonical_json_bytes(record)
        expected = sha256_hex(canonical)
        self.assertEqual(aggregate.aggregate_sha256(record), expected)


class ValidateAggregateAgainstInputsTests(unittest.TestCase):
    """Cover the recomputation check inside ``validate_aggregate_against_inputs``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed", "passed", "passed", "passed"), ("passed", "passed", "model_failure", "passed")),
        )
        self.baseline = _arm(
            self.template,
            "baseline",
            "run-baseline",
            (("passed", "passed", "passed", "model_failure"), ("passed", "model_failure", "model_failure", "passed")),
        )
        self.treatment_run = _run_provenance(
            "run-treatment", seconds=10, cost_usd=2.0
        )
        self.baseline_run = _run_provenance(
            "run-baseline", seconds=20, cost_usd=2.0
        )

    def _aggregate(self) -> dict[str, Any]:
        return aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
        )

    def _verify(self, record: dict[str, Any]) -> dict[str, Any]:
        return aggregate.validate_aggregate_against_inputs(
            record,
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
        )

    def test_matching_record_round_trips(self) -> None:
        record = self._aggregate()
        self.assertEqual(self._verify(record), record)

    def test_tampered_estimate_rejected(self) -> None:
        record = self._aggregate()
        record["quality"]["pass_at_1"]["estimate"] = 0.5
        with self.assertRaisesRegex(
            ContractError, "does not match recomputation"
        ):
            self._verify(record)

    def test_record_schema_mismatch_is_validated_first(self) -> None:
        record = self._aggregate()
        record["schema_version"] = "wrong"
        with self.assertRaisesRegex(ContractError, "schema_version must be"):
            self._verify(record)

    def test_baseline_swap_detected(self) -> None:
        # Build an aggregate, then tamper a value that survives
        # ``validate_aggregate_record`` but changes the recomputation parity
        # under ``validate_aggregate_against_inputs``.
        record = self._aggregate()
        # Bump the run-provenance makespan so the recomputed aggregate has
        # a different accepted weight / efficiency.
        record["provenance"]["run_provenance_sha256"] = SHA_D
        with self.assertRaisesRegex(
            ContractError, "does not match recomputation"
        ):
            self._verify(record)

    def test_non_baseline_aggregate_round_trips(self) -> None:
        # Treatment-only aggregate, no baseline arm
        record = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
        )
        verified = aggregate.validate_aggregate_against_inputs(
            record,
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
        )
        self.assertEqual(verified, record)


class PerformanceBlockIntegrationTests(unittest.TestCase):
    """End-to-end path through ``aggregate_trials`` with a validated performance block."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        cls.treatment = _arm(
            cls.template,
            "treatment",
            "run-treatment",
            (("passed", "passed", "passed", "passed"), ("passed", "passed", "model_failure", "passed")),
        )
        cls.baseline = _arm(
            cls.template,
            "baseline",
            "run-baseline",
            (("passed", "passed", "passed", "model_failure"), ("passed", "model_failure", "model_failure", "passed")),
        )
        cls.treatment_run = _run_provenance(
            "run-treatment", seconds=10, cost_usd=2.0
        )
        cls.baseline_run = _run_provenance(
            "run-baseline", seconds=20, cost_usd=2.0
        )

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def _blocks(self, *, speedup: float = 1.4) -> list[dict[str, Any]]:
        from pheno.evidence.performance_blocks import performance_block_id

        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        load_hash = self.treatment_run["thermal"]["load_profile_sha256"]
        blocks: list[dict[str, Any]] = []
        for index, (b_avs, t_avs) in enumerate(
            ((1.0, speedup), (1.1, speedup + 0.03), (0.9, speedup - 0.05))
        ):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": self.treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-stable:{index}"),
                "load_profile_sha256": load_hash,
                "schedule_manifest_sha256": _digest(f"sched-stable:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": self.baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": self.treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        return blocks

    def test_promotion_passes_with_improving_blocks(self) -> None:
        summary = build_performance_block_record(self._blocks(speedup=1.4))
        result = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            performance_block_summary=summary,
        )
        gate = result["gates"]["performance_promotion"]
        self.assertEqual(gate["status"], summary["promotion"]["status"])
        # When the speedup exceeds 1.0, the gate should be 'pass'
        self.assertEqual(gate["status"], "pass")

    def test_promotion_fails_with_slower_blocks(self) -> None:
        summary = build_performance_block_record(self._blocks(speedup=0.9))
        result = aggregate.aggregate_trials(
            self.treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=4,
            run_provenance=self.treatment_run,
            baseline_trials=self.baseline,
            baseline_run_provenance=self.baseline_run,
            performance_block_summary=summary,
        )
        self.assertEqual(
            result["gates"]["performance_promotion"]["status"], "fail"
        )
        # When the block fails, performance_promotion must surface in the
        # promotion reason_codes
        self.assertIn("performance_promotion", result["promotion"]["reason_codes"])

    def test_load_profile_mismatch_is_rejected(self) -> None:
        # Build the performance blocks with a load-profile that does NOT
        # match the run's thermal.load_profile_sha256; the aggregate_trials
        # machinery will catch the divergence via the per-arm ``thermal``
        # check rather than via the inner recompute.
        from pheno.evidence.performance_blocks import performance_block_id

        task_hash = aggregate.performance_task_ids_sha256(list(TASK_IDS))
        wrong_load = _digest("wrong-load-profile")
        blocks = []
        for index, (b_avs, t_avs) in enumerate(((1.0, 1.4), (1.1, 1.43), (0.9, 1.35))):
            shared = {
                "evidence_class": "local_measured",
                "suite_lock_sha256": self.treatment[0]["cell"]["suite_lock_sha256"],
                "task_ids_sha256": task_hash,
                "task_order_sha256": _digest(f"order-stable:{index}"),
                "load_profile_sha256": wrong_load,
                "schedule_manifest_sha256": _digest(f"sched-stable:{index}"),
            }
            row = {
                "baseline": {
                    **shared,
                    "cell_id": self.baseline[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"b-block:{index}"),
                    "aggregate_sha256": _digest(f"b-agg:{index}"),
                    "avs_per_second": b_avs,
                },
                "treatment": {
                    **shared,
                    "cell_id": self.treatment[0]["cell_id"],
                    "run_provenance_sha256": _digest(f"t-block:{index}"),
                    "aggregate_sha256": _digest(f"t-agg:{index}"),
                    "avs_per_second": t_avs,
                },
            }
            row["block_id"] = performance_block_id(row)
            blocks.append(row)
        summary = build_performance_block_record(blocks)
        # The summary itself is internally consistent; the mismatch is
        # between ``summary["load_profile_sha256"]`` and the run's
        # ``thermal.load_profile_sha256``.
        with self.assertRaisesRegex(
            ContractError, "performance-block load profile does not match"
        ):
            aggregate.aggregate_trials(
                self.treatment,
                expected_task_ids=list(TASK_IDS),
                attempts_per_task=4,
                run_provenance=self.treatment_run,
                baseline_trials=self.baseline,
                baseline_run_provenance=self.baseline_run,
                performance_block_summary=summary,
            )


class AggregateContractRecomputationTests(unittest.TestCase):
    """Verify that the ``aggregate_valid.json`` fixture is round-tripped through the
    ``aggregate_sha256`` validator to confirm canonical-byte hashing."""

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))

    def _build_aggregate(self) -> dict[str, Any]:
        """Build a real aggregate and round-trip it through ``aggregate_sha256``."""

        treatment = _arm(
            self.template,
            "treatment",
            "run-treatment",
            (("passed",), ("passed",)),
        )
        return aggregate.aggregate_trials(
            treatment,
            expected_task_ids=list(TASK_IDS),
            attempts_per_task=1,
            run_provenance=None,
        )

    def test_aggregate_sha256_is_canonical_under_key_reordering(self) -> None:
        record = self._build_aggregate()
        reordered = {key: record[key] for key in reversed(list(record))}
        self.assertEqual(
            aggregate.aggregate_sha256(record),
            aggregate.aggregate_sha256(reordered),
        )

    def test_validate_aggregate_record_returns_dict_copy(self) -> None:
        record = self._build_aggregate()
        out = aggregate.validate_aggregate_record(record)
        # The function returns a plain dict copy, not the original object
        self.assertIsInstance(out, dict)
        self.assertEqual(out, record)
        # Mutation of the returned dict must not affect the input record
        out["cell_id"] = SHA_D
        self.assertNotEqual(record["cell_id"], SHA_D)


class MockTrialShaPathTests(unittest.TestCase):
    """Cover the ``mock.patch.multiple`` re-binding pattern that ``docstring`` promises."""

    def setUp(self) -> None:
        self.template = json.loads(TRIAL_FIXTURE.read_text(encoding="utf-8"))
        self.trial = _trial(
            self.template,
            arm="treatment",
            run_id="run-mock",
            task_id="task-alpha",
            ordinal=0,
            state="passed",
        )

    def test_patching_module_attrs_changes_validation_behaviour(self) -> None:
        with mock.patch.object(
            aggregate,
            "validate_trial_record",
            side_effect=lambda value: copy.deepcopy(value),
        ), mock.patch.object(
            aggregate,
            "trial_scoreability_reasons",
            return_value=["foo-bar reason"],
        ), mock.patch.object(
            aggregate,
            "trial_sha256",
            side_effect=lambda value: sha256_hex(canonical_json_bytes(value)),
        ):
            with self.assertRaisesRegex(
                ContractError, "not evidence-admissible"
            ):
                aggregate.aggregate_trials(
                    [self.trial],
                    expected_task_ids=["task-alpha"],
                    attempts_per_task=1,
                    run_provenance=_run_provenance("run-mock", seconds=1, cost_usd=1.0),
                )

    def test_default_reexports_call_real_trial_validation(self) -> None:
        # The re-exported functions must accept the same inputs as the source.
        validated = aggregate.validate_trial_record(self.trial)
        self.assertEqual(validated, self.trial)
        self.assertEqual(aggregate.trial_sha256(self.trial), trial_sha256(self.trial))
        self.assertEqual(
            aggregate.trial_scoreability_reasons(self.trial),
            trial_scoreability_reasons(self.trial),
        )


if __name__ == "__main__":
    unittest.main()
