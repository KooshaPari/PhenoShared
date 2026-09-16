"""Integration test for bench matrix verifier wiring — v0.12 task 7."""

from __future__ import annotations


def test_helpers_importable() -> None:
    """Helpers module is importable and exposes verifier wiring."""
    from bench.matrix import run_ablation_helpers as helpers

    assert hasattr(helpers, "compute_verified_pass_at_1")
    assert hasattr(helpers, "build_cells_payload")
    assert hasattr(helpers, "_cell_to_task_result")
    assert hasattr(helpers, "verifier_available")
    assert hasattr(helpers, "verifier_judge_for_cell")
    assert callable(helpers.verifier_available)
    assert callable(helpers.verifier_judge_for_cell)


def test_verifier_judge_for_cell() -> None:
    from bench.matrix.run_ablation_helpers import verifier_judge_for_cell

    cell_ok = {"ok": True, "harbor_reward": 1.0}
    fields = verifier_judge_for_cell(cell_ok)
    assert fields["gen_ok"] == 1.0
    assert fields["verified_pass_at_1"] == 1.0

    cell_no_reward = {"ok": True}
    fields2 = verifier_judge_for_cell(cell_no_reward)
    assert fields2["verified_pass_at_1"] == 0.0


def test_run_ablation_importable() -> None:
    from bench.matrix.run_ablation import VARIANTS, AblationConfig, run_ablation

    assert len(VARIANTS) == 2
    assert AblationConfig is not None
    assert run_ablation is not None


def test_verifier_available_flag() -> None:
    from bench.matrix.run_ablation_helpers import verifier_available

    # Should be True in this repo (verifier/harness.py exists)
    assert verifier_available() is True
