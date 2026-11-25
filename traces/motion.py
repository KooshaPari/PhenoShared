"""Motion classification: forward | stagnate | regress + ROI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MotionClass(StrEnum):
    """Coarse classification of agent progress on one step."""

    FORWARD = "forward"
    STAGNATE = "stagnate"
    REGRESS = "regress"
    UNKNOWN = "unknown"


@dataclass
class MotionScore:
    """One motion classification result plus its ROI estimate."""

    motion: MotionClass
    roi: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the MotionScore to a JSON-friendly dict."""
        return {"motion": self.motion.value, "roi": self.roi, "reasons": self.reasons}


def classify_motion(
    event: dict[str, Any], prev: dict[str, Any] | None = None
) -> MotionScore:
    """Heuristic motion from trace metadata."""
    meta = event.get("meta") or {}
    status = meta.get("status")
    err = (meta.get("error_summary") or "").lower()
    state = (meta.get("state") or "").lower()

    if status and int(status) >= 400:
        return MotionScore(MotionClass.REGRESS, 0.0, ["http_error"])
    if state in ("failed", "error"):
        return MotionScore(MotionClass.REGRESS, 0.0, ["job_failed"])
    if (
        err
        and prev
        and (prev.get("meta") or {}).get("error_summary") == meta.get("error_summary")
    ):
        return MotionScore(MotionClass.STAGNATE, 0.2, ["repeated_error"])

    tin = int(event.get("tokens_in") or 0)
    tout = int(event.get("tokens_out") or 0)
    if prev:
        ptin = int(prev.get("tokens_in") or 0)
        if tin > 0 and ptin > 0 and abs(tin - ptin) / max(ptin, 1) < 0.05 and tout < 50:
            return MotionScore(
                MotionClass.STAGNATE, 0.3, ["duplicate_context_low_output"]
            )

    if tout > 100 or state in ("done", "completed", "success"):
        burn = tin + tout
        roi = min(1.0, tout / max(burn, 1) * 10) if burn else 0.5
        return MotionScore(MotionClass.FORWARD, round(roi, 4), ["productive_output"])

    if tout > 0:
        return MotionScore(MotionClass.FORWARD, 0.4, ["some_output"])

    return MotionScore(MotionClass.UNKNOWN, 0.0, ["insufficient_signal"])


def motion_roi(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate motion rates over ordered events."""
    if not events:
        return {"forward": 0, "stagnate": 0, "regress": 0, "unknown": 0, "avg_roi": 0.0}
    counts = {m.value: 0 for m in MotionClass}
    rois: list[float] = []
    prev = None
    for ev in events:
        sc = classify_motion(ev, prev)
        counts[sc.motion.value] += 1
        rois.append(sc.roi)
        prev = ev
    n = len(events)
    return {
        "forward": counts["forward"] / n,
        "stagnate": counts["stagnate"] / n,
        "regress": counts["regress"] / n,
        "unknown": counts["unknown"] / n,
        "avg_roi": round(sum(rois) / n, 4),
        "total_events": n,
    }
