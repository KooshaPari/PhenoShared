"""Tests for eval/route_matrix.py — coverage-focused.

Covers load_routes_config, load_routes_state, save_routes_state,
_entry_cost_rates, estimate_run_cost_usd, estimate_tok_s, _job_duration_sec,
pillar_scores, RouteScore dataclass, score_route_from_job,
build_route_leaderboard, export_route_leaderboard, and format_route_table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ======================================================================
# 1. _entry_cost_rates
# ======================================================================


class TestEntryCostRates:
    def test_entry_cost_rates_with_values(self) -> None:
        from eval.route_matrix import _entry_cost_rates

        entry = {"cost_per_m_in": 2.5, "cost_per_m_out": 10.0}
        assert _entry_cost_rates(entry) == (2.5, 10.0)

    def test_entry_cost_rates_defaults(self) -> None:
        from eval.route_matrix import _entry_cost_rates

        assert _entry_cost_rates({}) == (0.0, 0.0)

    def test_entry_cost_rates_partial(self) -> None:
        from eval.route_matrix import _entry_cost_rates

        entry = {"cost_per_m_in": 1.0}
        assert _entry_cost_rates(entry) == (1.0, 0.0)

    def test_entry_cost_rates_string_values(self) -> None:
        from eval.route_matrix import _entry_cost_rates

        entry = {"cost_per_m_in": "3.0", "cost_per_m_out": "7.0"}
        assert _entry_cost_rates(entry) == (3.0, 7.0)


# ======================================================================
# 2. estimate_run_cost_usd
# ======================================================================


class TestEstimateRunCostUsd:
    def test_basic_cost(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry = {"cost_per_m_in": 2.5, "cost_per_m_out": 10.0}
        cost = estimate_run_cost_usd(1_000_000, 500_000, entry)
        assert cost == pytest.approx(2.5 + 5.0)

    def test_zero_tokens(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry = {"cost_per_m_in": 2.5, "cost_per_m_out": 10.0}
        assert estimate_run_cost_usd(0, 0, entry) == 0.0

    def test_none_tokens(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry = {"cost_per_m_in": 2.5, "cost_per_m_out": 10.0}
        assert estimate_run_cost_usd(None, None, entry) == 0.0

    def test_only_input_tokens(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry = {"cost_per_m_in": 5.0, "cost_per_m_out": 10.0}
        cost = estimate_run_cost_usd(1_000_000, None, entry)
        assert cost == pytest.approx(5.0)

    def test_only_output_tokens(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry = {"cost_per_m_in": 5.0, "cost_per_m_out": 10.0}
        cost = estimate_run_cost_usd(None, 1_000_000, entry)
        assert cost == pytest.approx(10.0)

    def test_zero_cost_entry(self) -> None:
        from eval.route_matrix import estimate_run_cost_usd

        entry: dict[str, float] = {}
        assert estimate_run_cost_usd(1_000_000, 1_000_000, entry) == 0.0


# ======================================================================
# 3. estimate_tok_s
# ======================================================================


class TestEstimateTokS:
    def test_basic(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(1000, 10.0) == 100.0

    def test_none_tokens_out(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(None, 10.0) is None

    def test_none_duration(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(1000, None) is None

    def test_zero_duration(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(1000, 0.0) is None

    def test_negative_duration(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(1000, -5.0) is None

    def test_zero_tokens_out(self) -> None:
        from eval.route_matrix import estimate_tok_s

        assert estimate_tok_s(0, 10.0) is None


# ======================================================================
# 4. pillar_scores
# ======================================================================


class TestPillarScores:
    def test_perfect_scores(self) -> None:
        from eval.route_matrix import pillar_scores

        entry = {"tok_s_target": 50.0, "route_kind": "omniroute_cloud"}
        result = pillar_scores(1.0, tok_s=50.0, cost_usd=0.0, entry=entry, target_mean=0.8)
        assert result["accuracy"] == 1.0
        assert result["speed"] == 1.0
        assert result["cost"] == 1.0
        assert result["composite"] == pytest.approx(1.0)

    def test_zero_accuracy(self) -> None:
        from eval.route_matrix import pillar_scores

        entry: dict[str, Any] = {"tok_s_target": 40.0}
        result = pillar_scores(0.0, tok_s=0.0, cost_usd=5.0, entry=entry)
        assert result["accuracy"] == 0.0
        assert result["speed"] == 0.0
        assert result["cost"] == 0.0
        assert result["composite"] == pytest.approx(0.0)

    def test_zero_target_mean(self) -> None:
        from eval.route_matrix import pillar_scores

        entry: dict[str, Any] = {}
        result = pillar_scores(0.5, tok_s=None, cost_usd=2.5, entry=entry, target_mean=0.0)
        assert result["accuracy"] == 0.5

    def test_tok_s_none_local_direct(self) -> None:
        from eval.route_matrix import pillar_scores

        entry = {"route_kind": "local_direct"}
        result = pillar_scores(0.8, tok_s=None, cost_usd=0.0, entry=entry)
        assert result["speed"] == 0.0

    def test_tok_s_none_pheno_serve(self) -> None:
        from eval.route_matrix import pillar_scores

        entry = {"route_kind": "pheno_serve"}
        result = pillar_scores(0.8, tok_s=None, cost_usd=0.0, entry=entry)
        assert result["speed"] == 0.0

    def test_tok_s_none_cloud_route(self) -> None:
        from eval.route_matrix import pillar_scores

        entry = {"route_kind": "omniroute_cloud"}
        result = pillar_scores(0.8, tok_s=None, cost_usd=0.0, entry=entry)
        assert result["speed"] == 0.5

    def test_tok_s_exceeds_target(self) -> None:
        from eval.route_matrix import pillar_scores

        entry = {"tok_s_target": 40.0}
        result = pillar_scores(0.8, tok_s=100.0, cost_usd=0.0, entry=entry)
        assert result["speed"] == 1.0

    def test_cost_over_5_dollars(self) -> None:
        from eval.route_matrix import pillar_scores

        entry: dict[str, Any] = {}
        result = pillar_scores(0.8, tok_s=50.0, cost_usd=10.0, entry=entry)
        assert result["cost"] == 0.0

    def test_default_tok_s_target(self) -> None:
        from eval.route_matrix import pillar_scores

        entry: dict[str, Any] = {}
        result = pillar_scores(0.8, tok_s=40.0, cost_usd=0.0, entry=entry)
        assert result["speed"] == 1.0


# ======================================================================
# 5. RouteScore dataclass
# ======================================================================


class TestRouteScore:
    def test_to_dict(self) -> None:
        from eval.route_matrix import RouteScore

        rs = RouteScore(
            model_id="test-model",
            label="Test Model",
            route_kind="omniroute_cloud",
            routing_policy="round_robin",
            mean=0.85,
            n_trials=10,
            n_errors=0,
            pass_at_1=0.8,
            tokens_in=50000,
            tokens_out=20000,
            tok_s=30.0,
            cost_usd=0.123456,
            pillars={"accuracy": 1.0, "speed": 0.75, "cost": 0.9, "composite": 0.89},
            job_dir="/tmp/job",
        )
        d = rs.to_dict()
        assert d["model_id"] == "test-model"
        assert d["label"] == "Test Model"
        assert d["mean"] == 0.85
        assert d["n_trials"] == 10
        assert d["n_errors"] == 0
        assert d["pass_at_1"] == 0.8
        assert d["tokens_in"] == 50000
        assert d["tokens_out"] == 20000
        assert d["tok_s"] == 30.0
        assert d["cost_usd"] == 0.1235
        assert d["combo"] is False
        assert d["job_dir"] == "/tmp/job"

    def test_to_dict_combo(self) -> None:
        from eval.route_matrix import RouteScore

        rs = RouteScore(
            model_id="combo",
            label="Combo",
            route_kind="omniroute_combo",
            routing_policy="combo",
            mean=0.9,
            n_trials=5,
            n_errors=1,
            pass_at_1=0.6,
            tokens_in=None,
            tokens_out=None,
            tok_s=None,
            cost_usd=0.0,
            pillars={},
            job_dir="",
            combo=True,
        )
        d = rs.to_dict()
        assert d["combo"] is True
        assert d["tokens_in"] is None


# ======================================================================
# 6. load_routes_config
# ======================================================================


class TestLoadRoutesConfig:
    @patch("eval.route_matrix.yaml.safe_load")
    @patch("eval.route_matrix.CONFIG_DIR")
    def test_load_routes_config_dict(self, mock_cfg_dir: MagicMock, mock_safe_load: MagicMock) -> None:
        from eval.route_matrix import load_routes_config

        mock_file = MagicMock()
        mock_file.read_text.return_value = "models:\n  - id: test"
        mock_cfg_dir.__truediv__ = MagicMock(return_value=mock_file)
        mock_safe_load.return_value = {"models": [{"id": "test"}]}
        result = load_routes_config()
        assert isinstance(result, dict)
        assert "models" in result

    @patch("eval.route_matrix.yaml.safe_load")
    @patch("eval.route_matrix.CONFIG_DIR")
    def test_load_routes_config_non_dict(self, mock_cfg_dir: MagicMock, mock_safe_load: MagicMock) -> None:
        from eval.route_matrix import load_routes_config

        mock_file = MagicMock()
        mock_file.read_text.return_value = "item"
        mock_cfg_dir.__truediv__ = MagicMock(return_value=mock_file)
        mock_safe_load.return_value = "just a string"
        result = load_routes_config()
        assert result == {}


# ======================================================================
# 7. load_routes_state
# ======================================================================


class TestLoadRoutesState:
    @patch("eval.route_matrix.load_routes_config")
    @patch("eval.route_matrix.PHENO_ROOT")
    def test_load_routes_state_file_exists(self, mock_root: MagicMock, mock_cfg: MagicMock) -> None:
        from eval.route_matrix import load_routes_state

        mock_cfg.return_value = {"state_file": "state/test.json"}
        state_data = {"models": {"m1": {"status": "complete"}}, "updated_at": "2026-01-01"}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(state_data)
        mock_root.__truediv__ = MagicMock(return_value=mock_path)
        result = load_routes_state()
        assert result["models"]["m1"]["status"] == "complete"

    @patch("eval.route_matrix.load_routes_config")
    @patch("eval.route_matrix.PHENO_ROOT")
    def test_load_routes_state_file_missing(self, mock_root: MagicMock, mock_cfg: MagicMock) -> None:
        from eval.route_matrix import load_routes_state

        mock_cfg.return_value = {"state_file": "state/test.json"}
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_root.__truediv__ = MagicMock(return_value=mock_path)
        result = load_routes_state()
        assert result == {"models": {}, "updated_at": None}

    @patch("eval.route_matrix.load_routes_config")
    @patch("eval.route_matrix.PHENO_ROOT")
    def test_load_routes_state_non_dict_json(self, mock_root: MagicMock, mock_cfg: MagicMock) -> None:
        from eval.route_matrix import load_routes_state

        mock_cfg.return_value = {"state_file": "state/test.json"}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps("just a string")
        mock_root.__truediv__ = MagicMock(return_value=mock_path)
        result = load_routes_state()
        assert result == {"models": {}, "updated_at": None}

    @patch("eval.route_matrix.load_routes_config")
    @patch("eval.route_matrix.PHENO_ROOT")
    def test_load_routes_state_default_path(self, mock_root: MagicMock, mock_cfg: MagicMock) -> None:
        from eval.route_matrix import load_routes_state

        mock_cfg.return_value = {}
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_root.__truediv__ = MagicMock(return_value=mock_path)
        load_routes_state()
        # Verify it used the default state_file path
        mock_root.__truediv__.assert_called_with("state/tbench_routes_matrix.json")


# ======================================================================
# 8. save_routes_state
# ======================================================================


class TestSaveRoutesState:
    @patch("eval.route_matrix.load_routes_config")
    @patch("eval.route_matrix.PHENO_ROOT")
    def test_save_routes_state_creates_parent(self, mock_root: MagicMock, mock_cfg: MagicMock) -> None:
        from eval.route_matrix import save_routes_state

        mock_cfg.return_value = {"state_file": "state/test.json"}
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        mock_root.__truediv__ = MagicMock(return_value=mock_path)
        state: dict[str, Any] = {"models": {}, "updated_at": None}
        save_routes_state(state)
        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_path.write_text.assert_called_once()
        assert state["updated_at"] is not None


# ======================================================================
# 9. _job_duration_sec
# ======================================================================


class TestJobDurationSec:
    @patch("eval.route_matrix._parse_job_result")
    def test_valid_duration(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:01:00Z",
        }
        result = _job_duration_sec(Path("/tmp/job"))
        assert result == 60.0

    @patch("eval.route_matrix._parse_job_result")
    def test_no_parsed_result(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = None
        assert _job_duration_sec(Path("/tmp/job")) is None

    @patch("eval.route_matrix._parse_job_result")
    def test_missing_started_at(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {"finished_at": "2026-01-01T00:01:00Z"}
        assert _job_duration_sec(Path("/tmp/job")) is None

    @patch("eval.route_matrix._parse_job_result")
    def test_missing_finished_at(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {"started_at": "2026-01-01T00:00:00Z"}
        assert _job_duration_sec(Path("/tmp/job")) is None

    @patch("eval.route_matrix._parse_job_result")
    def test_invalid_timestamps(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {
            "started_at": "not-a-date",
            "finished_at": "also-not-a-date",
        }
        assert _job_duration_sec(Path("/tmp/job")) is None

    @patch("eval.route_matrix._parse_job_result")
    def test_same_timestamps(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:00Z",
        }
        assert _job_duration_sec(Path("/tmp/job")) == 0.0

    @patch("eval.route_matrix._parse_job_result")
    def test_negative_duration_clamped(self, mock_parse: MagicMock) -> None:
        from eval.route_matrix import _job_duration_sec

        mock_parse.return_value = {
            "started_at": "2026-01-01T00:01:00Z",
            "finished_at": "2026-01-01T00:00:00Z",
        }
        result = _job_duration_sec(Path("/tmp/job"))
        assert result == 0.0


# ======================================================================
# 10. score_route_from_job
# ======================================================================


class TestScoreRouteFromJob:
    @patch("eval.route_matrix.pillar_scores")
    @patch("eval.route_matrix.estimate_run_cost_usd")
    @patch("eval.route_matrix.estimate_tok_s")
    @patch("eval.route_matrix._job_duration_sec")
    @patch("eval.route_matrix.score_from_job")
    def test_returns_route_score(
        self,
        mock_score: MagicMock,
        mock_dur: MagicMock,
        mock_tok_s: MagicMock,
        mock_cost: MagicMock,
        mock_pillars: MagicMock,
    ) -> None:
        from eval.route_matrix import score_route_from_job

        mock_ms = MagicMock()
        mock_ms.tokens_out = 1000
        mock_ms.tokens_in = 2000
        mock_ms.mean = 0.85
        mock_ms.n_trials = 10
        mock_ms.n_errors = 0
        mock_ms.pass_at_1 = 0.8
        mock_score.return_value = mock_ms
        mock_dur.return_value = 30.0
        mock_tok_s.return_value = 33.33
        mock_cost.return_value = 0.15
        mock_pillars.return_value = {
            "accuracy": 1.0,
            "speed": 0.8,
            "cost": 0.9,
            "composite": 0.91,
        }
        entry = {"id": "test-model", "label": "Test", "route_kind": "omniroute_cloud"}
        result = score_route_from_job(Path("/tmp/job"), entry)
        assert result is not None
        assert result.model_id == "test-model"
        assert result.cost_usd == 0.15

    @patch("eval.route_matrix.score_from_job")
    def test_returns_none_when_no_score(self, mock_score: MagicMock) -> None:
        from eval.route_matrix import score_route_from_job

        mock_score.return_value = None
        entry = {"id": "test-model"}
        assert score_route_from_job(Path("/tmp/job"), entry) is None

    @patch("eval.route_matrix.pillar_scores")
    @patch("eval.route_matrix.estimate_run_cost_usd")
    @patch("eval.route_matrix.estimate_tok_s")
    @patch("eval.route_matrix._job_duration_sec")
    @patch("eval.route_matrix.score_from_job")
    def test_combo_entry(
        self,
        mock_score: MagicMock,
        mock_dur: MagicMock,
        mock_tok_s: MagicMock,
        mock_cost: MagicMock,
        mock_pillars: MagicMock,
    ) -> None:
        from eval.route_matrix import score_route_from_job

        mock_ms = MagicMock()
        mock_ms.tokens_out = 500
        mock_ms.tokens_in = 1000
        mock_ms.mean = 0.9
        mock_ms.n_trials = 5
        mock_ms.n_errors = 0
        mock_ms.pass_at_1 = 1.0
        mock_score.return_value = mock_ms
        mock_dur.return_value = 10.0
        mock_tok_s.return_value = 50.0
        mock_cost.return_value = 0.05
        mock_pillars.return_value = {
            "accuracy": 1.0,
            "speed": 1.0,
            "cost": 1.0,
            "composite": 1.0,
        }
        entry = {"id": "combo", "combo": True}
        result = score_route_from_job(Path("/tmp/job"), entry)
        assert result is not None
        assert result.combo is True


# ======================================================================
# 11. build_route_leaderboard
# ======================================================================


class TestBuildRouteLeaderboard:
    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_empty_when_no_models(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {"eval_protocol": {"target_mean": 0.8}}
        mock_state.return_value = {"models": {}}
        result = build_route_leaderboard()
        assert result == []

    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_filters_incomplete_models(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {
            "eval_protocol": {"target_mean": 0.8},
            "models": [{"id": "m1"}],
        }
        mock_state.return_value = {"models": {"m1": {"status": "pending", "job_dir": "/tmp"}}}
        result = build_route_leaderboard()
        assert result == []
        mock_score.assert_not_called()

    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_filters_by_route_kind(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {
            "eval_protocol": {"target_mean": 0.8},
            "models": [
                {"id": "m1", "route_kind": "omniroute_cloud"},
                {"id": "m2", "route_kind": "local_direct"},
            ],
        }
        mock_state.return_value = {
            "models": {
                "m1": {"status": "complete", "job_dir": "/tmp/m1"},
                "m2": {"status": "complete", "job_dir": "/tmp/m2"},
            }
        }
        mock_rs = MagicMock()
        mock_rs.pillars = {"composite": 0.9}
        mock_score.return_value = mock_rs
        result = build_route_leaderboard(route_kind="omniroute_cloud")
        assert len(result) == 1

    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_unknown_entry_skipped(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {
            "eval_protocol": {"target_mean": 0.8},
            "models": [{"id": "m1"}],
        }
        mock_state.return_value = {"models": {"unknown_id": {"status": "complete", "job_dir": "/tmp"}}}
        result = build_route_leaderboard()
        assert result == []

    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_relative_job_dir_resolved(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {
            "eval_protocol": {"target_mean": 0.8},
            "models": [{"id": "m1"}],
        }
        mock_state.return_value = {"models": {"m1": {"status": "complete", "job_dir": "relative/path"}}}
        mock_rs = MagicMock()
        mock_rs.pillars = {"composite": 0.8}
        mock_score.return_value = mock_rs
        build_route_leaderboard()
        call_args = mock_score.call_args
        assert call_args[0][0].is_absolute()

    @patch("eval.route_matrix.score_route_from_job")
    @patch("eval.route_matrix.load_routes_state")
    @patch("eval.route_matrix.load_routes_config")
    def test_sorted_by_composite(
        self, mock_cfg: MagicMock, mock_state: MagicMock, mock_score: MagicMock
    ) -> None:
        from eval.route_matrix import build_route_leaderboard

        mock_cfg.return_value = {
            "eval_protocol": {"target_mean": 0.8},
            "models": [{"id": "m1"}, {"id": "m2"}],
        }
        mock_state.return_value = {
            "models": {
                "m1": {"status": "complete", "job_dir": "/tmp/m1"},
                "m2": {"status": "complete", "job_dir": "/tmp/m2"},
            }
        }
        rs1 = MagicMock()
        rs1.pillars = {"composite": 0.5}
        rs2 = MagicMock()
        rs2.pillars = {"composite": 0.9}
        mock_score.side_effect = [rs1, rs2]
        result = build_route_leaderboard()
        assert result[0].pillars["composite"] == 0.9
        assert result[1].pillars["composite"] == 0.5


# ======================================================================
# 12. export_route_leaderboard
# ======================================================================


class TestExportRouteLeaderboard:
    @patch("eval.route_matrix.build_route_leaderboard")
    @patch("eval.route_matrix.load_routes_config")
    def test_export_empty(self, mock_cfg: MagicMock, mock_build: MagicMock, tmp_path: Path) -> None:
        from eval.route_matrix import export_route_leaderboard

        mock_cfg.return_value = {"eval_protocol": {"dataset": "test"}}
        mock_build.return_value = []
        with patch("eval.route_matrix.EVAL_RESULTS_DIR", tmp_path / "eval_results"):
            result = export_route_leaderboard()
            assert result.exists()
            payload = json.loads(result.read_text(encoding="utf-8"))
            assert payload["best_composite"] is None
            assert payload["models"] == []
            assert payload["combo_reference"] == []

    @patch("eval.route_matrix.build_route_leaderboard")
    @patch("eval.route_matrix.load_routes_config")
    def test_export_with_scores(self, mock_cfg: MagicMock, mock_build: MagicMock, tmp_path: Path) -> None:
        from eval.route_matrix import RouteScore, export_route_leaderboard

        mock_cfg.return_value = {"eval_protocol": {"dataset": "test"}}
        rs = RouteScore(
            model_id="m1",
            label="Model 1",
            route_kind="omniroute_cloud",
            routing_policy="rr",
            mean=0.85,
            n_trials=10,
            n_errors=0,
            pass_at_1=0.8,
            tokens_in=1000,
            tokens_out=500,
            tok_s=30.0,
            cost_usd=0.1,
            pillars={"accuracy": 1.0, "speed": 0.8, "cost": 0.9, "composite": 0.91},
            job_dir="/tmp/job",
        )
        mock_build.return_value = [rs]
        with patch("eval.route_matrix.EVAL_RESULTS_DIR", tmp_path / "eval_results"):
            result = export_route_leaderboard()
            payload = json.loads(result.read_text(encoding="utf-8"))
            assert len(payload["models"]) == 1
            assert payload["best_composite"]["model_id"] == "m1"
            assert "omniroute_cloud" in payload["by_route_kind"]

    @patch("eval.route_matrix.build_route_leaderboard")
    @patch("eval.route_matrix.load_routes_config")
    def test_export_combo_reference(self, mock_cfg: MagicMock, mock_build: MagicMock, tmp_path: Path) -> None:
        from eval.route_matrix import RouteScore, export_route_leaderboard

        mock_cfg.return_value = {"eval_protocol": {"dataset": "test"}}
        rs_combo = RouteScore(
            model_id="combo1",
            label="Combo 1",
            route_kind="omniroute_combo",
            routing_policy="combo",
            mean=0.9,
            n_trials=5,
            n_errors=0,
            pass_at_1=1.0,
            tokens_in=None,
            tokens_out=None,
            tok_s=None,
            cost_usd=0.0,
            pillars={"accuracy": 1.0, "speed": 0.5, "cost": 1.0, "composite": 0.85},
            job_dir="/tmp/combo",
            combo=True,
        )
        mock_build.return_value = [rs_combo]
        with patch("eval.route_matrix.EVAL_RESULTS_DIR", tmp_path / "eval_results"):
            result = export_route_leaderboard()
            payload = json.loads(result.read_text(encoding="utf-8"))
            assert len(payload["combo_reference"]) == 1
            assert len(payload["models"]) == 0

    @patch("eval.route_matrix.build_route_leaderboard")
    @patch("eval.route_matrix.load_routes_config")
    def test_export_multiple_route_kinds(
        self, mock_cfg: MagicMock, mock_build: MagicMock, tmp_path: Path
    ) -> None:
        from eval.route_matrix import RouteScore, export_route_leaderboard

        mock_cfg.return_value = {"eval_protocol": {"dataset": "test"}}
        rs_cloud = RouteScore(
            model_id="m1",
            label="Cloud",
            route_kind="omniroute_cloud",
            routing_policy="rr",
            mean=0.85,
            n_trials=10,
            n_errors=0,
            pass_at_1=0.8,
            tokens_in=1000,
            tokens_out=500,
            tok_s=30.0,
            cost_usd=0.1,
            pillars={"accuracy": 1.0, "speed": 0.8, "cost": 0.9, "composite": 0.91},
            job_dir="/tmp/m1",
        )
        rs_local = RouteScore(
            model_id="m2",
            label="Local",
            route_kind="local_direct",
            routing_policy="direct",
            mean=0.7,
            n_trials=8,
            n_errors=0,
            pass_at_1=0.5,
            tokens_in=2000,
            tokens_out=1000,
            tok_s=20.0,
            cost_usd=0.0,
            pillars={"accuracy": 0.8, "speed": 0.5, "cost": 1.0, "composite": 0.76},
            job_dir="/tmp/m2",
        )
        mock_build.return_value = [rs_cloud, rs_local]
        with patch("eval.route_matrix.EVAL_RESULTS_DIR", tmp_path / "eval_results"):
            result = export_route_leaderboard()
            payload = json.loads(result.read_text(encoding="utf-8"))
            assert "omniroute_cloud" in payload["by_route_kind"]
            assert "local_direct" in payload["by_route_kind"]

    @patch("eval.route_matrix.build_route_leaderboard")
    @patch("eval.route_matrix.load_routes_config")
    def test_export_cfg_path_different(
        self, mock_cfg: MagicMock, mock_build: MagicMock, tmp_path: Path
    ) -> None:
        from eval.route_matrix import export_route_leaderboard

        cfg_path = tmp_path / "custom" / "results.json"
        cfg_path.parent.mkdir()
        mock_cfg.return_value = {
            "eval_protocol": {"dataset": "test"},
            "results_file": "custom/results.json",
        }
        mock_build.return_value = []
        with patch("eval.route_matrix.EVAL_RESULTS_DIR", tmp_path / "eval_results"), \
             patch("eval.route_matrix.PHENO_ROOT", tmp_path):
            result = export_route_leaderboard()
            assert result.exists()


# ======================================================================
# 13. format_route_table
# ======================================================================


class TestFormatRouteTable:
    @patch("eval.route_matrix.build_route_leaderboard")
    def test_empty_table(self, mock_build: MagicMock) -> None:
        from eval.route_matrix import format_route_table

        mock_build.return_value = []
        table = format_route_table()
        assert "(no completed route runs yet)" in table
        assert "composite" in table

    @patch("eval.route_matrix.build_route_leaderboard")
    def test_table_with_scores(self, mock_build: MagicMock) -> None:
        from eval.route_matrix import RouteScore, format_route_table

        rs = RouteScore(
            model_id="m1",
            label="Test Model",
            route_kind="omniroute_cloud",
            routing_policy="rr",
            mean=0.85,
            n_trials=10,
            n_errors=0,
            pass_at_1=0.8,
            tokens_in=1000,
            tokens_out=500,
            tok_s=30.0,
            cost_usd=0.1,
            pillars={"accuracy": 1.0, "speed": 0.8, "cost": 0.9, "composite": 0.91},
            job_dir="/tmp/job",
        )
        mock_build.return_value = [rs]
        table = format_route_table()
        assert "Test Model" in table
        assert "omniroute_cloud" in table
        assert "0.850" in table
        assert "30.0" in table
        assert "(no completed route runs yet)" not in table

    @patch("eval.route_matrix.build_route_leaderboard")
    def test_table_none_tok_s(self, mock_build: MagicMock) -> None:
        from eval.route_matrix import RouteScore, format_route_table

        rs = RouteScore(
            model_id="m1",
            label="Test",
            route_kind="pheno_serve",
            routing_policy="rr",
            mean=0.8,
            n_trials=5,
            n_errors=0,
            pass_at_1=0.6,
            tokens_in=None,
            tokens_out=None,
            tok_s=None,
            cost_usd=0.0,
            pillars={"accuracy": 1.0, "speed": 0.0, "cost": 1.0, "composite": 0.7},
            job_dir="/tmp",
        )
        mock_build.return_value = [rs]
        table = format_route_table()
        assert "\u2014" in table  # em dash for None tok_s
