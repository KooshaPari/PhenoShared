"""Deep branch coverage for pheno.evidence.trial_contracts.

These tests target the helper validators and rejection branches that the
existing high-level fixtures leave untouched. They live next to (not in)
``test_eval_trial_contract`` / ``test_eval_trial_artifacts`` so each suite
remains focused; together they push the public ``validate_trial_record``,
``validate_trial_artifact_bundle``, and ``trial_scoreability_reasons`` entry
points plus every private validator helper above 85% line coverage.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from pheno.evidence import trial_contracts as tc
from pheno.evidence.contracts import ContractError
from pheno.evidence.trial_contracts import (
    TRIAL_SCHEMA_VERSION,
    _validate_intent_graph_artifact,
    _validate_parser,
    _validate_steps,
    trial_scoreability_reasons,
    trial_sha256,
    validate_trial_artifact_bundle,
    validate_trial_record,
)

VALID = Path(__file__).parent / "fixtures" / "eval_contracts" / "trial_valid.json"
BUNDLE = Path(__file__).parent / "fixtures" / "eval_contracts" / "trial_bundle"


def fresh_record() -> dict[str, Any]:
    """Return a deep copy of the canonical valid record used as a mutation base."""

    return json.loads(VALID.read_text(encoding="utf-8"))


def bundle_record() -> dict[str, Any]:
    """Return a deep copy of the canonical trial-bundle record used as a mutation base."""

    return json.loads((BUNDLE / "trial_bundle_record.json").read_text(encoding="utf-8"))


class HelperValidatorTests(unittest.TestCase):
    """Direct coverage of the private scalar helpers."""

    def test_object_helper_rejects_non_mapping(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            tc._object("not-a-mapping", "anywhere")

    def test_exact_helper_lists_missing_and_unknown_fields(self) -> None:
        with self.assertRaisesRegex(ContractError, "missing fields"):
            tc._exact({}, {"required"}, "x")
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            tc._exact({"extra": 1}, set(), "x")

    def test_text_helper_rejects_non_string_and_whitespace(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            tc._text(None, "p")
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            tc._text("   ", "p")

    def test_boolean_helper_rejects_non_bool(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be boolean"):
            tc._boolean(1, "p")  # type: ignore[arg-type]

    def test_number_helper_rejects_bool_non_numeric_and_out_of_range(self) -> None:
        with self.assertRaisesRegex(ContractError, "finite number"):
            tc._number(True, "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            tc._number("x", "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            tc._number(float("nan"), "p")
        with self.assertRaisesRegex(ContractError, "finite number"):
            tc._number(float("inf"), "p")
        with self.assertRaisesRegex(ContractError, "must be >= -1"):
            tc._number(-2.0, "p", minimum=-1.0)
        with self.assertRaisesRegex(ContractError, "must be <= 1"):
            tc._number(2.0, "p", maximum=1.0)
        # None+nullable path returns None
        self.assertIsNone(tc._number(None, "p", nullable=True))
        # No bounds = identity cast
        self.assertEqual(tc._number(2.5, "p"), 2.5)

    def test_integer_helper_rejects_non_int_and_below_minimum(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            tc._integer("x", "p")
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            tc._integer(-1, "p", minimum=0)
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            tc._integer(True, "p")
        self.assertIsNone(tc._integer(None, "p", nullable=True))

    def test_sha256_helper_rejects_non_hex_and_too_short(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            tc._sha256(None, "p")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            tc._sha256("z" * 64, "p")
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            tc._sha256("a" * 63, "p")

    def test_close_helper_rejects_non_number_and_mismatch(self) -> None:
        # Non-number path
        with self.assertRaisesRegex(ContractError, "finite number"):
            tc._close("not-numeric", 1.0, "p")
        # Mismatch path
        with self.assertRaisesRegex(ContractError, "reconcile"):
            tc._close(0.0, 5.0, "p")


class ParserValidatorTests(unittest.TestCase):
    """Direct coverage of ``_validate_parser``."""

    def test_parser_rejects_missing_fields_and_blanks(self) -> None:
        with self.assertRaisesRegex(ContractError, "missing fields"):
            tc._validate_parser({"name": "x"}, "p")
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            tc._validate_parser({"name": "", "revision": "r"}, "p")
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            tc._validate_parser({"name": "x", "revision": "   "}, "p")

    def test_parser_accepts_minimal_valid_input(self) -> None:
        tc._validate_parser({"name": "n", "revision": "r"}, "p")


class CellSubValidatorBranchTests(unittest.TestCase):
    """Field-by-field rejections inside ``_validate_cell`` not covered above."""

    def test_container_digest_must_be_oci_sha256(self) -> None:
        record = fresh_record()
        record["cell"]["runtime"]["container_digest"] = "not-oci-1"
        with self.assertRaisesRegex(ContractError, "sha256"):
            validate_trial_record(record)

    def test_device_ids_must_be_non_empty(self) -> None:
        record = fresh_record()
        record["cell"]["device"]["device_ids"] = []
        with self.assertRaisesRegex(ContractError, "non-empty"):
            validate_trial_record(record)

    def test_device_ids_must_be_unique(self) -> None:
        record = fresh_record()
        record["cell"]["device"]["device_ids"] = ["gpu:0", "gpu:0"]
        with self.assertRaisesRegex(ContractError, "unique"):
            validate_trial_record(record)

    def test_parser_revision_unknown_field_is_rejected(self) -> None:
        record = fresh_record()
        record["cell"]["model"]["reasoning_parser"]["extra"] = 1
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_trial_record(record)


class OutcomeBranchTests(unittest.TestCase):
    """``_validate_outcome`` state / reason / scoreable cross-checks."""

    def test_outcome_state_must_be_one_of_three(self) -> None:
        record = fresh_record()
        record["outcome"]["state"] = "unknown"
        with self.assertRaisesRegex(ContractError, "outcome.state is invalid"):
            validate_trial_record(record)

    def test_outcome_reason_for_model_failure_must_be_allowed(self) -> None:
        record = fresh_record()
        record["outcome"] = {
            "state": "model_failure",
            "reason": "nope",
            "scoreable": True,
            "reward": 0.0,
            "verifier_components": {"task_pass": 0.0},
        }
        record["accepted_steps"] = []
        record["total_weight"] = 0.0
        with self.assertRaisesRegex(ContractError, "outcome.reason is invalid"):
            validate_trial_record(record)

    def test_infrastructure_exclusion_with_reward_is_rejected(self) -> None:
        record = fresh_record()
        record["outcome"] = {
            "state": "infrastructure_exclusion",
            "reason": "network_error",
            "scoreable": False,
            "reward": 0.5,
            "verifier_components": {},
        }
        record["accepted_steps"] = []
        record["total_weight"] = 0.0
        with self.assertRaisesRegex(ContractError, "null reward and empty"):
            validate_trial_record(record)

    def test_model_failure_with_null_reward_is_rejected(self) -> None:
        record = fresh_record()
        record["outcome"] = {
            "state": "model_failure",
            "reason": "verifier_fail",
            "scoreable": True,
            "reward": None,
            "verifier_components": {"task_pass": 0.0},
        }
        record["accepted_steps"] = []
        record["total_weight"] = 0.0
        with self.assertRaisesRegex(ContractError, "require a finite reward"):
            validate_trial_record(record)


class StepsBranchTests(unittest.TestCase):
    """Direct rejections inside ``_validate_steps``."""

    def test_accepted_steps_must_be_list(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an array"):
            tc._validate_steps("not-a-list", 0.0, "passed", True)

    def test_duplicate_step_ids_are_rejected(self) -> None:
        record = fresh_record()
        first = copy.deepcopy(record["accepted_steps"][0])
        first["predicate_sha256"] = "9" * 64
        record["accepted_steps"].append(first)
        record["total_weight"] = 2.0
        with self.assertRaisesRegex(ContractError, "duplicate step_id"):
            validate_trial_record(record)

    def test_depends_on_must_be_list_of_strings_and_unique(self) -> None:
        record = fresh_record()
        record["accepted_steps"][0]["depends_on"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            validate_trial_record(record)

        record = fresh_record()
        record["accepted_steps"][0]["depends_on"] = [123]  # type: ignore[list-item]
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_trial_record(record)

        record = fresh_record()
        record["accepted_steps"][0]["depends_on"] = ["task-pass", "task-pass"]
        with self.assertRaisesRegex(ContractError, "unique and cannot contain"):
            validate_trial_record(record)

        record = fresh_record()
        record["accepted_steps"][0]["depends_on"] = ["task-pass"]
        with self.assertRaisesRegex(ContractError, "unique and cannot contain"):
            validate_trial_record(record)

    def test_false_to_true_and_terminal_bools_must_be_true(self) -> None:
        record = fresh_record()
        record["accepted_steps"][0]["false_to_true_transition"] = False
        with self.assertRaisesRegex(ContractError, "false to true"):
            validate_trial_record(record)

        record = fresh_record()
        record["accepted_steps"][0]["terminal_reverified"] = False
        with self.assertRaisesRegex(ContractError, "terminally reverified"):
            validate_trial_record(record)

    def test_cyclic_dependency_is_rejected(self) -> None:
        record = fresh_record()
        record["accepted_steps"][0]["step_id"] = "loop-a"
        record["accepted_steps"][0]["depends_on"] = ["loop-b"]
        record["accepted_steps"].append(copy.deepcopy(record["accepted_steps"][0]))
        record["accepted_steps"][1]["step_id"] = "loop-b"
        record["accepted_steps"][1]["depends_on"] = ["loop-a"]
        record["accepted_steps"][1]["predicate_sha256"] = "9" * 64
        record["accepted_steps"][0]["predicate_sha256"] = "8" * 64
        record["total_weight"] = 2.0
        with self.assertRaisesRegex(ContractError, "cycle"):
            validate_trial_record(record)

    def test_total_weight_mismatch_is_rejected(self) -> None:
        record = fresh_record()
        record["accepted_steps"][0]["weight"] = 0.5
        record["total_weight"] = 0.5
        # Now flip weight back up to 1.0 but keep total 0.5 (mismatch)
        record["accepted_steps"][0]["weight"] = 1.0
        with self.assertRaisesRegex(ContractError, "total_weight"):
            validate_trial_record(record)


class ToolsBranchTests(unittest.TestCase):
    """Count chain + gold-label branching."""

    def test_emitted_parsed_valid_executed_must_be_monotonic(self) -> None:
        record = fresh_record()
        record["tools"]["emitted_candidates"] = 0
        with self.assertRaisesRegex(ContractError, "do not reconcile"):
            validate_trial_record(record)

    def test_schema_valid_but_wrong_must_not_exceed_schema_valid(self) -> None:
        record = fresh_record()
        record["tools"]["schema_valid_but_wrong"] = 5
        with self.assertRaisesRegex(ContractError, "schema_valid_but_wrong"):
            validate_trial_record(record)

    def test_semantically_correct_must_not_exceed_executed(self) -> None:
        record = fresh_record()
        record["tools"]["executed_calls"] = 1
        record["tools"]["semantically_correct_calls"] = 5
        with self.assertRaisesRegex(ContractError, "exceeds executed_calls"):
            validate_trial_record(record)

    def test_gold_labels_require_exact_match_counts(self) -> None:
        record = fresh_record()
        # Keep emitted / parsed / valid / executed monotonic and bump the
        # chain to 5 so gold_labeled_calls=2 still respects gold <= executed.
        for field in (
            "emitted_candidates",
            "parsed_calls",
            "schema_valid_calls",
            "executed_calls",
        ):
            record["tools"][field] = 5
        record["tools"]["semantically_correct_calls"] = 2
        record["tools"]["gold_labeled_calls"] = 2
        # exact_tool_matches / exact_argument_matches remain None
        with self.assertRaisesRegex(ContractError, "require exact tool"):
            validate_trial_record(record)

    def test_exact_match_counts_must_be_ordered(self) -> None:
        record = fresh_record()
        # Keep emitted / parsed / valid / executed monotonic and large enough
        # that gold_labeled_calls and exact_* comparisons reach the ordering check.
        for field in (
            "emitted_candidates",
            "parsed_calls",
            "schema_valid_calls",
            "executed_calls",
        ):
            record["tools"][field] = 10
        record["tools"]["gold_labeled_calls"] = 5
        record["tools"]["exact_tool_matches"] = 1
        record["tools"]["exact_argument_matches"] = 2
        with self.assertRaisesRegex(ContractError, "exact match counts must satisfy"):
            validate_trial_record(record)


class TimingBranchTests(unittest.TestCase):
    """Lifecycle-monotonicity + token-latency cross-checks."""

    def test_timing_lifecycle_must_be_monotonic(self) -> None:
        record = fresh_record()
        record["timing"]["dispatched_ns"] = record["timing"]["enqueued_ns"] - 1
        with self.assertRaisesRegex(ContractError, "monotonic"):
            validate_trial_record(record)

    def test_first_and_last_token_timestamps_must_share_nullness(self) -> None:
        record = fresh_record()
        record["timing"]["first_token_ns"] = 1300000000
        record["timing"]["last_token_ns"] = None
        with self.assertRaisesRegex(ContractError, "first/last token"):
            validate_trial_record(record)

    def test_token_timestamps_must_lie_within_lifecycle(self) -> None:
        record = fresh_record()
        record["timing"]["first_token_ns"] = 2400000000  # past completed_ns
        with self.assertRaisesRegex(ContractError, "token timestamps"):
            validate_trial_record(record)

    def test_token_latency_must_be_null_when_no_token_timestamps(self) -> None:
        record = fresh_record()
        record["timing"]["first_token_ns"] = None
        record["timing"]["last_token_ns"] = None
        record["timing"]["ttft_ms"] = 1.0
        record["timing"]["decode_ms"] = 0.0
        with self.assertRaisesRegex(ContractError, "token latency"):
            validate_trial_record(record)


class TokensBranchTests(unittest.TestCase):
    """``_validate_tokens`` constraint families."""

    def test_cached_read_must_not_exceed_prompt(self) -> None:
        record = fresh_record()
        record["tokens"]["cached_read"] = 200  # > prompt=100
        with self.assertRaisesRegex(ContractError, "cached_read"):
            validate_trial_record(record)

    def test_reasoning_must_not_exceed_completion(self) -> None:
        record = fresh_record()
        record["tokens"]["reasoning"] = 999
        with self.assertRaisesRegex(ContractError, "reasoning"):
            validate_trial_record(record)

    def test_draft_proposed_and_accepted_must_share_nullness(self) -> None:
        record = fresh_record()
        record["tokens"]["draft_proposed"] = 1
        record["tokens"]["draft_accepted"] = None
        with self.assertRaisesRegex(ContractError, "draft token counts"):
            validate_trial_record(record)

    def test_completion_requires_token_timestamps(self) -> None:
        record = fresh_record()
        record["timing"]["first_token_ns"] = None
        record["timing"]["last_token_ns"] = None
        record["timing"]["ttft_ms"] = None
        record["timing"]["decode_ms"] = None
        # completion is still 20 -> must require token timestamps
        with self.assertRaisesRegex(ContractError, "completion tokens require"):
            validate_trial_record(record)


class CacheBranchTests(unittest.TestCase):
    """``_validate_cache`` ceiling enforcement."""

    def test_hit_tokens_must_not_exceed_eligible_prefix(self) -> None:
        record = fresh_record()
        record["cache"]["hit_tokens"] = 9999
        with self.assertRaisesRegex(ContractError, "hit_tokens"):
            validate_trial_record(record)


class ResourcesBranchTests(unittest.TestCase):
    """Range and type checks inside ``_validate_resources``."""

    def test_sampling_interval_must_be_at_least_floor(self) -> None:
        record = fresh_record()
        # 0.0 passes the finite-number check but fails the >= 1e-15 minimum;
        # a negative value triggers the "<= 0" path which is "finite number".
        record["resources"]["sampling_interval_ms"] = 0.0
        with self.assertRaisesRegex(ContractError, "must be >= 1e-15"):
            validate_trial_record(record)

    def test_coverage_fraction_must_be_in_unit_interval(self) -> None:
        record = fresh_record()
        record["resources"]["coverage_fraction"] = 1.5
        with self.assertRaisesRegex(ContractError, "must be <= 1"):
            validate_trial_record(record)

    def test_gpu_util_pct_must_be_0_to_100(self) -> None:
        record = fresh_record()
        record["resources"]["gpu_util_mean_pct"] = 250.0
        with self.assertRaisesRegex(ContractError, "must be <= 100"):
            validate_trial_record(record)

    def test_battery_delta_pct_out_of_range(self) -> None:
        record = fresh_record()
        record["resources"]["battery_delta_pct"] = -150.0
        with self.assertRaisesRegex(ContractError, "must be >= -100"):
            validate_trial_record(record)

    def test_thermal_state_must_be_non_empty_text_when_present(self) -> None:
        record = fresh_record()
        record["resources"]["os_thermal_state"] = "   "
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            validate_trial_record(record)


class DriftBranchTests(unittest.TestCase):
    """``_validate_drift`` array shape and bound enforcement."""

    def test_drift_checkpoints_must_be_an_array(self) -> None:
        record = fresh_record()
        record["drift"]["checkpoints"] = "not-a-list"
        with self.assertRaisesRegex(ContractError, "must be an array"):
            validate_trial_record(record)

    def test_drift_turn_must_be_in_allowed_set(self) -> None:
        record = fresh_record()
        record["drift"]["checkpoints"][0]["turn"] = 2
        with self.assertRaisesRegex(ContractError, "must be one of 1, 5, 10"):
            validate_trial_record(record)

    def test_drift_checkpoints_unknown_field_is_rejected(self) -> None:
        record = fresh_record()
        record["drift"]["checkpoints"][0]["note"] = "extra"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_trial_record(record)


class CostBranchTests(unittest.TestCase):
    """``_validate_cost`` completeness-state polarity."""

    def test_cost_completeness_must_be_one_of_two(self) -> None:
        record = fresh_record()
        record["cost"]["completeness"] = "unknown"
        with self.assertRaisesRegex(ContractError, "completeness"):
            validate_trial_record(record)

    def test_complete_cost_requires_all_components(self) -> None:
        record = fresh_record()
        record["cost"]["provider_usd"] = None
        with self.assertRaisesRegex(ContractError, "complete cost requires"):
            validate_trial_record(record)


class IntegrityBranchTests(unittest.TestCase):
    """``_validate_integrity`` cross-checks with tools / cache / outcome."""

    def test_risky_action_bypass_count_must_match_tools(self) -> None:
        record = fresh_record()
        record["integrity"]["risky_action_bypasses"] = 1
        with self.assertRaisesRegex(ContractError, "risky-action count"):
            validate_trial_record(record)

    def test_orphan_call_count_must_match_tools(self) -> None:
        record = fresh_record()
        record["integrity"]["orphan_calls"] = 1
        with self.assertRaisesRegex(ContractError, "orphan-call count"):
            validate_trial_record(record)

    def test_cache_contamination_flag_must_match(self) -> None:
        record = fresh_record()
        record["cache"]["cross_request_contamination"] = True
        with self.assertRaisesRegex(ContractError, "contamination"):
            validate_trial_record(record)

    def test_ooms_must_reflect_outcome(self) -> None:
        record = fresh_record()
        # outcome is passed; integrity.ooms must be 0
        record["integrity"]["ooms"] = 1
        with self.assertRaisesRegex(ContractError, "ooms does not match"):
            validate_trial_record(record)


class ArtifactPathBranchTests(unittest.TestCase):
    """Path-safety rejections inside ``_validate_artifacts``."""

    def test_absolute_artifact_path_is_rejected(self) -> None:
        record = fresh_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "/etc/passwd"
        with self.assertRaisesRegex(ContractError, "safe relative"):
            validate_trial_record(record)

    def test_dotdot_artifact_path_is_rejected(self) -> None:
        record = fresh_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "../escape.json"
        with self.assertRaisesRegex(ContractError, "safe relative"):
            validate_trial_record(record)

    def test_duplicate_artifact_paths_are_rejected(self) -> None:
        record = fresh_record()
        record["artifacts"]["verifier_outputs"].append(copy.deepcopy(
            record["artifacts"]["verifier_outputs"][0]
        ))
        with self.assertRaisesRegex(ContractError, "unique"):
            validate_trial_record(record)

    def test_drive_letter_in_path_is_rejected(self) -> None:
        record = fresh_record()
        record["artifacts"]["verifier_outputs"][0]["path"] = "C:outside.json"
        with self.assertRaisesRegex(ContractError, "safe relative"):
            validate_trial_record(record)


class RootRecordBranchTests(unittest.TestCase):
    """Top-level ``validate_trial_record`` cross-checks."""

    def test_schema_version_must_match(self) -> None:
        record = fresh_record()
        record["schema_version"] = "pheno.eval.trial.v1"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            validate_trial_record(record)

    def test_cell_id_mismatch_is_detected(self) -> None:
        record = fresh_record()
        record["cell_id"] = "f" * 64
        with self.assertRaisesRegex(ContractError, "cell_id does not match"):
            validate_trial_record(record)

    def test_pair_key_mismatch_is_detected(self) -> None:
        record = fresh_record()
        record["pair_key"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "pair_key does not match"):
            validate_trial_record(record)

    def test_invalid_evidence_class_and_run_mode(self) -> None:
        record = fresh_record()
        record["evidence_class"] = "vendor_measured"
        with self.assertRaisesRegex(ContractError, "evidence_class must"):
            validate_trial_record(record)

        record = fresh_record()
        record["run_mode"] = "fast"
        with self.assertRaisesRegex(ContractError, "run_mode must"):
            validate_trial_record(record)

    def test_root_secret_is_rejected_even_when_integrity_silent(self) -> None:
        record = fresh_record()
        record["integrity"]["secrets_absent"] = False
        record["trial_id"] = "Bearer " + "a" * 24
        with self.assertRaisesRegex(ContractError, "credential"):
            validate_trial_record(record)


class StrictJsonObjectTests(unittest.TestCase):
    """``_strict_json_object`` parsing rules (used inside the bundle validator)."""

    def test_non_utf8_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "strict UTF-8"):
            tc._strict_json_object(b"\xff\xfe not utf-8", "p")

    def test_duplicate_object_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "duplicate object key"):
            tc._strict_json_object(
                b'{"k": 1, "k": 2}', "p"
            )

    def test_non_finite_constants_are_rejected(self) -> None:
        # json.loads default for NaN is to accept it under allow_nan=True; our
        # parse_constant hook must raise instead so the wrapped ContractError fires.
        with self.assertRaisesRegex(ContractError, "strict UTF-8 JSON"):
            tc._strict_json_object(b"NaN", "p")

    def test_non_object_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "must contain a JSON object"):
            tc._strict_json_object(b"[1, 2, 3]", "p")

    def test_arbitrary_nested_object_round_trips(self) -> None:
        out = tc._strict_json_object(
            b'{"a": 1, "b": {"c": [1, 2]}}', "p"
        )
        self.assertEqual(out["a"], 1)
        self.assertEqual(out["b"]["c"], [1, 2])


class IntentGraphArtifactTests(unittest.TestCase):
    """``_validate_intent_graph_artifact`` exhaustive branch coverage."""

    @staticmethod
    def _graph(**overrides: Any) -> dict[str, Any]:
        graph = {
            "schema_version": 1,
            "run_id": "run-x",
            "suite": "fixture",
            "created_at": "2026-07-14T00:00:00+00:00",
            "metadata": {},
            "nodes": [
                {
                    "id": "root",
                    "kind": "run",
                    "name": "root",
                    "status": "finished",
                    "started_at": "2026-07-14T00:00:00+00:00",
                    "finished_at": "2026-07-14T00:00:01+00:00",
                    "duration_ms": 1000.0,
                    "attributes": {},
                },
                {
                    "id": "leaf",
                    "kind": "verifier",
                    "name": "leaf",
                    "status": "finished",
                    "started_at": None,
                    "finished_at": None,
                    "duration_ms": None,
                    "attributes": {},
                },
            ],
            "edges": [{"source": "root", "target": "leaf", "kind": "contains"}],
        }
        graph.update(overrides)
        return graph

    def test_schema_version_must_equal_one(self) -> None:
        with self.assertRaisesRegex(ContractError, "schema_version must be integer 1"):
            _validate_intent_graph_artifact(
                self._graph(schema_version=2), expected_run_id="run-x"
            )

    def test_run_id_must_match_trial(self) -> None:
        with self.assertRaisesRegex(ContractError, "does not match"):
            _validate_intent_graph_artifact(
                self._graph(run_id="other"), expected_run_id="run-x"
            )

    def test_nodes_must_be_a_non_empty_array(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-empty array"):
            _validate_intent_graph_artifact(
                self._graph(nodes=[]), expected_run_id="run-x"
            )

    def test_node_kind_must_be_allowed(self) -> None:
        graph = self._graph()
        graph["nodes"][1]["kind"] = "bogus"
        with self.assertRaisesRegex(ContractError, "kind is invalid"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_duplicate_node_ids_are_rejected(self) -> None:
        graph = self._graph()
        graph["nodes"][1]["id"] = graph["nodes"][0]["id"]
        with self.assertRaisesRegex(ContractError, "duplicate node id"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_edge_self_loop_is_rejected(self) -> None:
        graph = self._graph()
        graph["edges"][0]["target"] = "root"
        with self.assertRaisesRegex(ContractError, "self edges"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_edge_to_unknown_node_is_rejected(self) -> None:
        graph = self._graph()
        graph["edges"][0]["target"] = "ghost"
        with self.assertRaisesRegex(ContractError, "unknown node"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_edge_kind_must_be_allowed(self) -> None:
        graph = self._graph()
        graph["edges"][0]["kind"] = "bogus"
        with self.assertRaisesRegex(ContractError, "kind is invalid"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_cycle_in_intent_graph_is_rejected(self) -> None:
        graph = self._graph()
        graph["nodes"][0]["id"] = "a"
        graph["nodes"][1]["id"] = "b"
        graph["edges"] = [
            {"source": "a", "target": "b", "kind": "contains"},
            {"source": "b", "target": "a", "kind": "contains"},
        ]
        with self.assertRaisesRegex(ContractError, "contains a cycle"):
            _validate_intent_graph_artifact(graph, expected_run_id="run-x")

    def test_acyclic_two_node_graph_round_trip(self) -> None:
        result = _validate_intent_graph_artifact(
            self._graph(), expected_run_id="run-x"
        )
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["run_id"], "run-x")
        self.assertEqual(result["node_count"], 2)
        self.assertEqual(result["edge_count"], 1)
        self.assertEqual(result["root_node_count"], 1)


class BundleDeclarationsTests(unittest.TestCase):
    """``_bundle_declarations`` declarative roles."""

    def test_bundle_declarations_include_patch_when_set(self) -> None:
        record = bundle_record()
        # The shared fixture declares patch as null; populate it with a
        # syntactically valid artifact declaration to exercise the inclusion
        # branch in ``_bundle_declarations``.
        record["artifacts"]["patch"] = {
            "path": "changes.patch",
            "sha256": "6" * 64,
        }
        declarations = tc._bundle_declarations(record)
        roles = [role for role, _, _ in declarations]
        self.assertIn("atif_trajectory", roles)
        self.assertIn("intent_graph", roles)
        self.assertIn("verifier_output", roles)
        self.assertIn("patch", roles)

    def test_bundle_declarations_skip_patch_when_null(self) -> None:
        record = bundle_record()
        record["artifacts"]["patch"] = None
        declarations = tc._bundle_declarations(record)
        roles = [role for role, _, _ in declarations]
        self.assertNotIn("patch", roles)


class ArtifactBundleBranchTests(unittest.TestCase):
    """End-to-end bundle validation failures that complement the existing tests."""

    def test_artifact_root_must_be_a_directory(self) -> None:
        record = bundle_record()
        with tempfile.TemporaryDirectory() as temporary:
            file_path = Path(temporary) / "not-a-dir.json"
            file_path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "must be a directory"):
                validate_trial_artifact_bundle(record, file_path)

    def test_invalid_record_never_resolves_files(self) -> None:
        record = bundle_record()
        record["schema_version"] = "pheno.eval.trial.v0"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            validate_trial_artifact_bundle(record, BUNDLE)

    def test_duplicate_resolved_targets_are_rejected(self) -> None:
        record = bundle_record()
        # Two distinct relative paths must not resolve to the same physical
        # file.  We rely on ``os.symlink`` because hard links on Windows are
        # not collapsed by ``Path.resolve``.  Skip the test if the host
        # refuses symlink creation (some hardened Windows configurations).
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "shared.json"
            payload = b'{"k": 1}'
            real.write_bytes(payload)
            (root / "sub").mkdir()
            link = root / "sub" / "linked.json"
            try:
                os.symlink(real, link)
            except (OSError, NotImplementedError) as exc:  # pragma: no cover
                self.skipTest(f"host cannot create symlinks: {exc}")
            # Sibling copy sharing the same bytes but distinct inode.  This
            # keeps the artifact-path uniqueness check satisfied while still
            # letting the duplicate-resolved-target branch fire.
            alias = root / "alias.json"
            alias.write_bytes(payload)

            digest = hashlib.sha256(payload).hexdigest()
            record["artifacts"]["atif_trajectory"]["path"] = "shared.json"
            record["artifacts"]["intent_graph"]["path"] = "sub/linked.json"
            record["artifacts"]["verifier_outputs"][0]["path"] = "alias.json"
            record["artifacts"]["atif_trajectory"]["sha256"] = digest
            record["artifacts"]["intent_graph"]["sha256"] = digest
            record["artifacts"]["verifier_outputs"][0]["sha256"] = digest

            with self.assertRaisesRegex(ContractError, "resolve to the same"):
                validate_trial_artifact_bundle(record, root)


class ScoreabilityBranchTests(unittest.TestCase):
    """Every ``trial_scoreability_reasons`` branch not otherwise exercised."""

    def test_requires_local_measured_and_execute(self) -> None:
        record = fresh_record()
        record["evidence_class"] = "vendor"
        record["run_mode"] = "replay"
        reasons = trial_scoreability_reasons(record)
        self.assertIn("evidence_class is not local_measured", reasons)
        self.assertIn("run_mode is not execute", reasons)

    def test_integrity_required_true_fields_list_reasons(self) -> None:
        record = fresh_record()
        record["integrity"]["secrets_absent"] = False
        record["integrity"]["held_out"] = False
        record["integrity"]["risky_action_gate_enabled"] = False
        record["integrity"]["verifier_untampered"] = False
        record["integrity"]["atif_valid"] = False
        record["integrity"]["artifacts_valid"] = False
        reasons = trial_scoreability_reasons(record)
        for needle in (
            "secret-absence assertion",
            "held-out",
            "risky-action gate",
            "verifier integrity",
            "ATIF trajectory",
            "artifact verification failed",
        ):
            self.assertTrue(
                any(needle in r for r in reasons),
                msg=f"missing reason containing {needle!r}; got {reasons!r}",
            )

    def test_orphan_calls_and_risky_bypasses_are_reported(self) -> None:
        record = fresh_record()
        # Mirror integrity count in tools so the integrity cross-check passes;
        # the scoreability reasons only inspect the integrity / tools fields.
        record["integrity"]["risky_action_bypasses"] = 1
        record["integrity"]["orphan_calls"] = 1
        # ``integrity.cross_request_contamination`` must mirror the cache flag.
        record["cache"]["cross_request_contamination"] = True
        record["integrity"]["cross_request_contamination"] = True
        record["tools"]["risky_action_bypasses"] = 1
        record["tools"]["orphan_calls"] = 1
        record["tools"]["unauthorized_attempts"] = 1
        record["tools"]["orphan_observations"] = 1
        reasons = trial_scoreability_reasons(record)
        for needle in (
            "integrity.risky_action_bypasses is nonzero",
            "integrity.orphan_calls is nonzero",
            "unauthorized tool attempts",
            "orphan tool observations",
            "cross-request cache contamination",
        ):
            self.assertTrue(
                any(needle in r for r in reasons),
                msg=f"missing reason containing {needle!r}",
            )

    def test_resource_below_coverage_and_peak_memory_are_reported(self) -> None:
        record = fresh_record()
        record["resources"]["coverage_fraction"] = 0.5
        record["resources"]["peak_attributable_active_memory_bytes"] = 0
        reasons = trial_scoreability_reasons(record)
        self.assertIn(
            "resource instrumentation coverage is below 0.95", reasons
        )
        self.assertIn("peak attributable active memory is unavailable", reasons)


class Sha256HashTests(unittest.TestCase):
    """Top-level ``trial_sha256`` determinism and discrimination."""

    def test_schema_version_constant_matches(self) -> None:
        record = fresh_record()
        validated = validate_trial_record(record)
        self.assertEqual(validated["schema_version"], TRIAL_SCHEMA_VERSION)

    def test_hash_is_canonical_and_reorders_keys(self) -> None:
        record = fresh_record()
        reordered = {key: record[key] for key in reversed(record)}
        self.assertEqual(trial_sha256(record), trial_sha256(reordered))

    def test_hash_changes_when_payload_tampered(self) -> None:
        record = fresh_record()
        original = trial_sha256(record)
        tampered = copy.deepcopy(record)
        tampered["trial_id"] = "trial-task-alpha-0-mutated"
        self.assertNotEqual(original, trial_sha256(tampered))


if __name__ == "__main__":
    unittest.main()
