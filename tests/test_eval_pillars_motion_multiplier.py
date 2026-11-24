"""DAG-68 + follow-up: tests/test_eval_pillars_motion_multiplier.py

Motion multiplier semantics per AGENTS.md §1.3:
    forward: 1.0 / stagnate: 0.5 / regress: 0.0
    forward >= 0.70                  -> 1.0
    0.0 < forward < 0.70, regress<=0.10 -> 0.5 (stagnate)
    regress > 0.10                    -> 0.0

Composite = sum(pillar_score * weight) * motion_multiplier.

The canonical ``motion_multiplier`` lives in ``eval.pillars`` (relocated
from this test file's inline stub after DAG-68). Tests import from
production so the threshold semantics from AGENTS.md §1.3 are locked in
by both the test file and the ``score_from_wastage`` composite formula.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from eval.pillars import motion_multiplier

REPO_ROOT = Path(__file__).resolve().parents[1]
PILLARS = REPO_ROOT / "config" / "eval_pillars.yaml"


def _load_pillars() -> dict[str, Any]:
    return yaml.safe_load(PILLARS.read_text())


# ---------------------------------------------------------------------------
# Threshold semantics — the three core cases.
# ---------------------------------------------------------------------------


def test_motion_multiplier_forward_returns_one() -> None:
    # At the boundary and well above: every "forward" run pays full credit.
    assert motion_multiplier(forward=0.70, regress=0.00) == 1.0
    assert motion_multiplier(forward=0.85, regress=0.05) == 1.0
    assert motion_multiplier(forward=1.00, regress=0.10) == 1.0


def test_motion_multiplier_stagnate_returns_half() -> None:
    # Below the forward threshold and within the regress ceiling -> stagnate.
    assert motion_multiplier(forward=0.50, regress=0.00) == 0.5
    assert motion_multiplier(forward=0.10, regress=0.10) == 0.5
    assert motion_multiplier(forward=0.01, regress=0.05) == 0.5


def test_motion_multiplier_regress_returns_zero() -> None:
    # Any regress beyond the ceiling nukes the composite regardless of forward.
    assert motion_multiplier(forward=0.00, regress=0.11) == 0.0
    assert motion_multiplier(forward=0.50, regress=0.25) == 0.0
    assert motion_multiplier(forward=1.00, regress=0.50) == 0.0


# ---------------------------------------------------------------------------
# Parametrized edge cases on the two thresholds (0.69 vs 0.70, 0.10 vs 0.11).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forward,regress,expected",
    [
        # forward boundary: >= 0.70 promotes, < 0.70 stays stagnate (regress ok).
        (0.69, 0.00, 0.5),
        (0.70, 0.00, 1.0),
        (0.70, 0.10, 1.0),
        (0.69, 0.10, 0.5),
        # regress boundary: > 0.10 forces 0.0; <= 0.10 lets the forward rule apply.
        (0.50, 0.10, 0.5),
        (0.50, 0.11, 0.0),
        (0.80, 0.10, 1.0),
        (0.80, 0.11, 0.0),
    ],
)
def test_motion_multiplier_threshold_edges(
    forward: float, regress: float, expected: float
) -> None:
    assert motion_multiplier(forward=forward, regress=regress) == expected


# ---------------------------------------------------------------------------
# Composite formula: Σ(pillar_score × weight) × motion_multiplier
# ---------------------------------------------------------------------------


def test_composite_score_applies_motion_multiplier() -> None:
    pillars_cfg = _load_pillars()
    pillar_scores: dict[str, float] = {
        "accuracy": 0.90,
        "cost": 0.80,
        "token_burn": 0.70,
        "speed": 0.85,
        "safety": 0.95,
        "motion": 0.75,
        "quality": 0.60,
    }
    weights = {k: v["weight"] for k, v in pillars_cfg["pillars"].items()}

    base_sum = sum(pillar_scores[name] * weights[name] for name in pillar_scores)

    # Forward motion: full credit.
    forward = sum(
        (pillar_scores[name] * weights[name])
        * motion_multiplier(forward=0.80, regress=0.05)
        for name in pillar_scores
    )
    assert forward == pytest.approx(base_sum, abs=1e-9)

    # Stagnate motion: half credit.
    stagnate = sum(
        (pillar_scores[name] * weights[name])
        * motion_multiplier(forward=0.40, regress=0.05)
        for name in pillar_scores
    )
    assert stagnate == pytest.approx(0.5 * base_sum, abs=1e-9)

    # Regress motion: zeroed composite.
    regress = sum(
        (pillar_scores[name] * weights[name])
        * motion_multiplier(forward=0.80, regress=0.20)
        for name in pillar_scores
    )
    assert regress == 0.0


# ---------------------------------------------------------------------------
# Pillar weights sanity (mirrors test_eval_pillars.py::test_pillar_weights_sum_to_one)
# ---------------------------------------------------------------------------


def test_pillar_weights_sum_to_one() -> None:
    data = _load_pillars()
    pillars = data["pillars"]
    total = sum(p["weight"] for p in pillars.values())
    assert abs(total - 1.0) < 1e-9, f"pillar weights sum to {total}, not 1.0"
