"""Eval pillar scoring — token, accuracy, speed, cost, motion, quality.

Provides the ``PillarScores`` dataclass and scoring helpers that map
wastage/budget/harbor inputs to the seven weighted pillars defined in
``config/eval_pillars.yaml``. The composite is weighted sum times the motion
multiplier per AGENTS.md §1.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR


@dataclass
class PillarScores:
    """Container for the seven pillar scores and derived composite.

    Attributes:
        token_burn: 1 - normalized excess input tokens.
        accuracy: Task success rate pillar (often from Harbor).
        speed: Latency/throughput pillar.
        cost: Cost efficiency pillar (monthly USD vs targets).
        motion: Motion distribution pillar.
        quality: Output quality / giant-context proxy.
        safety: Risky-action gate pass rate pillar.
        composite: Weighted composite times motion multiplier.
        weights: Per-pillar weights loaded from config.
        details: Diagnostic details emitted alongside scores.

    """

    token_burn: float = 0.0
    accuracy: float = 0.0
    speed: float = 0.0
    cost: float = 0.0
    motion: float = 0.0
    quality: float = 0.0
    safety: float = 0.0
    composite: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize pillar scores to a JSON-compatible dict.

        Returns:
            Dict with all pillar values, weights, and details.

        """
        return {
            "token_burn": self.token_burn,
            "accuracy": self.accuracy,
            "speed": self.speed,
            "cost": self.cost,
            "motion": self.motion,
            "quality": self.quality,
            "safety": self.safety,
            "composite": self.composite,
            "weights": self.weights,
            "details": self.details,
        }


# Backwards-compatible alias for task 52: ``PillarScore`` singular.
PillarScore = PillarScores


def _load_yaml(name: str) -> dict[str, Any]:
    """Load a YAML file from ``CONFIG_DIR``.

    Args:
        name: Filename within ``CONFIG_DIR``.

    Returns:
        Parsed YAML mapping, empty dict if file is empty.

    """
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8")) or {}


def _clamp01(x: float) -> float:
    """Clamp a float to [0, 1].

    Args:
        x: Value to clamp.

    Returns:
        ``x`` bounded to the unit interval.

    """
    return max(0.0, min(1.0, x))


# Motion-multiplier thresholds from AGENTS.md §1.3.
_FORWARD_MIN = 0.70
_REGRESS_MAX = 0.10


def motion_multiplier(forward: float, regress: float) -> float:
    """Return the canonical motion multiplier per AGENTS.md §1.3.

    Args:
        forward: Forward motion ratio in [0, 1].
        regress: Regress ratio in [0, 1].

    Returns:
        1.0 — forward ≥ 0.70 (forward motion)
        0.5 — 0.0 < forward < 0.70 and regress ≤ 0.10 (stagnate)
        0.0 — regress > 0.10 (regress dominates)

    Ordering is intentional: ``regress > 0.10`` is the most severe
    condition and dominates; otherwise ``forward ≥ 0.70`` promotes to
    1.0; the residual case is stagnate at 0.5.

    """
    if regress > _REGRESS_MAX:
        return 0.0
    if forward >= _FORWARD_MIN:
        return 1.0
    return 0.5


def score_from_wastage(
    wastage: dict[str, Any], budget: dict[str, Any] | None = None
) -> PillarScores:
    """Score pillars from wastage report and optional budget snapshot.

    Args:
        wastage: Aggregated wastage dict from ``scripts/analyze_wastage.py``.
        budget: Optional budget snapshot dict (e.g., ``BudgetSnapshot.to_dict()``).

    Returns:
        Populated ``PillarScores`` with composite already multiplied by the
        motion multiplier.

    """
    pillars_cfg: dict[str, Any] = _load_yaml("eval_pillars.yaml")
    weights: dict[str, float] = {
        k: float(v["weight"]) for k, v in pillars_cfg["pillars"].items()
    }
    ps = PillarScores(weights=weights)

    tin: float = float(wastage.get("total_tokens_in") or 0)
    wastage.get("total_tokens_out") or 0
    target_in: float = float(
        pillars_cfg["pillars"]["token_burn"]["targets"]["avg_input_per_step_max"]
    )
    avg_in = tin / max(float(wastage.get("total_events") or 1), 1.0)
    ps.token_burn = _clamp01(1.0 - max(0.0, avg_in - target_in) / max(target_in, 1.0))
    ps.details["avg_input_tokens"] = round(avg_in, 1)

    motion: dict[str, Any] = wastage.get("motion") or {}
    ps.motion = _clamp01(
        float(motion.get("forward", 0)) * 1.0
        + float(motion.get("stagnate", 0)) * 0.5
        - float(motion.get("regress", 0)) * 1.0
    )
    ps.details["motion"] = motion

    forward_m = float(motion.get("forward", 0.0))
    regress_m = float(motion.get("regress", 0.0))
    multiplier = motion_multiplier(forward_m, regress_m)
    ps.details["motion_multiplier"] = multiplier

    giant_pct = float(wastage.get("giant_calls_32k_plus") or 0) / max(
        float(wastage.get("total_events") or 1), 1.0
    )
    pillars_cfg["pillars"]["quality"]["targets"]["compiler_reduction_min"]
    ps.quality = _clamp01(1.0 - giant_pct)  # proxy until compiler metrics wired
    ps.details["giant_context_pct"] = round(100 * giant_pct, 2)

    overlap = float(wastage.get("overlap_waste_rate") or 0)
    ps.quality = _clamp01((ps.quality + (1.0 - overlap)) / 2)

    gate_rate = wastage.get("risky_action_gate_pass_rate")
    if gate_rate is not None:
        ps.safety = _clamp01(float(gate_rate))
    else:
        ps.safety = 1.0  # assume pass until gate metrics wired
    ps.details["risky_action_gate_pass_rate"] = gate_rate

    if budget:
        monthly: float = float(
            budget.get("estimated_monthly_usd")
            or budget.get("current_baseline_usd")
            or 570
        )
        ideal: float = float(budget.get("ideal_monthly_usd") or 200)
        max_usd: float = float(budget.get("max_monthly_usd") or 400)
        if monthly <= ideal:
            ps.cost = 1.0
        elif monthly <= max_usd:
            ps.cost = _clamp01(1.0 - (monthly - ideal) / max(max_usd - ideal, 1))
        else:
            ps.cost = 0.0
        ps.details["monthly_usd"] = monthly

    w = weights
    raw_composite = (
        ps.token_burn * w.get("token_burn", 0)
        + ps.accuracy * w.get("accuracy", 0)
        + ps.speed * w.get("speed", 0)
        + ps.cost * w.get("cost", 0)
        + ps.motion * w.get("motion", 0)
        + ps.quality * w.get("quality", 0)
        + ps.safety * w.get("safety", 0)
    )
    ps.composite = round(raw_composite * multiplier, 4)
    return ps


def score_from_harbor(harbor_result: dict[str, Any]) -> float:
    """Map a Harbor result to the accuracy pillar.

    Args:
        harbor_result: Dict containing ``mean_reward`` or ``mean``.

    Returns:
        Clamped accuracy score in [0, 1].

    """
    mean = harbor_result.get("mean_reward") or harbor_result.get("mean") or 0
    return _clamp01(float(mean))
