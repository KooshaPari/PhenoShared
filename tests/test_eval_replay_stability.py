from __future__ import annotations

import unittest
from copy import deepcopy

from pheno.evidence.contracts import ContractError
from pheno.evidence.replay_stability import (
    build_replay_stability_record,
    replay_replicate_id,
    replay_stability_sha256,
    validate_replay_stability_record,
)


def _digest(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode()).hexdigest()


def _row(task: str, ordinal: int, *, mode: str = "greedy", seed: int = 0) -> dict:
    row = {
        "replicate_id": "0" * 64,
        "evidence_class": "local_measured",
        "suite_lock_sha256": _digest("suite"),
        "replay_manifest_sha256": _digest("replay"),
        "assertion_manifest_sha256": _digest("assertions"),
        "cell_id": _digest("cell"),
        "task_id": task,
        "mode": mode,
        "seed": seed,
        "attempt_ordinal": ordinal,
        "trial_schema_version": "pheno.eval.trial.v2",
        "trial_run_mode": "replay",
        "trial_sha256": _digest(f"trial:{task}:{ordinal}:{mode}"),
        "harness_valid": True,
        "semantic_passed": True,
        "normalized_output_sha256": _digest(f"output:{task}"),
        "tool_trace_sha256": _digest(f"tools:{task}"),
        "tool_calls_total": 2,
        "tool_calls_schema_valid": 2,
        "tool_calls_semantically_labeled": 2,
        "tool_calls_semantically_correct": 2,
        "valid_but_wrong_calls": 0,
        "duplicate_calls": 0,
        "repair_count": 0,
        "fallback_count": 0,
        "loop_detected": False,
        "injected_failure_expected": True,
        "injected_failure_recovered": True,
        "risky_action_bypass_count": 0,
    }
    row["replicate_id"] = replay_replicate_id(row)
    return row


def _greedy_rows() -> list[dict]:
    return [_row(task, ordinal) for task in ("router", "code") for ordinal in range(3)]


class ReplayStabilityContractTests(unittest.TestCase):
    def test_greedy_block_passes_and_hashes_deterministically(self) -> None:
        record = build_replay_stability_record(list(reversed(_greedy_rows())))
        self.assertEqual("pass", record["promotion"]["status"])
        self.assertEqual(1.0, record["statistics"]["harness_valid_rate"])
        self.assertEqual(
            1.0, record["statistics"]["normalized_output_modal_agreement_macro"]
        )
        self.assertEqual(record, validate_replay_stability_record(record))
        self.assertEqual(64, len(replay_stability_sha256(record)))
        self.assertEqual(record, build_replay_stability_record(record["replicates"]))

    def test_sampled_mode_requires_five_unique_seeds_and_skips_exact_output_gate(
        self,
    ) -> None:
        rows = [_row("sampled", i, mode="sampled", seed=100 + i) for i in range(5)]
        for index, row in enumerate(rows):
            row["normalized_output_sha256"] = _digest(f"varied:{index}")
            row["replicate_id"] = replay_replicate_id(row)
        record = build_replay_stability_record(rows)
        self.assertEqual("pass", record["promotion"]["status"])
        self.assertEqual(
            "not_applicable", record["gates"]["greedy_output_equivalence"]["status"]
        )

        duplicate_seed = deepcopy(rows)
        duplicate_seed[-1]["seed"] = duplicate_seed[0]["seed"]
        duplicate_seed[-1]["replicate_id"] = replay_replicate_id(duplicate_seed[-1])
        with self.assertRaisesRegex(ContractError, "unique seeds"):
            build_replay_stability_record(duplicate_seed)

    def test_dry_run_and_missing_l2_evidence_cannot_promote(self) -> None:
        rows = _greedy_rows()
        for row in rows:
            row.update(
                {
                    "evidence_class": "dry_run",
                    "tool_calls_total": 0,
                    "tool_calls_schema_valid": 0,
                    "tool_calls_semantically_labeled": 0,
                    "tool_calls_semantically_correct": 0,
                    "injected_failure_expected": False,
                    "injected_failure_recovered": None,
                }
            )
            row["replicate_id"] = replay_replicate_id(row)
        record = build_replay_stability_record(rows)
        self.assertEqual("not_evaluable", record["promotion"]["status"])
        self.assertIn("evidence_class", record["promotion"]["reason_codes"])
        self.assertIn("failure_recovery", record["promotion"]["reason_codes"])
        self.assertIn("tool_schema_validity", record["promotion"]["reason_codes"])

    def test_greedy_output_tool_and_semantic_drift_fail(self) -> None:
        rows = _greedy_rows()
        rows[0]["normalized_output_sha256"] = _digest("drifted output")
        rows[0]["tool_trace_sha256"] = _digest("drifted tools")
        rows[0]["semantic_passed"] = False
        rows[0]["replicate_id"] = replay_replicate_id(rows[0])
        record = build_replay_stability_record(rows)
        self.assertEqual("fail", record["promotion"]["status"])
        self.assertIn("greedy_output_equivalence", record["promotion"]["reason_codes"])
        self.assertIn(
            "greedy_tool_trace_equivalence", record["promotion"]["reason_codes"]
        )
        self.assertIn(
            "greedy_semantic_consistency", record["promotion"]["reason_codes"]
        )

    def test_tool_counters_and_attempt_identity_fail_closed(self) -> None:
        rows = _greedy_rows()
        rows[0]["valid_but_wrong_calls"] = 1
        with self.assertRaisesRegex(ContractError, "do not reconcile"):
            build_replay_stability_record(rows)

        rows = _greedy_rows()
        rows[0]["attempt_ordinal"] = 8
        rows[0]["replicate_id"] = replay_replicate_id(rows[0])
        with self.assertRaisesRegex(ContractError, "contiguous"):
            build_replay_stability_record(rows)

        rows = _greedy_rows()
        rows[0]["trial_run_mode"] = "execute"
        with self.assertRaisesRegex(ContractError, "must be replay"):
            build_replay_stability_record(rows)

    def test_tampered_derived_fields_and_unknown_fields_are_rejected(self) -> None:
        record = build_replay_stability_record(_greedy_rows())
        tampered = deepcopy(record)
        tampered["statistics"]["semantic_pass_rate"] = 0.0
        with self.assertRaisesRegex(ContractError, "recomputation"):
            validate_replay_stability_record(tampered)

        unknown = deepcopy(record)
        unknown["replicates"][0]["raw_output"] = "not permitted"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_replay_stability_record(unknown)

    def test_secret_like_content_is_not_accepted_as_task_identity(self) -> None:
        rows = _greedy_rows()[:3]
        for row in rows:
            row["task_id"] = "api_key=sk-this-is-a-fake-but-secret-shaped-value"
            row["replicate_id"] = replay_replicate_id(row)
        with self.assertRaisesRegex(ContractError, "credential"):
            build_replay_stability_record(rows)


if __name__ == "__main__":
    unittest.main()
