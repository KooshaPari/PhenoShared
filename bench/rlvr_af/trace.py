"""L1 — Trace: structured recording of transitions + artifacts.

Each suite run produces a `Trail`: an ordered list of `Transition` objects,
each carrying a structured artifact (prompt → completion → judge verdict →
debug metadata). The trail is the memory that L2 (Verifier), L3 (Critic),
and L4 (Optimizer) operate on.

From the RLVR-AF spec:
  "Trail: ordered, immutable-after-commit list of (state, action, reward)
   triples recorded during a suite run. Every transition carries a
   structured artifact (prompt, completion, judge verdict, debug metadata)."
"""

from __future__ import annotations

import dataclasses
import json
import time
from typing import Any

# ---------------------------------------------------------------------------
# Transition types
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Artifact:
    """A fixed snapshot produced by one transition."""

    elapsed_s: float
    prompt: str
    completion: str
    expected: Any = None
    tokens_in: int = 0
    tokens_out: int = 0
    raw: str = ""
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class JudgeVerdict:
    """Normalised judge result — the reward signal."""

    passed: bool
    reward: float  # ∈ [0, 1]
    strict: bool | None = None
    loose: bool | None = None
    reason: str = ""
    meta: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Transition:
    """A single (task_id, artifact, verdict) triple."""

    task_id: str
    artifact: Artifact
    verdict: JudgeVerdict | None = None
    debug: dict[str, Any] = dataclasses.field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trail — immutable replay log
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Trail:
    """Ordered, immutable-after-commit list of Transitions.

    `committed_at` is set when `commit()` is called, freezing the trail.
    """

    suite: str
    model: str
    run_id: str
    seed: int
    started_at: float = dataclasses.field(default_factory=time.time)
    committed_at: float | None = None
    transitions: list[Transition] = dataclasses.field(default_factory=list)
    meta: dict[str, Any] = dataclasses.field(default_factory=dict)

    def add(self, t: Transition) -> None:
        """Append a transition. Raises if already committed."""
        if self.committed_at is not None:
            raise RuntimeError("trail already committed — cannot add transitions")
        self.transitions.append(t)

    def commit(self) -> None:
        """Freeze the trail. Subsequent `add()` calls raise."""
        self.committed_at = time.time()

    @property
    def rewards(self) -> list[float]:
        """List of rewards for transitions that have a verdict."""
        return [t.verdict.reward for t in self.transitions if t.verdict is not None]

    @property
    def mean_reward(self) -> float:
        """Mean of all non-None verdict rewards (0.0 when empty)."""
        r = self.rewards
        return sum(r) / len(r) if r else 0.0

    @property
    def pass_ratio(self) -> float:
        """Alias for ``mean_reward``."""
        return self.mean_reward

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trail to a JSON-friendly dict."""
        return {
            "suite": self.suite,
            "model": self.model,
            "run_id": self.run_id,
            "seed": self.seed,
            "started_at": self.started_at,
            "committed_at": self.committed_at,
            "n": len(self.transitions),
            "mean_reward": self.mean_reward,
            "meta": self.meta,
            "transitions": [dataclasses.asdict(t) for t in self.transitions],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string (indented by default)."""
        return json.dumps(self.to_dict(), default=str, indent=indent)

    @classmethod
    def from_json(cls, s: str) -> Trail:
        """Deserialize a trail from a JSON string."""
        d = json.loads(s)
        t = cls(suite=d["suite"], model=d["model"], run_id=d["run_id"], seed=d["seed"])
        t.started_at = d["started_at"]
        t.committed_at = d.get("committed_at")
        t.meta = d.get("meta", {})
        for td in d.get("transitions", []):
            t.transitions.append(
                Transition(
                    task_id=td["task_id"],
                    artifact=Artifact(**td["artifact"]),
                    verdict=JudgeVerdict(**td["verdict"])
                    if td.get("verdict")
                    else None,
                    debug=td.get("debug", {}),
                )
            )
        return t


# ---------------------------------------------------------------------------
# Trace Recorder
# ---------------------------------------------------------------------------


class Recorder:
    """Context manager that accumulates transitions into a Trail.

    Usage:
        with Recorder("ifeval", "mock", "run-001", seed=42) as trail:
            for task in tasks:
                artifact = Artifact(...)
                verdict = JudgeVerdict(...)
                trail.add(Transition(task_id=t, artifact=artifact, verdict=verdict))
            trail.commit()
    """

    def __init__(self, suite: str, model: str, run_id: str, seed: int = 42) -> None:
        """Initialize a new Recorder with the given run metadata."""
        self.trail = Trail(suite=suite, model=model, run_id=run_id, seed=seed)

    def __enter__(self) -> Trail:
        """Return the Trail for the caller to populate."""
        return self.trail

    def __exit__(self, *exc: Any) -> None:
        """Auto-commit the trail if the caller forgot to commit manually."""
        if self.trail.committed_at is None:
            self.trail.commit()


__all__ = [
    "Artifact",
    "JudgeVerdict",
    "Transition",
    "Trail",
    "Recorder",
]
