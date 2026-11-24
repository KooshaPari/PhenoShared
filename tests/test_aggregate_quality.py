"""Coverage tests for ``pheno.evidence.aggregate_quality``.

This module owns per-trial summarization that feeds ``aggregate_trials``:
quality (pass-at-1/4/k), latency, tools, cache, drift, runtime-stability,
paired-comparison deltas, and the trial-arm validation primitives.  These
tests pin each private helper and exhaustively enumerate every documented
branch:

* schema helpers (``_mapping``, ``_text``, ``_integer``, ``_number``,
  ``_sha256``) — type guards, finite/positive bounds, exact-length checks;
* trial extractors and scoreability — ordinal ordering, score-state table;
* ``_accepted_weight`` — duplicates, dependency cycles, missing deps,
  total-weight reconciliation, infrastructure-exclusion zero-weight rule;
* ``_validate_arm`` — every failure path (empty, schema, duplicates,
  ordinals, pair_keys, cell_ids, suite_locks, run_ids, admissibility,
  non-excluded non-scoreable);
* ``_counts`` — state buckets and infrastructure-exclusion rate;
* ``_quality`` — pass-at-1/4/k estimates, bootstrap seeds, ci95 metadata;
* ``_paired_comparison`` — task/ordinal/seed mismatches, discordant
  exclusions, paired-only estimates;
* ``_summarize_tools`` — coverage, parse/schema/semantic/exact rates,
  partial/complete/missing status, labelled-vs-open-ended branches;
* ``_summarize_latency`` — timing/tokens gating, decode-throughput
  formula, type-7 quantiles;
* ``_summarize_cache`` — coverage, contamination, error max, status;
* ``_summarize_drift`` — manifest unification, checkpoint turns,
  retention-retained <= expected, retention totals;
* ``_summarize_runtime_stability`` — coverage and counter totals;
* module constants: ``RUNTIME_STABILITY_FIELDS``, decoded formulae.

The private ``_validate_arm`` late-binds ``aggregate_contracts`` from
inside its body, so this file follows the existing convention of
``mock.patch.multiple`` on the ``aggregate_contracts`` module to keep
fixtures terse.
"""

from __future__ import annotations

import copy
import hashlib
import unittest
from typing import Any
from unittest import mock

from pheno.evidence import aggregate_contracts
from pheno.evidence import aggregate_quality as quality
from pheno.evidence.aggregate_quality import (
    _RUNTIME_STABILITY_FIELDS,
    BOOTSTRAP_METHOD,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    QUANTILE_METHOD,
    TRUE_DECODE_FORMULA,
    TRUE_DECODE_TIMESTAMP_SOURCE,
    _accepted_weight,
    _counts,
    _distribution,
    _paired_comparison,
    _quality,
    _scoreable,
    _summarize_cache,
    _summarize_drift,
    _summarize_latency,
    _summarize_runtime_stability,
    _summarize_tools,
    _trial_ordinal,
    _trial_state,
    _trial_task,
    _validate_arm,
    performance_task_ids_sha256,
)
from pheno.evidence.contracts import ContractError, canonical_json_bytes, sha256_hex

# A fixed-suite-lock and pair-key used by every fixture builder.
SUITE_LOCK = "a" * 64
RUN_ID = "run-fixture"
CELL_ID = "b" * 64
TRIAL_SCHEMA = "pheno.eval.trial.v2"

DEFAULT_PATCHES = mock.patch.multiple(
    aggregate_contracts,
    validate_trial_record=lambda value: copy.deepcopy(value),
    trial_scoreability_reasons=lambda value: [],
    trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _outcome(state: str) -> dict:
    """Build a scoreable outcome dict for the given state."""
    return {
        "state": state,
        "reason": "verified" if state == "passed" else "verifier_fail",
        "scoreable": state != "infrastructure_exclusion",
    }


def _accepted_step(step_id: str = "task-pass", weight: float = 1.0) -> dict:
    return {
        "step_id": step_id,
        "weight": weight,
        "depends_on": [],
        "false_to_true_transition": True,
        "terminal_reverified": True,
    }


def _trial(
    task_id: str = "task-alpha",
    ordinal: int = 0,
    *,
    state: str = "passed",
    run_id: str = RUN_ID,
    cell_id: str = CELL_ID,
    suite_lock: str = SUITE_LOCK,
    pair_key: str | None = None,
    accepted_steps: list[dict] | None = None,
    total_weight: float | None = None,
    tools: dict | None = None,
    cache: dict | None = None,
    timing: dict | None = None,
    tokens: dict | None = None,
    integrity: dict | None = None,
    drift: dict | None = None,
    artifacts: dict | None = None,
    cost: dict | None = None,
    intent_graph: Any = None,
    atif_trajectory: Any = None,
    verifier_outputs: Any = None,
    resources: dict | None = None,
    schema_version: str = TRIAL_SCHEMA,
) -> dict:
    """Build a minimal trial dict consistent with the v2 trial contract."""
    if pair_key is None:
        pair_key = _digest(f"pair:{task_id}:{ordinal}")
    passed = state == "passed"
    if accepted_steps is None:
        accepted_steps = [_accepted_step()] if passed else []
    if total_weight is None:
        total_weight = sum(step["weight"] for step in accepted_steps)
    trial_dict: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "trial_id": f"trial-{task_id}-{ordinal}",
        "cell_id": cell_id,
        "pair_key": pair_key,
        "cell": {
            "suite_lock_sha256": suite_lock,
            "task_id": task_id,
            "attempt_ordinal": ordinal,
            "seed": ordinal,
        },
        "outcome": _outcome(state),
        "accepted_steps": accepted_steps,
        "total_weight": total_weight,
    }
    if tools is not None:
        trial_dict["tools"] = tools
    if cache is not None:
        trial_dict["cache"] = cache
    if tokens is not None:
        trial_dict["tokens"] = tokens
    if integrity is not None:
        trial_dict["integrity"] = integrity
    if drift is not None:
        trial_dict["drift"] = drift
    if timing is not None:
        trial_dict["timing"] = timing
    return trial_dict


class AggregateQualityModuleSurfaceTests(unittest.TestCase):
    """Verify the public surface, the re-exports, and the module constants."""

    def test_dunder_all_contains_expected_symbols(self) -> None:
        # Pulling the full dunder-all keeps the spot-check honest even after
        # future additions; if a new helper is added it must be listed here.
        self.assertIn("BOOTSTRAP_METHOD", quality.__all__)
        self.assertIn("DEFAULT_BOOTSTRAP_RESAMPLES", quality.__all__)
        self.assertIn("QUANTILE_METHOD", quality.__all__)
        self.assertIn("TRUE_DECODE_FORMULA", quality.__all__)
        self.assertIn("TRUE_DECODE_TIMESTAMP_SOURCE", quality.__all__)
        self.assertIn("_RUNTIME_STABILITY_FIELDS", quality.__all__)
        self.assertIn("_accepted_weight", quality.__all__)
        self.assertIn("_counts", quality.__all__)
        self.assertIn("_distribution", quality.__all__)
        self.assertIn("_paired_comparison", quality.__all__)
        self.assertIn("_quality", quality.__all__)
        self.assertIn("_scoreable", quality.__all__)
        self.assertIn("_summarize_cache", quality.__all__)
        self.assertIn("_summarize_drift", quality.__all__)
        self.assertIn("_summarize_latency", quality.__all__)
        self.assertIn("_summarize_runtime_stability", quality.__all__)
        self.assertIn("_summarize_tools", quality.__all__)
        self.assertIn("_validate_arm", quality.__all__)
        self.assertIn("performance_task_ids_sha256", quality.__all__)

    def test_runtime_stability_fields_enum(self) -> None:
        # The fields must remain in lockstep with ``integrity`` validation
        # in trial_contracts.py — drift here would cause runtime gating to
        # mis-read trial events.
        self.assertEqual(
            _RUNTIME_STABILITY_FIELDS,
            ("ooms", "deadlocks", "unexplained_restarts"),
        )

    def test_runtime_stability_admissibility_reasons_present(self) -> None:
        # Internal helper that exposes per-field reasons; sanity-check the
        # structure to catch accidental reformatting.
        names = quality._RUNTIME_STABILITY_ADMISSIBILITY_REASONS
        self.assertIn("integrity.ooms is nonzero", names)
        self.assertIn("integrity.deadlocks is nonzero", names)
        self.assertIn("integrity.unexplained_restarts is nonzero", names)

    def test_infrastructure_state_constant_is_lowercase(self) -> None:
        self.assertEqual(quality._INFRASTRUCTURE_STATE, "infrastructure_exclusion")

    def test_scored_states_constant_matches_outcome_states(self) -> None:
        self.assertEqual(quality._SCORED_STATES, frozenset({"passed", "model_failure"}))

    def test_tool_total_fields_are_tuple(self) -> None:
        # These field names are how ``_summarize_tools`` finds counters.
        for field in (
            "emitted_candidates",
            "executed_calls",
            "semantically_correct_calls",
            "gold_labeled_calls",
            "exact_tool_matches",
            "duplicate_calls",
            "loop_events",
        ):
            self.assertIn(field, quality._TOOL_TOTAL_FIELDS)

    def test_drift_checkpoint_turns(self) -> None:
        # The drift checkpoints are part of the v2 audit contract.
        self.assertEqual(quality._DRIFT_CHECKPOINT_TURNS, (1, 5, 10, 25, 50))

    def test_true_decode_formula_string(self) -> None:
        # The formula string is presented verbatim in latency summaries; any
        # edit must propagate to ``validate_aggregate_record`` auditors.
        self.assertEqual(
            TRUE_DECODE_FORMULA,
            "(completion_tokens - 1) / ((last_token_ns - first_token_ns) / 1e9)",
        )
        self.assertIn("monotonic", TRUE_DECODE_TIMESTAMP_SOURCE)


class SchemaHelperTests(unittest.TestCase):
    """Branch coverage for the private type-guard helpers."""

    def test_mapping_accepts_dict(self) -> None:
        # ``_mapping`` is the canonical Mapping-check; we use ``assertEqual``
        # rather than ``assertIs`` because the helper returns the input
        # unchanged and Python may not preserve identity for ``{}`` literals
        # passed through assertion helpers in some interpreters.
        self.assertEqual(quality._mapping({"k": 1}, "p"), {"k": 1})

    def test_mapping_rejects_non_mapping(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            quality._mapping([], "p")
        with self.assertRaisesRegex(ContractError, "must be an object"):
            quality._mapping("not-a-dict", "p")

    def test_text_accepts_non_empty(self) -> None:
        self.assertEqual(quality._text("hello", "p"), "hello")
        self.assertEqual(quality._text("  spaced  ", "p"), "  spaced  ")

    def test_text_rejects_empty_or_whitespace(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            quality._text("", "p")
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            quality._text("   ", "p")

    def test_text_rejects_non_string(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            quality._text(123, "p")
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            quality._text(None, "p")

    def test_integer_accepts_zero_and_above(self) -> None:
        self.assertEqual(quality._integer(0, "p"), 0)
        self.assertEqual(quality._integer(5, "p"), 5)

    def test_integer_rejects_bool(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            quality._integer(True, "p")

    def test_integer_rejects_negative(self) -> None:
        with self.assertRaisesRegex(ContractError, ">= 0"):
            quality._integer(-1, "p")

    def test_integer_rejects_non_int(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            quality._integer(1.5, "p")
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            quality._integer("1", "p")

    def test_integer_respects_minimum(self) -> None:
        with self.assertRaisesRegex(ContractError, ">= 1"):
            quality._integer(0, "p", minimum=1)

    def test_number_rejects_bool(self) -> None:
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number(True, "p")

    def test_number_rejects_non_finite(self) -> None:
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number(float("inf"), "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number(float("-inf"), "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number(float("nan"), "p")

    def test_number_enforces_minimum(self) -> None:
        with self.assertRaisesRegex(ContractError, ">= 0.0"):
            quality._number(-0.0001, "p", minimum=0.0)

    def test_number_enforces_maximum(self) -> None:
        with self.assertRaisesRegex(ContractError, "<= 1.0"):
            quality._number(1.5, "p", maximum=1.0)

    def test_number_rejects_non_numeric(self) -> None:
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number("abc", "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            quality._number(None, "p")

    def test_sha256_accepts_well_formed(self) -> None:
        digest = "0" * 64
        self.assertEqual(quality._sha256(digest, "p"), digest)

    def test_sha256_rejects_wrong_length(self) -> None:
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            quality._sha256("a" * 63, "p")
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            quality._sha256("a" * 65, "p")

    def test_sha256_rejects_uppercase(self) -> None:
        bad = "A" * 64
        with self.assertRaisesRegex(ContractError, "lowercase"):
            quality._sha256(bad, "p")

    def test_sha256_rejects_non_hex(self) -> None:
        with self.assertRaisesRegex(ContractError, "lowercase"):
            quality._sha256("g" * 64, "p")


class TrialExtractorTests(unittest.TestCase):
    """The four tiny extractors must agree on their input shape."""

    def test_trial_state_returns_state_string(self) -> None:
        self.assertEqual(_trial_state(_trial(state="passed")), "passed")
        self.assertEqual(_trial_state(_trial(state="model_failure")), "model_failure")
        self.assertEqual(
            _trial_state(_trial(state="infrastructure_exclusion")),
            "infrastructure_exclusion",
        )

    def test_trial_state_rejects_non_object_outcome(self) -> None:
        bad = _trial(state="passed")
        bad["outcome"] = "not-an-object"
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _trial_state(bad)

    def test_trial_task_returns_task_id(self) -> None:
        self.assertEqual(_trial_task(_trial(task_id="task-alpha")), "task-alpha")
        self.assertEqual(_trial_task(_trial(task_id="task-β")), "task-β")

    def test_trial_ordinal_returns_attempt_ordinal(self) -> None:
        self.assertEqual(_trial_ordinal(_trial(ordinal=0)), 0)
        self.assertEqual(_trial_ordinal(_trial(ordinal=3)), 3)


class ScoreabilityTests(unittest.TestCase):
    """The truth table for ``_scoreable`` across all states."""

    def test_passed_is_scoreable(self) -> None:
        self.assertTrue(_scoreable(_trial(state="passed")))

    def test_model_failure_is_scoreable(self) -> None:
        self.assertTrue(_scoreable(_trial(state="model_failure")))

    def test_infrastructure_exclusion_is_not_scoreable(self) -> None:
        self.assertFalse(_scoreable(_trial(state="infrastructure_exclusion")))

    def test_scoreable_flag_false_makes_trial_non_scoreable(self) -> None:
        # Even when state is in _SCORED_STATES, a non-scoreable flag wins.
        non_scoreable = _trial(state="passed")
        non_scoreable["outcome"]["scoreable"] = False
        self.assertFalse(_scoreable(non_scoreable))


class AcceptedWeightTests(unittest.TestCase):
    """``_accepted_weight`` is the strict gatekeeper for milestone totals."""

    def test_simple_single_step_returns_declared_weight(self) -> None:
        trial = _trial(
            state="passed", accepted_steps=[_accepted_step()], total_weight=1.0
        )
        self.assertEqual(_accepted_weight(trial), 1.0)

    def test_no_steps_returns_zero(self) -> None:
        trial = _trial(state="model_failure", accepted_steps=[], total_weight=0.0)
        self.assertEqual(_accepted_weight(trial), 0.0)

    def test_zero_weight_steps_counted_only_when_accepted(self) -> None:
        trial = _trial(
            state="passed",
            accepted_steps=[_accepted_step("step-a", 0.0)],
            total_weight=0.0,
        )
        self.assertEqual(_accepted_weight(trial), 0.0)

    def test_duplicate_step_id_rejected(self) -> None:
        trial = _trial(
            state="passed",
            accepted_steps=[
                _accepted_step("step-a"),
                _accepted_step("step-a"),
            ],
            total_weight=2.0,
        )
        with self.assertRaisesRegex(ContractError, "duplicate step_id"):
            _accepted_weight(trial)

    def test_total_weight_mismatch_rejected(self) -> None:
        # Accepted steps sum to 1.0 but total_weight claims 0.5 — must refuse.
        trial = _trial(
            state="passed",
            accepted_steps=[_accepted_step("step-a", 1.0)],
            total_weight=0.5,
        )
        with self.assertRaisesRegex(ContractError, "does not equal recomputed"):
            _accepted_weight(trial)

    def test_accepted_steps_not_a_list_rejected(self) -> None:
        trial = _trial(state="passed")
        trial["accepted_steps"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _accepted_weight(trial)

    def test_step_must_be_object(self) -> None:
        trial = _trial(
            state="passed", accepted_steps=["not-an-object"], total_weight=0.0
        )
        with self.assertRaisesRegex(ContractError, "must be an object"):
            _accepted_weight(trial)

    def test_step_id_alias_milestone_id_is_supported(self) -> None:
        # The legacy alias ``milestone_id`` is still accepted for forward
        # compatibility — verify it falls through to the same code path.
        step = _accepted_step("step-a")
        del step["step_id"]
        step["milestone_id"] = "step-a"
        trial = _trial(state="passed", accepted_steps=[step], total_weight=1.0)
        self.assertEqual(_accepted_weight(trial), 1.0)

    def test_transitioned_alias_terminal_recheck_passed(self) -> None:
        step = _accepted_step("step-a")
        del step["false_to_true_transition"]
        del step["terminal_reverified"]
        step["transitioned_false_to_true"] = True
        step["terminal_recheck_passed"] = True
        trial = _trial(state="passed", accepted_steps=[step], total_weight=1.0)
        self.assertEqual(_accepted_weight(trial), 1.0)

    def test_step_not_transitioned_is_excluded_from_total(self) -> None:
        # A step that never transitioned contributes no weight; the recomputed
        # total skips it but the declared total must still reconcile.
        accepted = _accepted_step("step-a", 0.3)
        accepted["false_to_true_transition"] = False
        trial = _trial(state="passed", accepted_steps=[accepted], total_weight=0.0)
        self.assertEqual(_accepted_weight(trial), 0.0)

    def test_non_boolean_transition_rejected(self) -> None:
        step = _accepted_step("step-a")
        step["false_to_true_transition"] = "yes"  # not a bool
        trial = _trial(state="passed", accepted_steps=[step], total_weight=0.0)
        with self.assertRaisesRegex(ContractError, "needs boolean transition"):
            _accepted_weight(trial)

    def test_non_boolean_terminal_reverified_rejected(self) -> None:
        step = _accepted_step("step-a")
        step["terminal_reverified"] = "yes"
        trial = _trial(state="passed", accepted_steps=[step], total_weight=0.0)
        with self.assertRaisesRegex(ContractError, "needs boolean transition"):
            _accepted_weight(trial)

    def test_dependency_must_be_string_list(self) -> None:
        step = _accepted_step("step-a")
        step["depends_on"] = [123]
        trial = _trial(state="passed", accepted_steps=[step], total_weight=0.0)
        with self.assertRaisesRegex(ContractError, "must be strings"):
            _accepted_weight(trial)

    def test_dependency_ids_alias_is_supported(self) -> None:
        # The legacy alias ``dependency_ids`` is accepted in place of
        # ``depends_on``.  Verify the alt name path.
        step_a = _accepted_step("step-a")
        step_b = _accepted_step("step-b")
        step_c = _accepted_step("step-c")
        for step in (step_a, step_b, step_c):
            del step["depends_on"]
        step_a["dependency_ids"] = ["step-b"]
        step_b["dependency_ids"] = ["step-c"]
        step_c["dependency_ids"] = []
        trial = _trial(
            state="passed",
            accepted_steps=[step_a, step_b, step_c],
            total_weight=3.0,
        )
        self.assertEqual(_accepted_weight(trial), 3.0)

    def test_missing_dependency_rejected(self) -> None:
        step = _accepted_step("step-a", 0.5)
        step["depends_on"] = ["ghost-step"]
        trial = _trial(state="passed", accepted_steps=[step], total_weight=0.0)
        with self.assertRaisesRegex(ContractError, "missing accepted dependency"):
            _accepted_weight(trial)

    def test_dependency_cycle_rejected(self) -> None:
        # Two steps that depend on each other form a cycle: nothing can resolve
        # in either direction, so the helper must refuse.
        step_a = _accepted_step("step-a", 0.5)
        step_b = _accepted_step("step-b", 0.5)
        step_a["depends_on"] = ["step-b"]
        step_b["depends_on"] = ["step-a"]
        trial = _trial(
            state="passed", accepted_steps=[step_a, step_b], total_weight=1.0
        )
        with self.assertRaisesRegex(ContractError, "contains a cycle"):
            _accepted_weight(trial)

    def test_partial_deps_remaining_cycle_is_rejected(self) -> None:
        # Self-referential cycle: A -> B -> A. Same as above.
        step_a = _accepted_step("step-a", 1.0)
        step_a["depends_on"] = ["step-a"]
        trial = _trial(state="passed", accepted_steps=[step_a], total_weight=1.0)
        with self.assertRaisesRegex(ContractError, "contains a cycle"):
            _accepted_weight(trial)

    def test_total_weight_must_be_numeric(self) -> None:
        trial = _trial(state="passed")
        trial["total_weight"] = "bad"
        with self.assertRaisesRegex(ContractError, "finite"):
            _accepted_weight(trial)

    def test_infrastructure_state_with_nonzero_weight_rejected(self) -> None:
        # Infrastructure exclusions must contribute no weight, even if the
        # trial record is badly-formed.
        step = _accepted_step("step-a", 0.5)
        trial = _trial(
            state="infrastructure_exclusion",
            accepted_steps=[step],
            total_weight=0.5,
        )
        with self.assertRaisesRegex(ContractError, "cannot contribute"):
            _accepted_weight(trial)

    def test_dependency_resolution_walks_in_order(self) -> None:
        # Three steps forming a chain: a depends on b which depends on c.
        # Verify that all three are summed in topological order.
        step_a = _accepted_step("step-a", 0.2)
        step_b = _accepted_step("step-b", 0.3)
        step_c = _accepted_step("step-c", 0.5)
        step_a["depends_on"] = ["step-b"]
        step_b["depends_on"] = ["step-c"]
        trial = _trial(
            state="passed",
            accepted_steps=[step_a, step_b, step_c],
            total_weight=1.0,
        )
        self.assertEqual(_accepted_weight(trial), 1.0)


class ValidateArmTests(unittest.TestCase):
    """Branch coverage for ``_validate_arm`` with mocked trial helpers."""

    def setUp(self) -> None:
        self.patches = mock.patch.multiple(
            aggregate_contracts,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        self.patches.start()

    def tearDown(self) -> None:
        self.patches.stop()

    def _trials(self, tasks: list[tuple[str, int]]) -> list[dict]:
        return [_trial(task_id=t, ordinal=o) for t, o in tasks]

    def test_empty_arm_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "must not be empty"):
            _validate_arm(
                [], expected_task_ids=["task-alpha"], attempts_per_task=1, arm="arm"
            )

    def test_wrong_schema_version_rejected(self) -> None:
        trials = self._trials([("task-alpha", 0)])
        trials[0]["schema_version"] = "wrong"
        with self.assertRaisesRegex(ContractError, "wrong trial schema"):
            _validate_arm(
                trials, expected_task_ids=["task-alpha"], attempts_per_task=1, arm="arm"
            )

    def test_unexpected_task_id_rejected(self) -> None:
        trials = self._trials([("task-alpha", 0)])
        trials[0]["cell"]["task_id"] = "task-other"
        with self.assertRaisesRegex(ContractError, "unexpected task_id"):
            _validate_arm(
                trials, expected_task_ids=["task-alpha"], attempts_per_task=1, arm="arm"
            )

    def test_ordinal_exceeds_budget_rejected(self) -> None:
        trials = self._trials([("task-alpha", 4)])
        with self.assertRaisesRegex(ContractError, "exceeds the precommitted budget"):
            _validate_arm(
                trials, expected_task_ids=["task-alpha"], attempts_per_task=2, arm="arm"
            )

    def test_duplicate_canonical_trial_rejected(self) -> None:
        trials = self._trials([("task-alpha", 0)])
        trials.append(copy.deepcopy(trials[0]))
        with self.assertRaisesRegex(ContractError, "duplicate canonical trial"):
            _validate_arm(
                trials, expected_task_ids=["task-alpha"], attempts_per_task=2, arm="arm"
            )

    def test_duplicate_pair_key_rejected(self) -> None:
        # Both trials must use the same 64-character pair_key.  Each trial
        # also needs its own cell_id so the cell_id-uniqueness check (which
        # runs later) does not fire first.
        shared_pair_key = "f" * 64
        a = _trial(
            task_id="task-alpha",
            ordinal=0,
            pair_key=shared_pair_key,
            cell_id="1" * 64,
        )
        b = _trial(
            task_id="task-beta",
            ordinal=0,
            pair_key=shared_pair_key,
            cell_id="2" * 64,
        )
        with self.assertRaisesRegex(ContractError, "duplicate pair_key"):
            _validate_arm(
                [a, b],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                arm="arm",
            )

    def test_duplicate_task_attempt_key_rejected(self) -> None:
        # Two trials with the same (task_id, ordinal) but distinct content
        # (different pair_keys and cell_ids) so the canonical-trial-hash
        # check does not fire first.
        a = _trial(
            task_id="task-alpha",
            ordinal=0,
            pair_key="1" * 64,
            cell_id="1" * 64,
        )
        b = _trial(
            task_id="task-alpha",
            ordinal=0,
            pair_key="2" * 64,
            cell_id="2" * 64,
        )
        with self.assertRaisesRegex(ContractError, "duplicates task/attempt"):
            _validate_arm(
                [a, b], expected_task_ids=["task-alpha"], attempts_per_task=2, arm="arm"
            )

    def test_two_cell_ids_rejected(self) -> None:
        a = _trial(task_id="task-alpha", ordinal=0, cell_id="c" * 64)
        b = _trial(task_id="task-beta", ordinal=0, cell_id="d" * 64)
        with self.assertRaisesRegex(ContractError, "cell_id"):
            _validate_arm(
                [a, b],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                arm="arm",
            )

    def test_two_suite_locks_rejected(self) -> None:
        a = _trial(task_id="task-alpha", ordinal=0, suite_lock="a" * 64)
        b = _trial(task_id="task-beta", ordinal=0, suite_lock="b" * 64)
        with self.assertRaisesRegex(ContractError, "suite lock"):
            _validate_arm(
                [a, b],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                arm="arm",
            )

    def test_two_run_ids_rejected(self) -> None:
        a = _trial(task_id="task-alpha", ordinal=0, run_id="run-1")
        b = _trial(task_id="task-beta", ordinal=0, run_id="run-2")
        with self.assertRaisesRegex(ContractError, "run_id"):
            _validate_arm(
                [a, b],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                arm="arm",
            )

    def test_non_scoreable_non_excluded_rejected(self) -> None:
        # State model_failure but scoreable=False: this is the "scorable
        # disagreement" path that the validator must reject.
        bad = _trial(task_id="task-alpha", ordinal=0)
        bad["outcome"] = {
            "state": "model_failure",
            "reason": "verifier_fail",
            "scoreable": False,
        }
        with self.assertRaisesRegex(ContractError, "non-excluded but not scoreable"):
            _validate_arm(
                [bad], expected_task_ids=["task-alpha"], attempts_per_task=1, arm="arm"
            )

    def test_admissibility_reasons_block_scoreable_trial(self) -> None:
        bad_scoreability = mock.patch.object(
            aggregate_contracts,
            "trial_scoreability_reasons",
            return_value=["run_mode is not execute"],
        )
        with bad_scoreability:
            with self.assertRaisesRegex(ContractError, "not evidence-admissible"):
                _validate_arm(
                    [_trial(task_id="task-alpha", ordinal=0)],
                    expected_task_ids=["task-alpha"],
                    attempts_per_task=1,
                    arm="arm",
                )

    def test_runtime_stability_reasons_are_admissibility_neutral(self) -> None:
        # ``integrity.{ooms,deadlocks,unexplained_restarts}`` are
        # admissibility-neutral — they are surfaced through the runtime
        # stability gate instead of the trial-integrity gate, so the trial
        # remains acceptable for evidence despite nonzero runtime counters.
        bad_scoreability = mock.patch.object(
            aggregate_contracts,
            "trial_scoreability_reasons",
            return_value=[
                "integrity.ooms is nonzero",
                "integrity.deadlocks is nonzero",
                "integrity.unexplained_restarts is nonzero",
            ],
        )
        with bad_scoreability:
            # Should NOT raise — these reasons are filtered out.
            trial = _trial(
                task_id="task-alpha",
                ordinal=0,
                integrity={"ooms": 1, "deadlocks": 1, "unexplained_restarts": 1},
            )
            result = _validate_arm(
                [trial],
                expected_task_ids=["task-alpha"],
                attempts_per_task=1,
                arm="arm",
            )
            self.assertEqual(len(result["trials"]), 1)

    def test_happy_path_returns_validation_envelope(self) -> None:
        trials = self._trials([("task-alpha", 0), ("task-alpha", 1)])
        result = _validate_arm(
            trials,
            expected_task_ids=["task-alpha"],
            attempts_per_task=2,
            arm="arm",
        )
        self.assertEqual(len(result["trials"]), 2)
        self.assertEqual(result["cell_id"], CELL_ID)
        self.assertEqual(result["suite_lock_sha256"], SUITE_LOCK)
        self.assertEqual(result["run_id"], RUN_ID)
        # hashes must be sorted before returning
        self.assertEqual(result["hashes"], sorted(result["hashes"]))
        # all (task, ordinal) keys captured
        self.assertEqual(result["keys"], {("task-alpha", 0), ("task-alpha", 1)})

    def test_accepted_weight_validation_called_for_each_trial(self) -> None:
        # Make a passing trial with malformed accepted_steps so the call to
        # ``_accepted_weight`` inside the loop blows up.  This pins the
        # call-site for the per-arm weight check.
        bad = _trial(task_id="task-alpha", ordinal=0)
        bad["total_weight"] = 0.0
        # No need to damage structure: empty steps still valid for pass.
        # Trigger a different rule: state=infrastructure with non-zero weight
        bad["outcome"]["state"] = "infrastructure_exclusion"
        bad["total_weight"] = 1.0
        with self.assertRaisesRegex(ContractError, "cannot contribute"):
            _validate_arm(
                [bad], expected_task_ids=["task-alpha"], attempts_per_task=1, arm="arm"
            )


class CountsTests(unittest.TestCase):
    """``_counts`` should classify attempts correctly."""

    def test_mixed_states_count_correctly(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-alpha", ordinal=1, state="model_failure"),
            _trial(task_id="task-beta", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=1, state="infrastructure_exclusion"),
            _trial(task_id="task-β", ordinal=0, state="infrastructure_exclusion"),
        ]
        result = _counts(trials)
        self.assertEqual(result["attempted"], 5)
        # Two passes + one model failure = three scored attempts (exclusions
        # are not scoreable).
        self.assertEqual(result["scored"], 3)
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["excluded"], 2)
        self.assertEqual(result["excluded_by_reason"], {"verifier_fail": 2})
        self.assertAlmostEqual(result["infrastructure_exclusion_rate"], 2 / 5)

    def test_infrastructure_reasons_sorted(self) -> None:
        # Both infrastructure_exclusion trials carry reason="verifier_fail"
        # because we build ``_outcome`` identically for every state — the
        # helper sorts these keys (a single key here, deterministically
        # order-checked) so that downstream JSON output is stable.
        a = _trial(task_id="task-alpha", ordinal=0, state="infrastructure_exclusion")
        b = _trial(task_id="task-beta", ordinal=0, state="infrastructure_exclusion")
        excluded_by_reason = _counts([a, b])["excluded_by_reason"]
        self.assertEqual(excluded_by_reason, {"verifier_fail": 2})
        self.assertEqual(list(excluded_by_reason), sorted(excluded_by_reason))

    def test_infrastructure_with_default_reason(self) -> None:
        # When ``reason`` is missing, the helper uses "unknown".
        trial = _trial(
            task_id="task-alpha", ordinal=0, state="infrastructure_exclusion"
        )
        del trial["outcome"]["reason"]
        result = _counts([trial])
        self.assertEqual(result["excluded_by_reason"], {"unknown": 1})


class QualitySummaryTests(unittest.TestCase):
    """``_quality`` should produce deterministic bootstrap estimates and metadata."""

    def test_empty_arm_returns_none_estimates(self) -> None:
        # ``pass_at_1`` and ``pass_at_4`` collapse to None when no scored
        # trials exist; ``pass_all_k`` is **not** None because the gate
        # short-circuits to ``all([]) = True`` when ``attempts_per_task=0``.
        # We pin that documented behaviour rather than over-assert.
        result = _quality(
            [],
            expected_task_ids=["task-alpha"],
            attempts_per_task=0,
            hashes=[],
            resamples=DEFAULT_BOOTSTRAP_RESAMPLES,
        )
        self.assertIsNone(result["pass_at_1"]["estimate"])
        self.assertIsNone(result["pass_at_4"]["estimate"])
        self.assertEqual(result["pass_at_1"]["expected_task_count"], 1)
        self.assertEqual(result["pass_at_1"]["eligible_task_count"], 0)
        self.assertEqual(result["pass_at_4"]["eligible_task_count"], 0)

    def test_pass_at_1_none_when_no_scored_trials(self) -> None:
        # Pass ``attempts_per_task=1`` so the trivially-complete branch does
        # not apply.  Now an arm with no scored trials produces None for
        # every pass-at-K estimate.
        excluded = [
            _trial(task_id="task-alpha", ordinal=0, state="infrastructure_exclusion")
        ]
        result = _quality(
            excluded,
            expected_task_ids=["task-alpha"],
            attempts_per_task=1,
            hashes=[_digest("h0")],
            resamples=8,
        )
        self.assertIsNone(result["pass_at_1"]["estimate"])
        self.assertIsNone(result["pass_at_4"]["estimate"])
        self.assertEqual(result["pass_at_1"]["eligible_task_count"], 0)

    def test_mixed_pass_rate_is_average_over_scored_tasks(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-alpha", ordinal=1, state="model_failure"),
            _trial(task_id="task-beta", ordinal=0, state="passed"),
        ]
        result = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=2,
            hashes=[_digest("h0"), _digest("h1"), _digest("h2")],
            resamples=32,
        )
        # task-alpha scored-1-of-2; task-beta scored-1-of-1 → mean 0.75
        self.assertEqual(result["pass_at_1"]["estimate"], 0.75)
        # pass-at-4 is the "fraction solved by at least one scored ordinal in
        # [0, 3]" — both tasks pass at least one ordinal → 1.0
        self.assertEqual(result["pass_at_4"]["estimate"], 1.0)
        self.assertEqual(result["pass_at_1"]["eligible_task_count"], 2)
        self.assertEqual(result["pass_at_4"]["eligible_task_count"], 2)

    def test_pass_all_k_uses_complete_tasks_only(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            # task-alpha missing ordinal 1; pass-all-k task is incomplete
            _trial(task_id="task-beta", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=1, state="passed"),
        ]
        result = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=2,
            hashes=[_digest("h0"), _digest("h1"), _digest("h2")],
            resamples=32,
        )
        self.assertEqual(result["pass_all_k"]["eligible_complete_task_count"], 1)
        self.assertEqual(result["pass_all_k"]["estimate"], 1.0)
        # Because pass-all-k lacks one task, ci95 lower/upper are None.
        self.assertIsNone(result["pass_all_k"]["ci95"]["lower"])
        self.assertIsNone(result["pass_all_k"]["ci95"]["upper"])
        self.assertEqual(
            result["pass_all_k"]["ci95"]["reason"],
            "one or more tasks has fewer than k scored attempts",
        )

    def test_pass_all_k_full_coverage_uses_bootstrap(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-alpha", ordinal=1, state="passed"),
            _trial(task_id="task-beta", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=1, state="passed"),
        ]
        result = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=2,
            hashes=[_digest("h0"), _digest("h1"), _digest("h2"), _digest("h3")],
            resamples=32,
        )
        self.assertEqual(result["pass_all_k"]["estimate"], 1.0)
        self.assertEqual(result["pass_all_k"]["ci95"]["lower"], 1.0)
        self.assertEqual(result["pass_all_k"]["ci95"]["upper"], 1.0)

    def test_bootstrap_seed_sha256_is_reproducible(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=0, state="model_failure"),
        ]
        first = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=1,
            hashes=[_digest("h0"), _digest("h1")],
            resamples=32,
        )
        second = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=1,
            hashes=[_digest("h0"), _digest("h1")],
            resamples=32,
        )
        self.assertEqual(
            first["bootstrap_seed_sha256"], second["bootstrap_seed_sha256"]
        )

    def test_ci95_metadata_carries_method_and_quantile(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=0, state="passed"),
        ]
        result = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=1,
            hashes=[_digest("h0"), _digest("h1")],
            resamples=8,
        )
        self.assertEqual(result["pass_at_1"]["ci95"]["method"], BOOTSTRAP_METHOD)
        self.assertEqual(
            result["pass_at_1"]["ci95"]["quantile_method"], QUANTILE_METHOD
        )
        self.assertEqual(result["pass_at_1"]["ci95"]["task_clusters"], 2)

    def test_scored_attempts_per_task_sorted(self) -> None:
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=0, state="passed"),
            _trial(task_id="task-beta", ordinal=1, state="model_failure"),
        ]
        result = _quality(
            trials,
            expected_task_ids=["task-alpha", "task-beta"],
            attempts_per_task=2,
            hashes=[_digest("h0"), _digest("h1"), _digest("h2")],
            resamples=8,
        )
        self.assertEqual(
            result["scored_attempts_by_task"],
            {"task-alpha": 1, "task-beta": 2},
        )


class PairedComparisonTests(unittest.TestCase):
    """``_paired_comparison`` must catch every disagreement type."""

    def test_pair_key_with_mismatched_task_rejected(self) -> None:
        treatment = [_trial(task_id="task-alpha", ordinal=0, pair_key="k1")]
        baseline = [_trial(task_id="task-beta", ordinal=0, pair_key="k1")]
        with self.assertRaisesRegex(ContractError, "different tasks"):
            _paired_comparison(
                treatment,
                baseline,
                expected_task_ids=["task-alpha", "task-beta"],
                treatment_hashes=["h1"],
                baseline_hashes=["h1"],
                resamples=8,
            )

    def test_pair_key_with_mismatched_ordinal_rejected(self) -> None:
        treatment = [_trial(task_id="task-alpha", ordinal=0, pair_key="k1")]
        baseline = [_trial(task_id="task-alpha", ordinal=1, pair_key="k1")]
        with self.assertRaisesRegex(ContractError, "different attempt ordinals"):
            _paired_comparison(
                treatment,
                baseline,
                expected_task_ids=["task-alpha"],
                treatment_hashes=["h1"],
                baseline_hashes=["h1"],
                resamples=8,
            )

    def test_pair_key_with_mismatched_seed_rejected(self) -> None:
        treatment = [_trial(task_id="task-alpha", ordinal=0, pair_key="k1")]
        baseline = [_trial(task_id="task-alpha", ordinal=0, pair_key="k1")]
        baseline[0]["cell"]["seed"] = 999
        with self.assertRaisesRegex(ContractError, "different seeds"):
            _paired_comparison(
                treatment,
                baseline,
                expected_task_ids=["task-alpha"],
                treatment_hashes=["h1"],
                baseline_hashes=["h1"],
                resamples=8,
            )

    def test_missing_pair_keys_are_reported(self) -> None:
        treatment = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1"),
            _trial(task_id="task-alpha", ordinal=1, pair_key="k3"),
        ]
        baseline = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1"),
            _trial(task_id="task-alpha", ordinal=1, pair_key="k2"),
        ]
        result = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha"],
            treatment_hashes=[_digest("t1"), _digest("t3")],
            baseline_hashes=[_digest("b1"), _digest("b2")],
            resamples=8,
        )
        self.assertEqual(result["pair_key_count"], 1)
        self.assertEqual(result["missing_baseline_pair_keys"], ["k3"])
        self.assertEqual(result["missing_treatment_pair_keys"], ["k2"])

    def test_discordant_exclusions_are_counted(self) -> None:
        # The treatment is scoreable but baseline is excluded for the same
        # pair_key: counts as a discordant exclusion (one pass, one fail).
        treatment = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1", state="passed")
        ]
        baseline = [
            _trial(
                task_id="task-alpha",
                ordinal=0,
                pair_key="k1",
                state="infrastructure_exclusion",
            )
        ]
        result = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha"],
            treatment_hashes=[_digest("t1")],
            baseline_hashes=[_digest("b1")],
            resamples=8,
        )
        self.assertEqual(result["discordant_exclusion_count"], 1)
        self.assertEqual(result["discordant_exclusion_rate"], 1.0)
        # No paired scored attempt: paired-scored and paired-task count = 0.
        self.assertEqual(result["paired_scored_attempt_count"], 0)
        self.assertEqual(result["paired_task_count"], 0)
        self.assertIsNone(result["pass_at_1_delta"]["estimate"])

    def test_paired_estimate_is_macro_mean_of_deltas(self) -> None:
        # Treatment: task-alpha passes both; baseline: task-alpha fails both.
        # Per-task delta = +1.0 for task-alpha.
        # Then add task-beta: treatment passes both, baseline passes both.
        # Per-task delta = 0.0 for task-beta.
        # Macro mean = (1.0 + 0.0) / 2 = 0.5
        treatment = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1", state="passed"),
            _trial(task_id="task-alpha", ordinal=1, pair_key="k2", state="passed"),
            _trial(task_id="task-beta", ordinal=0, pair_key="k3", state="passed"),
            _trial(task_id="task-beta", ordinal=1, pair_key="k4", state="passed"),
        ]
        baseline = [
            _trial(
                task_id="task-alpha", ordinal=0, pair_key="k1", state="model_failure"
            ),
            _trial(
                task_id="task-alpha", ordinal=1, pair_key="k2", state="model_failure"
            ),
            _trial(task_id="task-beta", ordinal=0, pair_key="k3", state="passed"),
            _trial(task_id="task-beta", ordinal=1, pair_key="k4", state="passed"),
        ]
        result = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha", "task-beta"],
            treatment_hashes=[
                _digest("t1"),
                _digest("t2"),
                _digest("t3"),
                _digest("t4"),
            ],
            baseline_hashes=[
                _digest("b1"),
                _digest("b2"),
                _digest("b3"),
                _digest("b4"),
            ],
            resamples=32,
        )
        self.assertEqual(result["paired_task_count"], 2)
        self.assertEqual(result["paired_scored_attempt_count"], 4)
        self.assertEqual(result["pass_at_1_delta"]["estimate"], 0.5)

    def test_bootstrap_seed_is_reproducible(self) -> None:
        treatment = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1", state="passed")
        ]
        baseline = [
            _trial(
                task_id="task-alpha", ordinal=0, pair_key="k1", state="model_failure"
            )
        ]
        first = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha"],
            treatment_hashes=[_digest("t1")],
            baseline_hashes=[_digest("b1")],
            resamples=8,
        )
        second = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha"],
            treatment_hashes=[_digest("t1")],
            baseline_hashes=[_digest("b1")],
            resamples=8,
        )
        self.assertEqual(
            first["bootstrap_seed_sha256"], second["bootstrap_seed_sha256"]
        )

    def test_delta_definition_string(self) -> None:
        # The definition string is enforced verbatim by the validators;
        # assert we have not drifted.
        treatment = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1", state="passed")
        ]
        baseline = [
            _trial(task_id="task-alpha", ordinal=0, pair_key="k1", state="passed")
        ]
        result = _paired_comparison(
            treatment,
            baseline,
            expected_task_ids=["task-alpha"],
            treatment_hashes=[_digest("t1")],
            baseline_hashes=[_digest("b1")],
            resamples=8,
        )
        self.assertEqual(
            result["pass_at_1_delta"]["definition"],
            "macro mean of treatment-minus-baseline paired task pass fractions",
        )


class DistributionTests(unittest.TestCase):
    """The type-7 quantiles are wrapped in a coverage-fraction helper."""

    def test_empty_distribution_yields_zero_count(self) -> None:
        result = _distribution([], expected_count=4)
        self.assertEqual(result["sample_count"], 0)
        self.assertEqual(result["coverage_fraction"], 0.0)
        self.assertIsNone(result["p50"])
        self.assertIsNone(result["p95"])
        self.assertIsNone(result["p99"])

    def test_populated_distribution_reports_quantiles(self) -> None:
        result = _distribution([0.0, 1.0, 2.0, 3.0, 4.0], expected_count=10)
        self.assertEqual(result["sample_count"], 5)
        self.assertAlmostEqual(result["coverage_fraction"], 0.5)
        self.assertEqual(result["p50"], 2.0)
        self.assertEqual(result["p95"], 3.8)
        self.assertEqual(result["p99"], 3.96)

    def test_distribution_with_zero_expected_count_yields_none_coverage(self) -> None:
        result = _distribution([], expected_count=0)
        self.assertIsNone(result["coverage_fraction"])

    def test_distribution_with_full_coverage(self) -> None:
        result = _distribution([1.0, 2.0], expected_count=2)
        self.assertEqual(result["coverage_fraction"], 1.0)


class ToolsSummaryTests(unittest.TestCase):
    """Cover the per-trial tool-rate branches."""

    def _tools(self, **overrides: Any) -> dict:
        base: dict[str, Any] = {
            "emitted_candidates": 1,
            "parsed_calls": 1,
            "schema_valid_calls": 1,
            "executed_calls": 1,
            "semantically_correct_calls": 0,
            "gold_labeled_calls": 0,
            "exact_tool_matches": 0,
            "exact_argument_matches": 0,
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
        base.update(overrides)
        return base

    def test_status_complete_when_all_scored_have_tools(self) -> None:
        trial = _trial(tools=self._tools())
        result = _summarize_tools([trial])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["coverage_fraction"], 1.0)

    def test_status_partial_when_some_trials_have_tools(self) -> None:
        with_tools = _trial(tools=self._tools())
        without_tools = _trial()
        result = _summarize_tools([with_tools, without_tools])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["coverage_fraction"], 0.5)

    def test_status_missing_when_no_trials_have_tools(self) -> None:
        result = _summarize_tools([_trial(), _trial()])
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["coverage_fraction"], 0.0)

    def test_parse_rate_when_no_emitted_is_none(self) -> None:
        # emitted_candidates=0 → parse_rate is None (denominator zero).
        tools = self._tools()
        tools["emitted_candidates"] = 0
        result = _summarize_tools([_trial(tools=tools)])
        self.assertIsNone(result["parse_rate"])

    def test_schema_valid_rate_uses_parsed_denominator(self) -> None:
        tools = self._tools(emitted_candidates=4, parsed_calls=4, schema_valid_calls=3)
        result = _summarize_tools([_trial(tools=tools)])
        self.assertEqual(result["parse_rate"], 1.0)
        self.assertEqual(result["schema_valid_rate"], 0.75)

    def test_valid_but_wrong_rate(self) -> None:
        tools = self._tools(
            parsed_calls=4, schema_valid_calls=4, schema_valid_but_wrong=2
        )
        result = _summarize_tools([_trial(tools=tools)])
        self.assertEqual(result["valid_but_wrong_rate"], 0.5)

    def test_semantic_correct_rate_uses_executed_denominator(self) -> None:
        tools = self._tools(executed_calls=4, semantically_correct_calls=2)
        result = _summarize_tools([_trial(tools=tools)])
        self.assertEqual(result["semantic_correct_rate"], 0.5)
        self.assertTrue(result["semantic_correct_count_complete"])

    def test_semantic_correct_rate_is_none_when_incomplete(self) -> None:
        # semantic_complete requires every trial to expose semantically_correct_calls.
        with_tools = _trial(tools=self._tools())
        without_tools = _trial()
        result = _summarize_tools([with_tools, without_tools])
        self.assertFalse(result["semantic_correct_count_complete"])
        self.assertIsNone(result["semantic_correct_rate"])

    def test_repair_and_fallback_counts(self) -> None:
        tools_repaired = self._tools(repair_attempts=1)
        tools_repaired["repair_attempts"] = 1
        tools_fallback = self._tools(fallbacks=1)
        result = _summarize_tools(
            [_trial(tools=tools_repaired), _trial(tools=tools_fallback)]
        )
        self.assertEqual(result["repair_attempt_trial_count"], 1)
        self.assertEqual(result["fallback_trial_count"], 1)
        self.assertEqual(result["fallback_trial_rate"], 0.5)

    def test_duplicate_or_loop_trial_count(self) -> None:
        loop = self._tools(loop_events=1)
        duplicate = self._tools(duplicate_calls=1)
        result = _summarize_tools([_trial(tools=loop), _trial(tools=duplicate)])
        self.assertEqual(result["duplicate_or_loop_trial_count"], 2)

    def test_exact_match_metrics_present_only_when_labeled(self) -> None:
        # gold_labeled_calls > 0 triggers exact-match metrics.
        tools = self._tools(
            gold_labeled_calls=4,
            exact_tool_matches=3,
            exact_argument_matches=2,
        )
        result = _summarize_tools([_trial(tools=tools)])
        self.assertIn("exact_tool_match_rate", result)
        self.assertEqual(result["exact_tool_match_rate"], 0.75)
        self.assertEqual(result["exact_argument_match_rate"], 0.5)

    def test_field_with_none_value_does_not_count_toward_total(self) -> None:
        # Some tool rows may have ``None`` for fields like
        # ``gold_labeled_calls`` — the helper must skip the field rather
        # than coerce None into an integer.  This exercises the
        # ``if value is not None:`` branch on line 502 (the only branch
        # that ends branch coverage at 99%).
        tools = self._tools(
            gold_labeled_calls=None,
            exact_tool_matches=None,
            exact_argument_matches=None,
        )
        result = _summarize_tools([_trial(tools=tools)])
        self.assertEqual(result["totals"]["gold_labeled_calls"], 0)
        self.assertEqual(result["totals"]["exact_tool_matches"], 0)
        self.assertEqual(result["totals"]["exact_argument_matches"], 0)
        # Labels are absent, so exact-match rate metrics are not surfaced.
        self.assertNotIn("exact_tool_match_rate", result)


class LatencySummaryTests(unittest.TestCase):
    """``_summarize_latency`` consumes only named timing/token measurements."""

    def test_populated_timing_and_tokens_report_decoded_throughput(self) -> None:
        timing = {
            "clock_id": "clock-1",
            "enqueued_ns": 0,
            "dispatched_ns": 100_000_000,
            "first_token_ns": 200_000_000,
            "last_token_ns": 1_100_000_000,
            "completed_ns": 1_200_000_000,
            "verifier_completed_ns": 1_300_000_000,
            "queue_ms": 100.0,
            "ttft_ms": 100.0,
            "decode_ms": 900.0,
            "task_wall_ms": 1100.0,
            "verifier_ms": 100.0,
        }
        tokens = {"completion": 11}
        trial = _trial(timing=timing, tokens=tokens)
        result = _summarize_latency([trial])
        self.assertEqual(result["population"], "scoreable_trials")
        self.assertEqual(result["scoreable_trial_count"], 1)
        self.assertEqual(result["queue_ms"]["sample_count"], 1)
        self.assertEqual(result["queue_ms"]["p50"], 100.0)
        self.assertEqual(result["true_decode_tokens_per_second"]["sample_count"], 1)
        # (11 - 1) / ((1.1e9 - 2e8) / 1e9) = 10 / 0.9 ≈ 11.111...
        self.assertAlmostEqual(result["true_decode_tokens_per_second"]["p50"], 10 / 0.9)
        self.assertEqual(
            result["true_decode_tokens_per_second"]["formula"], TRUE_DECODE_FORMULA
        )
        self.assertEqual(
            result["true_decode_tokens_per_second"]["timestamp_source"],
            TRUE_DECODE_TIMESTAMP_SOURCE,
        )

    def test_missing_timing_records_empty_distributions(self) -> None:
        # Passing ``timing=None`` omits the timing block from the trial, so
        # the latency summary should report zero samples for every field.
        result = _summarize_latency([_trial(timing=None)])
        self.assertEqual(result["scoreable_trial_count"], 1)
        self.assertEqual(result["queue_ms"]["sample_count"], 0)
        self.assertEqual(result["ttft_ms"]["sample_count"], 0)
        self.assertEqual(result["task_wall_ms"]["sample_count"], 0)
        self.assertEqual(result["verifier_ms"]["sample_count"], 0)
        self.assertEqual(result["true_decode_tokens_per_second"]["sample_count"], 0)

    def test_infrastructure_excluded_trials_excluded(self) -> None:
        # An excluded trial is not scoreable, so it contributes nothing to
        # the latency distributions.
        result = _summarize_latency([_trial(state="infrastructure_exclusion")])
        self.assertEqual(result["scoreable_trial_count"], 0)
        self.assertEqual(result["queue_ms"]["sample_count"], 0)

    def test_decode_throughput_requires_two_or_more_tokens(self) -> None:
        timing = {
            "clock_id": "c",
            "enqueued_ns": 0,
            "dispatched_ns": 1_000_000,
            "first_token_ns": 2_000_000,
            "last_token_ns": 3_000_000,
            "completed_ns": 4_000_000,
            "verifier_completed_ns": 5_000_000,
            "queue_ms": 1.0,
            "ttft_ms": 1.0,
            "decode_ms": 1.0,
            "task_wall_ms": 3.0,
            "verifier_ms": 1.0,
        }
        # completion=1: must be skipped because the formula requires >= 2.
        trial = _trial(timing=timing, tokens={"completion": 1})
        result = _summarize_latency([trial])
        self.assertEqual(result["true_decode_tokens_per_second"]["sample_count"], 0)

    def test_decode_throughput_requires_strictly_positive_interval(self) -> None:
        timing = {
            "clock_id": "c",
            "enqueued_ns": 0,
            "dispatched_ns": 1_000_000,
            "first_token_ns": 2_000_000,
            "last_token_ns": 2_000_000,  # equal to first
            "completed_ns": 4_000_000,
            "verifier_completed_ns": 5_000_000,
            "queue_ms": 1.0,
            "ttft_ms": 1.0,
            "decode_ms": 0.0,
            "task_wall_ms": 3.0,
            "verifier_ms": 1.0,
        }
        trial = _trial(timing=timing, tokens={"completion": 5})
        result = _summarize_latency([trial])
        self.assertEqual(result["true_decode_tokens_per_second"]["sample_count"], 0)

    def test_non_finite_timing_values_are_skipped(self) -> None:
        timing = {
            "clock_id": "c",
            "enqueued_ns": 0,
            "dispatched_ns": 1_000_000,
            "first_token_ns": 2_000_000,
            "last_token_ns": 3_000_000,
            "completed_ns": 4_000_000,
            "verifier_completed_ns": 5_000_000,
            "queue_ms": float("inf"),  # not finite
            "ttft_ms": -1.0,  # negative
            "decode_ms": 1.0,
            "task_wall_ms": 3.0,
            "verifier_ms": 1.0,
        }
        result = _summarize_latency([_trial(timing=timing)])
        self.assertEqual(result["queue_ms"]["sample_count"], 0)

    def test_bool_timing_fields_are_not_collected(self) -> None:
        timing = {
            "clock_id": "c",
            "enqueued_ns": 0,
            "dispatched_ns": 1_000_000,
            "first_token_ns": 2_000_000,
            "last_token_ns": 3_000_000,
            "completed_ns": 4_000_000,
            "verifier_completed_ns": 5_000_000,
            "queue_ms": True,  # bool must be excluded
            "ttft_ms": False,  # bool
            "decode_ms": 1.0,
            "task_wall_ms": 3.0,
            "verifier_ms": 1.0,
        }
        result = _summarize_latency([_trial(timing=timing)])
        self.assertEqual(result["queue_ms"]["sample_count"], 0)
        self.assertEqual(result["ttft_ms"]["sample_count"], 0)


class CacheSummaryTests(unittest.TestCase):
    """``_summarize_cache`` consumes only named cache measurements."""

    def test_cache_totals_and_rates(self) -> None:
        cache_row = {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 40,
            "misses": 60,
            "writes": 0,
            "evictions": 0,
            "restored_tokens": 0,
            "kv_bytes_peak": 0,
            "counter_reconciliation_error": 0.0,
            "cross_request_contamination": False,
        }
        result = _summarize_cache([_trial(cache=cache_row)])
        self.assertEqual(result["coverage_fraction"], 1.0)
        self.assertEqual(result["eligible_prefix_tokens"], 100)
        self.assertEqual(result["hit_tokens"], 40)
        self.assertEqual(result["effective_hit_rate"], 0.4)
        self.assertEqual(result["max_counter_reconciliation_error"], 0.0)
        self.assertEqual(result["cross_request_contamination_count"], 0)
        self.assertEqual(result["status"], "complete")

    def test_cache_partial_status_when_some_trials_have_cache(self) -> None:
        cache_row = {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 50,
            "misses": 50,
            "writes": 0,
            "evictions": 0,
            "restored_tokens": 0,
            "kv_bytes_peak": 0,
            "counter_reconciliation_error": 0.0,
            "cross_request_contamination": False,
        }
        result = _summarize_cache([_trial(cache=cache_row), _trial()])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["coverage_fraction"], 0.5)

    def test_cache_missing_status(self) -> None:
        result = _summarize_cache([_trial(), _trial()])
        self.assertEqual(result["status"], "missing")
        self.assertIsNone(result["effective_hit_rate"])
        self.assertIsNone(result["max_counter_reconciliation_error"])

    def test_cache_contamination_is_counted(self) -> None:
        cache_with_contam = {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0,
            "restored_tokens": 0,
            "kv_bytes_peak": 0,
            "counter_reconciliation_error": 0.0,
            "cross_request_contamination": True,
        }
        result = _summarize_cache([_trial(cache=cache_with_contam)])
        self.assertEqual(result["cross_request_contamination_count"], 1)

    def test_cache_max_error_is_max(self) -> None:
        cache_a = {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0,
            "restored_tokens": 0,
            "kv_bytes_peak": 0,
            "counter_reconciliation_error": 0.5,
            "cross_request_contamination": False,
        }
        cache_b = {
            "eligible_prefix_tokens": 100,
            "hit_tokens": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0,
            "restored_tokens": 0,
            "kv_bytes_peak": 0,
            "counter_reconciliation_error": 0.9,
            "cross_request_contamination": False,
        }
        result = _summarize_cache([_trial(cache=cache_a), _trial(cache=cache_b)])
        self.assertEqual(result["max_counter_reconciliation_error"], 0.9)

    def test_cache_infrastructure_excluded_excluded(self) -> None:
        # An excluded trial does not count as scoreable, so the cache block
        # reports ``coverage_fraction=None`` (no scored trials to take a
        # coverage ratio over) and ``status="complete"`` (the empty-vs-empty
        # branch when ``scored`` and ``present`` are both empty).  Either
        # way, ``eligible_prefix_tokens`` is 0.
        result = _summarize_cache([_trial(state="infrastructure_exclusion")])
        self.assertEqual(result["eligible_prefix_tokens"], 0)
        self.assertEqual(result["hit_tokens"], 0)
        self.assertIsNone(result["effective_hit_rate"])
        self.assertIsNone(result["coverage_fraction"])


class DriftSummaryTests(unittest.TestCase):
    """``_summarize_drift`` keeps the assertion manifest unified across scored trials."""

    def _drift(
        self,
        *,
        manifest: str | None = "f" * 64,
        checkpoints: list[dict] | None = None,
    ) -> dict:
        if checkpoints is None:
            checkpoints = [
                {"turn": turn, "assertions_expected": 1, "assertions_retained": 1}
                for turn in (1, 5, 10, 25, 50)
            ]
        return {
            "assertion_manifest_sha256": manifest,
            "checkpoints": checkpoints,
        }

    def test_unified_manifest_is_recorded(self) -> None:
        manifest = "f" * 64
        trials = [
            _trial(
                task_id="task-alpha",
                ordinal=0,
                drift=self._drift(manifest=manifest),
            ),
            _trial(
                task_id="task-beta",
                ordinal=0,
                drift=self._drift(manifest=manifest),
            ),
        ]
        result = _summarize_drift(trials, expected_task_ids=["task-alpha", "task-beta"])
        self.assertEqual(result["assertion_manifest_sha256"], manifest)
        self.assertEqual(result["retention_by_turn"]["1"]["retention"], 1.0)
        self.assertEqual(result["retention_by_turn"]["50"]["retention"], 1.0)
        self.assertEqual(result["long_turn_assertion_retention"], 1.0)
        self.assertEqual(result["long_turn_assertions_retained"], 10)
        self.assertEqual(result["long_turn_assertions_expected"], 10)

    def test_mismatched_manifests_rejected(self) -> None:
        trials = [
            _trial(
                task_id="task-alpha",
                ordinal=0,
                drift=self._drift(manifest="f" * 64),
            ),
            _trial(
                task_id="task-beta",
                ordinal=0,
                drift=self._drift(manifest="0" * 64),
            ),
        ]
        with self.assertRaisesRegex(
            ContractError, "different drift assertion manifests"
        ):
            _summarize_drift(trials, expected_task_ids=["task-alpha", "task-beta"])

    def test_invalid_turn_rejected(self) -> None:
        drift = self._drift(
            checkpoints=[
                {"turn": 2, "assertions_expected": 1, "assertions_retained": 1}
            ]
        )
        with self.assertRaisesRegex(ContractError, "must use unique turns"):
            _summarize_drift(
                [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
                expected_task_ids=["task-alpha"],
            )

    def test_duplicate_turn_rejected(self) -> None:
        drift = self._drift(
            checkpoints=[
                {"turn": 1, "assertions_expected": 1, "assertions_retained": 1},
                {"turn": 1, "assertions_expected": 1, "assertions_retained": 1},
            ]
        )
        with self.assertRaisesRegex(ContractError, "must use unique turns"):
            _summarize_drift(
                [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
                expected_task_ids=["task-alpha"],
            )

    def test_retained_cannot_exceed_expected(self) -> None:
        drift = self._drift(
            checkpoints=[
                {"turn": 1, "assertions_expected": 1, "assertions_retained": 2}
            ]
        )
        with self.assertRaisesRegex(ContractError, "exceed expected"):
            _summarize_drift(
                [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
                expected_task_ids=["task-alpha"],
            )

    def test_negative_integer_field_rejected(self) -> None:
        # The retained/expected fields are required to be integers >= 0.
        # Calling _integer on a negative value is forbidden.
        drift = self._drift(
            checkpoints=[
                {"turn": 1, "assertions_expected": -1, "assertions_retained": 0}
            ]
        )
        with self.assertRaisesRegex(ContractError, "integer >= 0"):
            _summarize_drift(
                [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
                expected_task_ids=["task-alpha"],
            )

    def test_checkpoints_must_be_a_list(self) -> None:
        drift = {"assertion_manifest_sha256": "f" * 64, "checkpoints": "not-a-list"}
        with self.assertRaisesRegex(ContractError, "must be an array"):
            _summarize_drift(
                [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
                expected_task_ids=["task-alpha"],
            )

    def test_partial_retention_is_recorded_per_turn(self) -> None:
        # 1 turn keeps 1 of 2, 5 turn keeps 2 of 4 (ratios are 0.5).
        checkpoints = [
            {"turn": 1, "assertions_expected": 2, "assertions_retained": 1},
            {"turn": 5, "assertions_expected": 4, "assertions_retained": 2},
            {"turn": 10, "assertions_expected": 1, "assertions_retained": 1},
            {"turn": 25, "assertions_expected": 1, "assertions_retained": 1},
            {"turn": 50, "assertions_expected": 1, "assertions_retained": 1},
        ]
        drift = self._drift(checkpoints=checkpoints)
        result = _summarize_drift(
            [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
            expected_task_ids=["task-alpha"],
        )
        self.assertEqual(result["retention_by_turn"]["1"]["retention"], 0.5)
        self.assertEqual(result["retention_by_turn"]["5"]["retention"], 0.5)
        self.assertEqual(result["long_turn_assertions_retained"], 6)
        self.assertEqual(result["long_turn_assertions_expected"], 9)

    def test_no_checkpoints_yields_none_retention(self) -> None:
        drift = {"assertion_manifest_sha256": None, "checkpoints": []}
        result = _summarize_drift(
            [_trial(task_id="task-alpha", ordinal=0, drift=drift)],
            expected_task_ids=["task-alpha"],
        )
        # No expected manifests, no checkpointed retention.
        self.assertIsNone(result["assertion_manifest_sha256"])
        self.assertIsNone(result["long_turn_assertion_retention"])

    def test_no_scoreable_trials_yields_none_metrics(self) -> None:
        # Only infrastructure-excluded trials → no scored drift info.
        result = _summarize_drift(
            [_trial(task_id="task-alpha", ordinal=0, state="infrastructure_exclusion")],
            expected_task_ids=["task-alpha"],
        )
        self.assertIsNone(result["verifier_flip_rate"])
        self.assertIsNone(result["decision_disagreement"])
        self.assertEqual(result["eligible_repeated_task_count"], 0)

    def test_drift_non_mapping_value_is_ignored(self) -> None:
        # ``drift`` is not a Mapping on this trial — the helper must skip
        # the drift block silently because task-level scoring continues.
        drift_string = "not-a-dict"
        trial = _trial(
            task_id="task-alpha", ordinal=0, state="passed", drift=drift_string
        )
        result = _summarize_drift([trial], expected_task_ids=["task-alpha"])
        self.assertIsNone(result["assertion_manifest_sha256"])
        self.assertEqual(result["retention_by_turn"]["1"]["retention"], None)

    def test_repeated_disagreeing_states_increase_disagreement(self) -> None:
        # Two scored attempts on the same task disagree (one passed, one
        # model_failure).  The disagreement index rises above zero and
        # ``verifier_flip_rate`` becomes 1.0 because the states differ.
        drift = {
            "assertion_manifest_sha256": "f" * 64,
            "checkpoints": [
                {"turn": turn, "assertions_expected": 1, "assertions_retained": 1}
                for turn in (1, 5, 10, 25, 50)
            ],
        }
        trials = [
            _trial(task_id="task-alpha", ordinal=0, state="passed", drift=drift),
            _trial(
                task_id="task-alpha",
                ordinal=1,
                state="model_failure",
                drift=drift,
                pair_key="2" * 64,
                cell_id="2" * 64,
            ),
        ]
        result = _summarize_drift(trials, expected_task_ids=["task-alpha"])
        self.assertEqual(result["eligible_repeated_task_count"], 1)
        self.assertEqual(result["verifier_flip_rate"], 1.0)
        self.assertGreater(result["decision_disagreement"], 0.0)


class RuntimeStabilitySummaryTests(unittest.TestCase):
    """``_summarize_runtime_stability`` builds the integrity counter gate."""

    def test_complete_coverage_sums_all_counters(self) -> None:
        integrity = {"ooms": 2, "deadlocks": 1, "unexplained_restarts": 0}
        result = _summarize_runtime_stability(
            [_trial(integrity=integrity), _trial(integrity=integrity)]
        )
        self.assertEqual(result["attempted_trial_count"], 2)
        self.assertEqual(result["covered_trial_count"], 2)
        self.assertEqual(result["coverage_fraction"], 1.0)
        self.assertEqual(result["ooms"], 4)
        self.assertEqual(result["deadlocks"], 2)
        self.assertEqual(result["unexplained_restarts"], 0)
        self.assertEqual(result["status"], "complete")

    def test_partial_when_some_trials_missing_integrity(self) -> None:
        with_integrity = _trial(
            integrity={"ooms": 0, "deadlocks": 0, "unexplained_restarts": 0}
        )
        result = _summarize_runtime_stability([with_integrity, _trial()])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["coverage_fraction"], 0.5)
        self.assertEqual(result["covered_trial_count"], 1)

    def test_missing_when_no_trials_have_integrity(self) -> None:
        result = _summarize_runtime_stability([_trial(), _trial()])
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["coverage_fraction"], 0.0)
        self.assertEqual(result["ooms"], 0)

    def test_partial_fields_are_ignored(self) -> None:
        # A negative ooms count skips the trial from "covered".
        bad = _trial(integrity={"ooms": -1, "deadlocks": 0, "unexplained_restarts": 0})
        result = _summarize_runtime_stability([bad])
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["ooms"], 0)

    def test_bool_integrity_fields_are_ignored(self) -> None:
        # True/False values are not integers; the trial must be skipped.
        bad = _trial(
            integrity={"ooms": True, "deadlocks": False, "unexplained_restarts": False}
        )
        result = _summarize_runtime_stability([bad])
        self.assertEqual(result["status"], "missing")


class PerformanceTaskIdsSha256Tests(unittest.TestCase):
    """``performance_task_ids_sha256`` is re-exported through the module surface."""

    def test_re_exported_helper_is_callable(self) -> None:
        self.assertEqual(
            performance_task_ids_sha256(["task-alpha", "task-beta"]),
            performance_task_ids_sha256(["task-beta", "task-alpha"]),
        )

    def test_rejects_non_sequence(self) -> None:
        with self.assertRaises(ContractError):
            performance_task_ids_sha256("not-a-sequence")

    def test_rejects_empty_or_duplicates(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty and unique"):
            performance_task_ids_sha256([])
        with self.assertRaisesRegex(ContractError, "non-empty and unique"):
            performance_task_ids_sha256(["t", "t"])


class QualityInteropTests(unittest.TestCase):
    """Cross-helper integration pin to keep the API wired correctly."""

    def test_validate_arm_then_counts_quality_summaries(self) -> None:
        # Combine ``_validate_arm`` (with the trial patch) and the
        # summarizers that depend on its ``trials`` output: ``_counts``,
        # ``_quality``, etc.  This protects against API regressions between
        # the validation step and the summary step.
        patches = mock.patch.multiple(
            aggregate_contracts,
            validate_trial_record=lambda value: copy.deepcopy(value),
            trial_scoreability_reasons=lambda value: [],
            trial_sha256=lambda value: sha256_hex(canonical_json_bytes(value)),
        )
        with patches:
            trials = [
                _trial(task_id="task-alpha", ordinal=0, state="passed"),
                _trial(task_id="task-beta", ordinal=0, state="model_failure"),
            ]
            validated = _validate_arm(
                trials,
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                arm="arm",
            )
            counts = _counts(validated["trials"])
            quality_summary = _quality(
                validated["trials"],
                expected_task_ids=["task-alpha", "task-beta"],
                attempts_per_task=1,
                hashes=validated["hashes"],
                resamples=8,
            )
            self.assertEqual(counts["scored"], 2)
            self.assertEqual(quality_summary["pass_at_1"]["estimate"], 0.5)


if __name__ == "__main__":
    unittest.main()
