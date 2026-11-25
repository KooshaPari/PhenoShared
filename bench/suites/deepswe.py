"""DeepSWE v1.1 — agentica-project/DeepSWE.

n tasks of mini-SWE-agent ReAct loop on Docker task definitions. Reward is
read from the verifier contract at `/logs/verifier/reward.json` (Harbor-style).

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2 row 1,
§3.1 (submodule), §3.3 (Harbor reward wire format).

G3 WSL-blocked (v0.12 task 10): DeepSWE Docker/Harbor eval requires WSL2
virtualization (HCS_E_HYPERV_NOT_INSTALLED on this host). Placeholder doc
at docs/plans/2026-08-20-N24-deepswe-wsl-blocked.md — skip live eval until
WSL re-enabled. Harness code remains importable and mypy-clean.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import Any

from bench.types import (
    RunSpec,
    TaskResult,
    TaskStatus,
)

try:
    from phenotype_shared.time_utils import now_iso
except ImportError:  # pragma: no cover - upstream module not vendored in this repo
    from datetime import datetime

    def now_iso() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return datetime.now(UTC).isoformat()


from ._stub import BaseSuite, TaskSpec, synthetic_prompt, synthetic_response
from .container_runner import ContainerRunner, run_or_stub

# Hard-coded dataset provenance (submodule-pinned; see §3.1).
SOURCE_URL = "github.com/agentica-project/DeepSWE"
VERSION = "1.1"
NUM_TASKS = 0  # Determined at subset time from the upstream submodule / dataset

CONTAINER_DEFAULT_TIMEOUT_S = 600.0  # 10 min per task (spec §7 row 1)
DEFAULT_WORKSPACE = Path.home() / ".cache" / "pheno-bench" / "deepswe"


class DeepSWE(BaseSuite):
    """DeepSWE v1.1 — flagship SWE-capability suite.

    Runs n tasks of the mini-SWE-agent ReAct loop inside a Docker container
    built from each task's Dockerfile. Reward is read from the Harbor
    `/logs/verifier/reward.json` contract. Falls back to stub-mode if
    Docker is unavailable (see spec rule 3).
    """

    name = "deep-swe"
    version = VERSION
    num_tasks = NUM_TASKS  # filled by `subset()` from upstream dataset
    task_format = "bash via mini-swe-agent (Princeton/SWE-bench)"
    scoring = "pass@1 (binary reward from verifier/reward.json)"
    source_url = SOURCE_URL
    format = task_format
    _subset_label = "n=5 deterministic seed=42"
    rationale = "flagship SWE capability"
    default_judge_mode = "deterministic"  # type: ignore[assignment]
    task_id_prefix = "deepswe"

    _PAPER_METRICS = (
        ("pass@1", "%", "spec §4.1 + leaderboard column for DeepSWE v1.1"),
        ("pass@1_ci95", "%", "spec §4.1 (95% binomial CI via wilson_ci)"),
        ("wall_clock_total", "s", "spec §4.3 (per-suite)"),
        ("tokens_per_sec_throughput", "tok/s", "spec §4.3 (per-suite)"),
    )

    def __init__(
        self,
        *,
        workspace: Path | str | None = None,
        container_timeout_s: float = CONTAINER_DEFAULT_TIMEOUT_S,
    ) -> None:
        self.workspace = Path(workspace) if workspace else DEFAULT_WORKSPACE
        self.container_timeout_s = float(container_timeout_s)
        self.runner = ContainerRunner(
            workspace=self.workspace, timeout_s=self.container_timeout_s
        )

    # ------------------------------------------------------------------
    # Subset: how many tasks does this suite have? Stub uses 25 default
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n DeepSWE task specs deterministically keyed by `seed`.

        Stub-mode (no submodule cloned): emit `n` synthetic specs whose IDs
        follow DeepSWE's `instance_id` convention (`pr-<repo>-<num>`).
        """
        n = max(0, int(n))
        # Default eval subset size per spec §3.1 (~25 tasks).
        # We expose the configured pool size via num_tasks even in stub-mode
        # so callers can ask for `n=5` and still get a deterministic subset.
        self.num_tasks = max(self.num_tasks, 25)
        out: list[TaskSpec] = []
        for i in range(n):
            idx = self._deterministic_idx(seed=seed, slot=i)
            out.append(
                TaskSpec(
                    task_id=f"pr-deepswe-{idx:04d}",
                    suite=self.name,
                    prompt=synthetic_prompt(seed, i),
                    reference="",
                    metadata={
                        "seed": seed,
                        "index": i,
                        "instance_id": f"pr-deepswe-{idx:04d}",
                        "stub": True,
                    },
                    tags=("swe", "deepswe", "stub"),
                )
            )
        return out

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Run a single DeepSWE task — container-backed or stub fallback.

        In real mode, builds + runs the task's Dockerfile via the
        `ContainerRunner`. In stub mode, emits a synthetic TaskResult with
        `metrics={}` (spec rule 1(c)).
        """
        if not kwargs.get("real", False):
            return super().run_task(task, model, **kwargs)
        # Real path: spin up the container; downgrade to stub if Docker is missing.
        dockerfile = kwargs.get("dockerfile")
        result = run_or_stub(
            self.runner,
            task.task_id,
            dockerfile=dockerfile,
        )
        reward = result.reward.reward if result.reward else 0.0
        status = TaskStatus.PASS if reward >= 0.999 else TaskStatus.FAIL
        return TaskResult(
            task_id=task.task_id,
            status=status,
            wall_clock_s=result.duration_s,
            tokens_in=len(task.prompt.split()),
            tokens_out=len(synthetic_response(0, 0).split()),
            tool_calls=[{"max_steps": kwargs.get("max_steps", 30)}],
            meta={
                "container_exit_code": float(result.exit_code),
                "wall_clock_total": result.duration_s,
                "pass@1": reward,
            },
        )

    # ------------------------------------------------------------------
    # Spec-mandated suite-level entry point
    # ------------------------------------------------------------------

    def run(self, run_spec: RunSpec) -> Any:
        """Skeleton `Suite.run` orchestrator; dispatched by the CLI."""
        from bench.types import (
            EnergySource,
            SuiteResult,
            TaskStatus,
        )

        # Re-use the BaseSuite orchestration; flag real mode if --real.
        now_iso()
        {
            **run_spec.to_dict(),
            "real": bool(run_spec.to_dict().get("real", False)),
        }
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = []
        for task in tasks:
            results.append(self.run_task(task, run_spec.model))
        now_iso()
        passes = sum(1 for r in results if r.status == TaskStatus.PASS)
        total = len(results)
        aggregate: dict[str, float] = {"pass@1": (passes / total) if total else 0.0}
        return SuiteResult(
            suite=self.name,
            model=run_spec.model,
            wall_clock_s=0.0,
            n=len(results),
            passed=passes,
            wrong=0,
            errored=0,
            pass_at_1=passes / total if total else 0.0,
            tokens_in=0,
            tokens_out=0,
            energy_source=EnergySource.NONE,
            task_results=results,
            meta=aggregate,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deterministic_idx(*, seed: int, slot: int) -> int:
        """Map (seed, slot) deterministically into [0, 10000) without RNG state."""
        return ((seed * 2654435761) ^ (slot * 40503)) % 10000


__all__ = ["DeepSWE", "DEFAULT_WORKSPACE"]
