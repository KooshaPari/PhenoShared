"""Tests for eval/budget.py — coverage-focused.

Covers BudgetSnapshot, _provider_key, estimate_from_omniroute,
and all alert level branches.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ======================================================================
# 1. BudgetSnapshot dataclass
# ======================================================================


class TestBudgetSnapshot:
    def test_to_dict(self) -> None:
        from eval.budget import BudgetSnapshot

        snap = BudgetSnapshot(
            generated_at="2026-01-01T00:00:00Z",
            estimated_monthly_usd=150.75,
            tokens_in_month=1_000_000,
            tokens_out_month=500_000,
            by_provider_usd={"openai": 50.5, "claude": 100.25},
            targets={"ideal_monthly_usd": 200},
            alert_level="green",
            codex_cut_progress=0.5,
        )
        d = snap.to_dict()
        assert d["generated_at"] == "2026-01-01T00:00:00Z"
        assert d["estimated_monthly_usd"] == 150.75
        assert d["tokens_in_month"] == 1_000_000
        assert d["tokens_out_month"] == 500_000
        assert d["by_provider_usd"]["openai"] == 50.5
        assert d["by_provider_usd"]["claude"] == 100.25
        assert d["targets"]["ideal_monthly_usd"] == 200
        assert d["alert_level"] == "green"
        assert d["codex_cut_progress"] == 0.5

    def test_to_dict_rounds_values(self) -> None:
        from eval.budget import BudgetSnapshot

        snap = BudgetSnapshot(
            generated_at="2026-01-01T00:00:00Z",
            estimated_monthly_usd=123.456,
            tokens_in_month=1000,
            tokens_out_month=500,
            by_provider_usd={"openai": 12.3456789},
            targets={},
            alert_level="yellow",
            codex_cut_progress=0.33333333,
        )
        d = snap.to_dict()
        assert d["estimated_monthly_usd"] == 123.46
        assert d["by_provider_usd"]["openai"] == 12.35
        assert d["codex_cut_progress"] == 0.3333

    def test_to_dict_empty_providers(self) -> None:
        from eval.budget import BudgetSnapshot

        snap = BudgetSnapshot(
            generated_at="2026-01-01T00:00:00Z",
            estimated_monthly_usd=0.0,
            tokens_in_month=0,
            tokens_out_month=0,
            by_provider_usd={},
            targets={},
            alert_level="green",
            codex_cut_progress=0.0,
        )
        d = snap.to_dict()
        assert d["by_provider_usd"] == {}


# ======================================================================
# 2. _provider_key
# ======================================================================


class TestProviderKey:
    def test_openai(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("openai") == "openai"

    def test_codex(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("codex-gpt-4o") == "openai"

    def test_gpt(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("gpt-4o-mini") == "openai"

    def test_anthropic(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("anthropic") == "claude"

    def test_claude(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("claude-3-opus") == "claude"

    def test_opus(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("opus") == "claude"

    def test_minimax(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("minimax-m3") == "minimax"

    def test_kimi(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("kimi") == "kimi"

    def test_local(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("local") == "local"

    def test_empty_string(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("") == "local"

    def test_none(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key(None) == "local"

    def test_unknown_passthrough(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("deepseek") == "deepseek"

    def test_case_insensitive(self) -> None:
        from eval.budget import _provider_key

        assert _provider_key("OpenAI") == "openai"
        assert _provider_key("CLAUDE") == "claude"
        assert _provider_key("KIMI") == "kimi"


# ======================================================================
# 3. estimate_from_omniroute
# ======================================================================


class TestEstimateFromOmniroute:
    def _make_budget_config(self) -> dict[str, Any]:
        return {
            "targets": {
                "ideal_monthly_usd": 200,
                "max_monthly_usd": 400,
            },
            "baseline": {"monthly_usd": 570},
            "codex_openai": {
                "current_monthly_usd": 200,
                "cut_scenarios": {
                    "half_bill": {"target_usd": 100},
                    "full_cut": {"target_usd": 0},
                },
            },
        }

    def _make_db(self, tmp_path: Path, rows: list[tuple] | None = None) -> Path:
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE call_logs (provider TEXT, tokens_in INTEGER, tokens_out INTEGER)"
        )
        if rows:
            conn.executemany("INSERT INTO call_logs VALUES (?, ?, ?)", rows)
        conn.commit()
        conn.close()
        return db_path

    def test_green_alert_low_spend(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()
        db_path = self._make_db(tmp_path, [
            ("openai", 1000, 500),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path, days=30)
            # Estimated < 50, so baseline kicks in (570 > max 400 -> blackout)
            assert snap.estimated_monthly_usd == 570.0
            assert snap.alert_level == "blackout"

    def test_yellow_alert(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        # Generate enough tokens to be between ideal (200) and max*0.75 (300)
        # With openai at 2.50/M, need ~100M tokens to get $250
        db_path = self._make_db(tmp_path, [
            ("openai", 50_000_000, 50_000_000),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            assert snap.alert_level == "yellow"

    def test_red_alert(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        # Need estimated between max*0.75 (300) and max (400)
        # With claude at 15.0/M, need ~23M tokens to get ~$350
        db_path = self._make_db(tmp_path, [
            ("claude", 12_000_000, 11_000_000),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            assert snap.alert_level == "red"

    def test_blackout_alert(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        # Need estimated > max (400)
        # With claude at 15.0/M, need >27M tokens
        db_path = self._make_db(tmp_path, [
            ("claude", 20_000_000, 20_000_000),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            assert snap.alert_level == "blackout"

    def test_no_db_falls_back_to_baseline(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        nonexistent_db = tmp_path / "nonexistent.sqlite"
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=nonexistent_db)
            # No DB -> 0 tokens -> estimated < 50 -> baseline
            assert snap.estimated_monthly_usd == 570.0
            assert snap.tokens_in_month == 0
            assert snap.tokens_out_month == 0

    def test_writes_output_files(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        nonexistent_db = tmp_path / "nonexistent.sqlite"
        eval_dir = tmp_path / "eval"
        with patch("eval.budget.EVAL_DIR", eval_dir), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            estimate_from_omniroute(db=nonexistent_db)
            # Check JSONL snapshot
            jsonl = training_dir / "budget_snapshots.jsonl"
            assert jsonl.exists()
            lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) >= 1
            snap_data = json.loads(lines[-1])
            assert "generated_at" in snap_data
            # Check latest JSON
            latest = eval_dir / "results" / "budget_latest.json"
            assert latest.exists()
            latest_data = json.loads(latest.read_text(encoding="utf-8"))
            assert "estimated_monthly_usd" in latest_data

    def test_codex_cut_progress(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        # High openai spend -> low codex cut progress
        db_path = self._make_db(tmp_path, [
            ("openai", 40_000_000, 40_000_000),  # 80M * 2.5/M = $200
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            # codex_current=200, baseline=200, progress = 1 - min(200/200, 1) = 0
            assert snap.codex_cut_progress == 0.0

    def test_codex_cut_progress_high(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        # Low openai spend -> high codex cut progress
        db_path = self._make_db(tmp_path, [
            ("openai", 2_000_000, 0),  # 2M * 2.5/M = $5
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            # codex_current=5, baseline=200, progress = 1 - min(5/200, 1) = 0.975
            assert snap.codex_cut_progress == pytest.approx(0.975)

    def test_multiple_providers(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        db_path = self._make_db(tmp_path, [
            ("openai", 10_000_000, 5_000_000),
            ("claude", 5_000_000, 3_000_000),
            ("minimax", 20_000_000, 10_000_000),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            assert "openai" in snap.by_provider_usd
            assert "claude" in snap.by_provider_usd
            assert "minimax" in snap.by_provider_usd
            # openai: (15M * 2.5/M) = 37.5
            assert snap.by_provider_usd["openai"] == pytest.approx(37.5)
            # claude: (8M * 15/M) = 120
            assert snap.by_provider_usd["claude"] == pytest.approx(120.0)
            # minimax: (30M * 1/M) = 30
            assert snap.by_provider_usd["minimax"] == pytest.approx(30.0)

    def test_unknown_provider_uses_default_rate(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        db_path = self._make_db(tmp_path, [
            ("deepseek", 10_000_000, 5_000_000),
        ])
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            snap = estimate_from_omniroute(db=db_path)
            # deepseek -> unknown -> rate=1.0, 15M * 1.0/M = 15
            assert snap.by_provider_usd["deepseek"] == pytest.approx(15.0)

    def test_jsonl_appends(
        self, tmp_path: Path
    ) -> None:
        from eval.budget import estimate_from_omniroute

        config = self._make_budget_config()
        import yaml
        config_file = tmp_path / "budget_targets.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")
        training_dir = tmp_path / "training"
        training_dir.mkdir()

        nonexistent_db = tmp_path / "nonexistent.sqlite"
        with patch("eval.budget.EVAL_DIR", tmp_path / "eval"), \
             patch("eval.budget.TRAINING_DIR", training_dir), \
             patch("eval.budget.CONFIG_DIR", tmp_path):
            # Run twice to verify JSONL appends
            estimate_from_omniroute(db=nonexistent_db)
            estimate_from_omniroute(db=nonexistent_db)
            jsonl = training_dir / "budget_snapshots.jsonl"
            lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 2


# ======================================================================
# 4. PROVIDER_COST_PER_M constant
# ======================================================================


class TestProviderCostPerM:
    def test_all_expected_keys(self) -> None:
        from eval.budget import PROVIDER_COST_PER_M

        expected = {"openai", "codex", "anthropic", "claude", "minimax", "kimi", "local", "unknown"}
        assert set(PROVIDER_COST_PER_M.keys()) == expected

    def test_local_is_free(self) -> None:
        from eval.budget import PROVIDER_COST_PER_M

        assert PROVIDER_COST_PER_M["local"] == 0.0

    def test_values_are_positive(self) -> None:
        from eval.budget import PROVIDER_COST_PER_M

        for provider, cost in PROVIDER_COST_PER_M.items():
            assert cost >= 0.0, f"{provider} has negative cost: {cost}"
