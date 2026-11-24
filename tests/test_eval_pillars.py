"""DAG-14: tests/test_eval_pillars.py

The eval pillars (accuracy, cost, token_burn, speed, safety, motion,
quality) sum to 1.00 and the motion multiplier (forward=1.0,
stagnate=0.5, regress=0.0) is applied. Both invariants must hold for
the canonical config and any override config that claims to be
canonical.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from eval.pillars import (
    PillarScore,
    PillarScores,
    _clamp01,
    motion_multiplier,
    score_from_harbor,
    score_from_wastage,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PILLARS = REPO_ROOT / "config" / "eval_pillars.yaml"


def _load() -> dict:
    return yaml.safe_load(PILLARS.read_text())


def test_pillar_weights_sum_to_one() -> None:
    data = _load()
    pillars = data["pillars"]
    total = sum(p["weight"] for p in pillars.values())
    assert abs(total - 1.0) < 1e-9, f"pillar weights sum to {total}, not 1.0"


def test_all_seven_canonical_pillars_present() -> None:
    data = _load()
    expected = {
        "accuracy",
        "cost",
        "token_burn",
        "speed",
        "safety",
        "motion",
        "quality",
    }
    actual = set(data["pillars"].keys())
    assert expected.issubset(actual), f"missing pillars: {expected - actual}"


def test_motion_multiplier_invariant() -> None:
    data = _load()
    mm = data["composite"]["motion_multiplier"]
    assert mm["forward"] == 1.0
    assert mm["stagnate"] == 0.5
    assert mm["regress"] == 0.0


def test_composite_formula_uses_motion_multiplier() -> None:
    data = _load()
    formula = data["composite"]["formula"]
    assert "motion_multiplier" in formula


def test_each_pillar_has_at_least_one_metric_and_target() -> None:
    data = _load()
    for name, pillar in data["pillars"].items():
        assert "metrics" in pillar and pillar["metrics"], f"{name} missing metrics"
        assert "targets" in pillar and pillar["targets"], f"{name} missing targets"


def test_safety_pillar_includes_risky_action_gate() -> None:
    data = _load()
    safety = data["pillars"]["safety"]
    assert "risky_action_gate_pass_rate" in safety["metrics"]
    assert safety["weight"] >= 0.05  # not zeroed out


# ---------------------------------------------------------------------------
# PillarScores dataclass tests
# ---------------------------------------------------------------------------


def test_pillar_scores_defaults() -> None:
    ps = PillarScores()
    assert ps.token_burn == 0.0
    assert ps.accuracy == 0.0
    assert ps.speed == 0.0
    assert ps.cost == 0.0
    assert ps.motion == 0.0
    assert ps.quality == 0.0
    assert ps.safety == 0.0
    assert ps.composite == 0.0
    assert ps.weights == {}
    assert ps.details == {}


def test_pillar_scores_to_dict() -> None:
    ps = PillarScores(
        token_burn=0.8,
        accuracy=0.9,
        speed=0.7,
        cost=0.6,
        motion=0.5,
        quality=0.4,
        safety=0.3,
        composite=0.55,
    )
    d = ps.to_dict()
    assert d["token_burn"] == 0.8
    assert d["accuracy"] == 0.9
    assert d["speed"] == 0.7
    assert d["cost"] == 0.6
    assert d["motion"] == 0.5
    assert d["quality"] == 0.4
    assert d["safety"] == 0.3
    assert d["composite"] == 0.55


def test_pillar_scores_to_dict_with_weights() -> None:
    w = {"token_burn": 0.15, "accuracy": 0.25}
    ps = PillarScores(weights=w)
    d = ps.to_dict()
    assert d["weights"] == w


def test_pillar_scores_to_dict_with_details() -> None:
    det = {"avg_input_tokens": 42.0, "motion_multiplier": 1.0}
    ps = PillarScores(details=det)
    d = ps.to_dict()
    assert d["details"] == det


def test_pillar_score_alias() -> None:
    assert PillarScore is PillarScores


# ---------------------------------------------------------------------------
# _clamp01 tests
# ---------------------------------------------------------------------------


def test_clamp01_below() -> None:
    assert _clamp01(-0.5) == 0.0


def test_clamp01_above() -> None:
    assert _clamp01(1.5) == 1.0


def test_clamp01_within() -> None:
    assert _clamp01(0.5) == 0.5


def test_clamp01_boundaries() -> None:
    assert _clamp01(0.0) == 0.0
    assert _clamp01(1.0) == 1.0


# ---------------------------------------------------------------------------
# motion_multiplier tests
# ---------------------------------------------------------------------------


def test_motion_multiplier_forward() -> None:
    assert motion_multiplier(forward=0.8, regress=0.0) == 1.0


def test_motion_multiplier_stagnate() -> None:
    assert motion_multiplier(forward=0.5, regress=0.0) == 0.5


def test_motion_multiplier_regress() -> None:
    assert motion_multiplier(forward=0.5, regress=0.2) == 0.0


def test_motion_multiplier_regress_dominates() -> None:
    # Even high forward is irrelevant when regress > 0.10
    assert motion_multiplier(forward=0.9, regress=0.15) == 0.0


def test_motion_multiplier_boundary_forward() -> None:
    # Exactly at forward threshold (0.70) should yield 1.0
    assert motion_multiplier(forward=0.7, regress=0.0) == 1.0


def test_motion_multiplier_boundary_regress() -> None:
    # Exactly at regress threshold (0.10) — not > 0.10, so not regress
    assert motion_multiplier(forward=0.5, regress=0.1) == 0.5


# ---------------------------------------------------------------------------
# score_from_harbor tests
# ---------------------------------------------------------------------------


def test_score_from_harbor_mean_reward() -> None:
    result = score_from_harbor({"mean_reward": 0.85})
    assert result == pytest.approx(0.85)


def test_score_from_harbor_mean_key() -> None:
    result = score_from_harbor({"mean": 0.6})
    assert result == pytest.approx(0.6)


def test_score_from_harbor_empty() -> None:
    result = score_from_harbor({})
    assert result == 0.0


def test_score_from_harbor_clamped() -> None:
    result = score_from_harbor({"mean_reward": 1.5})
    assert result == 1.0


def test_score_from_harbor_below_zero_clamped() -> None:
    result = score_from_harbor({"mean_reward": -0.3})
    assert result == 0.0


# ---------------------------------------------------------------------------
# score_from_wastage tests
# ---------------------------------------------------------------------------


SAMPLE_WASTAGE: dict = {
    "total_tokens_in": 10000,
    "total_tokens_out": 5000,
    "total_events": 10,
    "motion": {"forward": 0.8, "stagnate": 0.1, "regress": 0.05},
    "giant_calls_32k_plus": 1,
    "overlap_waste_rate": 0.1,
    "risky_action_gate_pass_rate": 0.95,
}

SAMPLE_BUDGET: dict = {
    "estimated_monthly_usd": 300,
    "ideal_monthly_usd": 200,
    "max_monthly_usd": 400,
}


def test_score_from_wastage_basic() -> None:
    """score_from_wastage without budget produces valid PillarScores."""
    ps = score_from_wastage(SAMPLE_WASTAGE)
    assert isinstance(ps, PillarScores)
    assert 0.0 <= ps.token_burn <= 1.0
    assert 0.0 <= ps.motion <= 1.0
    assert 0.0 <= ps.quality <= 1.0
    assert 0.0 <= ps.safety <= 1.0
    assert 0.0 <= ps.composite <= 1.0


def test_score_from_wastage_with_budget_ideal() -> None:
    """Monthly <= ideal → cost pillar = 1.0."""
    budget_ideal = {
        "estimated_monthly_usd": 150,
        "ideal_monthly_usd": 200,
        "max_monthly_usd": 400,
    }
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=budget_ideal)
    assert ps.cost == 1.0


def test_score_from_wastage_with_budget_mid() -> None:
    """Monthly between ideal and max → cost in (0, 1)."""
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=SAMPLE_BUDGET)
    # monthly=300, ideal=200, max=400
    # cost = 1.0 - (300-200)/(400-200) = 0.5
    assert ps.cost == pytest.approx(0.5)


def test_score_from_wastage_with_budget_over() -> None:
    """Monthly > max → cost pillar = 0.0."""
    budget_over = {
        "estimated_monthly_usd": 500,
        "ideal_monthly_usd": 200,
        "max_monthly_usd": 400,
    }
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=budget_over)
    assert ps.cost == 0.0


def test_score_from_wastage_no_budget() -> None:
    """budget=None → cost stays at default 0.0."""
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=None)
    assert ps.cost == 0.0


def test_score_from_wastage_safety_with_gate() -> None:
    """risky_action_gate_pass_rate present → safety = clamped rate."""
    ps = score_from_wastage(SAMPLE_WASTAGE)
    assert ps.safety == pytest.approx(0.95)


def test_score_from_wastage_safety_no_gate() -> None:
    """No gate rate → safety defaults to 1.0."""
    wastage_no_gate = {k: v for k, v in SAMPLE_WASTAGE.items() if k != "risky_action_gate_pass_rate"}
    ps = score_from_wastage(wastage_no_gate)
    assert ps.safety == 1.0


def test_score_from_wastage_composite() -> None:
    """Composite = weighted sum * motion_multiplier, rounded to 4 places."""
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=SAMPLE_BUDGET)
    # Verify composite is present and numeric
    assert isinstance(ps.composite, float)
    assert 0.0 <= ps.composite <= 1.0
    # Re-derive: weights from YAML, manually compute
    w = ps.weights
    raw = (
        ps.token_burn * w.get("token_burn", 0)
        + ps.accuracy * w.get("accuracy", 0)
        + ps.speed * w.get("speed", 0)
        + ps.cost * w.get("cost", 0)
        + ps.motion * w.get("motion", 0)
        + ps.quality * w.get("quality", 0)
        + ps.safety * w.get("safety", 0)
    )
    multiplier = motion_multiplier(
        SAMPLE_WASTAGE["motion"]["forward"],
        SAMPLE_WASTAGE["motion"]["regress"],
    )
    expected = round(raw * multiplier, 4)
    assert ps.composite == pytest.approx(expected)


def test_score_from_wastage_motion_calculation() -> None:
    """Verify motion pillar = forward*1.0 + stagnate*0.5 - regress*1.0, clamped."""
    ps = score_from_wastage(SAMPLE_WASTAGE)
    # forward=0.8, stagnate=0.1, regress=0.05
    expected_motion = max(0.0, min(1.0, 0.8 * 1.0 + 0.1 * 0.5 - 0.05 * 1.0))
    # = max(0, min(1, 0.8 + 0.05 - 0.05)) = 0.8
    assert ps.motion == pytest.approx(expected_motion)
    assert ps.motion == pytest.approx(0.8)


def test_score_from_wastage_token_burn_low_tokens() -> None:
    """Low token usage → token_burn close to 1.0."""
    wastage = {
        "total_tokens_in": 100,
        "total_tokens_out": 50,
        "total_events": 10,
    }
    ps = score_from_wastage(wastage)
    # avg_in = 100/10 = 10, target=5120 → token_burn = 1.0 - 0/5120 = 1.0
    assert ps.token_burn == pytest.approx(1.0)


def test_score_from_wastage_token_burn_high_tokens() -> None:
    """Excess tokens → token_burn drops below 1.0."""
    wastage = {
        "total_tokens_in": 100000,
        "total_tokens_out": 0,
        "total_events": 10,
    }
    ps = score_from_wastage(wastage)
    # avg_in = 10000, target=5120 → excess = (10000-5120)/5120 = 0.953...
    # token_burn = 1.0 - 0.953... ≈ 0.047...
    assert 0.0 < ps.token_burn < 0.5


def test_score_from_wastage_motion_regress_penalizes() -> None:
    """High regress → motion pillar drops."""
    wastage = {
        "total_tokens_in": 5000,
        "total_events": 10,
        "motion": {"forward": 0.2, "stagnate": 0.1, "regress": 0.5},
    }
    ps = score_from_wastage(wastage)
    # 0.2*1.0 + 0.1*0.5 - 0.5*1.0 = 0.2 + 0.05 - 0.5 = -0.25 → clamped to 0.0
    assert ps.motion == 0.0


def test_score_from_wastage_motion_multiplier_applied() -> None:
    """When regress > 0.10, multiplier=0.0 → composite=0.0."""
    wastage = {
        "total_tokens_in": 5000,
        "total_events": 10,
        "motion": {"forward": 0.5, "stagnate": 0.1, "regress": 0.3},
        "risky_action_gate_pass_rate": 1.0,
    }
    ps = score_from_wastage(wastage)
    # regress=0.3 > 0.10 → multiplier=0.0 → composite=0.0
    assert ps.composite == 0.0


def test_score_from_wastage_details_populated() -> None:
    """Details dict contains expected diagnostic keys."""
    ps = score_from_wastage(SAMPLE_WASTAGE, budget=SAMPLE_BUDGET)
    assert "avg_input_tokens" in ps.details
    assert "motion" in ps.details
    assert "motion_multiplier" in ps.details
    assert "giant_context_pct" in ps.details
    assert "monthly_usd" in ps.details
    assert ps.details["monthly_usd"] == 300
    assert ps.details["motion_multiplier"] == 1.0
