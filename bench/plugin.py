"""Plugin system for pheno-harness bench.

Enables third-party extensions (custom judges, custom contracts, custom
adapters) without modifying core code. Plugins register hook handlers
that the runner invokes at defined extension points.

Available hooks:
- pre_suite(name, n, seed)     -> mutate kwargs before subset generation
- post_suite(name, tasks)      -> mutate task list after subset generation
- pre_judge(task, response)    -> modify response before judging
- post_judge(task, result)     -> observe/record judge result
- pre_metric(task, metrics)    -> seed metrics for a task
- post_metric(task, metrics)   -> finalize/aggregate metrics for a task
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

PluginHandler = Callable[..., Any]
HookName = str


@dataclass
class Plugin:
    """A registered plugin with one or more hook handlers."""

    name: str
    handlers: dict[HookName, PluginHandler] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""

    def hook(self, name: HookName) -> Callable[[PluginHandler], PluginHandler]:
        """Decorator to register a handler for a named hook."""

        def deco(fn: PluginHandler) -> PluginHandler:
            self.handlers[name] = fn
            return fn

        return deco


class PluginRegistry:
    """Thread-safe-ish in-memory registry of plugins + hook dispatch."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise RuntimeError(f"Plugin {plugin.name!r} already registered")
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._plugins.keys())

    def dispatch(self, hook: HookName, *args: Any, **kwargs: Any) -> list[Any]:
        """Invoke all enabled handlers for a hook. Collect their return values."""
        results = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            handler = plugin.handlers.get(hook)
            if handler is None:
                continue
            try:
                results.append(handler(*args, **kwargs))
            except Exception as e:
                # Plugins must never break the runner — log and continue.
                print(f"plugin[{plugin.name}/{hook}] error: {e}")
        return results


# ---------------------------------------------------------------------------
# Built-in plugins
# ---------------------------------------------------------------------------


def make_timing_plugin() -> Plugin:
    """Records wall-clock time for each task."""
    p = Plugin(name="timing", description="Record per-task wall-clock time")
    state: dict[str, float] = {}

    @p.hook("pre_metric")
    def pre_metric(task: Any, metrics: Any) -> None:
        state[task.task_id] = __import__("time").monotonic()

    @p.hook("post_metric")
    def post_metric(task: Any, metrics: Any) -> None:
        start = state.pop(task.task_id, None)
        if start is not None:
            metrics.wall_clock_sec = __import__("time").monotonic() - start

    return p


def make_telemetry_plugin() -> Plugin:
    """Counts judge verdicts and emits a summary on demand."""
    p = Plugin(name="telemetry", description="Count judge verdicts per run")
    counts: dict[str, int] = {}

    @p.hook("post_judge")
    def post_judge(task: Any, result: Any) -> None:
        verdict = getattr(result, "verdict", "unknown")
        counts[verdict] = counts.get(verdict, 0) + 1

    @p.hook("pre_suite")
    def pre_suite(name: str, n: int, seed: int) -> None:
        counts.clear()

    return p


def make_normalization_plugin() -> Plugin:
    """Trims whitespace and collapses internal whitespace in judge responses."""
    import re

    p = Plugin(name="normalize", description="Normalize whitespace in responses")

    @p.hook("pre_judge")
    def pre_judge(task: Any, response: str) -> str:
        return re.sub(r"\s+", " ", response or "").strip()

    return p


_DEFAULT = PluginRegistry()
_DEFAULT.register(make_timing_plugin())
_DEFAULT.register(make_telemetry_plugin())
_DEFAULT.register(make_normalization_plugin())


def default_registry() -> PluginRegistry:
    """Return the process-wide default plugin registry with built-ins loaded."""
    return _DEFAULT


__all__ = [
    "Plugin",
    "PluginRegistry",
    "default_registry",
    "make_timing_plugin",
    "make_telemetry_plugin",
    "make_normalization_plugin",
]


# ---------------------------------------------------------------------------
# Smoke tests (run with `python -m bench.plugin`)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    reg = default_registry()
    assert set(reg.list_names()) == {"timing", "telemetry", "normalize"}

    @dataclass
    class FakeTask:
        task_id: str = "t1"

    @dataclass
    class FakeResult:
        verdict: str = "pass"

    @dataclass
    class FakeMetrics:
        wall_clock_sec: float = 0.0

    task = FakeTask()
    metrics = FakeMetrics()

    reg.dispatch("pre_metric", task, metrics)
    reg.dispatch("post_metric", task, metrics)
    reg.dispatch("post_judge", task, FakeResult())
    reg.dispatch("pre_judge", task, "  hello\n\n  world  ")
    assert metrics.wall_clock_sec >= 0.0
    print("plugin smoke OK; registry:", reg.list_names())
