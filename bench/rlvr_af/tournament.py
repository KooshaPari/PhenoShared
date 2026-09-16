"""L5 — Tournament runner: orchestrates the full RLVR-AF loop.

The tournament runner takes a suite + model, runs the 4-layer pipeline,
and outputs a report with score + traces + patches + delta.

From the RLVR-AF spec:
  "Tournament: given a suite and a model, runs Layers 1-4 N times.
   Each iteration: run suite → trace → verify → critic → optimize.
   The best optimizer patch is merged and the score delta is recorded.
   After N iterations the tournament reports the final score and the
   cumulative delta."
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from bench.rlvr_af.critic import BaseCritic, CriticReport, HeuristicCritic
from bench.rlvr_af.optimize import (
    BaseOptimizer,
    HeuristicOptimizer,
    OptimizerReport,
    apply_patch,
)
from bench.rlvr_af.trace import Artifact, JudgeVerdict, Trail, Transition
from bench.rlvr_af.verify import BaseVerifier, HeuristicVerifier

REPO_ROOT = "/Users/kooshapari/CodeProjects/Phenotype/pheno-harness"


@dataclass
class TournamentIteration:
    """A single tournament round (trace → verify → critic → optimize)."""

    iteration: int
    trace: Trail
    verdict: JudgeVerdict
    critic_report: CriticReport
    optimizer_report: OptimizerReport
    patch_applied: bool = False
    score_before: float = 0.0
    score_after: float = 0.0
    wall_clock_s: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TournamentResult:
    """The full tournament output."""

    suite_name: str
    model: str
    n_iterations: int
    iterations: list[TournamentIteration] = field(default_factory=list)
    final_score: float = 0.0
    cumulative_delta: float = 0.0
    total_wall_clock_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tournament runner
# ---------------------------------------------------------------------------


class TournamentRunner:
    """Orchestrates N iterations of the RLVR-AF loop."""

    def __init__(
        self,
        suite: Any,
        model: str = "mock",
        verifier: BaseVerifier | None = None,
        critic: BaseCritic | None = None,
        optimizer: BaseOptimizer | None = None,
        n: int = 3,
        repo_root: str = REPO_ROOT,
    ):
        self.suite = suite
        self.model = model
        self.verifier = verifier or HeuristicVerifier()
        self.critic = critic or HeuristicCritic()
        self.optimizer = optimizer or HeuristicOptimizer()
        self.n = n
        self.repo_root = repo_root
        self.score = 0.0

    def run(self) -> TournamentResult:
        """Run the tournament loop until convergence and return a TournamentResult."""
        iterations: list[TournamentIteration] = []
        total_start = time.monotonic()

        for i in range(self.n):
            iter_start = time.monotonic()

            # L1: Trace
            artifact = Artifact(
                elapsed_s=0.0,
                prompt=f"iter-{i} model={self.model} suite={self.suite.name}",
                completion="",
            )
            transition = Transition(
                task_id=f"iter-{i}",
                artifact=artifact,
            )
            trail = Trail(
                suite=self.suite.name,
                model=self.model,
                run_id=f"{self.suite.name}-tournament-{int(time.time())}-{i}",
                seed=42,
            )
            trail.add(transition)
            trail.commit()

            # Actually run the suite
            from bench.types import EnergySource, JudgeMode, RunSpec

            spec = RunSpec(
                suite=self.suite.name,
                n=3,
                seed=42,
                model=self.model,
                judge_mode=JudgeMode.DETERMINISTIC,
                energy_source=EnergySource.NONE,
                run_id=f"rlvr-tournament-{self.suite.name}-{i}",
            )
            try:
                result = self.suite.run(spec)
                trail.meta["output"] = (
                    result.__dict__ if hasattr(result, "__dict__") else {}
                )
            except Exception as e:
                trail.meta["output"] = {"error": str(e)}

            # L2: Verify
            verdict = JudgeVerdict(passed=False, reward=0.0)
            try:
                ok_count = sum(
                    1 for t in result.task_results if t.status.value in ("pass", "ok")
                )
                total = len(result.task_results)
                verdict = JudgeVerdict(
                    passed=ok_count == total,
                    reward=ok_count / max(total, 1),
                )
            except Exception:
                verdict = JudgeVerdict(
                    passed=False,
                    reward=0.0,
                    meta={"error": "could not parse result"},
                )
            self.score = verdict.reward

            # L3: Critic
            critic_report = self.critic.analyze(trail)

            # L4: Optimize
            optimizer_report = self.optimizer.optimize(trail, critic_report)

            # Apply the best patch if score is below 1.0
            patch_applied = False
            if verdict.reward < 1.0 and optimizer_report.best_proposal:
                patch_applied = apply_patch(optimizer_report.best_proposal)

            iter_wall = time.monotonic() - iter_start
            iteration = TournamentIteration(
                iteration=i,
                trace=trail,
                verdict=verdict,
                critic_report=critic_report,
                optimizer_report=optimizer_report,
                patch_applied=patch_applied,
                score_before=self.score,
                score_after=self.score,  # would re-measure in real run
                wall_clock_s=iter_wall,
            )
            iterations.append(iteration)

        total_wall = time.monotonic() - total_start
        cumulative_delta = sum(it.score_after - it.score_before for it in iterations)

        return TournamentResult(
            suite_name=self.suite.name,
            model=self.model,
            n_iterations=self.n,
            iterations=iterations,
            final_score=self.score,
            cumulative_delta=cumulative_delta,
            total_wall_clock_s=total_wall,
        )


# ---------------------------------------------------------------------------
# Convenience CLI
# ---------------------------------------------------------------------------


def run_tournament(
    suite_name: str,
    model: str = "mock",
    n: int = 3,
) -> TournamentResult:
    """Run a full tournament for a single suite."""
    # Import the suite class
    import importlib

    module_path = f"bench.suites.{suite_name.replace('-', '_')}"
    try:
        mod = importlib.import_module(module_path)
        # Find the Suite subclass
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isinstance(obj, type)
                and hasattr(obj, "name")
                and obj.name == suite_name
            ):
                suite = obj()
                break
        else:
            raise ValueError(f"no suite found with name={suite_name}")
    except (ImportError, ValueError):
        raise

    # Discover suite class
    from bench.registry import get_suite

    suite_cls = get_suite(suite_name)
    suite = suite_cls()

    runner = TournamentRunner(suite, model=model)
    return runner.run()


__all__ = [
    "TournamentIteration",
    "TournamentResult",
    "TournamentRunner",
    "run_tournament",
]
