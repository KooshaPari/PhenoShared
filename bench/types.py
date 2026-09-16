"""Core types for the pheno-harness benchmark suite.

Slim, executor-friendly API with backward-compat field name mapping
for old skeleton-style kwargs (``duration_s``, ``tasks``, ``metrics``,
``RunReport``, ``EnergySource.POWERMETRICS``).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(StrEnum):
    """Outcome of a single task execution in a suite run.

    String-valued enum so that JSON serialization preserves the
    canonical wire values (``"ok"``, ``"wrong"``, etc.). Aliases
    (``PASS = OK``, ``FAIL = WRONG``, ``SKIP = SKIPPED``) are
    declared as **references** to the canonical members so
    equality and identity both hold.
    """

    OK = "ok"
    WRONG = "wrong"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    # Back-compat aliases used by suite modules + skeleton / runner tests.
    # Declared as references (PASS = OK) so that TaskStatus.PASS is the
    # *same enum member* as TaskStatus.OK, not a sibling with the same
    # value. Equality (`PASS == OK`) and identity (`PASS is OK`) both hold.
    # See https://docs.python.org/3/library/enum.html#supported-sunder-names
    # and the DAG task 8 audit (TaskStatus.WRONG-vs-PASS regression).
    PASS = OK  # alias for OK
    FAIL = WRONG  # alias for WRONG
    SKIP = SKIPPED  # alias for SKIPPED


class EnergySource(StrEnum):
    """Source of energy / power readings for a benchmark run.

    Specialized sources are: ``M1_PMU`` (Apple Silicon PMU),
    ``NVIDIA_SMI`` (NVIDIA driver), and ``POWERMETRICS`` (macOS
    powermetrics — same wire as M1_PMU but legacy name).
    """

    NONE = "none"
    M1_PMU = "m1_pmu"
    NVIDIA_SMI = "nvidia_smi"
    # Skeleton / energy.py name for macOS powermetrics (same wire as M1_PMU).
    POWERMETRICS = "powermetrics"


# Accept hyphenated CLI aliases used by older docs/tests.
_ENERGY_ALIASES = {
    "nvidia-smi": EnergySource.NVIDIA_SMI,
    "powermetrics": EnergySource.POWERMETRICS,
    "m1-pmu": EnergySource.M1_PMU,
}


def coerce_energy_source(value: Any) -> EnergySource:
    """Coerce a wire value (string or already-coerced) into an ``EnergySource``.

    Accepts canonical values (``"m1_pmu"``, ``"nvidia_smi"``, etc.) and
    hyphenated CLI aliases (``"nvidia-smi"``, ``"m1-pmu"``).
    """
    if isinstance(value, EnergySource):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        if key in _ENERGY_ALIASES:
            return _ENERGY_ALIASES[key]
        return EnergySource(key)
    raise TypeError(f"Cannot coerce energy source: {value!r}")


class JudgeMode(StrEnum):
    """How the judge decides pass/fail for a task completion.

    ``DETERMINISTIC`` = exact match / regex / verifier output.
    ``LLM`` = use a separate judge model (e.g. claude-sonnet-5).
    """

    DETERMINISTIC = "deterministic"
    LLM = "llm"


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------


@dataclass
class RunSpec:
    """A single suite+model+config combination."""

    suite: str
    n: int = 5
    seed: int = 42
    model: str = "Qwen3.5-0.8B"
    judge_model: str | None = "claude-sonnet-5"
    judge_mode: JudgeMode = JudgeMode.DETERMINISTIC
    energy_source: EnergySource = EnergySource.NONE
    output: str = "bench/results/run.json"
    run_id: str | None = None
    task_subset: list[str] | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the run spec to a JSON-friendly dict (enums unwrapped)."""
        d = asdict(self)
        d["judge_mode"] = self.judge_mode.value
        d["energy_source"] = self.energy_source.value
        return d

    def __post_init__(self) -> None:
        if isinstance(self.judge_mode, str):
            self.judge_mode = JudgeMode(self.judge_mode)
        if not isinstance(self.energy_source, EnergySource):
            self.energy_source = coerce_energy_source(self.energy_source)
        if isinstance(self.suite, str):
            self.suite = self.suite.lower().replace("_", "-")


@dataclass
class SuiteSpec:
    """Static metadata describing a registered suite."""

    name: str
    cls: type
    domain: str = ""
    paper_metrics: tuple[str, ...] = ()
    default_judge: str | None = None
    source_url: str = ""
    notes: str = ""
    subset_label: str = "n=5"

    def short(self) -> str:
        """Return a one-line ``"<name> (<domain>)`` summary."""
        return f"{self.name} ({self.domain or '?'})"
        return f"{self.name} ({self.domain or '?'})"


# ---------------------------------------------------------------------------
# Canonical TaskSpec (v0.12 task 6 — moved from bench/suites/_stub_task.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskSpec:
    """Immutable description of a single benchmark task.

    Canonical location: bench/types.py (re-exported via bench/registry and
    bench/suites/_stub_task for backward compat).

    Suites yield these from ``subset(n, seed)``. The bench runner dispatches
    each ``TaskSpec`` to ``suite.run_task(task, model, **kwargs)``.

    The comparison pools (bench/comparison/stock_vs_ours_analysis_pools) also
    use this type; ``difficulty``, ``expected`` and the ``meta`` alias are
    provided for that use-case.
    """

    task_id: str
    suite: str
    prompt: str = ""
    reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    difficulty: str = ""
    expected: str = ""

    def __post_init__(self) -> None:
        # Keep reference <-> expected in sync (comparison uses expected).
        if self.expected and not self.reference:
            object.__setattr__(self, "reference", self.expected)
        elif self.reference and not self.expected:
            object.__setattr__(self, "expected", self.reference)

    @property
    def meta(self) -> dict[str, Any]:
        """Alias for ``metadata`` (comparison-pool compatibility)."""
        return self.metadata

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task spec to a JSON-friendly dict."""
        return {
            "task_id": self.task_id,
            "suite": self.suite,
            "prompt": self.prompt,
            "reference": self.reference,
            "expected": self.expected,
            "metadata": dict(self.metadata),
            "meta": dict(self.metadata),
            "tags": list(self.tags),
            "difficulty": self.difficulty,
        }


# Back-compat alias
Task = TaskSpec


# ---------------------------------------------------------------------------
# Per-task result
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """Outcome for a single task.

    Accepts skeleton / runner kwargs (``duration_s``, ``reward``,
    ``prompt_tokens``, ``message``, ``metrics``) and keeps them in sync with
    the executor-friendly field names.
    """

    task_id: str
    status: TaskStatus
    prompt: str = ""
    completion: str = ""
    expected: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    started_at_s: float = 0.0
    wall_clock_s: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    first_token_latency_s: float | None = None
    # Suites use list[dict]; restored runner executor uses int counts.
    tool_calls: Any = field(default_factory=list)
    cached: bool = False
    synthetic: bool = False
    error: str | None = None
    # Skeleton / runner aliases.
    duration_s: float = 0.0
    reward: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            legacy = {
                "pass": "ok",  # nosec B105
                "fail": "wrong",
                "skip": "skipped",
                "timeout": "timeout",
            }
            raw = legacy.get(self.status, self.status)
            self.status = TaskStatus(raw)
        if self.duration_s and not self.wall_clock_s:
            self.wall_clock_s = float(self.duration_s)
        elif self.wall_clock_s and not self.duration_s:
            self.duration_s = float(self.wall_clock_s)
        if self.prompt_tokens and not self.tokens_in:
            self.tokens_in = int(self.prompt_tokens)
        elif self.tokens_in and not self.prompt_tokens:
            self.prompt_tokens = int(self.tokens_in)
        if self.completion_tokens and not self.tokens_out:
            self.tokens_out = int(self.completion_tokens)
        elif self.tokens_out and not self.completion_tokens:
            self.completion_tokens = int(self.tokens_out)
        self.metrics = dict(self.metrics or {})
        self.meta = dict(self.meta or {})
        if self.reward is not None:
            self.meta.setdefault("reward", self.reward)
        if self.message and not self.completion:
            self.completion = self.message
        elif self.completion and not self.message:
            self.message = self.completion

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task result to a JSON-friendly dict (status enum unwrapped)."""
        return {
            "task_id": self.task_id,
            "status": self.status.value
            if isinstance(self.status, TaskStatus)
            else self.status,
            "prompt": self.prompt,
            "completion": self.completion,
            "expected": self.expected,
            "meta": self.meta,
            "metrics": self.metrics,
            "message": self.message,
            "started_at_s": self.started_at_s,
            "wall_clock_s": self.wall_clock_s,
            "duration_s": self.duration_s or self.wall_clock_s,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "prompt_tokens": self.prompt_tokens or self.tokens_in,
            "completion_tokens": self.completion_tokens or self.tokens_out,
            "first_token_latency_s": self.first_token_latency_s,
            "tool_calls": self.tool_calls,
            "cached": self.cached,
            "synthetic": self.synthetic,
            "error": self.error,
            "reward": self.reward,
        }


# ---------------------------------------------------------------------------
# Suite-level result  (backward-compat: accepts old skeleton field names)
# ---------------------------------------------------------------------------


class SuiteResult:
    """Aggregate outcome for a single suite+model run.

    Accepts old skeleton kwargs (``run_id``, ``started_at``, ``stopped_at``,
    ``tasks``, ``metrics``, ``notes``, ``reward``) transparently and maps
    them to current field names.  Silently drops unknown kwargs.
    """

    __slots__ = (
        "suite",
        "model",
        "n",
        "wall_clock_s",
        "passed",
        "wrong",
        "errored",
        "pass_at_1",
        "tokens_in",
        "tokens_out",
        "energy_total",
        "energy_source",
        "task_results",
        "meta",
        "run_id",
        "started_at",
        "stopped_at",
    )

    def __init__(self, suite: str, model: str, n: int = 0, **kwargs: Any) -> None:
        self.suite = suite
        self.model = model

        tasks_raw = kwargs.pop("task_results", kwargs.pop("tasks", []))
        self.task_results: list[TaskResult] = []
        for tr in tasks_raw if isinstance(tasks_raw, (list, tuple)) else []:
            if isinstance(tr, TaskResult):
                self.task_results.append(tr)
            elif isinstance(tr, dict):
                self.task_results.append(
                    TaskResult(
                        **{
                            k: v
                            for k, v in tr.items()
                            if k in TaskResult.__dataclass_fields__
                        }
                    )
                )
            else:
                self.task_results.append(tr)
        self.n: int = n if n else len(self.task_results)

        wall = kwargs.pop("wall_clock_s", None)
        self.started_at = kwargs.pop("started_at", None)
        self.stopped_at = kwargs.pop("stopped_at", None)
        if wall is not None:
            self.wall_clock_s = float(wall)
        elif isinstance(self.started_at, (int, float)) and isinstance(
            self.stopped_at, (int, float)
        ):
            self.wall_clock_s = float(self.stopped_at) - float(self.started_at)
        else:
            self.wall_clock_s = 0.0

        self.passed: int = int(kwargs.pop("passed", 0))
        self.wrong: int = int(kwargs.pop("wrong", 0))
        self.errored: int = int(kwargs.pop("errored", 0))
        self.pass_at_1: float = float(kwargs.pop("pass_at_1", 0.0))
        self.tokens_in: int = int(kwargs.pop("tokens_in", 0))
        self.tokens_out: int = int(kwargs.pop("tokens_out", 0))
        self.energy_total: Any = kwargs.pop("energy_total", None)
        energy_src = kwargs.pop("energy_source", EnergySource.NONE)
        self.energy_source: EnergySource = (
            coerce_energy_source(energy_src)
            if not isinstance(energy_src, EnergySource)
            else energy_src
        )
        metrics = kwargs.pop("metrics", None)
        meta = dict(kwargs.pop("meta", {}) or {})
        if metrics:
            meta = {**dict(metrics), **meta}
        self.meta: dict[str, Any] = meta

        self.run_id: str | None = kwargs.pop("run_id", None)
        kwargs.pop("notes", None)
        kwargs.pop("reward", None)

        if kwargs:
            logger.warning("SuiteResult ignoring unknown kwargs: %s", kwargs)

    # ---- skeleton aliases -------------------------------------------------

    @property
    def tasks(self) -> list[TaskResult]:
        """Alias for ``task_results`` (skeleton-friendly)."""
        return self.task_results

    @property
    def metrics(self) -> dict[str, Any]:
        """Alias for ``meta`` (skeleton-friendly)."""
        return self.meta

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SuiteResult):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    # ---- serialization helpers --------------------------------------------

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SuiteResult:
        """Reconstruct from JSON dict."""
        from copy import deepcopy

        d = deepcopy(d)
        raw_tasks = d.pop("task_results", None)
        if raw_tasks is None:
            raw_tasks = d.pop("tasks", []) or []
        task_results = []
        for tr in raw_tasks:
            if isinstance(tr, TaskResult):
                task_results.append(tr)
                continue
            status_raw = tr.get("status", "ok")
            kwargs = {
                "task_id": tr.get("task_id", ""),
                "status": status_raw,
                "prompt": tr.get("prompt", ""),
                "completion": tr.get("completion", ""),
                "expected": tr.get("expected"),
                "meta": dict(tr.get("meta", {}) or {}),
                "started_at_s": tr.get("started_at_s", 0.0),
                "wall_clock_s": tr.get(
                    "wall_clock_s", tr.get("duration_s", 0.0) or 0.0
                ),
                "duration_s": tr.get("duration_s", tr.get("wall_clock_s", 0.0) or 0.0),
                "tokens_in": tr.get("tokens_in", tr.get("prompt_tokens", 0) or 0),
                "tokens_out": tr.get("tokens_out", tr.get("completion_tokens", 0) or 0),
                "first_token_latency_s": tr.get("first_token_latency_s"),
                "tool_calls": list(tr.get("tool_calls", []) or [])
                if isinstance(tr.get("tool_calls"), list)
                else [],
                "cached": bool(tr.get("cached", False)),
                "synthetic": bool(tr.get("synthetic", False)),
                "error": tr.get("error"),
                "reward": tr.get("reward"),
            }
            task_results.append(TaskResult(**kwargs))
        d["task_results"] = task_results
        if "energy_source" in d and not isinstance(d["energy_source"], EnergySource):
            d["energy_source"] = coerce_energy_source(d["energy_source"])
        return cls(**d)

    @classmethod
    def from_json(cls, payload: str) -> SuiteResult:
        """Construct a SuiteResult from a JSON string."""
        return cls.from_dict(json.loads(payload))

    def to_json(self) -> str:
        """Serialize the suite result to a JSON string (indented)."""
        return json.dumps(self.to_dict(), default=str, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the suite result to a JSON-friendly dict (enums unwrapped)."""
        d = {
            "suite": self.suite,
            "model": self.model,
            "n": self.n,
            "wall_clock_s": self.wall_clock_s,
            "passed": self.passed,
            "wrong": self.wrong,
            "errored": self.errored,
            "pass_at_1": self.pass_at_1,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "energy_source": (
                self.energy_source.value
                if isinstance(self.energy_source, EnergySource)
                else self.energy_source
            ),
            "task_results": [
                t.to_dict() if hasattr(t, "to_dict") else t
                for t in (self.task_results or [])
            ],
            "tasks": [
                t.to_dict() if hasattr(t, "to_dict") else t
                for t in (self.task_results or [])
            ],
            "meta": self.meta,
            "metrics": self.meta,
        }
        if self.energy_total is not None:
            d["energy_total"] = str(self.energy_total)
        if self.run_id:
            d["run_id"] = self.run_id
        if self.started_at is not None:
            d["started_at"] = self.started_at
        if self.stopped_at is not None:
            d["stopped_at"] = self.stopped_at
        return d


# ---------------------------------------------------------------------------
# Multi-suite report
# ---------------------------------------------------------------------------


@dataclass
class RunReport:
    """Top-level report: many (suite, model) results cross-referenced."""

    version: str
    generated_at: str
    run_id: str
    judge_mode: JudgeMode
    energy_source: EnergySource
    results: list[SuiteResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.judge_mode, str):
            self.judge_mode = JudgeMode(self.judge_mode)
        if not isinstance(self.energy_source, EnergySource):
            self.energy_source = coerce_energy_source(self.energy_source)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the run report to a JSON-friendly dict (enums unwrapped)."""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "run_id": self.run_id,
            "judge_mode": self.judge_mode.value,
            "energy_source": self.energy_source.value,
            "results": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.results
            ],
        }

    def to_json(self) -> str:
        """Serialize the run report to a compact JSON string (no indent)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "RunSpec",
    "RunReport",
    "TaskResult",
    "TaskSpec",
    "Task",
    "SuiteResult",
    "SuiteSpec",
    "TaskStatus",
    "EnergySource",
    "JudgeMode",
    "coerce_energy_source",
]
