"""Unit tests for bench.matrix.run_ablation — coverage target 80%+.

All external APIs (MLX, git, dry-run banner) are mocked via monkeypatch /
unittest.mock. Tests are hermetic and fast.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bench.matrix import run_ablation as run_ablation_mod
from bench.matrix.run_ablation import (
    VARIANT_BASELINE,
    VARIANT_CANDIDATE,
    AblationConfig,
    AblationResult,
    _run_cell_dry,
    build_cell,
    build_evaluation_report,
    build_parser,
    main,
    run_ablation,
    write_artifacts,
)

# ==== Fixtures & helpers =====================================================


def _make_config(
    *,
    run_id: str = "test-run-001",
    suites: list[str] | None = None,
    variants: list[str] | None = None,
    tasks_per_suite: int = 2,
    model_id: str = "Qwen/Qwen3.5-0.8B",
    dry_run: bool = True,
    output_root: Path | None = None,
) -> AblationConfig:
    """Build an AblationConfig with sensible defaults for testing."""
    return AblationConfig(
        run_id=run_id,
        suites=suites or ["mmlu-pro"],
        variants=variants or [VARIANT_BASELINE],
        tasks_per_suite=tasks_per_suite,
        model_id=model_id,
        dry_run=dry_run,
        output_root=output_root or Path("/tmp/ablation-test"),
    )


def _make_result(
    *,
    run_id: str = "test-run-001",
    cells: list[dict] | None = None,
    suites: list[str] | None = None,
    variants: list[str] | None = None,
    tasks_per_suite: int = 2,
    dry_run: bool = True,
) -> AblationResult:
    """Build an AblationResult for evaluation report / artifact tests."""
    suites = suites or ["mmlu-pro"]
    variants = variants or [VARIANT_BASELINE]
    return AblationResult(
        run_id=run_id,
        cells=cells or [],
        started_at="2026-01-01T00:00:00Z",
        stopped_at="2026-01-01T00:00:01Z",
        dry_run=dry_run,
        model_id="Qwen/Qwen3.5-0.8B",
        suites=suites,
        variants=variants,
        tasks_per_suite=tasks_per_suite,
    )


# ===========================================================================
# build_cell (3 tests)
# ===========================================================================


class TestBuildCell:
    """build_cell() constructs V5 cell dicts with correct pass-metric fields."""

    def test_build_cell_with_harbor_reward(self):
        """cell with harbor_reward yields verified_pass_at_1 = reward."""
        cell = build_cell(
            suite="mmlu-pro",
            task_id="t001",
            variant=VARIANT_BASELINE,
            model_id="test-model",
            gen_success=True,
            wall_clock_s=1.5,
            reply="The answer is 4",
            harbor_reward=0.85,
        )
        assert cell["suite"] == "mmlu-pro"
        assert cell["task_id"] == "t001"
        assert cell["suite_task_key"] == "mmlu-pro::t001"
        assert cell["variant"] == VARIANT_BASELINE
        assert cell["model_id"] == "test-model"
        assert cell["ok"] is True
        assert cell["wall_clock_s"] == 1.5
        assert cell["gen_ok"] == 1.0
        assert cell["verified_pass_at_1"] == 0.85
        assert cell["evidence_label"] == "verified"
        assert cell["reply"] == "The answer is 4"

    def test_build_cell_without_harbor_reward(self):
        """cell without harbor_reward defaults verified_pass_at_1 to 0.0."""
        cell = build_cell(
            suite="ifeval",
            task_id="t002",
            variant=VARIANT_CANDIDATE,
            model_id="test-model",
            gen_success=True,
            wall_clock_s=0.5,
            reply="hello",
        )
        assert cell["verified_pass_at_1"] == 0.0
        assert cell["evidence_label"] == "reported"
        assert cell["gen_ok"] == 1.0
        assert cell["ok"] is True
        assert cell["suite_task_key"] == "ifeval::t002"
        assert cell["tokens_created"] == len("hello") // 4

    def test_build_cell_gen_success_false(self):
        """gen_success=False sets gen_ok=0.0, ok=False, reply truncated."""
        cell = build_cell(
            suite="aime",
            task_id="t003",
            variant=VARIANT_BASELINE,
            model_id="test-model",
            gen_success=False,
            wall_clock_s=0.0,
            reply="",
        )
        assert cell["ok"] is False
        assert cell["gen_ok"] == 0.0
        assert cell["pass_at_1"] == 0.0
        assert cell["verified_pass_at_1"] == 0.0
        assert cell["reply"] == ""
        assert cell["tokens_created"] == 0


# ===========================================================================
# _run_cell_dry (1 test)
# ===========================================================================


class TestRunCellDry:
    """_run_cell_dry() returns a valid V5 cell from synthetic data."""

    def test_run_cell_dry(self):
        cell = _run_cell_dry("mmlu-pro", "mmlu-pro-task-000", VARIANT_BASELINE, "test-model")
        assert cell["suite"] == "mmlu-pro"
        assert cell["task_id"] == "mmlu-pro-task-000"
        assert cell["variant"] == VARIANT_BASELINE
        assert cell["ok"] is True
        assert cell["gen_ok"] == 1.0
        assert cell["wall_clock_s"] == 0.001
        assert cell["verified_pass_at_1"] == 0.0
        assert "[dry-run:baseline_mlx]" in cell["reply"]


# ===========================================================================
# run_ablation (4 tests)
# ===========================================================================


class TestRunAblation:
    """run_ablation() orchestrates dry and live ablation runs."""

    def test_run_ablation_dry_run(self, monkeypatch):
        """dry_run=True calls get_dry_run_banner and produces cells."""
        monkeypatch.setattr(
            run_ablation_mod, "get_dry_run_banner", lambda **kw: "=== DRY ===",
        )
        config = _make_config(dry_run=True, tasks_per_suite=1, suites=["mmlu-pro"])
        result = run_ablation(config)
        assert result.dry_run is True
        assert len(result.cells) == 1  # 1 suite * 1 task * 1 variant
        assert result.cells[0]["ok"] is True

    def test_run_ablation_dry_run_creates_correct_config(self, monkeypatch):
        """config fields propagate into the AblationResult."""
        monkeypatch.setattr(
            run_ablation_mod, "get_dry_run_banner", lambda **kw: "=== DRY ===",
        )
        config = _make_config(
            run_id="cfg-prop-001",
            suites=["s1", "s2"],
            variants=[VARIANT_BASELINE, VARIANT_CANDIDATE],
            tasks_per_suite=3,
            model_id="test-model-v2",
            dry_run=True,
        )
        result = run_ablation(config)
        assert result.run_id == "cfg-prop-001"
        assert result.suites == ["s1", "s2"]
        assert result.variants == [VARIANT_BASELINE, VARIANT_CANDIDATE]
        assert result.tasks_per_suite == 3
        assert result.model_id == "test-model-v2"
        assert result.dry_run is True
        # 2 suites * 3 tasks * 2 variants = 12 cells
        assert len(result.cells) == 12

    def test_run_ablation_live_mlx_not_available(self):
        """raises RuntimeError when mlx_lm is not installed."""
        config = _make_config(dry_run=False, tasks_per_suite=1)
        with patch.object(run_ablation_mod, "mlx_is_available", return_value=False):
            with pytest.raises(RuntimeError, match="mlx_lm is not installed"):
                run_ablation(config)

    def test_run_ablation_live_mlx_success(self):
        """live run with mocked MLXDirect produces cells."""
        mock_mlx_instance = MagicMock()
        mock_mlx_instance.generate.return_value = "live answer"

        config = _make_config(
            dry_run=False,
            tasks_per_suite=1,
            suites=["mmlu-pro"],
            variants=[VARIANT_BASELINE],
        )
        with (
            patch.object(run_ablation_mod, "mlx_is_available", return_value=True),
            patch.object(run_ablation_mod, "MLXDirect", return_value=mock_mlx_instance),
        ):
            result = run_ablation(config)

        assert result.dry_run is False
        assert len(result.cells) == 1
        cell = result.cells[0]
        assert cell["ok"] is True
        assert cell["reply"] == "live answer"
        assert cell["gen_ok"] == 1.0
        mock_mlx_instance.generate.assert_called_once()


# ===========================================================================
# run_ablation — multiple suites (1 test)
# ===========================================================================


class TestRunAblationMultipleSuites:
    """run_ablation() with multiple suites generates all expected cells."""

    def test_run_ablation_multiple_suites(self, monkeypatch):
        monkeypatch.setattr(
            run_ablation_mod, "get_dry_run_banner", lambda **kw: "=== DRY ===",
        )
        config = _make_config(
            suites=["mmlu-pro", "ifeval"],
            variants=[VARIANT_BASELINE],
            tasks_per_suite=2,
        )
        result = run_ablation(config)
        # 2 suites * 2 tasks * 1 variant = 4 cells
        assert len(result.cells) == 4
        suites_seen = {c["suite"] for c in result.cells}
        assert suites_seen == {"mmlu-pro", "ifeval"}


# ===========================================================================
# build_evaluation_report (5 tests)
# ===========================================================================


class TestBuildEvaluationReport:
    """build_evaluation_report() produces contract-shaped EvaluationReport."""

    def test_build_evaluation_report_single_suite(self, monkeypatch):
        """single suite with cells produces a suite entry."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        cell = build_cell(
            suite="mmlu-pro",
            task_id="t001",
            variant=VARIANT_BASELINE,
            model_id="test-model",
            gen_success=True,
        )
        result = _make_result(cells=[cell], suites=["mmlu-pro"])
        report = build_evaluation_report(result)
        assert report["artifact_kind"] == "EvaluationReport"
        assert report["contract_version"] == "0.1"
        assert len(report["suites"]) == 1
        assert report["suites"][0]["suite"] == "mmlu-pro"
        assert report["suites"][0]["n"] == 1
        assert report["suites"][0]["passed"] == 1

    def test_build_evaluation_report_empty(self, monkeypatch):
        """empty result produces no suite entries and zero totals."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        result = _make_result(cells=[], suites=[])
        report = build_evaluation_report(result)
        assert report["suites"] == []
        assert report["totals"]["cells"] == 0
        assert report["totals"]["passed"] == 0

    def test_build_evaluation_report_gen_ok_path(self, monkeypatch):
        """cells with gen_ok field populate suite-level gen_ok metric."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        cell = build_cell(
            suite="mmlu-pro",
            task_id="t001",
            variant=VARIANT_BASELINE,
            model_id="test-model",
            gen_success=True,
        )
        # Inject gen_ok into the cell directly to exercise the gen_ok path
        cell["gen_ok"] = 1.0
        result = _make_result(cells=[cell], suites=["mmlu-pro"])
        report = build_evaluation_report(result)
        suite = report["suites"][0]
        assert "gen_ok" in suite
        assert suite["gen_ok"] == 1.0
        assert suite["pass_at_1"] == 1.0

    def test_build_evaluation_report_totals(self, monkeypatch):
        """totals aggregate passed/cells across suites."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        cells = [
            build_cell(
                suite="s1",
                task_id=f"t{i}",
                variant=VARIANT_BASELINE,
                model_id="m",
                gen_success=(i < 3),
            )
            for i in range(5)
        ]
        result = _make_result(cells=cells, suites=["s1"])
        report = build_evaluation_report(result)
        assert report["totals"]["cells"] == 5
        assert report["totals"]["passed"] == 3  # first 3 have gen_success=True

    def test_build_evaluation_report_hash_chain(self, monkeypatch):
        """hash_chain is present and contains top_level_sha256."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        cell = build_cell(
            suite="mmlu-pro",
            task_id="t001",
            variant=VARIANT_BASELINE,
            model_id="m",
            gen_success=True,
        )
        result = _make_result(cells=[cell], suites=["mmlu-pro"])
        report = build_evaluation_report(result)
        assert "hash_chain" in report
        assert "top_level_sha256" in report["hash_chain"]
        assert "task_ids_sorted_sha256" in report["hash_chain"]
        assert len(report["hash_chain"]["top_level_sha256"]) == 64


# ===========================================================================
# write_artifacts (2 tests)
# ===========================================================================


class TestWriteArtifacts:
    """write_artifacts() creates cells.json and evaluation_report.json."""

    def test_write_artifacts_creates_files(self, monkeypatch, tmp_path):
        """both files exist after write_artifacts."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        result = _make_result(suites=["mmlu-pro"])
        paths = write_artifacts(result, output_root=tmp_path)
        assert paths["cells"].exists()
        assert paths["evaluation_report"].exists()

    def test_write_artifacts_json_valid(self, monkeypatch, tmp_path):
        """written JSON files are parseable."""
        monkeypatch.setattr(run_ablation_mod, "_git_head", lambda: "abc123")
        result = _make_result(suites=["mmlu-pro"])
        paths = write_artifacts(result, output_root=tmp_path)
        cells_data = json.loads(paths["cells"].read_text(encoding="utf-8"))
        assert "cells" in cells_data
        assert "run_id" in cells_data
        report_data = json.loads(paths["evaluation_report"].read_text(encoding="utf-8"))
        assert report_data["artifact_kind"] == "EvaluationReport"


# ===========================================================================
# build_parser (2 tests)
# ===========================================================================


class TestBuildParser:
    """build_parser() returns an ArgumentParser with correct defaults."""

    def test_build_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.run_id is None
        assert args.tasks_per_suite == 2
        assert args.model == "Qwen/Qwen3.5-0.8B"
        assert args.dry_run is False
        # defaults for suites and variants are comma-separated strings
        assert "mmlu-pro" in args.suites
        assert "baseline_mlx" in args.variants

    def test_build_parser_custom_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "--run-id", "custom-001",
            "--suites", "aime,livecodebench",
            "--variants", "baseline_mlx",
            "--tasks-per-suite", "5",
            "--model", "custom-model",
            "--dry-run",
            "--output-root", "/tmp/custom",
        ])
        assert args.run_id == "custom-001"
        assert args.suites == "aime,livecodebench"
        assert args.variants == "baseline_mlx"
        assert args.tasks_per_suite == 5
        assert args.model == "custom-model"
        assert args.dry_run is True
        assert args.output_root == "/tmp/custom"


# ===========================================================================
# main (4 tests)
# ===========================================================================


class TestMain:
    """main() CLI entry point handles dry-run, invalid args, and auto run-id."""

    def test_main_dry_run(self, monkeypatch, tmp_path):
        """--dry-run completes successfully and writes artifacts."""
        monkeypatch.setattr(
            run_ablation_mod, "get_dry_run_banner", lambda **kw: "=== DRY ===",
        )
        rc = main([
            "--dry-run",
            "--tasks-per-suite", "1",
            "--output-root", str(tmp_path),
        ])
        assert rc == 0

    def test_main_invalid_variant(self):
        """unknown variant returns exit code 2."""
        rc = main([
            "--variants", "bogus_variant",
            "--dry-run",
        ])
        assert rc == 2

    def test_main_zero_tasks(self):
        """--tasks-per-suite 0 returns exit code 2."""
        rc = main([
            "--tasks-per-suite", "0",
            "--dry-run",
        ])
        assert rc == 2

    def test_main_run_id_default(self, monkeypatch, tmp_path):
        """without --run-id, a UUID is generated (run completes successfully)."""
        monkeypatch.setattr(
            run_ablation_mod, "get_dry_run_banner", lambda **kw: "=== DRY ===",
        )
        rc = main([
            "--dry-run",
            "--tasks-per-suite", "1",
            "--output-root", str(tmp_path),
        ])
        assert rc == 0
        # Check that a UUID-like directory was created under tmp_path
        dirs = [d.name for d in tmp_path.iterdir() if d.is_dir()]
        assert len(dirs) == 1
        # UUID4 format: 8-4-4-4-12
        uuid.UUID(dirs[0])  # raises ValueError if not valid UUID


# ===========================================================================
# AblationConfig dataclass (1 test)
# ===========================================================================


class TestAblationConfig:
    """AblationConfig is a frozen dataclass."""

    def test_ablation_config_fields(self):
        config = AblationConfig(
            run_id="r1",
            suites=["s1"],
            variants=["v1"],
            tasks_per_suite=2,
            model_id="m1",
            dry_run=True,
            output_root=Path("/tmp/x"),
        )
        assert config.run_id == "r1"
        assert config.suites == ["s1"]
        assert config.variants == ["v1"]
        assert config.tasks_per_suite == 2
        assert config.model_id == "m1"
        assert config.dry_run is True
        assert config.output_root == Path("/tmp/x")
        # frozen: assignment should raise
        with pytest.raises(AttributeError):
            config.run_id = "r2"  # type: ignore[misc]


# ===========================================================================
# AblationResult dataclass (1 test)
# ===========================================================================


class TestAblationResult:
    """AblationResult is a mutable dataclass."""

    def test_ablation_result_fields(self):
        result = AblationResult(
            run_id="r1",
            cells=[{"k": "v"}],
            started_at="2026-01-01T00:00:00Z",
            stopped_at="2026-01-01T00:00:01Z",
            dry_run=True,
            model_id="m1",
            suites=["s1"],
            variants=["v1"],
            tasks_per_suite=2,
        )
        assert result.run_id == "r1"
        assert len(result.cells) == 1
        assert result.started_at == "2026-01-01T00:00:00Z"
        assert result.stopped_at == "2026-01-01T00:00:01Z"
        assert result.dry_run is True
        assert result.model_id == "m1"
        assert result.suites == ["s1"]
        assert result.variants == ["v1"]
        assert result.tasks_per_suite == 2
        # mutable: assignment should work
        result.run_id = "r2"
        assert result.run_id == "r2"
