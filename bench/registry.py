"""Auto-discovery registries for suites, tasks, and metrics."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .metric import Metric
from .types import SuiteSpec  # re-export canonical TaskSpec

# ---------------------------------------------------------------------------
# Suite registry (auto via __init_subclass__)
# ---------------------------------------------------------------------------


_SUITES: dict[str, type[Suite]] = {}
_SUITE_SPECS: dict[str, SuiteSpec] = {}
_ALLOW_SUITE_OVERWRITE = False


def allow_suite_overwrite(enabled: bool = True) -> None:
    """Permit replacing an existing suite registration (reload / test recovery)."""
    global _ALLOW_SUITE_OVERWRITE
    _ALLOW_SUITE_OVERWRITE = enabled


class Suite:
    """Base class for benchmark suites. Subclasses auto-register."""

    name: str = ""
    source_url: str = ""
    format: str = "deterministic"
    subset_label: str = "n=5"
    rationale: str = ""
    default_judge_mode: str = "deterministic"

    def subset(self, n: int, seed: int) -> list[Any]:
        """Return n deterministic task descriptors for `seed`.

        Subclasses override for suite-specific sources (HF, GitHub,
        local JSON, etc.). The default raises NotImplementedError so
        the auto-registered spec accurately reflects missing impls.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement subset()")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", "") or cls.__name__
        cls.name = name
        # Skip abstract classes / skeletons with no name.
        if not name or name == "Suite":
            return
        if name in _SUITES and _SUITES[name] is not cls and not _ALLOW_SUITE_OVERWRITE:
            raise RuntimeError(
                f"Suite {name!r} already registered (by {_SUITES[name].__name__})"
            )
        # Build the SuiteSpec for this subclass and persist useful class-level
        # metadata so the runner and CLI can introspect without re-walking
        # the class.
        spec = SuiteSpec(name=name, cls=cls)
        for attr in (
            "source_url",
            "format",
            "subset_label",
            "rationale",
            "default_judge_mode",
            "domain",
            "paper_metrics",
            "default_judge",
            "notes",
            "task_count",
        ):
            if hasattr(cls, attr):
                setattr(spec, attr, getattr(cls, attr))
        _SUITES[name] = cls
        _SUITE_SPECS[name] = spec

    def run(self, run_spec: Any) -> Any:  # pragma: no cover - abstract
        """Execute this suite and return a `SuiteResult`. Concrete subclasses override."""
        raise NotImplementedError(
            f"Suite {self.name!r} does not implement run()"
        )  # pragma: no cover  # abstract


def list_suites() -> list[type[Suite]]:
    """Return all registered Suite subclasses in registration order."""
    return list(_SUITES.values())


def get_suite(name: str) -> type[Suite]:
    """Look up a registered Suite subclass by name; raises KeyError if missing."""
    return _SUITES[name]


def get_suite_spec(name: str) -> SuiteSpec:
    """Return the SuiteSpec for a registered Suite by name."""
    return _SUITE_SPECS[name]


def list_suite_specs() -> list[SuiteSpec]:
    """Return all registered SuiteSpec instances."""
    return list(_SUITE_SPECS.values())


def reset_registry() -> None:
    """Clear the registry; intended for tests only."""
    _SUITES.clear()
    _SUITE_SPECS.clear()


# ---------------------------------------------------------------------------
# Task registry (decorator-based)
# ---------------------------------------------------------------------------


_TASKS: dict[str, Task] = {}


class Task:
    """A single runnable task within a suite."""

    def __init__(
        self,
        task_id: str,
        suite: str,
        handler: Callable[..., Any] | None = None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.task_id = task_id
        self.suite = suite
        self.handler = handler
        self.metadata = dict(metadata or {})
        _TASKS[self.task_id] = self

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the underlying handler with the provided arguments."""
        if self.handler is None:
            raise NotImplementedError(f"Task {self.task_id!r} has no handler")
        return self.handler(*args, **kwargs)


def task(
    task_id: str, suite: str, **metadata: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator registering a function as a Task in the given suite.

    Returns the original function so it remains directly callable.
    """

    def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Register ``fn`` as a Task under (task_id, suite) and return it unchanged."""
        metadata_clean = {k: v for k, v in metadata.items() if k != "self"}
        Task(task_id=task_id, suite=suite, handler=fn, metadata=metadata_clean)
        return fn

    return wrap


def get_task(task_id: str) -> Task:
    """Look up a registered Task by ID; raises KeyError if missing."""
    return _TASKS[task_id]


def list_tasks() -> Iterable[Task]:
    """Iterate over registered Tasks."""
    return list(_TASKS.values())


def reset_task_registry() -> None:
    """Clear the Task registry; intended for tests only."""
    _TASKS.clear()


# ---------------------------------------------------------------------------
# Metric registry (decorator-based)
# ---------------------------------------------------------------------------


_METRICS: dict[str, Metric] = {}


def metric(
    name: str, *, units: str = "", source: str = "manual", higher_is_better: bool = True
) -> Callable[[Callable[[], float]], Metric]:
    """Decorator: capture `name`, `units`, `source` on the produced Metric.

    The decorated callable must take no arguments and return a numeric value.
    """

    def wrap(fn: Callable[[], float]) -> Metric:
        """Capture the metric value at registration time and return the Metric."""
        m = Metric(
            name=name,
            value=float(fn()),
            source=source,
            units=units,
            higher_is_better=higher_is_better,
        )
        _METRICS[name] = m
        return m

    return wrap


def get_metric(name: str) -> Metric:
    """Look up a registered Metric by name."""
    return _METRICS[name]


def list_metrics() -> list[Metric]:
    """Return all registered Metrics in registration order."""
    return list(_METRICS.values())


def reset_metric_registry() -> None:
    """Clear the Metric registry; intended for tests only."""
    _METRICS.clear()


def registry_summary() -> dict[str, list[str]]:
    """Return a snapshot of registry contents (useful for --self-test)."""
    return {
        "suites": sorted(_SUITES.keys()),
        "tasks": sorted(_TASKS.keys()),
        "metrics": sorted(_METRICS.keys()),
    }
