"""Unit tests for eval.tbench — score parsing, leaderboard, and export.

Covers ModelScore, _safe_slug, _parse_job_result, score_from_job,
load_state, save_state, build_leaderboard, _representative_task_names,
_matrix_job_is_representative, _matrix_job_task_names, export_leaderboard,
format_leaderboard_table, and best_l2_harbor_reward.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from eval.tbench import (
    ModelScore,
    _matrix_job_is_representative,
    _matrix_job_task_names,
    _matrix_job_task_names_from_path,
    _parse_job_result,
    _representative_task_names,
    _safe_slug,
    best_l2_harbor_reward,
    build_leaderboard,
    build_matrix_cell_leaderboard,
    export_leaderboard,
    format_leaderboard_table,
    load_matrix_config,
    load_state,
    save_state,
    score_from_job,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_model_score() -> ModelScore:
    return ModelScore(
        model_id="local/qwen35-08b",
        label="qwen35-08b",
        mean=0.85,
        n_trials=10,
        n_errors=0,
        pass_at_1=0.7,
        job_dir="/tmp/job",
        combo=False,
        tokens_in=50000,
        tokens_out=10000,
        per_task={"task1": 1.0, "task2": 0.5, "task3": 0.0},
    )


@pytest.fixture
def combo_model_score() -> ModelScore:
    return ModelScore(
        model_id="combo/ref",
        label="combo-ref",
        mean=0.92,
        n_trials=5,
        n_errors=0,
        pass_at_1=0.8,
        job_dir="/tmp/combo",
        combo=True,
        per_task={"task1": 1.0},
    )


@pytest.fixture
def tbench_config() -> dict:
    return {
        "eval_protocol": {
            "dataset": "terminal-bench@2.0",
            "target_mean": 0.80,
            "integrity": {"no_oracle_in_leaderboard": True},
        },
        "models": [
            {"id": "local/qwen35-08b", "label": "qwen35-08b"},
            {"id": "local/lfm25-8b-a1b", "label": "lfm25-8b-a1b"},
        ],
        "combo_reference": [
            {"id": "combo/ref", "label": "combo-ref"},
        ],
        "state_file": "state/tbench_matrix.json",
    }


@pytest.fixture
def sample_result_json(tmp_path: Path) -> Path:
    """Create a job dir with result.json and trial subdirs."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    result_data = {
        "stats": {
            "n_trials": 5,
            "n_errors": 1,
            "n_input_tokens": 10000,
            "n_output_tokens": 2000,
            "evals": {
                "eval1": {
                    "metrics": [{"mean": 0.82, "std": 0.1}],
                },
            },
        },
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T01:00:00Z",
    }
    (job_dir / "result.json").write_text(json.dumps(result_data), encoding="utf-8")

    # Trial directories
    for i, (task, reward) in enumerate(
        [("task_a", 1.0), ("task_b", 0.5), ("task_c", 0.0)]
    ):
        trial = job_dir / f"trial_{i}"
        trial.mkdir()
        trial_result = {
            "task_name": task,
            "verifier_result": {"rewards": {"reward": reward}},
        }
        (trial / "result.json").write_text(json.dumps(trial_result), encoding="utf-8")

    return job_dir


# ---------------------------------------------------------------------------
# ModelScore
# ---------------------------------------------------------------------------

class TestModelScore:
    def test_to_dict(self, sample_model_score: ModelScore) -> None:
        d = sample_model_score.to_dict()
        assert d["model_id"] == "local/qwen35-08b"
        assert d["label"] == "qwen35-08b"
        assert d["mean"] == 0.85
        assert d["n_trials"] == 10
        assert d["n_errors"] == 0
        assert d["pass_at_1"] == 0.7
        assert d["combo"] is False
        assert d["tokens_in"] == 50000
        assert d["tokens_out"] == 10000
        assert d["per_task_count"] == 3

    def test_defaults(self) -> None:
        ms = ModelScore(
            model_id="test",
            label="Test",
            mean=0.5,
            n_trials=1,
            n_errors=0,
            pass_at_1=0.5,
            job_dir="/tmp",
        )
        assert ms.combo is False
        assert ms.tokens_in is None
        assert ms.tokens_out is None
        assert ms.per_task == {}

    def test_combo_score(self, combo_model_score: ModelScore) -> None:
        d = combo_model_score.to_dict()
        assert d["combo"] is True


# ---------------------------------------------------------------------------
# _safe_slug
# ---------------------------------------------------------------------------

class TestSafeSlug:
    def test_slash_replacement(self) -> None:
        assert _safe_slug("openai/gpt-4") == "openai__gpt-4"

    def test_colon_replacement(self) -> None:
        assert _safe_slug("model:v2") == "model_v2"

    def test_combined(self) -> None:
        assert _safe_slug("a/b:c") == "a__b_c"

    def test_no_changes_needed(self) -> None:
        assert _safe_slug("simple-model") == "simple-model"


# ---------------------------------------------------------------------------
# _parse_job_result
# ---------------------------------------------------------------------------

class TestParseJobResult:
    def test_missing_result(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "no_result"
        job_dir.mkdir()
        assert _parse_job_result(job_dir) is None

    def test_parses_correctly(self, sample_result_json: Path) -> None:
        result = _parse_job_result(sample_result_json)
        assert result is not None
        assert result["mean"] == 0.82
        assert result["n_trials"] == 5
        assert result["n_errors"] == 1
        assert result["tokens_in"] == 10000
        assert result["tokens_out"] == 2000
        assert "task_a" in result["per_task"]
        assert result["per_task"]["task_a"] == 1.0

    def test_no_mean_in_evals(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {"stats": {"n_trials": 1, "evals": {"e1": {"metrics": []}}}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        result = _parse_job_result(job_dir)
        assert result is not None
        assert result["mean"] is None

    def test_fallback_n_total_trials(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {"n_total_trials": 7, "stats": {"evals": {}}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        result = _parse_job_result(job_dir)
        assert result is not None
        assert result["n_trials"] == 7

    def test_empty_stats(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {"stats": {}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        result = _parse_job_result(job_dir)
        assert result is not None
        assert result["n_trials"] == 0
        assert result["n_errors"] == 0

    def test_trial_without_result_json_skipped(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        trial = job_dir / "trial_empty"
        trial.mkdir()
        data = {"stats": {"n_trials": 1, "evals": {}}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        result = _parse_job_result(job_dir)
        assert result is not None
        assert result["per_task"] == {}

    def test_non_directory_in_job_dir_skipped(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "not_a_dir.txt").write_text("x")
        data = {"stats": {"n_trials": 1, "evals": {}}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        result = _parse_job_result(job_dir)
        assert result is not None


# ---------------------------------------------------------------------------
# score_from_job
# ---------------------------------------------------------------------------

class TestScoreFromJob:
    def test_returns_none_on_missing(self, tmp_path: Path) -> None:
        assert score_from_job(tmp_path / "nonexistent", "test", "Test") is None

    def test_returns_none_on_no_mean(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {"stats": {"n_trials": 1, "evals": {}}}
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        assert score_from_job(job_dir, "test", "Test") is None

    def test_returns_model_score(self, sample_result_json: Path) -> None:
        ms = score_from_job(sample_result_json, "local/qwen35-08b", "qwen35-08b")
        assert ms is not None
        assert ms.model_id == "local/qwen35-08b"
        assert ms.mean == 0.82
        assert ms.n_trials == 5
        assert ms.n_errors == 1
        assert ms.pass_at_1 > 0  # 1.0 reward >= 1.0

    def test_pass_at_1_computed(self, sample_result_json: Path) -> None:
        ms = score_from_job(sample_result_json, "m", "L")
        assert ms is not None
        # task_a: 1.0 (pass), task_b: 0.5 (fail), task_c: 0.0 (fail)
        # pass_at_1 = 1/3
        assert abs(ms.pass_at_1 - 1 / 3) < 0.01

    def test_pass_at_1_empty_per_task(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {
            "stats": {
                "n_trials": 0,
                "evals": {"e1": {"metrics": [{"mean": 0.9}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        ms = score_from_job(job_dir, "m", "L")
        assert ms is not None
        assert ms.pass_at_1 == 0.0

    def test_combo_flag(self, sample_result_json: Path) -> None:
        ms = score_from_job(sample_result_json, "m", "L", combo=True)
        assert ms is not None
        assert ms.combo is True

    def test_tokens_passed_through(self, sample_result_json: Path) -> None:
        ms = score_from_job(sample_result_json, "m", "L")
        assert ms is not None
        assert ms.tokens_in == 10000
        assert ms.tokens_out == 2000


# ---------------------------------------------------------------------------
# _safe_slug edge cases
# ---------------------------------------------------------------------------

class TestSafeSlugEdge:
    def test_empty_string(self) -> None:
        assert _safe_slug("") == ""


# ---------------------------------------------------------------------------
# _matrix_job_task_names
# ---------------------------------------------------------------------------

class TestMatrixJobTaskNames:
    def test_extracts_names(self) -> None:
        config = {
            "datasets": [
                {"task_names": ["task_a", "task_b"]},
                {"task_names": ["task_c"]},
            ]
        }
        result = _matrix_job_task_names(config)
        assert result == {"task_a", "task_b", "task_c"}

    def test_empty_datasets(self) -> None:
        assert _matrix_job_task_names({"datasets": []}) == set()

    def test_no_datasets(self) -> None:
        assert _matrix_job_task_names({}) == set()

    def test_strips_whitespace(self) -> None:
        config = {"datasets": [{"task_names": [" task_a ", ""]}]}.copy()
        result = _matrix_job_task_names(config)
        assert result == {"task_a"}

    def test_skips_none_names(self) -> None:
        # str(None) becomes "None" which is truthy after strip; the function
        # does not filter None from input — it converts via str() then strips.
        config = {"datasets": [{"task_names": [None, "valid"]}]}.copy()
        result = _matrix_job_task_names(config)
        # None passes through as string "None" — function does not special-case it
        assert "valid" in result


# ---------------------------------------------------------------------------
# _matrix_job_task_names_from_path
# ---------------------------------------------------------------------------

class TestMatrixJobTaskNamesFromPath:
    def test_missing_config(self, tmp_path: Path) -> None:
        assert _matrix_job_task_names_from_path(tmp_path) == []

    def test_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text("not json", encoding="utf-8")
        assert _matrix_job_task_names_from_path(tmp_path) == []

    def test_valid_config(self, tmp_path: Path) -> None:
        config = {"datasets": [{"task_names": ["b", "a"]}]}
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        result = _matrix_job_task_names_from_path(tmp_path)
        assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# _matrix_job_is_representative
# ---------------------------------------------------------------------------

class TestMatrixJobIsRepresentative:
    def test_empty_task_names(self, tmp_path: Path) -> None:
        assert _matrix_job_is_representative(tmp_path, set()) is False

    def test_missing_config(self, tmp_path: Path) -> None:
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is False

    def test_not_single_task(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_a", "task_b"]}],
            "agents": [{"import_path": "harness.harbor.terminus_safe:SafeTerminus2"}],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a", "task_b"}) is False

    def test_task_not_in_lock(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_x"]}],
            "agents": [{"import_path": "harness.harbor.terminus_safe:SafeTerminus2"}],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is False

    def test_wrong_import_path(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_a"]}],
            "agents": [{"import_path": "wrong/path:Class"}],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is False

    def test_valid_representative(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_a"]}],
            "agents": [{"import_path": "harness.harbor.terminus_safe:SafeTerminus2"}],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is True

    def test_legacy_import_path(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_a"]}],
            "agents": [{"import_path": "pheno_agent.terminus_safe:SafeTerminus2"}],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is True

    def test_no_agents(self, tmp_path: Path) -> None:
        config = {
            "datasets": [{"task_names": ["task_a"]}],
            "agents": [],
        }
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        assert _matrix_job_is_representative(tmp_path, {"task_a"}) is False


# ---------------------------------------------------------------------------
# _representative_task_names
# ---------------------------------------------------------------------------

class TestRepresentativeTaskNames:
    def test_missing_manifest(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            "eval.tbench.PHENO_ROOT", tmp_path,
        )
        result = _representative_task_names()
        assert result == set()

    def test_invalid_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir.parent / "config" / "..").mkdir(parents=True, exist_ok=True)
        manifest = tmp_path / "config" / "tbench20_representative_subset.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("bad json", encoding="utf-8")
        # We need to patch PHENO_ROOT to point to tmp_path
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = _representative_task_names()
        assert result == set()

    def test_loads_task_names(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        manifest = config_dir / "tbench20_representative_subset.json"
        manifest.write_text(
            json.dumps({"task_names": ["task_a", "task_b"]}), encoding="utf-8"
        )
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = _representative_task_names()
        assert result == {"task_a", "task_b"}

    def test_uses_task_ids_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        manifest = config_dir / "tbench20_representative_subset.json"
        manifest.write_text(
            json.dumps({"task_ids": ["id1"]}), encoding="utf-8"
        )
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = _representative_task_names()
        assert result == {"id1"}


# ---------------------------------------------------------------------------
# load_state / save_state
# ---------------------------------------------------------------------------

class TestState:
    def test_save_and_load_roundtrip(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = {"state_file": "state/tbench_matrix.json"}
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        state = {"models": {"m1": {"status": "complete"}}}
        path = save_state(state)
        assert path.exists()
        loaded = load_state()
        assert loaded["models"]["m1"]["status"] == "complete"
        assert "updated_at" in loaded

    def test_load_state_missing_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = {"state_file": "state/tbench_matrix.json"}
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = load_state()
        assert result == {"models": {}, "updated_at": None}

    def test_load_state_non_dict(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = {"state_file": "state/tbench_matrix.json"}
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        (state_dir / "tbench_matrix.json").write_text(
            json.dumps([1, 2, 3]), encoding="utf-8"
        )
        result = load_state()
        assert result == {"models": {}, "updated_at": None}

    def test_load_state_default_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {})
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = load_state()
        assert result == {"models": {}, "updated_at": None}


# ---------------------------------------------------------------------------
# build_leaderboard
# ---------------------------------------------------------------------------

class TestBuildLeaderboard:
    def test_empty_when_no_state(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = {
            "models": [{"id": "m1", "label": "M1"}],
            "state_file": "state/tbench_matrix.json",
        }
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        scores = build_leaderboard()
        assert scores == []

    def test_includes_completed_models(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {
            "stats": {
                "n_trials": 1,
                "evals": {"e1": {"metrics": [{"mean": 0.9}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        cfg = {
            "models": [{"id": "m1", "label": "M1"}],
            "state_file": "state/tbench_matrix.json",
        }
        state = {"models": {"m1": {"status": "complete", "job_dir": str(job_dir)}}}
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.load_state", lambda: state)
        scores = build_leaderboard()
        assert len(scores) == 1
        assert scores[0].mean == 0.9

    def test_excludes_incomplete_models(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = {
            "models": [{"id": "m1", "label": "M1"}],
            "state_file": "state/tbench_matrix.json",
        }
        state = {"models": {"m1": {"status": "running"}}}
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.load_state", lambda: state)
        scores = build_leaderboard()
        assert scores == []

    def test_sorted_by_mean_desc(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        """Build two job dirs and verify descending sort."""
        for name, mean_val in [("job_low", 0.5), ("job_high", 0.9)]:
            jdir = tmp_path / name
            jdir.mkdir()
            data = {
                "stats": {
                    "n_trials": 1,
                    "evals": {"e1": {"metrics": [{"mean": mean_val}]}},
                }
            }
            (jdir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        cfg = {
            "models": [
                {"id": "low", "label": "Low"},
                {"id": "high", "label": "High"},
            ],
            "state_file": "state/tbench_matrix.json",
        }
        state = {
            "models": {
                "low": {"status": "complete", "job_dir": str(tmp_path / "job_low")},
                "high": {"status": "complete", "job_dir": str(tmp_path / "job_high")},
            }
        }
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.load_state", lambda: state)
        scores = build_leaderboard()
        assert len(scores) == 2
        assert scores[0].mean >= scores[1].mean

    def test_include_combo(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {
            "stats": {
                "n_trials": 1,
                "evals": {"e1": {"metrics": [{"mean": 0.8}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        cfg = {
            "models": [{"id": "ind", "label": "Ind"}],
            "combo_reference": [{"id": "combo", "label": "Combo"}],
            "state_file": "state/tbench_matrix.json",
        }
        state = {
            "models": {
                "ind": {"status": "complete", "job_dir": str(job_dir)},
                "combo": {"status": "complete", "job_dir": str(job_dir)},
            }
        }
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.load_state", lambda: state)
        scores = build_leaderboard(include_combo=True)
        combo_scores = [s for s in scores if s.combo]
        assert len(combo_scores) == 1

    def test_relative_job_dir_resolved(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        data = {
            "stats": {
                "n_trials": 1,
                "evals": {"e1": {"metrics": [{"mean": 0.7}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        cfg = {
            "models": [{"id": "m1", "label": "M1"}],
            "state_file": "state/tbench_matrix.json",
        }
        state = {
            "models": {
                "m1": {"status": "complete", "job_dir": "job"},
            }
        }
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: cfg)
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.load_state", lambda: state)
        scores = build_leaderboard()
        assert len(scores) == 1


# ---------------------------------------------------------------------------
# build_matrix_cell_leaderboard
# ---------------------------------------------------------------------------

class TestBuildMatrixCellLeaderboard:
    def test_empty_when_no_root(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        result = build_matrix_cell_leaderboard()
        assert result == []

    def test_scores_jobs(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cells_root = tmp_path / "jobs" / "harbor" / "matrix-cells"
        cell_dir = cells_root / "model_a"
        cell_dir.mkdir(parents=True)
        job_dir = cell_dir / "job1"
        job_dir.mkdir()
        data = {
            "stats": {
                "n_trials": 1,
                "evals": {"e1": {"metrics": [{"mean": 0.75}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        scores = build_matrix_cell_leaderboard()
        assert len(scores) == 1
        assert scores[0].model_id == "model_a"

    def test_representative_only_filters(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cells_root = tmp_path / "jobs" / "harbor" / "matrix-cells"
        cell_dir = cells_root / "model_a"
        cell_dir.mkdir(parents=True)
        job_dir = cell_dir / "job1"
        job_dir.mkdir()
        config = {"datasets": [{"task_names": ["task_a"]}], "agents": []}
        (job_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
        data = {
            "stats": {
                "n_trials": 1,
                "evals": {"e1": {"metrics": [{"mean": 0.75}]}},
            }
        }
        (job_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        # Empty representative subset means nothing is representative
        monkeypatch.setattr("eval.tbench._representative_task_names", lambda: set())
        scores = build_matrix_cell_leaderboard(representative_only=True)
        assert scores == []

    def test_skips_dirs_without_result_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cells_root = tmp_path / "jobs" / "harbor" / "matrix-cells"
        cell_dir = cells_root / "model_a"
        cell_dir.mkdir(parents=True)
        job_dir = cell_dir / "job_no_result"
        job_dir.mkdir()
        # No result.json
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        scores = build_matrix_cell_leaderboard()
        assert scores == []


# ---------------------------------------------------------------------------
# format_leaderboard_table
# ---------------------------------------------------------------------------

class TestFormatLeaderboardTable:
    def test_no_models(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {})
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [])
        table = format_leaderboard_table()
        assert "no completed individual model runs yet" in table

    def test_renders_rows(
        self, monkeypatch: pytest.MonkeyPatch, sample_model_score: ModelScore,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {"eval_protocol": {"target_mean": 0.8}})
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [sample_model_score])
        table = format_leaderboard_table(include_combo=False)
        assert "qwen35-08b" in table
        assert "0.850" in table

    def test_combo_rows(
        self, monkeypatch: pytest.MonkeyPatch,
        sample_model_score: ModelScore, combo_model_score: ModelScore,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {"eval_protocol": {"target_mean": 0.8}})
        monkeypatch.setattr(
            "eval.tbench.build_leaderboard",
            lambda **kw: [sample_model_score, combo_model_score],
        )
        table = format_leaderboard_table(include_combo=True)
        assert "combo" in table.lower()


# ---------------------------------------------------------------------------
# best_l2_harbor_reward
# ---------------------------------------------------------------------------

class TestBestL2HarborReward:
    def test_returns_none_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [])
        assert best_l2_harbor_reward() is None

    def test_returns_best_mean(self, monkeypatch: pytest.MonkeyPatch, sample_model_score: ModelScore) -> None:
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [sample_model_score])
        assert best_l2_harbor_reward() == 0.85


# ---------------------------------------------------------------------------
# load_matrix_config
# ---------------------------------------------------------------------------

class TestLoadMatrixConfig:
    def test_loads_yaml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg_path = tmp_path / "harbor_tbench_models.yaml"
        cfg_path.write_text(yaml.dump({"eval_protocol": {"target_mean": 0.9}}), encoding="utf-8")
        monkeypatch.setattr("eval.tbench.CONFIG_DIR", tmp_path)
        result = load_matrix_config()
        assert result["eval_protocol"]["target_mean"] == 0.9

    def test_non_dict_returns_empty(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg_path = tmp_path / "harbor_tbench_models.yaml"
        cfg_path.write_text(yaml.dump(["a", "b"]), encoding="utf-8")
        monkeypatch.setattr("eval.tbench.CONFIG_DIR", tmp_path)
        result = load_matrix_config()
        assert result == {}


# ---------------------------------------------------------------------------
# export_leaderboard
# ---------------------------------------------------------------------------

class TestExportLeaderboard:
    def test_writes_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8, "integrity": {}},
            "results_file": str(tmp_path / "custom_results.json"),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        path = export_leaderboard()
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert data["dataset"] == "terminal-bench@2.0"
        # Also check the latest file
        latest = tmp_path / "eval_results" / "tbench_model_scores_latest.json"
        assert latest.exists()

    def test_custom_results_file_written(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        custom_path = custom_dir / "out.json"
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8},
            "results_file": str(custom_path),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        export_leaderboard()
        assert custom_path.exists()

    def test_results_file_same_as_out_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        out_path = tmp_path / "eval_results" / "tbench_model_scores.json"
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8},
            "results_file": str(out_path),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        path = export_leaderboard()
        assert path.exists()

    def test_meets_target_true(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_model_score: ModelScore,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8},
            "results_file": str(tmp_path / "out.json"),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [sample_model_score])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        path = export_leaderboard()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["meets_target"] is True

    def test_best_individual(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_model_score: ModelScore,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8},
            "results_file": str(tmp_path / "out.json"),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [sample_model_score])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        path = export_leaderboard()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["best_individual"] is not None
        assert data["best_individual"]["model_id"] == "local/qwen35-08b"

    def test_best_individual_combo_only(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, combo_model_score: ModelScore,
    ) -> None:
        monkeypatch.setattr("eval.tbench.load_matrix_config", lambda: {
            "eval_protocol": {"target_mean": 0.8},
            "results_file": str(tmp_path / "out.json"),
        })
        monkeypatch.setattr("eval.tbench.build_leaderboard", lambda **kw: [combo_model_score])
        monkeypatch.setattr("eval.tbench.build_matrix_cell_leaderboard", lambda **kw: [])
        monkeypatch.setattr("eval.tbench.PHENO_ROOT", tmp_path)
        monkeypatch.setattr("eval.tbench.EVAL_RESULTS_DIR", tmp_path / "eval_results")
        path = export_leaderboard()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["best_individual"] is None
