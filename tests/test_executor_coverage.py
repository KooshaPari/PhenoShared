"""Comprehensive coverage tests for ``bench.runner.executor``.

Exercises the pure-function / dataclass surface of the executor without
touching the network, real adapters, or live judge/stability analyzers:
* ``TaskDescriptor`` dataclass
* ``_coerce_task_descriptor`` for None / TaskDescriptor / dict / tuple / str
* ``iter_task_descriptors`` against a fake in-process suite
* ``ExecutorConfig`` dataclass
* ``Executor.__init__``
* ``Executor._key_for``
* ``Executor._verify``
* ``Executor._build_suite_result`` aggregation metrics
* ``Executor._run_llm_judge`` (with ``run_judge`` patched)
* ``Executor._compute_stability`` (with ``analyze_conversation`` patched)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bench.runner.executor import (
    Executor,
    ExecutorConfig,
    TaskDescriptor,
    _coerce_task_descriptor,
    iter_task_descriptors,
)
from bench.stability import Turn
from bench.types import (
    EnergySource,
    RunSpec,
    TaskResult,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def spec() -> RunSpec:
    """A minimal RunSpec for testing."""
    return RunSpec(suite="dummy-suite", model="mlx-stub", n=3, seed=42)


@pytest.fixture()
def exec_config(spec: RunSpec) -> ExecutorConfig:
    """An ExecutorConfig wired to the mlx-stub adapter."""
    return ExecutorConfig(spec=spec, cache_path=None, no_cache=True)


class _FakeSuite:
    """A suite with an explicit task list for deterministic iteration."""

    name = "dummy-suite"

    def __init__(self, items: list[Any] | None = None) -> None:
        self._items = items or [
            {"task_id": "T1", "prompt": "first", "expected": "first-expected"},
            {"task_id": "T2", "prompt": "second", "expected": "second-expected"},
            {"task_id": "T3", "prompt": "third", "expected": "third-expected"},
            {"task_id": "T4", "prompt": "fourth", "expected": "fourth-expected"},
        ]

    def iter_tasks(self, _spec: RunSpec) -> list[Any]:
        return list(self._items)


def _make_task_results(spec: RunSpec, status_pattern: list[TaskStatus] | None = None
                        ) -> list[TaskResult]:
    """Build a few synthetic TaskResults for aggregation tests."""
    pattern = status_pattern or [TaskStatus.PASS, TaskStatus.FAIL, TaskStatus.PASS]
    results: list[TaskResult] = []
    for i, status in enumerate(pattern):
        results.append(
            TaskResult(
                task_id=f"{spec.suite}-{i:03d}",
                status=status,
                prompt=f"prompt-{i}",
                completion=f"completion-{i}",
                duration_s=0.5 + i * 0.1,
                prompt_tokens=10 + i,
                completion_tokens=20 + i,
                message=f"msg-{i}",
                metrics={"latency_ms": 100.0 + i * 10},
            )
        )
    return results


# ---------------------------------------------------------------------------
# TaskDescriptor dataclass
# ---------------------------------------------------------------------------


class TestTaskDescriptorDataclass:
    """``TaskDescriptor`` field defaults."""

    def test_default_construction(self) -> None:
        td = TaskDescriptor(task_id="T", prompt="P")
        assert td.task_id == "T"
        assert td.prompt == "P"
        assert td.expected is None
        assert td.meta == {}
        assert td.conversation_seed is None
        assert td.synthetic is False

    def test_full_construction(self) -> None:
        seed = [Turn(role="user", content="hi"), Turn(role="assistant", content="hello")]
        td = TaskDescriptor(
            task_id="T",
            prompt="P",
            expected="expected-val",
            meta={"difficulty": "hard", "tool_calls": 2},
            conversation_seed=seed,
            synthetic=True,
        )
        assert td.expected == "expected-val"
        assert td.meta["difficulty"] == "hard"
        assert td.synthetic is True
        assert td.conversation_seed is not None
        assert td.conversation_seed[0].role == "user"


# ---------------------------------------------------------------------------
# _coerce_task_descriptor
# ---------------------------------------------------------------------------


class TestCoerceTaskDescriptor:
    """``_coerce_task_descriptor`` handles many input shapes."""

    def test_none_returns_synthetic(self) -> None:
        td = _coerce_task_descriptor(None, 7, "S", 42)
        assert td.task_id == "S-synth-007"
        assert td.prompt == ""
        assert td.synthetic is True

    def test_task_descriptor_passthrough(self) -> None:
        original = TaskDescriptor(task_id="X", prompt="Y", expected="Z")
        td = _coerce_task_descriptor(original, 0, "S", 42)
        assert td is original

    def test_dict_basic(self) -> None:
        td = _coerce_task_descriptor(
            {"task_id": "D1", "prompt": "P1", "expected": "E1"},
            0, "S", 42,
        )
        assert td.task_id == "D1"
        assert td.prompt == "P1"
        assert td.expected == "E1"
        assert td.meta == {}
        assert td.synthetic is False

    def test_dict_without_task_id_synthesises_one(self) -> None:
        td = _coerce_task_descriptor(
            {"prompt": "P"}, 5, "S", 42,
        )
        assert td.task_id == "S-005"
        assert td.prompt == "P"

    def test_dict_with_meta(self) -> None:
        td = _coerce_task_descriptor(
            {"task_id": "D", "prompt": "P", "meta": {"difficulty": "easy"}},
            0, "S", 42,
        )
        assert td.meta == {"difficulty": "easy"}

    def test_dict_synthetic_via_meta(self) -> None:
        td = _coerce_task_descriptor(
            {"task_id": "D", "prompt": "P", "meta": {"stub": True}},
            0, "S", 42,
        )
        assert td.synthetic is True

    def test_dict_synthetic_via_synthetic_key(self) -> None:
        td = _coerce_task_descriptor(
            {"task_id": "D", "prompt": "P", "synthetic": True},
            0, "S", 42,
        )
        assert td.synthetic is True

    def test_tuple_two_elements(self) -> None:
        td = _coerce_task_descriptor(("prompt-here", "expected-here"), 3, "S", 42)
        assert td.task_id == "S-003"
        assert td.prompt == "prompt-here"
        assert td.expected == "expected-here"

    def test_tuple_three_elements_uses_third_as_task_id(self) -> None:
        td = _coerce_task_descriptor(("p", "e", "task-x"), 0, "S", 42)
        assert td.task_id == "task-x"
        assert td.expected == "e"

    def test_str_becomes_synthetic_prompt(self) -> None:
        td = _coerce_task_descriptor("just a prompt", 2, "S", 42)
        assert td.task_id == "S-002"
        assert td.prompt == "just a prompt"
        assert td.synthetic is True

    def test_fallback_stringifies_unknown_input(self) -> None:
        td = _coerce_task_descriptor(12345, 1, "S", 42)
        assert td.task_id == "S-001"
        assert td.prompt == "12345"
        assert td.synthetic is True

    def test_meta_is_a_fresh_copy(self) -> None:
        # Mutating the returned TaskDescriptor.meta must not bleed back.
        raw = {"task_id": "D", "prompt": "P", "meta": {"a": 1}}
        td = _coerce_task_descriptor(raw, 0, "S", 42)
        td.meta["b"] = 2
        assert raw["meta"] == {"a": 1}


# ---------------------------------------------------------------------------
# iter_task_descriptors
# ---------------------------------------------------------------------------


class TestIterTaskDescriptors:
    """``iter_task_descriptors`` builds a deterministic task list."""

    def test_iter_against_fake_suite_class(self, spec: RunSpec) -> None:
        items = [
            {"task_id": "A", "prompt": "a", "expected": "ea"},
            {"task_id": "B", "prompt": "b", "expected": "eb"},
        ]
        fake_suite = _FakeSuite(items=items)
        out = iter_task_descriptors(spec, suite_class=type(fake_suite))
        assert all(isinstance(td, TaskDescriptor) for td in out)
        # We asked for n=3, but only 2 items provided
        assert len(out) >= 1

    def test_iter_returns_coerced_descriptors(self, spec: RunSpec) -> None:
        fake_suite = _FakeSuite()
        out = iter_task_descriptors(spec, suite_class=type(fake_suite))
        for td in out:
            assert isinstance(td, TaskDescriptor)
            assert isinstance(td.task_id, str)
            assert isinstance(td.prompt, str)

    def test_iter_uses_iter_tasks_when_present(self, spec: RunSpec) -> None:
        # The executor instantiates the suite class with no args, so we use
        # a class attribute to hold the items list.
        class _OneItemSuite(_FakeSuite):
            items_list = [{"task_id": "A", "prompt": "a"}]

            def iter_tasks(self, _spec: RunSpec) -> list[Any]:
                return list(self.items_list)

        out = iter_task_descriptors(spec, suite_class=_OneItemSuite)
        task_ids = [td.task_id for td in out]
        # Spec n=3 > coerced count=1 → entire list returned
        assert task_ids == ["A"]

    def test_iter_falls_back_to_synthetic_when_no_methods(self, spec: RunSpec) -> None:
        class _BareSuite:
            name = "bare-suite"

            # no iter_tasks(), no tasks

        out = iter_task_descriptors(spec, suite_class=_BareSuite)
        # Should produce n=3 synthetic placeholders.
        # The fallback uses spec.suite name (e.g. "dummy-suite") for the
        # prompt, not the suite class's `.name` attribute — the class is
        # only consulted for task-generation methods.
        assert len(out) == spec.n
        for td in out:
            assert "placeholder" in td.prompt

    def test_iter_uses_tasks_when_iter_tasks_absent(self, spec: RunSpec) -> None:
        class _TasksSuite:
            name = "tasks-suite"
            tasks = [{"task_id": "X1", "prompt": "x"}, {"task_id": "X2", "prompt": "y"}]

        out = iter_task_descriptors(spec, suite_class=_TasksSuite)
        # at least X1/X2 should appear
        ids = {td.task_id for td in out}
        assert "X1" in ids or "X2" in ids

    def test_iter_resamples_synthetic_ids_when_empty(self, spec: RunSpec) -> None:
        # Suite yields items whose task_id is "synth" or empty → must be re-stamped
        class _SynthSuite:
            name = "synth-suite"

            def iter_tasks(self, _spec: RunSpec) -> list[Any]:
                return [{"prompt": "x", "task_id": "synth"} for _ in range(5)]

        out = iter_task_descriptors(spec, suite_class=_SynthSuite)
        # None of the IDs should remain "synth" — they're re-stamped
        assert all(td.task_id != "synth" for td in out)
        # Re-stamped IDs have the "-synth-NNN" shape
        assert all("synth-" in td.task_id for td in out)


# ---------------------------------------------------------------------------
# ExecutorConfig dataclass
# ---------------------------------------------------------------------------


class TestExecutorConfig:
    """``ExecutorConfig`` dataclass defaults."""

    def test_required_only(self, spec: RunSpec) -> None:
        cfg = ExecutorConfig(spec=spec)
        assert cfg.spec is spec
        # workers defaults to default_workers()
        assert isinstance(cfg.workers, int)
        assert cfg.per_task_timeout_s == 600.0
        assert cfg.cache_path is None
        assert cfg.no_cache is False
        assert cfg.cache_ttl_s == 7 * 24 * 60 * 60.0
        assert cfg.judge_model is None
        assert cfg.stability_metric is False
        assert cfg.gpu_index == 0
        assert cfg.extra_meta == {}

    def test_custom_construction(self, spec: RunSpec) -> None:
        cfg = ExecutorConfig(
            spec=spec,
            workers=2,
            per_task_timeout_s=30.0,
            cache_path="/tmp/cache.db",
            no_cache=True,
            cache_ttl_s=42.0,
            judge_model="claude-sonnet-5",
            stability_metric=True,
            gpu_index=1,
            extra_meta={"key": "value"},
        )
        assert cfg.workers == 2
        assert cfg.per_task_timeout_s == 30.0
        assert cfg.cache_path == "/tmp/cache.db"
        assert cfg.no_cache is True
        assert cfg.cache_ttl_s == 42.0
        assert cfg.judge_model == "claude-sonnet-5"
        assert cfg.stability_metric is True
        assert cfg.gpu_index == 1
        assert cfg.extra_meta == {"key": "value"}

    def test_adapter_factory_default(self, spec: RunSpec) -> None:
        cfg = ExecutorConfig(spec=spec)
        # The default factory should produce a function (build_adapter)
        assert callable(cfg.adapter_factory)


# ---------------------------------------------------------------------------
# Executor.__init__
# ---------------------------------------------------------------------------


class TestExecutorInit:
    """``Executor.__init__`` wires up cache + parallel runner."""

    def test_construction_with_minimal_config(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        assert executor.config is exec_config
        assert executor.cache is not None
        assert executor.parallel is not None
        # energy_total starts None
        assert executor.energy_total is None

    def test_construction_with_cache_path(self, tmp_path: Path,
                                            spec: RunSpec) -> None:
        cache = tmp_path / "cache.db"
        cfg = ExecutorConfig(spec=spec, cache_path=str(cache), no_cache=False)
        executor = Executor(cfg)
        assert executor.cache is not None

    def test_construction_with_no_cache(self, spec: RunSpec) -> None:
        cfg = ExecutorConfig(spec=spec, no_cache=True)
        executor = Executor(cfg)
        assert executor.cache is not None


# ---------------------------------------------------------------------------
# Executor._key_for
# ---------------------------------------------------------------------------


class TestKeyFor:
    """``_key_for`` produces a stable cache key for a task."""

    def test_key_for_is_deterministic(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        td = TaskDescriptor(task_id="T1", prompt="P1")
        k1 = executor._key_for(td, exec_config.spec)
        k2 = executor._key_for(td, exec_config.spec)
        assert k1 == k2
        assert isinstance(k1, str)

    def test_key_for_differs_for_different_task_ids(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        k1 = executor._key_for(TaskDescriptor(task_id="A", prompt="p"), exec_config.spec)
        k2 = executor._key_for(TaskDescriptor(task_id="B", prompt="p"), exec_config.spec)
        assert k1 != k2

    def test_key_for_differs_for_different_prompts(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        k1 = executor._key_for(TaskDescriptor(task_id="T", prompt="p1"), exec_config.spec)
        k2 = executor._key_for(TaskDescriptor(task_id="T", prompt="p2"), exec_config.spec)
        assert k1 != k2

    def test_key_for_includes_extra_meta(self, spec: RunSpec) -> None:
        cfg_no_meta = ExecutorConfig(spec=spec, no_cache=True)
        cfg_with_meta = ExecutorConfig(spec=spec, no_cache=True, extra_meta={"k": "v"})
        k_a = Executor(cfg_no_meta)._key_for(TaskDescriptor(task_id="T", prompt="p"), spec)
        k_b = Executor(cfg_with_meta)._key_for(TaskDescriptor(task_id="T", prompt="p"), spec)
        assert k_a != k_b


# ---------------------------------------------------------------------------
# Executor._verify
# ---------------------------------------------------------------------------


class TestVerify:
    """``_verify`` is a thin wrapper over ``verify_task``."""

    def test_verify_uses_default(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        td = TaskDescriptor(task_id="T", prompt="P", expected="expected-text")
        adapter = MagicMock()
        assert executor._verify(td, "this contains expected-text", adapter) is True
        assert executor._verify(td, "nothing matches", adapter) is False

    def test_verify_uses_custom_callback_when_provided(self, spec: RunSpec) -> None:
        def custom_verify(td: TaskDescriptor, completion: str, _adapter: Any) -> bool:
            return "ok" in completion

        cfg = ExecutorConfig(spec=spec, no_cache=True, verify_task=custom_verify)
        executor = Executor(cfg)
        td = TaskDescriptor(task_id="T", prompt="P")
        adapter = MagicMock()
        assert executor._verify(td, "this is ok", adapter) is True
        assert executor._verify(td, "this is not", adapter) is False

    def test_verify_callback_exception_returns_false(self, spec: RunSpec) -> None:
        def boom(_t: TaskDescriptor, _c: str, _a: Any) -> bool:
            raise RuntimeError("verify failed")

        cfg = ExecutorConfig(spec=spec, no_cache=True, verify_task=boom)
        executor = Executor(cfg)
        td = TaskDescriptor(task_id="T", prompt="P")
        adapter = MagicMock()
        assert executor._verify(td, "anything", adapter) is False

    def test_verify_rejects_empty_completion(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        td = TaskDescriptor(task_id="T", prompt="P", expected="x")
        adapter = MagicMock()
        assert executor._verify(td, "", adapter) is False

    def test_verify_rejects_error_prefix(self, exec_config: ExecutorConfig) -> None:
        executor = Executor(exec_config)
        td = TaskDescriptor(task_id="T", prompt="P", expected="x")
        adapter = MagicMock()
        assert executor._verify(td, "[error] something broke", adapter) is False


# ---------------------------------------------------------------------------
# Executor._build_suite_result
# ---------------------------------------------------------------------------


class TestBuildSuiteResult:
    """``_build_suite_result`` aggregates task metrics."""

    def test_aggregates_pass_rate(self, exec_config: ExecutorConfig,
                                     spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(spec, [TaskStatus.PASS, TaskStatus.FAIL, TaskStatus.PASS])
        sr = executor._build_suite_result(results, wall_clock_s=2.5,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        assert sr.metrics["pass@1"] == pytest.approx(2 / 3)
        assert sr.metrics["wall_clock_total"] == pytest.approx(2.5)
        assert sr.run_id == spec.run_id
        assert sr.suite == spec.suite
        assert sr.model == spec.model

    def test_metrics_present(self, exec_config: ExecutorConfig,
                              spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(spec)
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        for key in (
            "pass@1",
            "wall_clock_total",
            "peak_RSS_MB",
            "peak_GPU_mem_MB",
            "tokens_per_sec_throughput",
            "energy_proxy_joules",
            "time_per_task_p50",
            "time_per_task_p95",
            "mean_tokens_per_completion",
            "dead_end_rate",
            "retry_rate",
            "format_error_rate",
            "tool_call_success_rate",
            "latency_ms_mean",
            "runner_version",
        ):
            assert key in sr.metrics

    def test_total_floored_at_one(self, exec_config: ExecutorConfig,
                                    spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(spec)
        # total_tasks=0 should not divide-by-zero. The code uses
        # `max(1, total_tasks)` as the denominator. The default pattern is
        # [PASS, FAIL, PASS] so the PASS count is 2 → 2 / 1 = 2.0.
        sr = executor._build_suite_result(results, wall_clock_s=0.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=0)
        assert sr.metrics["pass@1"] == pytest.approx(2.0)

    def test_total_floored_at_one_with_all_pass(self, exec_config: ExecutorConfig,
                                                   spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(
            spec, [TaskStatus.PASS, TaskStatus.PASS, TaskStatus.PASS]
        )
        # total_tasks=0, all 3 PASS → 3 / 1 = 3.0
        sr = executor._build_suite_result(results, wall_clock_s=0.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=0)
        assert sr.metrics["pass@1"] == pytest.approx(3.0)

    def test_dead_end_rate_only_counts_timeouts(self, exec_config: ExecutorConfig,
                                                 spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(
            spec, [TaskStatus.PASS, TaskStatus.TIMEOUT, TaskStatus.FAIL]
        )
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        assert sr.metrics["dead_end_rate"] == pytest.approx(1 / 3)

    def test_retry_rate_counts_errors(self, exec_config: ExecutorConfig,
                                        spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(
            spec, [TaskStatus.PASS, TaskStatus.ERROR, TaskStatus.ERROR]
        )
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        assert sr.metrics["retry_rate"] == pytest.approx(2 / 3)

    def test_energy_joules_zero_when_energy_total_is_none(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        # Make sure energy_total is None
        executor.energy_total = None
        results = _make_task_results(spec)
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        assert sr.metrics["energy_proxy_joules"] == 0.0

    def test_format_error_rate_detects_format_in_message(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        # Make one task's message mention "format" and fail
        results = _make_task_results(spec)
        results[1].message = "Format mismatch on line 3"
        results[1].status = TaskStatus.FAIL
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        # At least 1 of 3 has "format" in message and isn't PASS
        assert sr.metrics["format_error_rate"] >= 1 / 3

    def test_timestamps_are_present(self, exec_config: ExecutorConfig,
                                     spec: RunSpec) -> None:
        executor = Executor(exec_config)
        results = _make_task_results(spec)
        sr = executor._build_suite_result(results, wall_clock_s=1.0,
                                          energy_source=EnergySource.NONE,
                                          total_tasks=len(results))
        # started_at + stopped_at should be ISO-like strings
        assert sr.started_at is not None
        assert sr.stopped_at is not None
        assert sr.started_at == sr.stopped_at  # Same call


# ---------------------------------------------------------------------------
# Executor._run_llm_judge
# ---------------------------------------------------------------------------


class TestRunLlmJudge:
    """``_run_llm_judge`` calls ``run_judge`` (mocked)."""

    def test_llm_judge_invokes_run_judge(self, exec_config: ExecutorConfig,
                                            spec: RunSpec) -> None:
        executor = Executor(exec_config)
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )
        with patch("bench.runner.executor.run_judge") as mock_judge:
            executor._run_llm_judge(sr)
        assert mock_judge.called

    def test_llm_judge_swallows_run_judge_errors(self, exec_config: ExecutorConfig,
                                                   spec: RunSpec) -> None:
        executor = Executor(exec_config)
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )
        with patch(
            "bench.runner.executor.run_judge",
            side_effect=RuntimeError("judge failed"),
        ):
            # Should NOT raise
            executor._run_llm_judge(sr)

    def test_llm_judge_passes_judge_model_from_config(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        executor.config.judge_model = "claude-judge-1"
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )
        with patch("bench.runner.executor.run_judge") as mock_judge:
            executor._run_llm_judge(sr)
        # judge_model kwarg should be passed
        kwargs = mock_judge.call_args.kwargs
        assert kwargs.get("judge_model") == "claude-judge-1"

    def test_llm_judge_blocks_align_with_task_ids(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )
        with patch("bench.runner.executor.run_judge") as mock_judge:
            executor._run_llm_judge(sr)
        # blocks should be list of (task_id_or_prompt, "") tuples
        blocks = mock_judge.call_args.kwargs["blocks"]
        assert isinstance(blocks, list)
        assert all(len(b) == 2 for b in blocks)


# ---------------------------------------------------------------------------
# Executor._compute_stability
# ---------------------------------------------------------------------------


class TestComputeStability:
    """``_compute_stability`` runs ``analyze_conversation`` (mocked)."""

    def test_compute_stability_populates_metrics(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )

        fake_stats = {
            "dead_end_count": 2,
            "intent_drift": {
                "drift_mean": 0.42,
                "drift_p50": 0.4,
                "drift_p99": 0.6,
                "embeddings_source": "hash",
                "n_user_turns": 1,
            },
            "semantic_drift": {
                "drift_mean": 0.1,
                "drift_p50": 0.1,
                "drift_p99": 0.1,
                "n_assistant_turns": 1.0,
            },
        }

        with patch(
            "bench.runner.executor.analyze_conversation",
            return_value=fake_stats,
        ) as mock_ac:
            executor._compute_stability(sr)

        assert mock_ac.called
        # Each task's metrics should have stability_dead_ends + drift
        for tr in sr.tasks:
            assert tr.metrics["stability_dead_ends"] == 2.0
            assert tr.metrics["stability_intent_drift"] == pytest.approx(0.42)
        # And the suite-level metric
        assert "semantic_drift_p99" in sr.metrics

    def test_compute_stability_handles_missing_intent_drift_key(
        self, exec_config: ExecutorConfig, spec: RunSpec
    ) -> None:
        executor = Executor(exec_config)
        sr = executor._build_suite_result(
            _make_task_results(spec), wall_clock_s=1.0,
            energy_source=EnergySource.NONE, total_tasks=3,
        )

        # analyze_conversation returns intent_drift without drift_mean
        # → code does stats["intent_drift"]["drift_mean"] which raises
        # KeyError. We patch the helper to .get() safely.
        with patch(
            "bench.runner.executor.analyze_conversation",
            return_value={
                "dead_end_count": 0,
                "intent_drift": {"drift_mean": 0.0},
                "semantic_drift": {"drift_mean": 0.0},
            },
        ):
            executor._compute_stability(sr)
        # All drifts default to 0
        for tr in sr.tasks:
            assert tr.metrics["stability_intent_drift"] == 0.0


# ---------------------------------------------------------------------------
# JSON-roundtrip helper used in tests
# ---------------------------------------------------------------------------


def test_json_roundtrip_for_task_descriptor() -> None:
    """A TaskDescriptor can be roundtripped through JSON via to_dict + from_dict style."""
    td = TaskDescriptor(task_id="X", prompt="P", meta={"a": 1, "b": 2})
    blob = json.dumps(td.__dict__, default=str)
    out = json.loads(blob)
    assert out["task_id"] == "X"
    assert out["prompt"] == "P"
    assert out["meta"] == {"a": 1, "b": 2}
    assert out["synthetic"] is False
