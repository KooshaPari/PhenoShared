"""DAG-65: isolated helper tests for bench/contracts/cell_metrics.py.

DAG-64 (test_bench_contract_v0_5.py) covers the round-trip envelope:
producer emits a cell via ``cell_pass_fields``, embeds it in a synthetic
suite, and the consumer reads it back via ``task_gen_ok`` /
``suite_gen_ok_mean`` / ``effective_pass_at_1``. That covers the
producer/consumer contract as a whole.

This file pins the v0.2 helpers standalone — edge cases and branches
that aren't worth exercising in a round-trip test:

  * ``cell_pass_fields`` boundary behavior at harbor_reward = 0.0
    (still "verified" not "reported" — the truthiness of the value
    matters, not its magnitude).
  * ``task_gen_ok`` two-path lookup: ``task['additionalProperties']['gen_ok']``
    takes precedence over ``task['gen_ok']``; both are absent => None.
  * ``suite_gen_ok_mean`` rounding to 4 decimals (including the
    n=0 / n<=0 edge cases that return 0.0 vs None).
  * ``effective_pass_at_1`` returning 0.0 (legacy pass_at_1 absent) vs
    None is not possible here — the helper returns float, but the
    "no gen_ok anywhere" path returns the legacy value or 0.0.
  * Mixed evidence_label across a suite (some verified, some reported)
    must not leak across task boundaries.
  * Empty / missing task lists must short-circuit cleanly.
"""

from __future__ import annotations

from typing import Any

import pytest

from bench.contracts import cell_metrics

# ---------------------------------------------------------------------------
# cell_pass_fields — boundary behavior
# ---------------------------------------------------------------------------


def test_cell_pass_fields_gen_success_true_sets_gen_ok_one() -> None:
    cell = cell_metrics.cell_pass_fields(gen_success=True)
    assert cell["gen_ok"] == 1.0
    assert cell["pass_at_1"] == 1.0  # dual-write alias
    assert cell["verified_pass_at_1"] == 0.0
    assert cell["evidence_label"] == cell_metrics.EVIDENCE_REPORTED


def test_cell_pass_fields_gen_success_false_sets_gen_ok_zero() -> None:
    cell = cell_metrics.cell_pass_fields(gen_success=False)
    assert cell["gen_ok"] == 0.0
    assert cell["pass_at_1"] == 0.0
    assert cell["verified_pass_at_1"] == 0.0
    assert cell["evidence_label"] == cell_metrics.EVIDENCE_REPORTED


def test_cell_pass_fields_harbor_reward_zero_is_still_verified() -> None:
    """harbor_reward=0.0 is truthy as 'present' — label flips to 'verified'.

    The helper tests `harbor_reward is not None`, not truthiness. A Harbor
    run that scored 0.0 is still a verified run, not a reported one.
    """
    cell = cell_metrics.cell_pass_fields(gen_success=True, harbor_reward=0.0)
    assert cell["verified_pass_at_1"] == 0.0
    assert cell["evidence_label"] == cell_metrics.EVIDENCE_VERIFIED
    # gen_ok and pass_at_1 alias are independent of harbor_reward:
    assert cell["gen_ok"] == 1.0
    assert cell["pass_at_1"] == 1.0


def test_cell_pass_fields_harbor_reward_is_carried_through_when_gen_fails() -> None:
    """Failed generation can still be harbor-verified (rewards the attempt)."""
    cell = cell_metrics.cell_pass_fields(gen_success=False, harbor_reward=0.3)
    assert cell["gen_ok"] == 0.0
    assert cell["pass_at_1"] == 0.0
    assert cell["verified_pass_at_1"] == 0.3
    assert cell["evidence_label"] == cell_metrics.EVIDENCE_VERIFIED


@pytest.mark.parametrize(
    "harbor_reward,expected",
    [
        (0.85, 0.85),
        (1.0, 1.0),
        (0.0, 0.0),  # boundary: still verified
    ],
)
def test_cell_pass_fields_harbor_reward_passes_through(
    harbor_reward: float, expected: float
) -> None:
    cell = cell_metrics.cell_pass_fields(gen_success=True, harbor_reward=harbor_reward)
    assert cell["verified_pass_at_1"] == expected
    assert cell["evidence_label"] == cell_metrics.EVIDENCE_VERIFIED


# ---------------------------------------------------------------------------
# task_gen_ok — two-path lookup
# ---------------------------------------------------------------------------


def test_task_gen_ok_reads_from_additional_properties_first() -> None:
    """additionalProperties.gen_ok takes precedence over top-level gen_ok."""
    task: dict[str, Any] = {
        "task_id": "t1",
        "gen_ok": 0.0,  # legacy field (won)
        "additionalProperties": {"gen_ok": 1.0},  # canonical location (wins)
    }
    assert cell_metrics.task_gen_ok(task) == 1.0


def test_task_gen_ok_falls_back_to_top_level_field() -> None:
    """When additionalProperties is absent, read top-level gen_ok."""
    task: dict[str, Any] = {"task_id": "t1", "gen_ok": 1.0}
    assert cell_metrics.task_gen_ok(task) == 1.0


def test_task_gen_ok_handles_empty_additional_properties() -> None:
    """empty additionalProperties dict must not crash; falls back to top-level."""
    task: dict[str, Any] = {
        "task_id": "t1",
        "gen_ok": 0.0,
        "additionalProperties": {},
    }
    assert cell_metrics.task_gen_ok(task) == 0.0


def test_task_gen_ok_returns_none_when_field_missing() -> None:
    legacy_task: dict[str, Any] = {"task_id": "t1", "status": "ok"}
    assert cell_metrics.task_gen_ok(legacy_task) is None


def test_task_gen_ok_returns_none_when_additional_properties_lacks_gen_ok() -> None:
    task: dict[str, Any] = {
        "task_id": "t1",
        "additionalProperties": {"other_field": 1.0},
    }
    assert cell_metrics.task_gen_ok(task) is None


def test_task_gen_ok_treats_non_dict_additional_properties_as_missing() -> None:
    """additionalProperties=None must not raise; falls back to top-level."""
    task: dict[str, Any] = {
        "task_id": "t1",
        "gen_ok": 1.0,
        "additionalProperties": None,
    }
    assert cell_metrics.task_gen_ok(task) == 1.0


# ---------------------------------------------------------------------------
# suite_gen_ok_mean — rounding + edge cases
# ---------------------------------------------------------------------------


def _ok_task(gen_ok: float) -> dict[str, Any]:
    return {"task_id": f"t-{gen_ok}", "gen_ok": gen_ok}


def test_suite_gen_ok_mean_rounds_to_4_decimals() -> None:
    """Mean of [1, 1, 1, 1, 1, 0, 0, 0, 0, 0] / 10 = 0.5 exactly."""
    suite = {"n": 10, "task_results": [_ok_task(1.0)] * 5 + [_ok_task(0.0)] * 5}
    # 0.5 is exact in float64; verify rounding didn't over-round to 0.0:
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.5


def test_suite_gen_ok_mean_rounds_irrational_sum_to_4dp() -> None:
    """Mean of [1, 0, 0] / 3 = 0.3333... -> 0.3333 (rounded to 4dp)."""
    suite = {"n": 3, "task_results": [_ok_task(1.0), _ok_task(0.0), _ok_task(0.0)]}
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.3333


def test_suite_gen_ok_mean_rounds_long_irrational_sum_to_4dp() -> None:
    """Mean of [1, 1, 1, 0] / 4 = 0.75 exactly — guard against fp drift."""
    suite = {"n": 4, "task_results": [_ok_task(1.0)] * 3 + [_ok_task(0.0)]}
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.75


def test_suite_gen_ok_mean_returns_none_when_no_task_has_gen_ok() -> None:
    suite = {"n": 3, "task_results": [{"task_id": "t1"}, {"task_id": "t2"}]}
    assert cell_metrics.suite_gen_ok_mean(suite) is None


def test_suite_gen_ok_mean_returns_none_when_task_results_empty() -> None:
    """Empty task_results list => no values => None."""
    assert cell_metrics.suite_gen_ok_mean({"n": 0, "task_results": []}) is None


def test_suite_gen_ok_mean_returns_zero_when_n_is_zero() -> None:
    """n=0 with task_results present must return 0.0 (not None, not divide-by-zero).

    Per the helper: ``if n <= 0: return 0.0``. This guards against a
    divide-by-zero crash when n is missing or stale.
    """
    suite = {"n": 0, "task_results": [_ok_task(1.0), _ok_task(0.0)]}
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.0


def test_suite_gen_ok_mean_ignores_tasks_without_gen_ok() -> None:
    """Tasks missing gen_ok are excluded from the mean; n is the denominator."""
    suite = {
        "n": 4,
        "task_results": [
            _ok_task(1.0),
            _ok_task(1.0),
            {"task_id": "legacy-a"},  # no gen_ok
            {"task_id": "legacy-b"},  # no gen_ok
        ],
    }
    # 2 successes / 4 n = 0.5
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.5


@pytest.mark.parametrize(
    "values,expected",
    [
        ([1.0, 0.0], 0.5),
        ([1.0, 1.0, 1.0], 1.0),
        ([0.0, 0.0, 0.0], 0.0),
        ([1.0], 1.0),
    ],
)
def test_suite_gen_ok_mean_boundary_values(
    values: list[float], expected: float
) -> None:
    """gen_ok at exactly 0.0 and 1.0 (the v0.2 boundary values)."""
    suite = {"n": len(values), "task_results": [_ok_task(v) for v in values]}
    assert cell_metrics.suite_gen_ok_mean(suite) == expected


# ---------------------------------------------------------------------------
# effective_pass_at_1 — None vs 0.0 disambiguation
# ---------------------------------------------------------------------------


def test_effective_pass_at_1_returns_zero_when_no_gen_ok_and_no_legacy_pass_at_1() -> (
    None
):
    """Neither gen_ok nor legacy pass_at_1 present => 0.0 (NOT None)."""
    suite = {"suite": "blank", "n": 0, "task_results": []}
    assert cell_metrics.effective_pass_at_1(suite) == 0.0


def test_effective_pass_at_1_falls_back_to_legacy_pass_at_1() -> None:
    """No gen_ok anywhere; legacy pass_at_1 = 0.42 => returns 0.42."""
    suite = {
        "suite": "legacy",
        "pass_at_1": 0.42,
        "task_results": [{"task_id": "t1"}, {"task_id": "t2"}],
    }
    assert cell_metrics.effective_pass_at_1(suite) == 0.42


def test_effective_pass_at_1_reports_zero_when_legacy_pass_at_1_also_missing() -> None:
    """No gen_ok, no pass_at_1 => 0.0 (default)."""
    suite = {"suite": "bare", "task_results": [{"task_id": "t1"}]}
    assert cell_metrics.effective_pass_at_1(suite) == 0.0


def test_effective_pass_at_1_prefers_gen_ok_mean_over_legacy_even_when_legacy_higher() -> (
    None
):
    """gen_ok_mean wins over legacy pass_at_1, even when legacy is higher.

    This is the documented consumer rule (AGENTS.md §12.5 #1): prefer gen_ok
    when present. The legacy field is only a backward-compat fallback.
    """
    suite = {
        "suite": "mixed",
        "n": 4,
        "pass_at_1": 0.99,  # misleading legacy value
        "task_results": [_ok_task(1.0), _ok_task(0.0), _ok_task(1.0), _ok_task(0.0)],
    }
    # gen_ok mean = 0.5 (4 dividing), legacy pass_at_1 = 0.99
    assert cell_metrics.effective_pass_at_1(suite) == 0.5


# ---------------------------------------------------------------------------
# Mixed evidence_label across a suite
# ---------------------------------------------------------------------------


def test_mixed_evidence_labels_across_suite_do_not_leak() -> None:
    """Some tasks verified, some reported — suite_gen_ok_mean sees only gen_ok.

    The helper does NOT weight by evidence_label; it is purely a gen_ok
    mean. Evidence labels are per-cell metadata and don't interact with
    the suite-level aggregation.
    """
    suite = {
        "suite": "mixed",
        "n": 4,
        "task_results": [
            {"task_id": "v1", "gen_ok": 1.0, "evidence_label": "verified"},
            {"task_id": "v2", "gen_ok": 1.0, "evidence_label": "verified"},
            {"task_id": "r1", "gen_ok": 0.0, "evidence_label": "reported"},
            {"task_id": "r2", "gen_ok": 0.0, "evidence_label": "reported"},
        ],
    }
    # gen_ok mean = 0.5 (verified successes / 4), uniform across labels:
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.5
    assert cell_metrics.effective_pass_at_1(suite) == 0.5


def test_mixed_evidence_labels_via_additional_properties() -> None:
    """Same suite, but gen_ok lives in additionalProperties for some tasks.

    Verifies the two task_gen_ok paths coexist correctly across cells in
    a single suite.
    """
    suite = {
        "suite": "mixed-paths",
        "n": 3,
        "task_results": [
            {"task_id": "ap", "additionalProperties": {"gen_ok": 1.0}},
            {"task_id": "legacy", "gen_ok": 1.0},
            {"task_id": "fail", "gen_ok": 0.0},
        ],
    }
    # (1 + 1 + 0) / 3 = 0.6667
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.6667


def test_mixed_evidence_labels_with_only_reported_cells() -> None:
    """A suite of only reported-evidence cells must still aggregate."""
    suite = {
        "suite": "reported-only",
        "n": 3,
        "task_results": [
            {"task_id": "r1", "gen_ok": 1.0, "evidence_label": "reported"},
            {"task_id": "r2", "gen_ok": 1.0, "evidence_label": "reported"},
            {"task_id": "r3", "gen_ok": 1.0, "evidence_label": "reported"},
        ],
    }
    assert cell_metrics.suite_gen_ok_mean(suite) == 1.0
    assert cell_metrics.effective_pass_at_1(suite) == 1.0


def test_mixed_evidence_labels_with_only_verified_cells() -> None:
    """A suite of only verified-evidence cells must still aggregate."""
    suite = {
        "suite": "verified-only",
        "n": 2,
        "task_results": [
            {"task_id": "v1", "gen_ok": 1.0, "evidence_label": "verified"},
            {"task_id": "v2", "gen_ok": 0.0, "evidence_label": "verified"},
        ],
    }
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.5
    assert cell_metrics.effective_pass_at_1(suite) == 0.5


# ---------------------------------------------------------------------------
# Constants — sanity check
# ---------------------------------------------------------------------------


def test_evidence_label_constants_match_expected_strings() -> None:
    """The exported constants must be the canonical evidence_label strings."""
    assert cell_metrics.EVIDENCE_REPORTED == "reported"
    assert cell_metrics.EVIDENCE_VERIFIED == "verified"
    # They must be distinct — the producer's branch depends on this:
    assert cell_metrics.EVIDENCE_REPORTED != cell_metrics.EVIDENCE_VERIFIED
    assert (
        frozenset({"reported", "verified"}) == cell_metrics.VALID_CELL_EVIDENCE_LABELS
    )
