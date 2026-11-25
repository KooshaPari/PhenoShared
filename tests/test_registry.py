"""Coverage tests for bench/registry.py.

Exercises the Suite/Task/Metric registries, the ``task`` and ``metric``
decorators, registry reset helpers, and ``registry_summary``.

Constraints:
- Uses module references for ``monkeypatch.setattr`` (no string paths).
- No subprocess, no network, no HuggingFace downloads.
- Suite subclasses are defined *inside* test functions so each test
  starts from a clean registry without relying on autouse teardown.
"""

from __future__ import annotations

from typing import Any

import pytest

import bench.registry as registry
from bench.registry import (
    Metric,
    Suite,
    SuiteSpec,
    Task,
    _METRICS,
    _SUITES,
    _SUITE_SPECS,
    _TASKS,
    allow_suite_overwrite,
    get_metric,
    get_suite,
    get_suite_spec,
    get_task,
    list_metrics,
    list_suite_specs,
    list_suites,
    list_tasks,
    metric,
    registry_summary,
    reset_metric_registry,
    reset_registry,
    reset_task_registry,
    task,
)


def _fresh_registries() -> None:
    """Reset every module-level registry dict. Safe to call repeatedly."""
    reset_registry()
    reset_task_registry()
    reset_metric_registry()


def _make_suite_class(
    name: str,
    *,
    domain: str = "",
    paper_metrics: tuple[str, ...] = (),
    default_judge: str | None = None,
    source_url: str = "",
    notes: str = "",
    subset_label: str = "n=5",
    rationale: str = "",
    format_: str = "deterministic",
    default_judge_mode: str = "deterministic",
) -> type[Suite]:
    """Dynamically build a Suite subclass with the given metadata.

    Uses ``type()`` so the ``name`` class attribute is present at
    class-creation time — ``Suite.__init_subclass__`` reads the name
    during class construction to populate the registry.
    """

    def subset(self: Suite, n: int, seed: int) -> list[Any]:
        return [{"task_id": f"{name}-{i}", "seed": seed} for i in range(n)]

    def run(self: Suite, run_spec: Any) -> Any:
        return {"suite": name}

    return type(
        name,
        (Suite,),
        {
            "name": name,
            "domain": domain,
            "paper_metrics": paper_metrics,
            "default_judge": default_judge,
            "source_url": source_url,
            "notes": notes,
            "subset_label": subset_label,
            "rationale": rationale,
            "format": format_,
            "default_judge_mode": default_judge_mode,
            "subset": subset,
            "run": run,
        },
    )


# ---------------------------------------------------------------------------
# Module-level globals
# ---------------------------------------------------------------------------


def test_module_globals_are_initialized() -> None:
    assert isinstance(registry._SUITES, dict)
    assert isinstance(registry._SUITE_SPECS, dict)
    assert isinstance(registry._TASKS, dict)
    assert isinstance(registry._METRICS, dict)
    assert isinstance(registry._ALLOW_SUITE_OVERWRITE, bool)


def test_module_exports_suite_class_and_decorators() -> None:
    assert registry.Suite is Suite
    assert callable(registry.task)
    assert callable(registry.metric)
    assert callable(registry.allow_suite_overwrite)
    assert callable(registry.reset_registry)
    assert callable(registry.reset_task_registry)
    assert callable(registry.reset_metric_registry)


def test_suite_class_defaults_match_documented_values() -> None:
    """Suite base class ships sensible defaults so subclasses inherit them."""
    assert Suite.source_url == ""
    assert Suite.format == "deterministic"
    assert Suite.subset_label == "n=5"
    assert Suite.rationale == ""
    assert Suite.default_judge_mode == "deterministic"


# ---------------------------------------------------------------------------
# Suite registry
# ---------------------------------------------------------------------------


def test_suite_subclass_auto_registers() -> None:
    _fresh_registries()
    cls = _make_suite_class("sample")
    assert "sample" in _SUITES
    assert get_suite("sample") is cls
    assert "sample" in _SUITE_SPECS


def test_suite_spec_pulls_class_level_metadata() -> None:
    _fresh_registries()
    _make_suite_class(
        "ifeval",
        domain="instruction-following",
        paper_metrics=("strict_acc", "loose_acc"),
        default_judge="regex",
        source_url="https://example.com/ifeval",
        notes="rfc-123",
        subset_label="n=10",
        rationale="instruction fidelity",
        format_="jsonl",
        default_judge_mode="deterministic",
    )
    spec = get_suite_spec("ifeval")
    assert isinstance(spec, SuiteSpec)
    assert spec.name == "ifeval"
    assert spec.domain == "instruction-following"
    assert spec.paper_metrics == ("strict_acc", "loose_acc")
    assert spec.default_judge == "regex"
    assert spec.source_url == "https://example.com/ifeval"
    assert spec.notes == "rfc-123"
    assert spec.subset_label == "n=10"
    assert spec.rationale == "instruction fidelity"
    assert spec.format == "jsonl"
    assert spec.default_judge_mode == "deterministic"


def test_list_suites_returns_in_registration_order() -> None:
    _fresh_registries()
    a = _make_suite_class("a-suite")
    b = _make_suite_class("b-suite")
    suites = list_suites()
    assert suites == [a, b]
    # list_suites returns a fresh list each call.
    snap = list_suites()
    suites.append(_make_suite_class("z-suite"))
    assert snap == [a, b]


def test_get_suite_raises_keyerror_for_unknown() -> None:
    _fresh_registries()
    with pytest.raises(KeyError):
        get_suite("does-not-exist")


def test_get_suite_spec_raises_keyerror_for_unknown() -> None:
    _fresh_registries()
    with pytest.raises(KeyError):
        get_suite_spec("missing")


def test_list_suite_specs_returns_specs() -> None:
    _fresh_registries()
    _make_suite_class("alpha")
    _make_suite_class("beta")
    specs = list_suite_specs()
    assert {s.name for s in specs} == {"alpha", "beta"}
    for s in specs:
        assert isinstance(s, SuiteSpec)


def test_reset_registry_clears_both_suites_and_specs() -> None:
    _fresh_registries()
    _make_suite_class("reset-me")
    assert _SUITES
    assert _SUITE_SPECS
    reset_registry()
    assert _SUITES == {}
    assert _SUITE_SPECS == {}
    assert list_suites() == []
    assert list_suite_specs() == []


def test_allow_suite_overwrite_toggles_global_flag() -> None:
    _fresh_registries()
    _make_suite_class("dup-target")
    assert registry._ALLOW_SUITE_OVERWRITE is False
    allow_suite_overwrite(True)
    assert registry._ALLOW_SUITE_OVERWRITE is True
    # Re-register same name now succeeds.
    replacement = _make_suite_class("dup-target")
    assert get_suite("dup-target") is replacement
    allow_suite_overwrite(False)
    assert registry._ALLOW_SUITE_OVERWRITE is False


def test_duplicate_suite_registration_raises_without_overwrite() -> None:
    _fresh_registries()
    _make_suite_class("collide")
    with pytest.raises(RuntimeError, match="already registered"):
        _make_suite_class("collide")


def test_suite_subset_default_raises_not_implemented() -> None:
    """Base ``Suite.subset`` is a no-op template that raises."""
    _fresh_registries()
    instance = Suite()
    with pytest.raises(NotImplementedError, match="does not implement subset"):
        instance.subset(1, 42)


def test_suite_run_default_raises_not_implemented() -> None:
    """Base ``Suite.run`` is a no-op template that raises."""
    instance = Suite()
    with pytest.raises(NotImplementedError, match="does not implement run"):
        instance.run(object())


def test_suite_spec_short_uses_domain_or_placeholder() -> None:
    spec = SuiteSpec(name="x", cls=Suite, domain="vision")
    assert spec.short() == "x (vision)"
    spec_blank = SuiteSpec(name="x", cls=Suite)
    assert spec_blank.short() == "x (?)"


# ---------------------------------------------------------------------------
# Task registry + decorator
# ---------------------------------------------------------------------------


def test_task_class_stores_attributes_and_registers() -> None:
    _fresh_registries()

    def handler() -> str:
        return "noop"

    t = Task(task_id="t-1", suite="sample", handler=handler, metadata={"k": 1})
    assert t.task_id == "t-1"
    assert t.suite == "sample"
    assert t.handler is handler
    assert t.metadata == {"k": 1}
    assert get_task("t-1") is t


def test_task_class_metadata_defaults_to_empty_dict() -> None:
    _fresh_registries()
    t = Task(task_id="t-empty", suite="sample")
    assert t.metadata == {}
    assert isinstance(t.metadata, dict)


def test_task_class_metadata_is_copied() -> None:
    _fresh_registries()
    src = {"k": 1}
    t = Task(task_id="t-meta", suite="sample", metadata=src)
    src["k"] = 999
    assert t.metadata == {"k": 1}


def test_task_run_invokes_handler() -> None:
    _fresh_registries()
    captured: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def handler(*args: Any, **kwargs: Any) -> str:
        captured.append((args, kwargs))
        return "ok"

    t = Task(task_id="t-run", suite="sample", handler=handler)
    assert t.run(1, 2, x=3) == "ok"
    assert captured == [((1, 2), {"x": 3})]


def test_task_run_raises_when_no_handler() -> None:
    _fresh_registries()
    t = Task(task_id="t-no-handler", suite="sample")
    with pytest.raises(NotImplementedError, match="has no handler"):
        t.run()


def test_task_decorator_returns_original_function() -> None:
    """The decorator returns ``fn`` unchanged so it remains directly callable."""
    _fresh_registries()

    captured: list[int] = []

    def fn(x: int) -> int:
        captured.append(x)
        return x * 2

    result = task("decorated", suite="sample")(fn)
    t = get_task("decorated")
    assert t.suite == "sample"
    assert t.handler is fn
    assert result is fn
    assert fn(3) == 6
    assert result(4) == 8
    assert captured == [3, 4]


def test_task_decorator_strips_self_keyword_from_metadata() -> None:
    _fresh_registries()

    @task("kw-meta", suite="sample", self="ignored", real=42)
    def fn() -> None:
        return None

    t = get_task("kw-meta")
    assert "self" not in t.metadata
    assert t.metadata == {"real": 42}


def test_get_task_raises_keyerror_for_unknown() -> None:
    _fresh_registries()
    with pytest.raises(KeyError):
        get_task("absent")


def test_list_tasks_returns_iterable_of_tasks() -> None:
    _fresh_registries()

    @task("a", suite="sample")
    def a() -> None:
        return None

    @task("b", suite="sample")
    def b() -> None:
        return None

    task_list = list(list_tasks())
    ids = sorted(t.task_id for t in task_list)
    assert ids == ["a", "b"]


def test_reset_task_registry_clears_tasks() -> None:
    _fresh_registries()

    @task("z", suite="sample")
    def z() -> None:
        return None

    assert _TASKS
    reset_task_registry()
    assert _TASKS == {}
    assert list(list_tasks()) == []


# ---------------------------------------------------------------------------
# Metric registry + decorator
# ---------------------------------------------------------------------------


def test_metric_decorator_captures_value_immediately() -> None:
    _fresh_registries()
    calls: list[int] = [0]

    def probe() -> float:
        calls[0] += 1
        return 7.5

    metric("calls", units="count", source="probe")(probe)
    # Decorator runs the function once at decoration time.
    assert calls[0] == 1
    m = get_metric("calls")
    assert isinstance(m, Metric)
    assert m.name == "calls"
    assert m.value == 7.5
    assert m.source == "probe"
    assert m.units == "count"
    assert m.higher_is_better is True


def test_metric_decorator_supports_lower_is_better() -> None:
    _fresh_registries()

    def latency() -> float:
        return 12.3

    metric("latency", units="ms", source="bench", higher_is_better=False)(latency)
    m = get_metric("latency")
    assert m.higher_is_better is False
    assert m.value == 12.3
    assert m.units == "ms"
    assert m.source == "bench"


def test_metric_decorator_defaults_units_and_source() -> None:
    _fresh_registries()

    def ret() -> float:
        return 1.0

    metric("defaults")(ret)
    m = get_metric("defaults")
    assert m.units == ""
    assert m.source == "manual"
    assert m.higher_is_better is True


def test_metric_decorator_returns_metric_object() -> None:
    _fresh_registries()

    def ret() -> float:
        return 1.0

    result = metric("ret", units="", source="manual")(ret)
    assert isinstance(result, Metric)


def test_get_metric_raises_keyerror_for_unknown() -> None:
    _fresh_registries()
    with pytest.raises(KeyError):
        get_metric("absent")


def test_list_metrics_returns_all_in_order() -> None:
    _fresh_registries()

    def a() -> float:
        return 1.0

    def b() -> float:
        return 2.0

    metric("a", units="", source="x")(a)
    metric("b", units="", source="x")(b)
    metrics = list_metrics()
    assert [m.name for m in metrics] == ["a", "b"]
    assert metrics[0].value == 1.0
    assert metrics[1].value == 2.0


def test_reset_metric_registry_clears_metrics() -> None:
    _fresh_registries()

    def to_clear() -> float:
        return 0.0

    metric("to-clear", units="", source="x")(to_clear)
    assert _METRICS
    reset_metric_registry()
    assert _METRICS == {}
    assert list_metrics() == []


# ---------------------------------------------------------------------------
# registry_summary()
# ---------------------------------------------------------------------------


def test_registry_summary_keys_are_sorted_strings() -> None:
    _fresh_registries()
    _make_suite_class("alpha-suite")
    _make_suite_class("zeta-suite")

    @task("zeta", suite="alpha-suite")
    def zeta() -> None:
        return None

    @task("alpha", suite="alpha-suite")
    def alpha() -> None:
        return None

    def m() -> float:
        return 1.0

    metric("m", units="", source="x")(m)

    summary = registry_summary()
    assert set(summary.keys()) == {"suites", "tasks", "metrics"}
    assert summary["tasks"] == ["alpha", "zeta"]
    assert summary["metrics"] == ["m"]
    assert summary["suites"] == ["alpha-suite", "zeta-suite"]


def test_registry_summary_empty_after_reset() -> None:
    _fresh_registries()
    summary = registry_summary()
    assert summary == {"suites": [], "tasks": [], "metrics": []}


# ---------------------------------------------------------------------------
# Module-reference monkeypatching (constraint #1)
# ---------------------------------------------------------------------------


def test_allow_suite_overwrite_can_be_monkeypatched_via_module_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Demonstrate the constraint: use the module reference, not a string."""
    _fresh_registries()
    monkeypatch.setattr(registry, "_ALLOW_SUITE_OVERWRITE", True)
    assert registry._ALLOW_SUITE_OVERWRITE is True
    _make_suite_class("first")
    # Re-register same name now succeeds.
    replacement = _make_suite_class("first")
    assert get_suite("first") is replacement


def test_monkeypatch_metrics_dict_via_module_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace the module-level _METRICS dict via direct attribute reference."""
    _fresh_registries()
    sentinel: dict[str, Metric] = {}
    monkeypatch.setattr(registry, "_METRICS", sentinel)

    def anything() -> float:
        return 1.0

    metric("anything", units="", source="x")(anything)
    # The decorator used the monkeypatched dict (module reference).
    assert "anything" in sentinel
    # list_metrics reads _METRICS via module globals — same dict.
    assert list_metrics() == [sentinel["anything"]]
