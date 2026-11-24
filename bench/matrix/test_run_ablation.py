"""Tests for bench.matrix.run_ablation (dry-run scaffold)."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
from pathlib import Path

from bench.contracts.cell_metrics import EVIDENCE_REPORTED
from bench.matrix.run_ablation import (
    VARIANTS,
    AblationConfig,
    build_cell,
    run_ablation,
    write_artifacts,
)


def test_build_cell_dual_pass_fields() -> None:
    """build_cell surfaces both gen_ok and pass_at_1 with consistent values."""
    cell = build_cell(
        suite="ifeval",
        task_id="ifeval-001",
        variant="baseline_mlx",
        model_id="Qwen/Qwen3.5-0.8B",
        gen_success=True,
        reply="four",
    )
    assert cell["gen_ok"] == 1.0  # nosec B101
    assert cell["pass_at_1"] == 1.0  # nosec B101
    assert cell["gen_ok"] == cell["pass_at_1"]  # nosec B101
    assert cell["verified_pass_at_1"] == 0.0  # nosec B101
    assert cell["evidence_label"] == EVIDENCE_REPORTED  # nosec B101
    assert cell["task_title"] == "ifeval-001"  # nosec B101
    assert cell["prompt"]  # nosec B101
    assert cell["reply"] == "four"  # nosec B101
    assert cell["reply_full"] == "four"  # nosec B101
    assert cell["acceptance"]  # nosec B101
    assert cell["rubric"] == cell["acceptance"]  # nosec B101
    assert cell["chat_trace"] == cell["progress_trace"]  # nosec B101
    assert any(s.get("kind") == "turn" for s in cell["progress_trace"])  # nosec B101


def test_dry_run_emits_cells_and_report(tmp_path: Path) -> None:
    """A dry-run writes a cells.json + evaluation_report.json pair."""
    config = AblationConfig(
        run_id="test-dry-run",
        suites=["ifeval"],
        variants=VARIANTS,
        tasks_per_suite=1,
        model_id="Qwen/Qwen3.5-0.8B",
        dry_run=True,
        output_root=tmp_path,
    )
    result = run_ablation(config)
    assert len(result.cells) == len(VARIANTS)  # nosec B101
    for cell in result.cells:
        assert cell["gen_ok"] == 1.0  # nosec B101
        assert cell["pass_at_1"] == cell["gen_ok"]  # nosec B101
        assert cell["verified_pass_at_1"] == 0.0  # nosec B101
        assert cell["evidence_label"] == EVIDENCE_REPORTED  # nosec B101

    paths = write_artifacts(result, tmp_path)
    report = json.loads(paths["evaluation_report"].read_text(encoding="utf-8"))
    cells_doc = json.loads(paths["cells"].read_text(encoding="utf-8"))

    assert report["artifact_kind"] == "EvaluationReport"  # nosec B101
    assert report["run"]["dry_run"] is True  # nosec B101
    assert cells_doc["dry_run"] is True  # nosec B101
    assert len(cells_doc["cells"]) == len(VARIANTS)  # nosec B101
    assert paths["evaluation_report"].parent == tmp_path / "test-dry-run"  # nosec B101
    ap = report["suites"][0]["task_results"][0]["additionalProperties"]
    assert ap["task_title"]  # nosec B101
    assert ap["prompt"]  # nosec B101
    assert ap["reply_full"]  # nosec B101
    assert ap["progress_trace"]  # nosec B101
    assert ap["chat_trace"] == ap["progress_trace"]  # nosec B101


def test_cli_help_exits_zero() -> None:
    """The --help CLI invocation exits 0 and mentions both baseline_mlx + --dry-run."""
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-m", "bench.matrix.run_ablation", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0  # nosec B101
    assert "baseline_mlx" in proc.stdout  # nosec B101
    assert "--dry-run" in proc.stdout  # nosec B101


def test_verifier_helpers_wired() -> None:
    """Verifier helpers are importable via run_ablation and helpers."""
    from bench.matrix.run_ablation import verifier_available, verifier_judge_for_cell
    from bench.matrix.run_ablation_helpers import (
        verifier_available as helpers_available,
    )
    from bench.matrix.run_ablation_helpers import (
        verifier_judge_for_cell as helpers_judge,
    )

    assert callable(verifier_available)  # nosec B101
    assert callable(verifier_judge_for_cell)  # nosec B101
    # Helpers and run_ablation should expose the same callables.
    assert verifier_available is helpers_available  # nosec B101
    assert verifier_judge_for_cell is helpers_judge  # nosec B101
    assert isinstance(verifier_available(), bool)  # nosec B101
    assert verifier_available() is True  # nosec B101  # harness is present in repo
    # verifier_judge_for_cell delegates to cell_pass_fields / verifier/harness
    ok_fields = verifier_judge_for_cell({"ok": True, "harbor_reward": 1.0})
    assert ok_fields["verified_pass_at_1"] == 1.0  # nosec B101
    assert ok_fields["evidence_label"] == "verified"  # nosec B101
    fail_fields = verifier_judge_for_cell({"ok": False})
    assert fail_fields["gen_ok"] == 0.0  # nosec B101
    assert fail_fields["verified_pass_at_1"] == 0.0  # nosec B101


def test_verifier_judge_uses_harness() -> None:
    """run_ablation_helpers imports verifier.harness (wiring check)."""
    import bench.matrix.run_ablation_helpers as helpers

    assert hasattr(helpers, "_HAS_VERIFIER")  # nosec B101
    assert helpers.verifier_available() is True  # nosec B101
    # module source references verifier.harness
    src = Path(helpers.__file__).read_text(encoding="utf-8")
    assert "verifier.harness" in src  # nosec B101
    assert "VerifierHarness" in src  # nosec B101
