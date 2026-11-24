"""Verifier audit — aggregate gate and reward audit logging.

Provides helpers to audit verifier runs, compute gate pass rates, and emit
structured audit records for the budget and pillar scoring pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pheno.paths import TRAINING_DIR
from verifier.harness import VerifierResult
from verifier.rewards import RewardBreakdown


@dataclass
class AuditRecord:
    """Single audit entry for a trace verification.

    Attributes:
        trace_id: Identifier of the audited trace.
        role: Normalized role string.
        ok: Whether the trace passed the gate.
        reward_total: Weighted reward total.
        tier: Risky-action tier if present.
        created_at: ISO-8601 timestamp of audit.

    """

    trace_id: str
    role: str
    ok: bool
    reward_total: float
    tier: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize the audit record to a dict.

        Returns:
            JSON-compatible dict.

        """
        return {
            "trace_id": self.trace_id,
            "role": self.role,
            "ok": self.ok,
            "reward_total": self.reward_total,
            "tier": self.tier,
            "created_at": self.created_at,
        }


def build_audit_record(result: VerifierResult, reward: RewardBreakdown) -> AuditRecord:
    """Build an audit record from a verifier result and reward breakdown.

    Args:
        result: ``VerifierResult`` from ``VerifierHarness``.
        reward: ``RewardBreakdown`` from ``compute_rewards``.

    Returns:
        ``AuditRecord`` with tier extracted from result meta.

    """
    return AuditRecord(
        trace_id=result.trace_id,
        role=result.role,
        ok=result.ok and reward.passed,
        reward_total=reward.total,
        tier=str(result.meta.get("risky_action_tier", "none")),
    )


def gate_pass_rate(results: list[VerifierResult]) -> float:
    """Compute the risky-action gate pass rate.

    Args:
        results: List of ``VerifierResult`` records.

    Returns:
        Fraction in [0, 1] where gate check equals True, 1.0 if empty.

    """
    if not results:
        return 1.0
    sum(1 for r in results if r.checks.get("risky_action_gate") is not False)
    # Explicit False counts as fail; missing check counts as pass (gate disabled).
    explicit_fails = sum(
        1 for r in results if r.checks.get("risky_action_gate") is False
    )
    total = len(results)
    return round((total - explicit_fails) / max(total, 1), 4)


def reward_summary(rewards: list[RewardBreakdown]) -> dict[str, Any]:
    """Summarize a list of reward breakdowns.

    Args:
        rewards: List of ``RewardBreakdown`` records.

    Returns:
        Dict with ``count``, ``mean_total``, ``pass_rate``, and ``by_dimension``.

    """
    if not rewards:
        return {"count": 0, "mean_total": 0.0, "pass_rate": 0.0, "by_dimension": {}}
    mean_total = round(sum(r.total for r in rewards) / len(rewards), 4)
    pass_rate = round(sum(1 for r in rewards if r.passed) / len(rewards), 4)
    dims = [
        "json_valid",
        "tool_valid",
        "patch_applies",
        "tests_pass",
        "output_under_cap",
        "context_under_budget",
        "correct_escalation",
        "tokens_saved",
    ]
    by_dim: dict[str, float] = {}
    for dim in dims:
        by_dim[dim] = round(sum(getattr(r, dim) for r in rewards) / len(rewards), 4)
    return {
        "count": len(rewards),
        "mean_total": mean_total,
        "pass_rate": pass_rate,
        "by_dimension": by_dim,
    }


def write_audit_log(records: list[AuditRecord], path: Path | None = None) -> Path:
    """Persist audit records as JSONL.

    Args:
        records: List of ``AuditRecord`` entries.
        path: Optional override path. Defaults to
            ``TRAINING_DIR/audit_log.jsonl``.

    Returns:
        Path to the written file.

    """
    out = path or TRAINING_DIR / "audit_log.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict()) + "\n")
    return out


def read_audit_log(path: Path | None = None) -> list[AuditRecord]:
    """Read audit records from JSONL.

    Args:
        path: Optional override path. Defaults to ``TRAINING_DIR/audit_log.jsonl``.

    Returns:
        List of ``AuditRecord`` entries, empty if file missing.

    """
    src = path or TRAINING_DIR / "audit_log.jsonl"
    if not src.exists():
        return []
    records: list[AuditRecord] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data: dict[str, Any] = json.loads(line)
        records.append(
            AuditRecord(
                trace_id=str(data.get("trace_id", "")),
                role=str(data.get("role", "")),
                ok=bool(data.get("ok", False)),
                reward_total=float(data.get("reward_total", 0.0)),
                tier=str(data.get("tier", "none")),
                created_at=str(data.get("created_at", "")),
            )
        )
    return records


def audit_batch(
    results: list[VerifierResult], rewards: list[RewardBreakdown]
) -> dict[str, Any]:
    """Audit a batch of results and rewards.

    Args:
        results: List of ``VerifierResult`` entries.
        rewards: List of corresponding ``RewardBreakdown`` entries.

    Returns:
        Dict with gate pass rate, reward summary, and counts.

    """
    return {
        "count": len(results),
        "gate_pass_rate": gate_pass_rate(results),
        "reward_summary": reward_summary(rewards),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def audit_trace(trace: dict[str, Any]) -> AuditRecord:
    """Audit a single trace dict end-to-end.

    Args:
        trace: Trace dict as accepted by ``VerifierHarness.verify_trace``.

    Returns:
        ``AuditRecord`` for the trace.

    """
    from verifier.harness import VerifierHarness
    from verifier.rewards import compute_rewards

    harness = VerifierHarness()
    result = harness.verify_trace(trace)
    reward = compute_rewards(result)
    return build_audit_record(result, reward)


def load_recent_audit(limit: int = 100) -> list[AuditRecord]:
    """Load the most recent audit records.

    Args:
        limit: Maximum number of records to return (most recent first).

    Returns:
        List of ``AuditRecord`` entries up to ``limit``.

    """
    recs = read_audit_log()
    return recs[-limit:][::-1]


def verify_audit_consistency(records: list[AuditRecord]) -> dict[str, Any]:
    """Verify audit consistency invariants.

    Args:
        records: List of ``AuditRecord`` entries.

    Returns:
        Dict with ``valid`` flag and ``errors`` list.

    """
    errors: list[str] = []
    for rec in records:
        if not rec.trace_id:
            errors.append("missing trace_id")
        if rec.reward_total < 0 or rec.reward_total > 1.5:
            errors.append(
                f"{rec.trace_id}: reward_total out of range {rec.reward_total}"
            )
        if rec.tier not in {"low", "medium", "high", "critical", "none", "disabled"}:
            errors.append(f"{rec.trace_id}: unknown tier {rec.tier}")
    return {"valid": not errors, "errors": errors}
