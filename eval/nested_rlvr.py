"""Nested RLVR-AF reward aggregation — L0-L3 plus Soft-SVeRL plus MR-RLVR.

This module aggregates verifier rewards into four levels (micro/role/agent/
swarm) and adds soft-checklist partial credit and process-bonus signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from eval.pillars import score_from_wastage  # noqa: F401  (re-export surface)
from pheno.paths import CONFIG_DIR
from traces.motion import classify_motion
from verifier.harness import VerifierHarness
from verifier.rewards import compute_rewards


@dataclass
class NestedScore:
    """Hierarchical score across L0-L3 plus soft/process bonuses.

    Attributes:
        L0_micro: Micro-level efficiency score.
        L1_role: Role-conditioned score.
        L2_agent: Agent/task reward (Harbor or patch proxy).
        L3_swarm: Swarm/ROI score.
        soft_partial: Soft-SVeRL checklist partial credit.
        process_bonus: MR-RLVR process bonus.
        composite: Weighted composite including soft/process bonuses.
        passed: Whether composite exceeds the pass threshold and verifier passed.
        details: Diagnostic metadata (motion, verifier_total, role).

    """

    L0_micro: float = 0.0
    L1_role: float = 0.0
    L2_agent: float = 0.0
    L3_swarm: float = 0.0
    soft_partial: float = 0.0
    process_bonus: float = 0.0
    composite: float = 0.0
    passed: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the nested score to a JSON-compatible dict.

        Returns:
            Dict with all level scores and diagnostics.

        """
        return {
            "L0_micro": self.L0_micro,
            "L1_role": self.L1_role,
            "L2_agent": self.L2_agent,
            "L3_swarm": self.L3_swarm,
            "soft_partial": self.soft_partial,
            "process_bonus": self.process_bonus,
            "composite": self.composite,
            "passed": self.passed,
            "details": self.details,
        }


def _load_config(path: Path | None = None) -> dict[str, Any]:
    """Load nested RLVR config from YAML.

    Args:
        path: Optional override path. Defaults to
            ``CONFIG_DIR/../training/nested_rlvr.yaml`` or the repo
            ``training/nested_rlvr.yaml`` fallback.

    Returns:
        Parsed config dict.

    """
    p = path or (CONFIG_DIR / ".." / "training" / "nested_rlvr.yaml")
    p = Path(p).resolve()
    if not p.exists():
        p = Path(__file__).resolve().parents[1] / "training" / "nested_rlvr.yaml"
    data: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data


def soft_checklist_score(trace: dict[str, Any], cfg: dict[str, Any]) -> float:
    """Compute Soft-SVeRL partial credit from checklist items.

    Args:
        trace: Trace dict as produced by the harness.
        cfg: Loaded nested RLVR config.

    Returns:
        Soft checklist score in [0, 1], rounded to 4 decimals.

    """
    soft: dict[str, Any] = cfg.get("soft_verifier", {})
    if not soft.get("enabled"):
        return 0.0
    harness = VerifierHarness()
    vr = harness.verify_trace(trace)
    rb = compute_rewards(vr)
    total = 0.0
    for item in soft.get("checklist_items", []):
        iid: str = str(item["id"])
        w = float(item.get("weight", 0.1))
        mapping: dict[str, float] = {
            "json_schema": rb.json_valid,
            "tool_call_valid": rb.tool_valid,
            "patch_applies": rb.patch_applies,
            "tests_pass": rb.tests_pass,
            "context_under_budget": rb.context_under_budget,
            "output_under_cap": rb.output_under_cap,
            "motion_forward": 1.0
            if classify_motion(trace).motion.value == "forward"
            else 0.0,
        }
        total += w * mapping.get(iid, 0.0)
    if trace.get("meta", {}).get("self_verified"):
        total *= 1.0 - float(soft.get("self_verify_penalty", 0.3))
    return round(min(1.0, total), 4)


def process_reward_bonus(
    trace: dict[str, Any], prev: dict[str, Any] | None, cfg: dict[str, Any]
) -> float:
    """Compute MR-RLVR-style intermediate process bonus.

    Args:
        trace: Current trace dict.
        prev: Previous trace dict if available.
        cfg: Loaded nested RLVR config.

    Returns:
        Process bonus in [0, 1], rounded to 4 decimals.

    """
    proc: dict[str, Any] = cfg.get("process_rewards", {})
    if not proc.get("enabled"):
        return 0.0
    bonus = 0.0
    meta: dict[str, Any] = trace.get("meta") or {}
    for sig in proc.get("signals", []):
        w = float(sig.get("weight", 0.1))
        kind = sig.get("detect")
        if kind == "repeated_error" and prev:
            if (prev.get("meta") or {}).get("error_summary") != meta.get(
                "error_summary"
            ):
                bonus += w
        elif kind == "compiler_reduction":
            if int(meta.get("tokens_compressed") or 0) > 0:
                bonus += w
        elif kind == "pytest_delta":
            if meta.get("state") in ("done", "completed", "success"):
                bonus += w
        elif kind == "output_per_input_ratio":
            tin = int(trace.get("tokens_in") or 0)
            tout = int(trace.get("tokens_out") or 0)
            if tin > 0 and tout / tin > 0.01:
                bonus += w
        elif kind == "duplicate_context_cluster":
            if not meta.get("duplicate_context"):
                bonus += w
    return round(min(1.0, bonus), 4)


def score_trace(
    trace: dict[str, Any],
    *,
    prev: dict[str, Any] | None = None,
    wastage: dict[str, Any] | None = None,
    harbor_reward: float | None = None,
    config_path: Path | None = None,
) -> NestedScore:
    """Score a single trace across L0-L3 plus soft and process bonuses.

    Args:
        trace: Trace dict produced by the harness.
        prev: Previous trace for motion delta if available.
        wastage: Optional aggregated wastage dict for L3 scaling.
        harbor_reward: Optional Harbor reward to use for L2_agent directly.
        config_path: Optional override path for nested RLVR config.

    Returns:
        Populated ``NestedScore`` with composite and passed flag.

    """
    cfg: dict[str, Any] = _load_config(config_path)
    levels: dict[str, Any] = cfg.get("levels", {})
    weights: dict[str, float] = {
        k: float(v.get("weight", 0.25)) for k, v in levels.items()
    }

    harness = VerifierHarness()
    vr = harness.verify_trace(trace)
    rb = compute_rewards(vr, pass_threshold=float(cfg.get("pass_threshold", 0.72)))

    motion = classify_motion(trace, prev)
    role: str = str(
        trace.get("meta", {}).get("pheno_role") or trace.get("harness", "patch")
    )

    ns = NestedScore(
        L0_micro=round(
            (rb.context_under_budget + rb.correct_escalation + rb.tokens_saved) / 3, 4
        ),
        L1_role=round(
            rb.total
            if role in ("patch", "plan", "debug", "retrieve")
            else rb.total * 0.8,
            4,
        ),
        L2_agent=round(
            harbor_reward
            if harbor_reward is not None
            else (rb.tests_pass * 0.5 + rb.patch_applies * 0.5),
            4,
        ),
        L3_swarm=round(
            motion.roi * (1.0 - float((wastage or {}).get("overlap_waste_rate", 0))), 4
        ),
        soft_partial=soft_checklist_score(trace, cfg),
        process_bonus=process_reward_bonus(trace, prev, cfg),
    )

    ns.composite = round(
        ns.L0_micro * weights.get("L0_micro", 0.15)
        + ns.L1_role * weights.get("L1_role", 0.25)
        + ns.L2_agent * weights.get("L2_agent", 0.35)
        + ns.L3_swarm * weights.get("L3_swarm", 0.25)
        + 0.1 * ns.soft_partial
        + 0.1 * ns.process_bonus,
        4,
    )
    if wastage:
        overlap = float(wastage.get("overlap_waste_rate") or 0)
        ns.composite = round(ns.composite * (1.0 - overlap), 4)

    ns.passed = ns.composite >= float(cfg.get("pass_threshold", 0.72)) and rb.passed
    ns.details = {
        "motion": motion.motion.value,
        "verifier_total": rb.total,
        "role": role,
    }
    return ns


def score_batch(
    traces: list[dict[str, Any]], wastage: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Score a batch of traces and aggregate statistics.

    Args:
        traces: List of trace dicts.
        wastage: Optional aggregated wastage dict for L3 scaling.

    Returns:
        Dict with ``count``, ``mean_composite``, ``pass_rate``, and
        up to 5 sample scores.

    """
    scores: list[dict[str, Any]] = []
    prev: dict[str, Any] | None = None
    for t in traces:
        scores.append(score_trace(t, prev=prev, wastage=wastage).to_dict())
        prev = t
    if not scores:
        return {"count": 0, "mean_composite": 0.0, "pass_rate": 0.0}
    passed = sum(1 for s in scores if s["passed"])
    return {
        "count": len(scores),
        "mean_composite": round(
            sum(float(s["composite"]) for s in scores) / len(scores), 4
        ),
        "pass_rate": round(passed / len(scores), 4),
        "samples": scores[:5],
    }
