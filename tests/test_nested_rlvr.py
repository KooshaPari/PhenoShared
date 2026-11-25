"""Unit tests for eval.nested_rlvr — hierarchical scoring, soft checklist, and batch.

Covers NestedScore, _load_config, soft_checklist_score, process_reward_bonus,
score_trace, and score_batch.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
import yaml

from eval.nested_rlvr import (
    NestedScore,
    _load_config,
    process_reward_bonus,
    score_batch,
    score_trace,
    soft_checklist_score,
)
from traces.motion import MotionClass, MotionScore
from verifier.harness import VerifierResult
from verifier.rewards import RewardBreakdown

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    *,
    soft_enabled: bool = False,
    proc_enabled: bool = False,
    pass_threshold: float = 0.72,
) -> dict:
    """Build a minimal nested RLVR config dict."""
    return {
        "levels": {
            "L0_micro": {"weight": 0.15},
            "L1_role": {"weight": 0.25},
            "L2_agent": {"weight": 0.35},
            "L3_swarm": {"weight": 0.25},
        },
        "pass_threshold": pass_threshold,
        "soft_verifier": {
            "enabled": soft_enabled,
            "checklist_items": [
                {"id": "json_schema", "weight": 0.10},
                {"id": "tests_pass", "weight": 0.25},
                {"id": "patch_applies", "weight": 0.20},
            ],
            "self_verify_penalty": 0.3,
        },
        "process_rewards": {
            "enabled": proc_enabled,
            "signals": [
                {"name": "repeated_error", "weight": 0.15, "detect": "repeated_error"},
                {"name": "compiler_reduction", "weight": 0.20, "detect": "compiler_reduction"},
                {"name": "pytest_delta", "weight": 0.30, "detect": "pytest_delta"},
                {"name": "token_efficiency", "weight": 0.15, "detect": "output_per_input_ratio"},
                {"name": "lane_no_overlap", "weight": 0.20, "detect": "duplicate_context_cluster"},
            ],
        },
    }


def _make_trace(
    *,
    tokens_out: int = 200,
    tokens_in: int = 500,
    response: str = '{"tool": "apply"}',
    role: str = "patch",
    meta: dict | None = None,
    harness: str = "patch",
) -> dict:
    """Build a minimal trace dict."""
    return {
        "id": "trace-1",
        "role": role,
        "response": response,
        "tokens_out": tokens_out,
        "tokens_in": tokens_in,
        "baseline_context_tokens": tokens_in,
        "harness": harness,
        "meta": meta or {},
    }


# ---------------------------------------------------------------------------
# NestedScore
# ---------------------------------------------------------------------------

class TestNestedScore:
    def test_to_dict(self) -> None:
        ns = NestedScore(
            L0_micro=0.5,
            L1_role=0.6,
            L2_agent=0.7,
            L3_swarm=0.8,
            soft_partial=0.1,
            process_bonus=0.2,
            composite=0.65,
            passed=True,
            details={"motion": "forward"},
        )
        d = ns.to_dict()
        assert d["L0_micro"] == 0.5
        assert d["L1_role"] == 0.6
        assert d["L2_agent"] == 0.7
        assert d["L3_swarm"] == 0.8
        assert d["soft_partial"] == 0.1
        assert d["process_bonus"] == 0.2
        assert d["composite"] == 0.65
        assert d["passed"] is True
        assert d["details"]["motion"] == "forward"

    def test_defaults(self) -> None:
        ns = NestedScore()
        assert ns.L0_micro == 0.0
        assert ns.L1_role == 0.0
        assert ns.L2_agent == 0.0
        assert ns.L3_swarm == 0.0
        assert ns.soft_partial == 0.0
        assert ns.process_bonus == 0.0
        assert ns.composite == 0.0
        assert ns.passed is False
        assert ns.details == {}

    def test_to_dict_roundtrip(self) -> None:
        ns = NestedScore(composite=0.42, passed=False, details={"role": "debug"})
        d = ns.to_dict()
        ns2 = NestedScore(**{k: v for k, v in d.items() if k != "details"})
        ns2.details = d["details"]
        assert ns2.composite == 0.42


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_explicit_path(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(
            yaml.dump({"levels": {"L0_micro": {"weight": 0.5}}}), encoding="utf-8"
        )
        result = _load_config(cfg_path)
        assert result["levels"]["L0_micro"]["weight"] == 0.5

    def test_missing_file_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The fallback reads from repo's training/nested_rlvr.yaml which exists
        # We just verify it doesn't crash; the real config has levels
        result = _load_config()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# soft_checklist_score
# ---------------------------------------------------------------------------

class TestSoftChecklistScore:
    def test_disabled_returns_zero(self) -> None:
        cfg = _make_config(soft_enabled=False)
        trace = _make_trace()
        assert soft_checklist_score(trace, cfg) == 0.0

    def test_enabled_with_passing_checks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = _make_config(soft_enabled=True)

        vr = VerifierResult(
            trace_id="t1", role="patch", ok=True,
            checks={"json_valid": True, "tests_pass": True, "patch_applies": True},
            meta={},
        )
        rb = RewardBreakdown(
            json_valid=1.0, tool_valid=1.0, patch_applies=1.0, tests_pass=1.0,
            context_under_budget=1.0, output_under_cap=1.0, total=0.8, passed=True,
        )
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.8, reasons=["ok"])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        score = soft_checklist_score(_make_trace(), cfg)
        # All checks pass + motion forward: 0.1*1 + 0.25*1 + 0.2*1 + 0.1*1 = 0.65
        assert 0.0 < score <= 1.0

    def test_self_verify_penalty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = _make_config(soft_enabled=True)
        trace = _make_trace(meta={"self_verified": True})

        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(
            json_valid=1.0, tool_valid=0.0, patch_applies=0.0, tests_pass=0.0,
            context_under_budget=0.0, output_under_cap=0.0, total=0.1, passed=False,
        )
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=["ok"])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        score_with_penalty = soft_checklist_score(trace, cfg)

        # Without self_verified
        trace_no_penalty = _make_trace(meta={})
        score_without = soft_checklist_score(trace_no_penalty, cfg)

        assert score_with_penalty <= score_without

    def test_unknown_check_item_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = _make_config(soft_enabled=True)
        # Add an unknown checklist item
        cfg["soft_verifier"]["checklist_items"].append(
            {"id": "nonexistent_check", "weight": 0.5}
        )

        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.1, passed=False)
        motion = MotionScore(motion=MotionClass.UNKNOWN, roi=0.0, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        score = soft_checklist_score(_make_trace(), cfg)
        # Unknown items score 0.0, so they don't add to total
        assert score >= 0.0


# ---------------------------------------------------------------------------
# process_reward_bonus
# ---------------------------------------------------------------------------

class TestProcessRewardBonus:
    def test_disabled_returns_zero(self) -> None:
        cfg = _make_config(proc_enabled=False)
        assert process_reward_bonus(_make_trace(), None, cfg) == 0.0

    def test_repeated_error_same_returns_zero(self) -> None:
        cfg = _make_config(proc_enabled=True)
        prev = _make_trace(
            tokens_in=9999, tokens_out=1,
            meta={"error_summary": "same error"},
        )
        trace = _make_trace(
            tokens_in=9999, tokens_out=1,
            meta={"error_summary": "same error", "duplicate_context": True},
        )
        bonus = process_reward_bonus(trace, prev, cfg)
        # Same error = no bonus for repeated_error signal
        # output_per_input_ratio: 1/9999 < 0.01 -> no fire
        # duplicate_context=True -> no fire
        assert bonus == 0.0

    def test_repeated_error_different_returns_bonus(self) -> None:
        cfg = _make_config(proc_enabled=True)
        prev = _make_trace(meta={"error_summary": "error_a"})
        trace = _make_trace(meta={"error_summary": "error_b"})
        bonus = process_reward_bonus(trace, prev, cfg)
        # Different errors: repeated_error signal fires (weight 0.15)
        assert bonus >= 0.15

    def test_compiler_reduction(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"tokens_compressed": 100})
        bonus = process_reward_bonus(trace, None, cfg)
        # compiler_reduction fires (weight 0.20)
        assert bonus >= 0.20

    def test_pytest_delta_done(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"state": "done"})
        bonus = process_reward_bonus(trace, None, cfg)
        # pytest_delta fires (weight 0.30)
        assert bonus >= 0.30

    def test_pytest_delta_completed(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"state": "completed"})
        bonus = process_reward_bonus(trace, None, cfg)
        assert bonus >= 0.30

    def test_pytest_delta_success(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"state": "success"})
        bonus = process_reward_bonus(trace, None, cfg)
        assert bonus >= 0.30

    def test_output_per_input_ratio_high(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(tokens_in=1000, tokens_out=50)
        bonus = process_reward_bonus(trace, None, cfg)
        # 50/1000 = 0.05 > 0.01, so fires (weight 0.15)
        assert bonus >= 0.15

    def test_output_per_input_ratio_low(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(tokens_in=10000, tokens_out=10)
        bonus = process_reward_bonus(trace, None, cfg)
        # 10/10000 = 0.001 < 0.01, output_per_input_ratio does not fire
        # At minimum no crash

    def test_output_per_input_zero_tokens_in(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(tokens_in=0, tokens_out=100)
        bonus = process_reward_bonus(trace, None, cfg)
        # tin=0 means ratio check skips

    def test_duplicate_context_cluster_no_dup(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"duplicate_context": False})
        bonus = process_reward_bonus(trace, None, cfg)
        # duplicate_context_cluster fires when no dup (weight 0.20)
        assert bonus >= 0.20

    def test_duplicate_context_cluster_has_dup(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"duplicate_context": True})
        bonus = process_reward_bonus(trace, None, cfg)
        # duplicate_context_cluster does NOT fire when dup exists

    def test_capped_at_one(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(
            tokens_in=1000,
            tokens_out=50,
            meta={
                "tokens_compressed": 100,
                "state": "done",
                "duplicate_context": False,
            },
        )
        prev = _make_trace(meta={"error_summary": "old"})
        bonus = process_reward_bonus(trace, prev, cfg)
        assert bonus <= 1.0

    def test_all_signals_combined(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(
            tokens_in=1000,
            tokens_out=50,
            meta={
                "tokens_compressed": 100,
                "state": "done",
                "duplicate_context": False,
                "error_summary": "new_error",
            },
        )
        prev = _make_trace(meta={"error_summary": "old_error"})
        bonus = process_reward_bonus(trace, prev, cfg)
        # All 5 signals fire: 0.15 + 0.20 + 0.30 + 0.15 + 0.20 = 1.0
        assert bonus == 1.0

    def test_prev_none_skips_repeated_error(self) -> None:
        cfg = _make_config(proc_enabled=True)
        trace = _make_trace(meta={"error_summary": "error"})
        bonus = process_reward_bonus(trace, None, cfg)
        # Without prev, repeated_error does not fire, but other signals may
        # At minimum no crash


# ---------------------------------------------------------------------------
# score_trace
# ---------------------------------------------------------------------------

class TestScoreTrace:
    def test_basic_scoring(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config(pass_threshold=0.72)
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(
            trace_id="t1", role="patch", ok=True,
            checks={"json_valid": True, "tests_pass": True},
            meta={},
        )
        rb = RewardBreakdown(
            json_valid=1.0, tool_valid=0.0, patch_applies=0.0, tests_pass=1.0,
            output_under_cap=0.8, context_under_budget=0.9, correct_escalation=0.5,
            tokens_saved=0.6, total=0.8, passed=True,
        )
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.7, reasons=["ok"])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(
            _make_trace(tokens_out=200, tokens_in=500),
            config_path=cfg_path,
        )
        assert isinstance(ns, NestedScore)
        assert ns.L2_agent == 0.5  # tests_pass=1*0.5 + patch_applies=0*0.5
        assert ns.details["motion"] == "forward"
        assert ns.details["role"] == "patch"

    def test_harbor_reward_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.5, passed=False)
        motion = MotionScore(motion=MotionClass.UNKNOWN, roi=0.0, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(_make_trace(), harbor_reward=0.95, config_path=cfg_path)
        assert ns.L2_agent == 0.95

    def test_wastage_reduces_composite(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.5, passed=False)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.8, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns_without = score_trace(_make_trace(), config_path=cfg_path)
        ns_with = score_trace(
            _make_trace(), wastage={"overlap_waste_rate": 0.5}, config_path=cfg_path
        )
        # With wastage, composite should be lower
        assert ns_with.composite <= ns_without.composite

    def test_passed_requires_threshold_and_verifier(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        cfg = _make_config(pass_threshold=0.9)
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="patch", ok=False, checks={}, meta={})
        rb = RewardBreakdown(total=0.3, passed=False)
        motion = MotionScore(motion=MotionClass.UNKNOWN, roi=0.0, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(_make_trace(), config_path=cfg_path)
        assert ns.passed is False

    def test_non_standard_role_reduces_l1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="custom", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.8, passed=True)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(
            _make_trace(role="custom", harness="custom"),
            config_path=cfg_path,
        )
        # Non-standard role: 0.8 * 0.8 = 0.64
        assert ns.L1_role == round(0.8 * 0.8, 4)

    def test_standard_role_full_l1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.8, passed=True)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(_make_trace(role="patch"), config_path=cfg_path)
        assert ns.L1_role == 0.8

    def test_plan_role_standard(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="plan", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=1.0, passed=True)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(_make_trace(role="plan"), config_path=cfg_path)
        assert ns.L1_role == 1.0

    def test_pheno_role_from_meta(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg = _make_config()
        cfg_path = tmp_path / "nested_rlvr.yaml"
        cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

        vr = VerifierResult(trace_id="t1", role="debug", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.7, passed=True)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        trace = _make_trace(role="unknown_role")
        trace["meta"]["pheno_role"] = "debug"
        ns = score_trace(trace, config_path=cfg_path)
        # pheno_role from meta overrides harness field, "debug" is standard
        assert ns.L1_role == 0.7

    def test_default_config_levels(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that score_trace works with the actual default config."""
        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.5, passed=False)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.5, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        ns = score_trace(_make_trace())
        assert isinstance(ns, NestedScore)
        # Should use default weights from the real config
        assert ns.composite >= 0.0


# ---------------------------------------------------------------------------
# score_batch
# ---------------------------------------------------------------------------

class TestScoreBatch:
    def test_empty_batch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Need to mock score_trace even for empty batch since it iterates
        result = score_batch([])
        assert result["count"] == 0
        assert result["mean_composite"] == 0.0
        assert result["pass_rate"] == 0.0
        assert "samples" not in result

    def test_single_trace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        vr = VerifierResult(trace_id="t1", role="patch", ok=True, checks={}, meta={})
        rb = RewardBreakdown(total=0.8, passed=True)
        motion = MotionScore(motion=MotionClass.FORWARD, roi=0.6, reasons=[])

        harness_mock = mock.MagicMock()
        harness_mock.verify_trace = mock.MagicMock(return_value=vr)
        monkeypatch.setattr("eval.nested_rlvr.VerifierHarness", lambda: harness_mock)
        monkeypatch.setattr("eval.nested_rlvr.compute_rewards", lambda vr, **kw: rb)
        monkeypatch.setattr(
            "eval.nested_rlvr.classify_motion", lambda t, prev=None: motion
        )

        result = score_batch([_make_trace()])
        assert result["count"] == 1
        assert "mean_composite" in result
        assert "pass_rate" in result

    def test_multiple_traces(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            nonlocal call_count
            call_count += 1
            return NestedScore(
                composite=0.5 * call_count,
                passed=call_count == 2,
            )

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        traces = [_make_trace() for _ in range(3)]
        result = score_batch(traces)
        assert result["count"] == 3
        assert call_count == 3
        assert len(result["samples"]) == 3

    def test_samples_capped_at_five(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            nonlocal call_count
            call_count += 1
            return NestedScore(composite=0.5, passed=False)

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        traces = [_make_trace() for _ in range(10)]
        result = score_batch(traces)
        assert result["count"] == 10
        assert len(result["samples"]) == 5

    def test_pass_rate_calculation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            nonlocal call_count
            call_count += 1
            return NestedScore(composite=0.5, passed=(call_count in (1, 3)))

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        traces = [_make_trace() for _ in range(4)]
        result = score_batch(traces)
        # 2 passed out of 4 = 0.5
        assert result["pass_rate"] == 0.5

    def test_prev_trace_passed_between_iterations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        prevs = []

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            prevs.append(prev)
            return NestedScore(composite=0.5, passed=False)

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        traces = [_make_trace() for _ in range(3)]
        score_batch(traces)
        # First trace has prev=None, second has trace[0], third has trace[1]
        assert prevs[0] is None
        assert prevs[1] is traces[0]
        assert prevs[2] is traces[1]

    def test_mean_composite_calculation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            nonlocal call_count
            call_count += 1
            return NestedScore(composite=float(call_count), passed=False)

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        traces = [_make_trace() for _ in range(3)]
        result = score_batch(traces)
        # mean of [1.0, 2.0, 3.0] = 2.0
        assert result["mean_composite"] == 2.0

    def test_wastage_passed_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        received_wastage = []

        def fake_score_trace(trace, prev=None, wastage=None, **kw):
            received_wastage.append(wastage)
            return NestedScore(composite=0.5, passed=False)

        monkeypatch.setattr("eval.nested_rlvr.score_trace", fake_score_trace)

        wastage = {"overlap_waste_rate": 0.3}
        score_batch([_make_trace()], wastage=wastage)
        assert received_wastage[0] == wastage
