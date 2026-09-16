"""Unit tests for the bench.runner layer (spec §7 — 40+ tests).

All external APIs (Anthropic, OpenAI, MLX, nvidia-smi, powermetrics, sentence-
transformers, rich) are mocked via `unittest.mock`. Tests are hermetic and
fast: the entire suite runs in well under 30 seconds.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from bench.adapters import (
    Completion,
    HttpAnthropic,
    HttpOpenAI,
    build_adapter,
)
from bench.adapters_mock import MockModel
from bench.cache import (
    CacheEntry,
    ResponseCache,
    default_cache_path,
    make_cache_key,
    open_cache,
    temp_cache_path,
)
from bench.cache import (
    disabled as disabled_cache,
)
from bench.cli import build_parser
from bench.cli import main as cli_main
from bench.console import ProgressBar, make_console
from bench.energy import (
    EnergyReading,
    EnergySource,
    EnergyTotal,
    _NoOpSource,
    _parse_powermetrics_line,
    detect_source,
    measure,
)
from bench.executor import (
    Executor,
    RunConfig,
    _coerce_task_descriptor,
    iter_task_descriptors,
)
from bench.judge_runner import (
    JudgeBatch,
    _parse_verdicts,
    attach_verdicts,
    build_batches,
    evaluate_batch,
    run_judge,
)
from bench.mlx_stub import stub_verify_task
from bench.parallel import (
    ParallelRunner,
    TaskTimeoutError,
    default_workers,
)
from bench.perf import (
    PerfReading,
    TimedSection,
    aggregate,
    nvidia_smi_mem_mb,
    peak_rss_mb,
)
from bench.report import (
    RunReportAggregator,
    render_markdown,
    write_report,
    write_suite_result,
)
from bench.seeds import sample, shuffled_pool
from bench.stability import (
    Turn,
    _hash_embed,
    dead_end_count,
    embed_texts,
    intent_drift,
    semantic_drift_score,
)
from bench.types import (
    JudgeMode,
    RunSpec,
    SuiteResult,
    TaskResult,
    TaskStatus,
)
from tests._harness import skipif_windows

# ===========================================================================
# Model adapter (10 tests)
# ===========================================================================


class TestBuildAdapter:
    """`build_adapter()` routes prefixes to the right concrete adapter."""

    def test_mock_prefix_routes_to_mock(self):
        a = build_adapter("mock")
        assert isinstance(a, MockModel)
        assert a.name == "mock"

    def test_unknown_prefix_falls_back_to_mock(self):
        a = build_adapter("totally-bogus-model")
        assert isinstance(a, MockModel)


class TestMockModel:
    """`MockModel.generate()` is deterministic and thread-safe."""

    def test_generate_is_deterministic(self):
        a = MockModel()
        c1 = a.generate([{"role": "user", "content": "Hello world"}])
        c2 = a.generate([{"role": "user", "content": "Hello world"}])
        assert c1.text == c2.text
        assert "Hello" in c1.text
        assert c1.completion_tokens > 0
        assert a.n_calls == 2

    def test_generate_picks_echo_for_stub(self):
        a = MockModel(echo=True)
        c1 = a.generate([{"role": "user", "content": "alpha foo"}])
        c2 = a.generate([{"role": "user", "content": "beta bar"}])
        assert c1.text != c2.text


class TestHttpOpenAI:
    """`HttpOpenAI` posts to `chat/completions` and parses the response."""

    def test_openai_posts_to_base_url(self, monkeypatch):
        captured: dict = {}

        class _DummyResp:
            def __init__(self, data):
                self._data = data

            def read(self) -> bytes:
                return json.dumps(self._data).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["headers"] = dict(req.headers)
            return _DummyResp(
                {
                    "id": "openai-1",
                    "choices": [
                        {
                            "message": {"content": "stub openai reply"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 7},
                }
            )

        monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
        adapter = HttpOpenAI(model="qwen-0.8b", base_url="http://localhost:8000")
        comp = adapter.generate([{"role": "user", "content": "Hello world"}])
        assert comp.text == "stub openai reply"
        assert comp.prompt_tokens == 5
        assert comp.completion_tokens == 7
        assert captured["url"].endswith("/v1/chat/completions")
        assert captured["body"]["model"] == "qwen-0.8b"


class TestHttpAnthropic:
    """Anthropic adapter uses HTTP; mocking urllib covers all calls."""

    def test_anthropic_generate_uses_messages_endpoint(self, monkeypatch):
        mock_resp_data = {
            "id": "msg_1",
            "content": [{"type": "text", "text": "hello world"}],
            "usage": {"input_tokens": 11, "output_tokens": 22},
            "stop_reason": "end_turn",
            "model": "claude-sonnet-5",
        }

        class _DummyResp:
            def __init__(self, data):
                self._data = data

            def read(self) -> bytes:
                return json.dumps(self._data).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(req, timeout=None):
            return _DummyResp(mock_resp_data)

        monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
        adapter = HttpAnthropic(model="claude-sonnet-5", api_key="sk-test")
        comp = adapter.generate([{"role": "user", "content": "Hi"}])
        assert comp.text == "hello world"
        assert comp.prompt_tokens == 11
        assert comp.completion_tokens == 22


# ===========================================================================
# Parallel (5 tests)
# ===========================================================================


class TestParallel:
    def test_default_workers(self, monkeypatch):
        monkeypatch.setattr("os.cpu_count", lambda: 4)
        assert default_workers() == 4
        monkeypatch.setattr("os.cpu_count", lambda: 64)
        assert default_workers() == 8
        monkeypatch.setattr("os.cpu_count", lambda: 1)
        assert default_workers() == 1

    def test_run_fires_concurrently(self):
        async def go():
            pr = ParallelRunner(workers=4, per_task_timeout_s=10.0)
            t0 = time.monotonic()

            async def slow(item):
                await asyncio.sleep(0.1)
                return item * 2

            results, stats = await pr.run([1, 2, 3, 4], slow)
            return results, stats, time.monotonic() - t0

        results, stats, took = asyncio.run(go())
        assert results == [2, 4, 6, 8]
        assert stats.completed == 4
        # 4 tasks of ~0.1s concurrently → well under 0.35s.
        assert took < 0.35, f"expected concurrency, took {took:.3f}s"

    def test_run_enforces_per_task_timeout(self):
        async def go():
            pr = ParallelRunner(workers=2, per_task_timeout_s=0.05)

            async def slow(item):
                await asyncio.sleep(1.0)
                return item

            results, stats = await pr.run([1, 2, 3], slow)
            return results, stats

        results, stats = asyncio.run(go())
        assert stats.timed_out == 3
        for r in results:
            assert isinstance(r, TaskTimeoutError)

    def test_run_surfaces_exception(self):
        async def go():
            pr = ParallelRunner(workers=2, per_task_timeout_s=2.0)

            async def maybe_fail(item):
                if item == "bad":
                    raise ValueError("nope")
                return item

            results, stats = await pr.run(["ok", "bad"], maybe_fail)
            return results, stats

        results, stats = asyncio.run(go())
        assert stats.completed == 1
        assert stats.failed == 1
        assert results[0] == "ok"
        assert isinstance(results[1], ValueError)

    def test_run_sync_runs_in_threadpool(self):
        import threading

        seen_threads = set()

        def worker(item):
            seen_threads.add(threading.current_thread().name)
            time.sleep(0.05)
            return item * 10

        async def go():
            pr = ParallelRunner(workers=3, per_task_timeout_s=5.0)
            results = await pr.run_sync([1, 2, 3, 4], worker)
            return results

        results = asyncio.run(go())
        assert sorted(results) == [10, 20, 30, 40]
        # All work happened on the bench-runner-sync pool threads.
        assert any(t.startswith("bench-runner-sync") for t in seen_threads)


# ===========================================================================
# Cache (7 tests)
# ===========================================================================


class TestCache:
    def test_make_cache_key_is_stable(self):
        k1 = make_cache_key(
            suite="ifeval",
            task_id="t1",
            model="mlx-stub",
            prompt="hello",
            temperature=0.0,
        )
        k2 = make_cache_key(
            suite="ifeval",
            task_id="t1",
            model="mlx-stub",
            prompt="hello",
            temperature=0.0,
        )
        assert k1 == k2
        assert len(k1) == 32

    def test_make_cache_key_varies_on_inputs(self):
        base = {
            "suite": "ifeval",
            "task_id": "t1",
            "model": "mlx-stub",
            "prompt": "hello",
            "temperature": 0.0,
        }
        k = make_cache_key(**base)
        for variant in (
            dict(base, suite="mt-bench"),
            dict(base, task_id="t2"),
            dict(base, model="claude-sonnet-5"),
            dict(base, prompt="goodbye"),
            dict(base, temperature=0.5),
            dict(base, extra={"judge": 1}),
        ):
            assert make_cache_key(**variant) != k, f"collision for {variant}"

    def test_cache_get_put_roundtrip(self, tmp_path):
        with open_cache(str(tmp_path / "c.sqlite3")) as c:
            c.put(
                key="abc",
                suite="ifeval",
                task_id="t1",
                model="mlx-stub",
                temperature=0.0,
                value={"text": "hi", "tokens": 3},
                now=1000.0,
                ttl_s=60,
            )
            hit = c.get("abc", now=1010.0)
            assert isinstance(hit, CacheEntry)
            assert hit.value["text"] == "hi"
            assert hit.is_fresh(1010.0)

    def test_cache_ttl_expiry(self, tmp_path):
        with open_cache(str(tmp_path / "c2.sqlite3")) as c:
            c.put(
                key="xyz",
                suite="ifeval",
                task_id="t1",
                model="mlx-stub",
                temperature=0.0,
                value={"text": "hi"},
                now=1000.0,
                ttl_s=10,
            )
            assert c.get("xyz", now=1005.0) is not None
            assert c.get("xyz", now=1015.0) is None

    def test_cache_invalidate_and_clear(self, tmp_path):
        with open_cache(str(tmp_path / "c3.sqlite3")) as c:
            c.put(
                key="a",
                suite="s",
                task_id="t",
                model="m",
                temperature=0.0,
                value={"v": 1},
                now=time.time(),
                ttl_s=10,
            )
            c.put(
                key="b",
                suite="s",
                task_id="t",
                model="m",
                temperature=0.0,
                value={"v": 2},
                now=time.time(),
                ttl_s=10,
            )
            assert c.invalidate("a") == 1
            assert c.invalidate("a") == 0
            assert c.get("a") is None
            assert c.get("b") is not None
            assert c.clear() == 1
            assert c.stats()["rows"] == 0

    def test_disabled_cache_returns_none(self):
        c = disabled_cache()
        c.put(
            key="x", suite="s", task_id="t", model="m", temperature=0.0, value={"a": 1}
        )
        assert c.get("x") is None
        assert c.stats()["path"] == "disabled"

    def test_default_cache_path_uses_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        path = default_cache_path()
        assert path.startswith(str(tmp_path))
        assert path.endswith(".sqlite3")
        # Ensure directory parent is touched (the cache itself creates).
        with open_cache(path) as c:
            c.put(
                key="xdg",
                suite="s",
                task_id="t",
                model="m",
                temperature=0.0,
                value={"v": 1},
                now=time.time(),
                ttl_s=10,
            )
            assert c.get("xdg") is not None


# ===========================================================================
# Seeds (5 tests)
# ===========================================================================


class TestSeeds:
    def test_sample_full_returns_all(self):
        s = sample("ifeval", seed=1, count=5, n=5)
        assert s.ordered_indices == [0, 1, 2, 3, 4]

    def test_sample_empty_returns_empty(self):
        s = sample("ifeval", seed=1, count=5, n=0)
        assert s.ordered_indices == []
        assert len(s) == 0

    def test_sample_is_deterministic(self):
        a = sample("ifeval", seed=42, count=100, n=10)
        b = sample("ifeval", seed=42, count=100, n=10)
        assert a.ordered_indices == b.ordered_indices

    def test_sample_differs_with_seed(self):
        a = sample("ifeval", seed=42, count=100, n=10)
        b = sample("ifeval", seed=43, count=100, n=10)
        assert a.ordered_indices != b.ordered_indices

    def test_sample_with_pool_returns_task_ids(self):
        pool = ["alpha", "beta", "gamma", "delta", "epsilon"]
        s = sample("ifeval", seed=42, pool=pool, n=3)
        assert s.task_ids is not None
        assert len(s.task_ids) == 3
        assert all(t in pool for t in s.task_ids)

    def test_shuffled_pool_deterministic(self):
        pool = list(range(10))
        a = shuffled_pool(pool, "ifeval", seed=42)
        b = shuffled_pool(pool, "ifeval", seed=42)
        assert a == b


# ===========================================================================
# Energy (4 tests)
# ===========================================================================


class TestEnergy:
    def test_parse_powermetrics_sums_power(self):
        line = b"CPU Power: 1234 mW\nGPU Power: 8000 mW\nANE Power: 500 mW\n"
        watts = _parse_powermetrics_line(line) / 1000.0
        assert watts == pytest.approx((1234 + 8000 + 500) / 1000.0)

    def test_noop_source_returns_zero(self):
        src = _NoOpSource()
        total = src.stop()
        assert isinstance(total, EnergyTotal)
        assert total.joules == 0.0
        assert total.source == EnergySource.NONE

    def test_detect_source_with_no_binaries(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("platform.system", lambda: "Linux")
        assert detect_source() == EnergySource.NONE

    def test_detect_source_prefers_powermetrics_on_darwin(self, monkeypatch):
        calls = {"count": 0}

        def which(name: str):
            calls["count"] += 1
            if name == "powermetrics":
                return "/usr/bin/powermetrics"
            if name == "nvidia-smi":
                return "/usr/bin/nvidia-smi"
            return None

        monkeypatch.setattr("shutil.which", which)
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        src = detect_source()
        assert src == EnergySource.POWERMETRICS

    def test_measure_contextmanager_yields_total(self):
        with measure(EnergySource.NONE) as total_holder:
            time.sleep(0.01)
        assert total_holder.total is not None
        assert total_holder.total.joules >= 0.0


# ===========================================================================
# Perf (4 tests)
# ===========================================================================


class TestPerf:
    @skipif_windows
    def test_peak_rss_mb_positive(self):
        v = peak_rss_mb()
        assert v >= 0.0
        # If we got back 0 (very weird host) accept it; otherwise it's small.
        assert v < 1024.0 * 4.0  # sanity

    def test_nvidia_smi_mem_mb_with_no_binary(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        assert nvidia_smi_mem_mb(0) == 0.0

    def test_aggregate_perf_readings(self):
        rs = [
            PerfReading(
                task_id="t1",
                peak_rss_mb=10,
                peak_gpu_mem_mb=5,
                prompt_tokens=4,
                completion_tokens=8,
                duration_s=0.5,
            ),
            PerfReading(
                task_id="t2",
                peak_rss_mb=20,
                peak_gpu_mem_mb=15,
                prompt_tokens=4,
                completion_tokens=8,
                duration_s=0.5,
            ),
        ]
        agg = aggregate(rs, wall_clock_s=1.0)
        assert agg.peak_rss_mb == 20.0
        assert agg.peak_gpu_mem_mb == 15.0
        assert agg.total_completion_tokens == 16
        # 16 tokens / 1.0s wall = 16 tok/s
        assert agg.throughput_tok_per_s == pytest.approx(16.0)

    @skipif_windows
    def test_timed_section_records_duration(self):
        with TimedSection(task_id="t") as ts:
            time.sleep(0.01)
        assert ts.duration_s > 0.0
        r = ts.to_reading(prompt_tokens=2, completion_tokens=4)
        assert r.tokens_per_sec > 0.0


# ===========================================================================
# Stability (5 tests)
# ===========================================================================


class TestStability:
    def test_hash_embed_deterministic(self):
        a = _hash_embed("hello world")
        b = _hash_embed("hello world")
        assert a == b
        assert len(a) == 64

    def test_hash_embed_dimension_different(self):
        # Smoke-check default dim doesn't crash (return value not asserted).
        _hash_embed("hello")
        assert _hash_embed("hello", dim=128).__len__() == 128

    def test_dead_end_count_detects_repeats(self):
        conv = [
            Turn("user", "do thing"),
            Turn("assistant", "I am doing thing for you"),  # unique enough
            Turn("assistant", "I am doing thing for you"),  # repeat
            Turn("assistant", "I am doing thing for you"),  # repeat
            Turn("assistant", "different answer"),
        ]
        assert dead_end_count(conv, max_repeats=3) >= 1

    def test_intent_drift_zero_for_trivial(self):
        result = intent_drift([Turn("user", "hi"), Turn("assistant", "hi")])
        assert result["drift_mean"] == 0.0
        assert result["n_user_turns"] == 1

    def test_semantic_drift_returns_metrics(self):
        result = semantic_drift_score(
            [
                Turn("user", "x"),
                Turn("assistant", "y"),
                Turn("user", "z"),
                Turn("assistant", "w"),
            ]
        )
        assert "drift_mean" in result
        assert "drift_p99" in result

    def test_embed_texts_fallback_path(self, monkeypatch):
        # Force the fallback by failing the sentence_transformers import.
        # We must capture the original `__import__` BEFORE monkeypatching,
        # otherwise `_builtins.__import__` resolves to the patched function.
        import builtins as _builtins

        _orig_import = _builtins.__import__

        def _blocked(name, *args, **kwargs):
            if name == "sentence_transformers" or name.startswith(
                "sentence_transformers."
            ):
                raise ImportError("blocked")
            return _orig_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _blocked)
        vecs = embed_texts(["a", "b", "c"])
        assert len(vecs) == 3
        for v in vecs:
            assert len(v) == 64


# ===========================================================================
# Console (3 tests)
# ===========================================================================


class TestConsole:
    def test_make_console_forces_plain(self, capsys):
        c = make_console(force_plain=True)
        c.info("hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_progress_bar_advance(self):
        with ProgressBar(total=10, description="t") as bar:
            for _ in range(5):
                bar.advance(1)
            bar.update(completed=10)

    def test_make_console_no_rich(self, monkeypatch):
        import bench.console as console_mod

        monkeypatch.setattr(console_mod, "_HAS_RICH", False)
        c = make_console(force_plain=True)
        assert c.has_rich is False
        c.warn("warn")
        c.error("error")


# ===========================================================================
# Judge (6 tests)
# ===========================================================================


class TestJudge:
    def test_build_batches(self):
        blocks = [(f"p{i}", f"a{i}") for i in range(20)]
        ids = [f"t{i}" for i in range(20)]
        batches = build_batches(blocks, ids, batch_size=8)
        assert len(batches) == 3
        assert [len(b.task_ids) for b in batches] == [8, 8, 4]

    def test_parse_verdicts_json_array(self):
        raw = json.dumps(
            [
                {"i": 0, "verdict": "PASS", "score": 0.9, "reasoning": "ok"},
                {"i": 1, "verdict": "FAIL", "score": 0.1, "reasoning": "bad"},
            ]
        )
        out = _parse_verdicts(raw, expected=2)
        assert out[0]["verdict"] == "PASS"
        assert out[1]["verdict"] == "FAIL"

    def test_parse_verdicts_markdown_fenced(self):
        raw = (
            "```json\n"
            + json.dumps([{"i": 0, "verdict": "PASS", "score": 1.0}])
            + "\n```"
        )
        out = _parse_verdicts(raw, expected=1)
        assert out and out[0]["verdict"] == "PASS"

    def test_parse_verdicts_window_regex_fallback(self):
        raw = (
            '[0]\nblah\n"verdict": "PASS", "score": 0.5\n\n'
            '[1]\nblah\n"verdict": "FAIL", "score": 0.2\n'
        )
        out = _parse_verdicts(raw, expected=2)
        assert {o["verdict"] for o in out} == {"PASS", "FAIL"}

    def test_run_judge_deterministic_is_noop(self):
        results = [
            TaskResult(task_id="t1", status=TaskStatus.PASS, duration_s=0.1, reward=1.0)
        ]
        out = run_judge(
            results, blocks=[("p", "a")], judge_mode=JudgeMode.DETERMINISTIC
        )
        assert out.judge_mode == JudgeMode.DETERMINISTIC
        assert out.verdicts == []
        # Status unchanged.
        assert results[0].status == TaskStatus.PASS

    def test_evaluate_batch_with_completion_fn(self):
        # Stub the completion without touching the SDK.
        def fake(prompt: str) -> Completion:
            return Completion(
                text=json.dumps(
                    [
                        {"i": 0, "verdict": "PASS", "score": 0.8, "reasoning": "fine"},
                        {"i": 1, "verdict": "FAIL", "score": 0.2, "reasoning": "no"},
                    ]
                ),
                prompt_tokens=4,
                completion_tokens=20,
            )

        batch = JudgeBatch(
            batch_idx=0,
            task_ids=["t0", "t1"],
            prompts=["p0\nANSWER: a0", "p1\nANSWER: a1"],
        )
        evaluate_batch(batch, completion_fn=fake)
        assert batch.verdict is not None
        per_task = batch._per_task_verdicts
        assert per_task[0].task_id == "t0"
        assert per_task[1].verdict == "FAIL"

    def test_attach_verdicts_overrides_fail_to_pass(self):
        results = [
            TaskResult(task_id="t0", status=TaskStatus.FAIL, duration_s=0.0, reward=0.0)
        ]
        batch = JudgeBatch(batch_idx=0, task_ids=["t0"], prompts=["p"])
        evaluate_batch(
            batch,
            completion_fn=lambda prompt: Completion(
                text=json.dumps(
                    [
                        {"i": 0, "verdict": "PASS", "score": 1.0, "reasoning": "ok"},
                    ]
                )
            ),
        )
        attach_verdicts([batch], results)
        assert results[0].status == TaskStatus.PASS
        assert results[0].reward == 1.0


# ===========================================================================
# Report (4 tests)
# ===========================================================================


class TestReport:
    def _mk_suite_result(
        self, suite: str = "ifeval", model: str = "mlx-stub"
    ) -> SuiteResult:
        return SuiteResult(
            run_id="r1",
            suite=suite,
            model=model,
            started_at="2026-07-16T00:00:00Z",
            stopped_at="2026-07-16T00:00:01Z",
            tasks=[
                TaskResult(
                    task_id=f"t{i}",
                    status=TaskStatus.PASS if i % 2 else TaskStatus.FAIL,
                    duration_s=0.1 * i,
                    prompt_tokens=10,
                    completion_tokens=20,
                    reward=1.0 if i % 2 else 0.0,
                    message="ok",
                )
                for i in range(1, 4)
            ],
            metrics={"pass@1": 0.66, "wall_clock_total": 0.6},
        )

    def test_aggregator_round_trip(self):
        agg = RunReportAggregator(
            run_id="r1",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NVIDIA_SMI,
        )
        agg.add(self._mk_suite_result())
        agg.set_extra("host", "test-host")
        # Smoke-check report rendering (return value not asserted).
        agg.to_run_report()
        d = agg.to_dict()
        assert d["runner_metadata"]["host"] == "test-host"
        assert d["results"][0]["suite"] == "ifeval"

    def test_render_markdown_includes_table(self):
        agg = RunReportAggregator(
            run_id="r1",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NVIDIA_SMI,
        )
        agg.add(self._mk_suite_result())
        agg.add(self._mk_suite_result(suite="mt-bench", model="claude-sonnet-5"))
        rep = agg.to_run_report()
        text = render_markdown(rep)
        assert "ifeval" in text
        assert "mt-bench" in text
        assert "mlx-stub" in text
        assert "claude-sonnet-5" in text
        # The metrics columns must be present.
        assert "pass@1" in text
        assert "wall_clock_total" in text

    def test_write_report_writes_both_files(self, tmp_path):
        agg = RunReportAggregator(
            run_id="r2",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NVIDIA_SMI,
        )
        agg.add(self._mk_suite_result())
        rep = agg.to_run_report()
        files = write_report(rep, tmp_path, aggregator=agg)
        assert Path(files["json"]).exists()
        assert Path(files["md"]).exists()
        # Spot-check the JSON is parseable.
        payload = json.loads(Path(files["json"]).read_text())
        assert payload["run_id"] == "r2"
        # Spot-check the MD body contains the table.
        body = Path(files["md"]).read_text()
        assert "| suite |" in body

    def test_write_suite_result(self, tmp_path):
        res = self._mk_suite_result()
        files = write_suite_result(res, tmp_path, filename_base="smoke")
        assert Path(files["json"]).exists()
        assert Path(files["md"]).exists()
        md = Path(files["md"]).read_text()
        assert "t1" in md
        # Status enum wire value is ok/wrong; markdown may render OK/WRONG or PASS/FAIL.
        assert any(tok in md for tok in ("PASS", "FAIL", "OK", "WRONG", "ok", "wrong"))


# ===========================================================================
# Executor (3 tests)
# ===========================================================================


class TestExecutor:
    def test_iter_task_descriptors_uses_seeds(self):
        spec = RunSpec(
            suite="ifeval",
            n=3,
            seed=42,
            model="mlx-stub",
            judge_model="claude-sonnet-5",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NONE,
            output="/tmp/x.json",  # nosec B108 — test fixture; ephemeral /tmp path
            run_id="r1",
        )

        # Use a sentinel suite class so we don't depend on a registered suite.
        class FakeSuite:
            name = "ifeval"
            source_url = ""
            format = "test"

            def iter_tasks(self, run_spec):
                for i in range(10):
                    yield {
                        "task_id": f"task-{i:03d}",
                        "prompt": f"prompt {i}",
                    }

        ts = iter_task_descriptors(spec, suite_class=FakeSuite)
        assert len(ts) == 3
        # Deterministic
        ts2 = iter_task_descriptors(spec, suite_class=FakeSuite)
        assert [t.task_id for t in ts] == [t.task_id for t in ts2]

    def test_executor_runs_end_to_end_with_stub(self, tmp_path, monkeypatch):
        # Patch the suite registry to inject a synthetic suite.
        from bench.registry import Suite

        class _Reg(Suite):
            name = "deep-swe-exec-test"
            source_url = "test://fake"
            format = "test"
            subset = "n=3"

            def iter_tasks(self, run_spec):
                for i in range(5):
                    yield {
                        "task_id": f"deep-swe-{i:03d}",
                        "prompt": f"fix this bug #{i}",
                    }

        spec = RunSpec(
            suite="deep-swe-exec-test",
            n=3,
            seed=42,
            model="mlx-stub",
            judge_model="claude-sonnet-5",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NONE,
            output=str(tmp_path / "x.json"),
            run_id="r1",
        )
        cfg = RunConfig(
            spec=spec,
            workers=2,
            per_task_timeout_s=10.0,
            no_cache=True,
            gpu_index=0,
            # Stub always emits non-empty text → PASS. Opt in to the lenient
            # verify path because this synthetic suite has no `expected`.
            verify_task=stub_verify_task,
        )
        result = asyncio.run(Executor(cfg).run())
        assert isinstance(result, SuiteResult)
        assert result.suite == "deep-swe-exec-test"
        assert len(result.tasks) == 3
        for t in result.tasks:
            assert t.duration_s > 0.0
            assert t.prompt_tokens >= 1
            # Stub always emits non-empty text → PASS
            assert t.status == TaskStatus.PASS
        # Spec §4 metrics must be present.
        for m in (
            "pass@1",
            "wall_clock_total",
            "peak_RSS_MB",
            "peak_GPU_mem_MB",
            "tokens_per_sec_throughput",
            "energy_proxy_joules",
            "time_per_task_p50",
            "dead_end_rate",
            "retry_rate",
        ):
            assert m in result.metrics, f"missing metric: {m}"

    def test_executor_uses_cache_for_second_run(self, tmp_path):
        from bench.registry import Suite

        class _Reg(Suite):
            name = "ifeval-cache-test"
            source_url = "test://fake"
            format = "test"

            def iter_tasks(self, run_spec):
                for i in range(3):
                    yield {
                        "task_id": f"ifeval-{i:03d}",
                        "prompt": f"prompt {i}",
                    }

        spec = RunSpec(
            suite="ifeval-cache-test",
            n=3,
            seed=42,
            model="mlx-stub",
            judge_model="claude-sonnet-5",
            judge_mode=JudgeMode.DETERMINISTIC,
            energy_source=EnergySource.NONE,
            output=str(tmp_path),
            run_id="r-cache",
        )
        cache_path = str(tmp_path / "bench-cache.sqlite3")
        cfg1 = RunConfig(
            spec=spec,
            workers=2,
            per_task_timeout_s=10.0,
            cache_path=cache_path,
            no_cache=False,
            gpu_index=0,
        )
        # First run warms the cache (return value not asserted).
        asyncio.run(Executor(cfg1).run())
        # All tasks were first run; cache is now warm.

        stats = ResponseCache(path=cache_path).stats()
        assert stats["rows"] == 3
        # Second run: same path → all hits.
        cfg2 = RunConfig(
            spec=spec,
            workers=2,
            per_task_timeout_s=10.0,
            cache_path=cache_path,
            no_cache=False,
            gpu_index=0,
        )
        r2 = asyncio.run(Executor(cfg2).run())
        for t in r2.tasks:
            assert t.metrics.get("from_cache") == 1.0


# ===========================================================================
# CLI + main (3 tests)
# ===========================================================================


class TestCLI:
    def test_cli_help_runs_cleanly(self):
        with pytest.raises(SystemExit) as exc:
            cli_main(["--help"])
        assert exc.value.code == 0

    def test_cli_rejects_unknown_suite(self):
        # Unknown suite names fail at registry lookup (not argparse choices).
        with pytest.raises(KeyError):
            cli_main(
                [
                    "run-dry",
                    "--suite",
                    "totally-bogus-suite-xyz",
                    "--n",
                    "3",
                    "--model",
                    "mock",
                ]
            )

    def test_build_parser_default_command(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None
        # Flat CLI only sets ``func`` on subcommands; bare parse has no func.
        assert getattr(args, "func", None) is None

    def test_no_command_prints_help(self, capsys):
        rc = cli_main([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "usage:" in out.lower() or "{run}" in out


# ===========================================================================
# Misc helpers / smoke
# ===========================================================================


class TestMisc:
    def test_coerce_task_descriptor(self):
        td = _coerce_task_descriptor(
            {"task_id": "x", "prompt": "P", "expected": "E"},
            index=0,
            suite_name="ifeval",
            seed=42,
        )
        assert td.task_id == "x"
        assert td.prompt == "P"

    def test_coerce_task_descriptor_string_fallback(self):
        td = _coerce_task_descriptor("hello", index=7, suite_name="ifeval", seed=42)
        assert td.prompt == "hello"
        assert td.task_id.endswith("-007")

    def test_default_cache_path_returns_string(self):
        path = default_cache_path()
        assert isinstance(path, str)
        assert path.endswith(".sqlite3")

    def test_temp_cache_path_unique(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        a = temp_cache_path()
        b = temp_cache_path()
        assert a != b

    def test_energy_reading_to_dict(self):
        r = EnergyReading(timestamp=1.0, watts=12.5, joules=3.0)
        d = r.to_dict()
        assert d == {"timestamp": 1.0, "watts": 12.5, "joules": 3.0}

    def test_completion_to_dict_roundtrip(self):
        c = Completion(
            text="hi",
            prompt_tokens=1,
            completion_tokens=2,
            latency_ms=3.5,
            extra={"x": 1},
        )
        d = c.to_dict()
        assert json.loads(json.dumps(d)) == d


# ===========================================================================
# MLXStubAdapter (3 tests, WBS Phase 6 tasks 88-90)
# ===========================================================================


class TestMLXStub:
    """`bench.mlx_stub.MLXStubAdapter` is the deterministic test adapter."""

    def test_mlx_stub_load(self):
        """``bench.mlx_stub`` is importable; MLXStubAdapter registers under 'mlx-stub'."""
        from bench.adapters import _get_registry
        from bench.mlx_stub import MLXStubAdapter

        registry = _get_registry()
        assert registry.get("mlx-stub") is MLXStubAdapter
        assert MLXStubAdapter.name == "mlx-stub"
        # verify_task is a staticmethod wrapping stub_verify_task.
        assert MLXStubAdapter.verify_task is not None
        assert MLXStubAdapter.verify_task(None, "good response", None) is True
        assert MLXStubAdapter.verify_task(None, "", None) is False

    def test_mlx_stub_generate(self):
        """generate() echoes the last user message with deterministic hash."""
        from bench.mlx_stub import MLXStubAdapter

        adapter = MLXStubAdapter(seed=0)
        messages = [{"role": "user", "content": "hello"}]
        response = adapter.generate(messages)
        assert response.text == "hello"
        assert response.finish_reason == "stop"
        assert response.raw["adapter_kind"] == "mlx-stub"
        assert response.raw["n"] == 1
        # Second call increments n_calls.
        response2 = adapter.generate(messages)
        assert response2.raw["n"] == 2
        # Echo off produces hash-prefixed text.
        adapter.echo = False
        response3 = adapter.generate(messages)
        assert response3.text.startswith("mlx-stub:")
        assert len(response3.text) == len("mlx-stub:") + 8

    def test_mlx_stub_handles_timeout(self):
        """generate() returns an error ModelResponse when fail_rate fires."""
        from bench.mlx_stub import MLXStubAdapter

        # fail_rate=1.0 guarantees the failure branch fires every call.
        adapter = MLXStubAdapter(fail_rate=1.0)
        messages = [{"role": "user", "content": "anything"}]
        response = adapter.generate(messages)
        assert response.finish_reason == "error"
        assert "mlx-stub" in (response.error or "")
        # The verify_task should reject the [error] sentinel prefix.
        from bench.mlx_stub import stub_verify_task

        assert not stub_verify_task(None, "[error] simulated failure", adapter)
        # Empty completion also fails.
        assert not stub_verify_task(None, "", adapter)
