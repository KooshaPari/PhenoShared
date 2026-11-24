"""BaseSuite: shared scaffolding for the 10 vendored benchmark suites.

This module lives at `bench/suites/_stub.py` (note the leading underscore — it's
not a suite itself, just helpers). Concrete suites import from here.

.. deprecated::
    The bespoke ``pheno-harness/bench/suites/*`` modules are deprecated as of
    2026-07-21. The canonical eval harness is the **Harbor Framework fork at**
    ``/Users/<REDACTED>/CodeProjects/Phenotype/repos/portage/`` with 50+ mature
    benchmark adapters under ``portage/adapters/``. Migration target:

        - ``_stub.py`` (placeholder)       → ``portage/adapters/{aime,gpqa-diamond,...}``
        - ``hle.py`` (HLE placeholder)     → ``portage/adapters/hle/``
        - ``perplexity.py``                → custom scorer via ``portage/src/harbor/analyze/``
        - ``container_runner.py``          → ``portage/src/harbor/environments/{docker,daytona,...}``
        - Pheno-specific quantization     → ``portage/adapters/phenotype_stock_vs_ours/``

    The ``pheno-harness`` repo remains for smoke-test pipelines only. The
    last ``pheno-harness`` commit is on the ``fix/100pct-bug`` branch; all
    future eval work happens in portage + the ``harbor-pheno`` extension
    package (``portage/packages/harbor-pheno/``).

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from bench.registry import Suite
from bench.suites._stub_task import (  # noqa: F401  (re-exported)
    Task,
    TaskSpec,
    synthetic_prompt,
    synthetic_response,
)
from bench.types import JudgeMode, RunSpec, SuiteResult, TaskResult, TaskStatus

# ---------------------------------------------------------------------------
# BaseSuite: concrete-suite defaults
# ---------------------------------------------------------------------------


class BaseSuite(Suite):
    """Shared scaffolding for the 10 vendored suites.

    Subclasses set class attributes (name, version, num_tasks, task_format,
    scoring, paper_metrics) and override `subset()` + `run_task()` for their
    specific behaviour. Default behaviour is stub-mode (synthetic data, no
    external API/Docker/HF download).
    """

    # Concrete-suite metadata (set on subclasses)
    name: str = ""
    version: str = "1.0"
    num_tasks: int = 0
    task_format: str = ""
    scoring: str = ""
    source_url: str = ""
    format: str = ""
    subset_label: str = "n=5"
    rationale: str = ""
    # Stored as enum (not str) so `SuiteSpec.judge_mode.value` works at to_dict()
    # time. Subclasses declare their own `default_judge_mode` as a string and
    # `__init_subclass__` below coerces it to a JudgeMode enum before the
    # skeleton's `Suite.__init_subclass__` reads it.
    default_judge_mode: JudgeMode = JudgeMode.DETERMINISTIC

    # Per-suite task prefixes for ID generation
    task_id_prefix: str = "task"

    # Override in subclasses: list of (metric_name, units, spec_section)
    _PAPER_METRICS: tuple[tuple[str, str, str], ...] = ()

    # ------------------------------------------------------------------
    # Spec §suite interface — subclasses override subset + run_task
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n deterministic `TaskSpec` instances for `seed`.

        Default: yield stable IDs of the form `<prefix>-<idx>` with synthetic
        prompts. Subclasses override for suite-specific task sources (HF,
        GitHub, local JSON).
        """
        n = max(0, int(n))
        out: list[TaskSpec] = []
        for i in range(n):
            tid = self._deterministic_task_id(seed=seed, idx=i)
            out.append(
                TaskSpec(
                    task_id=tid,
                    suite=self.name,
                    prompt=synthetic_prompt(seed, i),
                    reference="",
                    metadata={"index": i, "seed": seed, "stub": True},
                    tags=self._default_tags(),
                )
            )
        return out

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Run a single task and return a `TaskResult`.

        Default: stub-mode. Subclasses override for real execution paths
        (container, judge, perplexity, etc.) and should fall back to this
        when external deps are missing (Docker, API keys, HF cache).
        """
        start = time.time()
        # Synthetic stub result: alternating pass/fail based on task_id hash.
        # usedforsecurity=False: SHA-1 is used here only as a deterministic
        # mixing function for stub outcomes, not for any cryptographic purpose.
        digest = hashlib.sha1(
            f"{self.name}:{task.task_id}".encode(),
            usedforsecurity=False,
        ).digest()
        flip = digest[0] & 1
        status = TaskStatus.PASS if flip == 0 else TaskStatus.FAIL
        duration = float(kwargs.get("simulated_duration_s", 0.42))
        # Optional stub-mode override for outcomes
        if "stub_outcome" in kwargs:
            outcome = str(kwargs["stub_outcome"]).lower()
            if outcome == "pass":
                status = TaskStatus.PASS
            elif outcome == "fail":
                status = TaskStatus.FAIL
        elapsed = time.time() - start
        return TaskResult(
            task_id=str(task.task_id),
            status=status,
            prompt=str(task.prompt),
            completion=str(task.reference or ""),
            meta=dict(getattr(task, "paper_metrics", []) or []),
            wall_clock_s=elapsed + duration,
            tokens_in=0,
            tokens_out=0,
            cached=False,
            synthetic=True,
        )

    # ------------------------------------------------------------------
    # Suite.run(run_spec) orchestrator
    # ------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Coerce string `default_judge_mode` to a JudgeMode enum before registration.

        The ``Suite.__init_subclass__`` stores `default_judge_mode`
        verbatim in `SuiteSpec`, but `SuiteSpec.to_dict()` calls `.value` on
        it (which only works for enums). Concrete suites declare the
        attribute as a string ("deterministic" / "llm"); we coerce here so
        `python -m bench list --with-specs` doesn't crash.

        Also patch `SuiteSpec.subset` to read from `cls._subset_label` (a
        string) instead of `cls.subset` (which on concrete suites is shadowed
        by the `subset(n, seed)` method).
        """
        mode = getattr(cls, "default_judge_mode", "deterministic")
        if isinstance(mode, str):
            try:
                cls.default_judge_mode = JudgeMode(mode)
            except ValueError:
                cls.default_judge_mode = JudgeMode.DETERMINISTIC
        super().__init_subclass__(**kwargs)
        # Override the registered SuiteSpec.subset with our string label.
        try:
            from bench.registry import _SUITE_SPECS

            name = getattr(cls, "name", "") or cls.__name__
            if name in _SUITE_SPECS:
                _SUITE_SPECS[name].subset = getattr(cls, "_subset_label", "n=5")
        except Exception:  # pragma: no cover - defensive  # nosec B110
            pass

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the full suite against a `RunSpec` and return `SuiteResult`.

        This is the entry point called by the CLI dispatcher.  It calls
        `subset()` then iterates `run_task()` for each task. Real execution
        happens via the `**kwargs` override (`real=True`) which individual
        suites interpret (e.g. spin up a container, hit the Anthropic API, etc.).
        The default falls through to stub-mode.

        NOTE: We deliberately pass only safe scalar kwargs (seed, n) into
        `run_task` — never the full `RunSpec.to_dict()`, because `to_dict`
        includes string fields like `model` that would crash suites which
        pass kwargs through to `random.seed(...)`.
        """
        started_at = time.monotonic()
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = []
        for task in tasks:
            safe_kwargs: dict[str, Any] = {
                "seed": run_spec.seed,
                "n": run_spec.n,
                "judge_model": run_spec.judge_model,
            }
            results.append(self.run_task(task, run_spec.model, **safe_kwargs))
        stopped_at = time.monotonic()
        passed = sum(1 for r in results if r.status in (TaskStatus.PASS, TaskStatus.OK))
        wrong = sum(1 for r in results if r.status == TaskStatus.WRONG)
        errored = sum(1 for r in results if r.status == TaskStatus.ERROR)
        n = len(results)
        return SuiteResult(
            suite=run_spec.suite,
            model=run_spec.model,
            n=n,
            wall_clock_s=stopped_at - started_at,
            passed=passed,
            wrong=wrong,
            errored=errored,
            pass_at_1=passed / n if n else 0.0,
            tokens_in=sum(r.tokens_in for r in results),
            tokens_out=sum(r.tokens_out for r in results),
            energy_source=run_spec.energy_source,
            task_results=results,
            meta={"run_id": run_spec.run_id},
        )

    # ------------------------------------------------------------------
    # paper_metrics: leaderboard reference (spec rule 7)
    # ------------------------------------------------------------------

    @property
    def paper_metrics(self) -> list[tuple[str, str, str]]:
        """Return `[(metric_name, units, spec_section)]` for leaderboard rows."""
        return list(self._PAPER_METRICS)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _deterministic_task_id(self, seed: int, idx: int) -> str:
        """Build a stable task_id `<prefix>-<seed>-<idx>` (no randomness)."""
        return f"{self.task_id_prefix}-seed{seed}-idx{idx:04d}"

    def _default_tags(self) -> tuple[str, ...]:
        """Default tags for synthetic tasks; subclasses may override."""
        return ("synthetic", "stub")


def aggregate_paper_metrics(*suites: BaseSuite) -> list[tuple[str, str, str]]:
    """Merge paper_metrics from multiple suites into a unique-by-name list."""
    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for s in suites:
        for metric_name, units, section in s.paper_metrics:
            if metric_name in seen:
                continue
            seen.add(metric_name)
            out.append((metric_name, units, section))
    return out


# ---------------------------------------------------------------------------
# Cleanup: BaseSuite sneaks into the suite registry because
# `Suite.__init_subclass__` falls back to `cls.__name__` ("BaseSuite") when
# `cls.name` is "". Strip it so `python -m bench list` shows only the 10
# vendored suites + any third-party registrations.
# ---------------------------------------------------------------------------
try:
    from bench.registry import _SUITE_SPECS, _SUITES

    _SUITES.pop("BaseSuite", None)
    _SUITE_SPECS.pop("BaseSuite", None)
except Exception:  # pragma: no cover - defensive  # nosec B110
    pass


__all__ = [
    "BaseSuite",
    "Task",
    "TaskSpec",
    "aggregate_paper_metrics",
    "synthetic_prompt",
    "synthetic_response",
]
