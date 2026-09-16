"""DAG-64: round-trip tests for the EvaluationReport v0.5 cell contract.

Per AGENTS.md §12.2, every cell in a v0.5 envelope carries:

  * gen_ok               (0.0 | 1.0)
  * pass_at_1            (deprecated alias of gen_ok; dual-written for one release)
  * verified_pass_at_1   (0.0–1.0; 0.0 when no Harbor reward)
  * evidence_label       ('reported' | 'verified')

These tests pin the producer/consumer semantics by:

  1. Calling ``cell_pass_fields`` to emit a cell.
  2. Embedding the cell in a synthetic suite envelope.
  3. Reading it back via ``task_gen_ok``, ``suite_gen_ok_mean``,
     and ``effective_pass_at_1``.
  4. Asserting the round-trip preserves gen_ok, the dual-write alias,
     and the evidence-label-driven fallback for verified_pass_at_1.

The round-trip is the actual contract — anyone who changes
``cell_pass_fields`` without preserving these invariants breaks
downstream consumers (SOTA snapshot, leaderboard, harbor gate).
"""

from __future__ import annotations

from typing import Any

from bench.contracts import cell_metrics

# ---------------------------------------------------------------------------
# Producer tests: cell_pass_fields output shape
# ---------------------------------------------------------------------------


def test_emitted_cell_has_all_v05_keys() -> None:
    """Every v0.5 cell must carry the four required keys."""
    cell = cell_metrics.cell_pass_fields(gen_success=True)
    assert set(cell) >= {
        "gen_ok",
        "pass_at_1",
        "verified_pass_at_1",
        "evidence_label",
    }


def test_emitted_cell_reported_when_no_harbor_reward() -> None:
    """No harbor_reward => verified_pass_at_1 = 0.0, evidence_label = 'reported'."""
    cell = cell_metrics.cell_pass_fields(gen_success=True)
    assert cell["gen_ok"] == 1.0
    assert cell["pass_at_1"] == 1.0  # dual-write alias
    assert cell["verified_pass_at_1"] == 0.0
    assert cell["evidence_label"] == "reported"


def test_emitted_cell_verified_when_harbor_reward_supplied() -> None:
    """harbor_reward => verified_pass_at_1 carries the score, label = 'verified'."""
    cell = cell_metrics.cell_pass_fields(gen_success=True, harbor_reward=0.85)
    assert cell["gen_ok"] == 1.0
    assert cell["pass_at_1"] == 1.0
    assert cell["verified_pass_at_1"] == 0.85
    assert cell["evidence_label"] == "verified"


def test_emitted_cell_gen_failure_keeps_gen_ok_zero() -> None:
    """gen_success=False => gen_ok=0.0 regardless of harbor_reward."""
    cell = cell_metrics.cell_pass_fields(gen_success=False, harbor_reward=0.5)
    assert cell["gen_ok"] == 0.0
    assert cell["pass_at_1"] == 0.0
    assert cell["verified_pass_at_1"] == 0.5  # harbor reward still carried
    assert cell["evidence_label"] == "verified"


# ---------------------------------------------------------------------------
# Consumer tests: read-back from a synthetic envelope
# ---------------------------------------------------------------------------


def _make_task_result(
    gen_success: bool, harbor_reward: float | None = None
) -> dict[str, Any]:
    """Build a minimal v0.5 task_result carrying the cell fields."""
    cell = cell_metrics.cell_pass_fields(
        gen_success=gen_success, harbor_reward=harbor_reward
    )
    return {
        "task_id": f"task-{gen_success}",
        "status": "ok" if gen_success else "wrong",
        "wall_clock_s": 0.1,
        "tokens_in": 1,
        "tokens_out": 1,
        "judge": "ok" if gen_success else "wrong",
        "evidence_label": cell["evidence_label"],
        # v0.5 cell fields live alongside the legacy fields:
        "gen_ok": cell["gen_ok"],
        "pass_at_1": cell["pass_at_1"],
        "verified_pass_at_1": cell["verified_pass_at_1"],
    }


def _make_suite(task_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {"suite": "test-suite", "n": len(task_results), "task_results": task_results}


def test_task_gen_ok_round_trip() -> None:
    """task_gen_ok must echo what cell_pass_fields emitted."""
    tasks = [
        _make_task_result(True),
        _make_task_result(False),
        _make_task_result(True, harbor_reward=0.9),
    ]
    assert cell_metrics.task_gen_ok(tasks[0]) == 1.0
    assert cell_metrics.task_gen_ok(tasks[1]) == 0.0
    assert cell_metrics.task_gen_ok(tasks[2]) == 1.0


def test_suite_gen_ok_mean_matches_arithmetic_mean() -> None:
    """suite_gen_ok_mean must equal sum/n rounded to 4 decimals."""
    tasks = [
        _make_task_result(True),
        _make_task_result(True),
        _make_task_result(False),
        _make_task_result(True),
    ]
    suite = _make_suite(tasks)
    assert cell_metrics.suite_gen_ok_mean(suite) == 0.75


def test_effective_pass_at_1_prefers_gen_ok_mean_when_present() -> None:
    """effective_pass_at_1 must return gen_ok_mean over legacy pass_at_1."""
    suite = _make_suite([_make_task_result(True), _make_task_result(False)])
    # Set a misleading legacy pass_at_1; effective_pass_at_1 should ignore it.
    suite["pass_at_1"] = 0.42
    assert cell_metrics.effective_pass_at_1(suite) == 0.5


def test_effective_pass_at_1_falls_back_to_legacy_when_no_gen_ok() -> None:
    """When no task carries gen_ok, fall back to legacy suite.pass_at_1."""
    suite = {
        "suite": "legacy",
        "n": 3,
        "pass_at_1": 0.6,
        "task_results": [
            {"task_id": "t1", "status": "ok", "wall_clock_s": 0.1},
            {"task_id": "t2", "status": "ok", "wall_clock_s": 0.1},
            {"task_id": "t3", "status": "wrong", "wall_clock_s": 0.1},
        ],
    }
    assert cell_metrics.effective_pass_at_1(suite) == 0.6


def test_effective_pass_at_1_zero_default() -> None:
    """When neither gen_ok nor pass_at_1 are present, default to 0.0."""
    suite = {"suite": "empty", "n": 0, "task_results": []}
    assert cell_metrics.effective_pass_at_1(suite) == 0.0


# ---------------------------------------------------------------------------
# Evidence-label invariants (consumer rules per AGENTS.md §12.4)
# ---------------------------------------------------------------------------


def test_reported_evidence_legacy_pass_at_1_treated_as_gen_ok() -> None:
    """For evidence_label == 'reported', legacy pass_at_1 == gen_ok fallback."""
    # No gen_ok, pass_at_1 present, evidence_label='reported':
    legacy_suite = {
        "suite": "legacy",
        "n": 2,
        "pass_at_1": 0.8,
        "task_results": [
            {"task_id": "t1", "evidence_label": "reported"},
            {"task_id": "t2", "evidence_label": "reported"},
        ],
    }
    # No gen_ok present anywhere -> falls back to legacy pass_at_1.
    assert cell_metrics.effective_pass_at_1(legacy_suite) == 0.8


def test_all_gen_ok_consumers_handle_missing_field() -> None:
    """Graceful None / 0.0 for cells missing the v0.5 keys."""
    legacy_task = {"task_id": "t1", "status": "ok"}
    assert cell_metrics.task_gen_ok(legacy_task) is None

    legacy_suite = {"suite": "empty", "n": 0, "task_results": [legacy_task]}
    assert cell_metrics.suite_gen_ok_mean(legacy_suite) is None
