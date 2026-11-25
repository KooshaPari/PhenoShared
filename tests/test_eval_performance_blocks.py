from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from pheno.evidence import aggregate_contracts
from pheno.evidence.contracts import ContractError
from pheno.evidence.performance_blocks import (
    BOOTSTRAP_RESAMPLES,
    PERFORMANCE_BLOCK_SCHEMA_VERSION,
    build_performance_block_record,
    performance_block_id,
    performance_block_sha256,
    task_ids_sha256,
    validate_performance_block_record,
)
from tests.test_eval_aggregate_integration import (
    TASK_IDS,
    TRIAL_FIXTURE,
    _arm,
    _digest,
    _run_provenance,
)


def _blocks(
    *,
    suite_lock: str = "a" * 64,
    treatment_cell: str = "b" * 64,
    baseline_cell: str = "c" * 64,
    load_profile: str | None = None,
) -> list[dict]:
    task_hash = task_ids_sha256(TASK_IDS)
    load_hash = load_profile or _digest("performance-load")
    rows = []
    for index, (baseline_avs, treatment_avs) in enumerate(
        ((1.0, 1.40), (1.1, 1.43), (0.9, 1.35))
    ):
        shared = {
            "evidence_class": "local_measured",
            "suite_lock_sha256": suite_lock,
            "task_ids_sha256": task_hash,
            "task_order_sha256": _digest(f"order:{index}"),
            "load_profile_sha256": load_hash,
            "schedule_manifest_sha256": _digest(f"schedule:{index}"),
        }
        row = {
            "baseline": {
                **shared,
                "cell_id": baseline_cell,
                "run_provenance_sha256": _digest(f"baseline-run:{index}"),
                "aggregate_sha256": _digest(f"baseline-aggregate:{index}"),
                "avs_per_second": baseline_avs,
            },
            "treatment": {
                **shared,
                "cell_id": treatment_cell,
                "run_provenance_sha256": _digest(f"treatment-run:{index}"),
                "aggregate_sha256": _digest(f"treatment-aggregate:{index}"),
                "avs_per_second": treatment_avs,
            },
        }
        row["block_id"] = performance_block_id(row)
        rows.append(row)
    return rows


def _refresh_block_id(row: dict) -> None:
    row["block_id"] = performance_block_id(row)


class PerformanceBlockContractTests(unittest.TestCase):
    def test_positive_record_is_deterministic_and_promotable(self) -> None:
        blocks = _blocks()
        first = build_performance_block_record(blocks)
        second = build_performance_block_record(list(reversed(blocks)))
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], PERFORMANCE_BLOCK_SCHEMA_VERSION)
        self.assertEqual(first["bootstrap_resamples"], BOOTSTRAP_RESAMPLES)
        self.assertEqual(first["statistics"]["block_count"], 3)
        self.assertGreater(first["statistics"]["speedup_ci95"]["lower"], 1.0)
        self.assertEqual(first["promotion"], {"status": "pass", "reasons": []})
        self.assertEqual(validate_performance_block_record(first), first)
        self.assertEqual(
            performance_block_sha256(first), performance_block_sha256(second)
        )

    def test_adversarial_rows_fail_closed(self) -> None:
        cases: list[tuple[str, list[dict], str]] = []
        cases.append(("too few", _blocks()[:2], "at least 3"))

        nonfinite = _blocks()
        nonfinite[0]["treatment"]["avs_per_second"] = math.nan
        cases.append(("nonfinite", nonfinite, "finite positive"))

        vendor = _blocks()
        vendor[0]["baseline"]["evidence_class"] = "vendor"
        cases.append(("non-local", vendor, "local_measured"))

        mismatched_order = _blocks()
        mismatched_order[0]["baseline"]["task_order_sha256"] = _digest("other-order")
        _refresh_block_id(mismatched_order[0])
        cases.append(("pair mismatch", mismatched_order, "disagree on task_order"))

        duplicate_schedule = _blocks()
        schedule = duplicate_schedule[0]["treatment"]["schedule_manifest_sha256"]
        for arm in ("baseline", "treatment"):
            duplicate_schedule[1][arm]["schedule_manifest_sha256"] = schedule
        _refresh_block_id(duplicate_schedule[1])
        cases.append(("duplicate schedule", duplicate_schedule, "unique schedule"))

        duplicate_run = _blocks()
        duplicate_run[1]["baseline"]["run_provenance_sha256"] = duplicate_run[0][
            "baseline"
        ]["run_provenance_sha256"]
        _refresh_block_id(duplicate_run[1])
        cases.append(("duplicate run", duplicate_run, "unique run provenance"))

        for label, rows, message in cases:
            with (
                self.subTest(label=label),
                self.assertRaisesRegex(ContractError, message),
            ):
                build_performance_block_record(rows)

    def test_persisted_statistics_cannot_be_forged(self) -> None:
        record = build_performance_block_record(_blocks())
        record["statistics"]["speedup_ci95"]["lower"] = 99.0
        with self.assertRaisesRegex(ContractError, "deterministic recomputation"):
            validate_performance_block_record(record)

    def test_non_improving_blocks_fail_the_promotion_gate(self) -> None:
        blocks = _blocks()
        for block in blocks:
            block["treatment"]["avs_per_second"] = (
                block["baseline"]["avs_per_second"] * 0.9
            )
            _refresh_block_id(block)
        record = build_performance_block_record(blocks)
        self.assertLess(record["statistics"]["speedup_ci95"]["upper"], 1.0)
        self.assertEqual(record["promotion"]["status"], "fail")
        self.assertTrue(record["promotion"]["reasons"])


class AggregatePerformanceBlockIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template = json.loads(Path(TRIAL_FIXTURE).read_text(encoding="utf-8"))
        cls.treatment = _arm(
            template,
            "treatment",
            "run-treatment-performance",
            (("passed",), ("passed",)),
        )
        cls.baseline = _arm(
            template,
            "baseline",
            "run-baseline-performance",
            (("passed",), ("passed",)),
        )
        cls.treatment_run = _run_provenance(
            "run-treatment-performance", seconds=4, cost_usd=1.0
        )
        cls.baseline_run = _run_provenance(
            "run-baseline-performance", seconds=8, cost_usd=2.0
        )
        cls.summary = build_performance_block_record(
            _blocks(
                suite_lock=cls.treatment[0]["cell"]["suite_lock_sha256"],
                treatment_cell=cls.treatment[0]["cell_id"],
                baseline_cell=cls.baseline[0]["cell_id"],
                load_profile=cls.treatment_run["thermal"]["load_profile_sha256"],
            )
        )

    def _aggregate(self, **overrides: object) -> dict:
        values = {
            "trials": self.treatment,
            "expected_task_ids": TASK_IDS,
            "attempts_per_task": 1,
            "run_provenance": self.treatment_run,
            "baseline_trials": self.baseline,
            "baseline_run_provenance": self.baseline_run,
            "performance_block_summary": self.summary,
        }
        values.update(overrides)
        return aggregate_contracts.aggregate_trials(**values)

    def test_validated_blocks_close_the_performance_gate(self) -> None:
        result = self._aggregate()
        self.assertEqual(result["gates"]["performance_promotion"]["status"], "pass")
        self.assertEqual(result["gates"]["long_turn_drift"]["status"], "pass")
        self.assertEqual(result["gates"]["concurrency"]["status"], "pass")
        self.assertTrue(result["promotion"]["core_eligible"])
        self.assertEqual(
            aggregate_contracts.validate_aggregate_against_inputs(
                result,
                self.treatment,
                expected_task_ids=TASK_IDS,
                attempts_per_task=1,
                run_provenance=self.treatment_run,
                baseline_trials=self.baseline,
                baseline_run_provenance=self.baseline_run,
                performance_block_summary=self.summary,
            ),
            result,
        )

    def test_absent_blocks_remain_not_evaluable(self) -> None:
        result = self._aggregate(performance_block_summary=None)
        self.assertEqual(
            result["gates"]["performance_promotion"]["status"], "not_evaluable"
        )
        self.assertFalse(result["promotion"]["core_eligible"])

    def test_summary_identity_mismatch_is_rejected(self) -> None:
        mismatched = build_performance_block_record(
            _blocks(
                suite_lock=self.treatment[0]["cell"]["suite_lock_sha256"],
                treatment_cell=_digest("wrong-treatment-cell"),
                baseline_cell=self.baseline[0]["cell_id"],
                load_profile=self.treatment_run["thermal"]["load_profile_sha256"],
            )
        )
        with self.assertRaisesRegex(ContractError, "treatment cell"):
            self._aggregate(performance_block_summary=mismatched)

    def test_drift_and_concurrency_are_required_core_gates(self) -> None:
        treatment = copy.deepcopy(self.treatment)
        for trial in treatment:
            trial["drift"] = {"assertion_manifest_sha256": None, "checkpoints": []}
        run = copy.deepcopy(self.treatment_run)
        run["concurrency"] = None
        result = self._aggregate(trials=treatment, run_provenance=run)
        self.assertEqual(result["gates"]["long_turn_drift"]["status"], "not_applicable")
        self.assertEqual(result["gates"]["concurrency"]["status"], "not_applicable")
        self.assertFalse(result["promotion"]["core_eligible"])
        self.assertIn("long_turn_drift", result["promotion"]["reason_codes"])
        self.assertIn("concurrency", result["promotion"]["reason_codes"])


if __name__ == "__main__":
    unittest.main()
