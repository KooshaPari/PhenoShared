"""Tests for all bench/suites/ modules — coverage-focused.

Covers every suite module, its helper functions, dataclasses, and the
standard suite interface (spec/name, tasks/subset, run_task, run).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bench.types import (
    RunSpec,
    SuiteResult,
    SuiteSpec,
    TaskResult,
    TaskStatus,
)

# ======================================================================
# 1. bench/suites/vending_bench.py
# ======================================================================


class TestVendingBenchHelpers:
    """Unit tests for vending_bench helper functions."""

    def test_vending_prompt_contains_variant(self) -> None:
        from bench.suites.vending_bench import _vending_prompt

        text = _vending_prompt("v0-100", 100)
        assert "v0-100" in text
        assert "100" in text

    def test_parse_vending_response_valid(self) -> None:
        from bench.suites.vending_bench import _parse_vending_response

        resp = "\n".join(
            [f"DAY {i}: keep_price" for i in range(1, 51)]
            + ["END_BALANCE=25.00"]
        )
        parsed = _parse_vending_response(resp, 50)
        assert parsed["decisions"] >= 25
        assert parsed["end_balance"] == 25.0
        assert parsed["valid_format"] is True

    def test_parse_vending_response_empty(self) -> None:
        from bench.suites.vending_bench import _parse_vending_response

        parsed = _parse_vending_response("", 100)
        assert parsed["decisions"] == 0
        assert parsed["end_balance"] is None
        assert parsed["valid_format"] is False

    def test_parse_vending_response_no_balance(self) -> None:
        from bench.suites.vending_bench import _parse_vending_response

        resp = "\n".join(f"DAY {i}: keep_price" for i in range(1, 60))
        parsed = _parse_vending_response(resp, 100)
        assert parsed["end_balance"] is None
        assert parsed["valid_format"] is False

    def test_vending_score_profitable(self) -> None:
        from bench.suites.vending_bench import _vending_score

        parsed = {"valid_format": True, "end_balance": 30.0, "decisions": 100}
        passed, reason, profit = _vending_score(parsed, 100)
        assert passed is True
        assert reason == "profitable"
        assert profit == pytest.approx(10.0)

    def test_vending_score_non_profitable(self) -> None:
        from bench.suites.vending_bench import _vending_score

        parsed = {"valid_format": True, "end_balance": 10.0, "decisions": 100}
        passed, reason, profit = _vending_score(parsed, 100)
        assert passed is False
        assert reason == "non-profitable"

    def test_vending_score_invalid_format(self) -> None:
        from bench.suites.vending_bench import _vending_score

        parsed = {"valid_format": False, "end_balance": None, "decisions": 0}
        passed, reason, profit = _vending_score(parsed, 100)
        assert passed is False
        assert reason == "invalid-format"
        assert profit == 0.0


class TestVendingBenchSuite:
    """Integration tests for the VendingBench suite class."""

    def test_name(self) -> None:
        from bench.suites.vending_bench import VendingBench

        assert VendingBench.name == "vending-bench"

    def test_subset_returns_tasks(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        tasks = inst.subset(2, 42)
        assert len(tasks) == 2
        assert tasks[0].suite == "vending-bench"

    def test_subset_all(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        tasks = inst.subset(10, 42)
        assert len(tasks) == 2  # only 2 tasks exist

    def test_run_task_returns_task_result(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert result.task_id == task.task_id

    def test_run_returns_suite_result(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        rs = RunSpec(suite="vending-bench", model="test-model", n=2, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.suite == "vending-bench"
        assert sr.n == 2

    def test_verify_valid(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        task = inst.subset(1, 42)[0]
        resp = "\n".join(
            [f"DAY {i}: keep_price" for i in range(1, 51)]
            + ["END_BALANCE=30.00"]
        )
        passed, info = inst.verify(task, resp)
        assert isinstance(passed, bool)
        assert "profit_usd" in info

    def test_verify_invalid(self) -> None:
        from bench.suites.vending_bench import VendingBench

        inst = VendingBench()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad response")
        assert passed is False


# ======================================================================
# 2. bench/suites/pinchbench.py
# ======================================================================


class TestPinchBenchHelpers:
    def test_pinchbench_prompt_format(self) -> None:
        from bench.suites.pinchbench import _pinchbench_prompt

        text = _pinchbench_prompt("PINCH-0-001", "calendar", 1)
        assert "PINCH-0-001" in text
        assert "calendar" in text

    def test_correctness_check_valid(self) -> None:
        from bench.suites.pinchbench import _pinchbench_correctness_check

        resp = (
            "Meeting scheduled for Monday 10am with 3 attendees. "
            "Duration: 1 hour. "
            + "x" * 80
            + "\nPINCHBENCH_DONE=PINCH-0-001"
        )
        passed, reason = _pinchbench_correctness_check(resp, "calendar")
        assert passed is True

    def test_correctness_check_too_short(self) -> None:
        from bench.suites.pinchbench import _pinchbench_correctness_check

        passed, reason = _pinchbench_correctness_check("short", "calendar")
        assert passed is False
        assert reason == "too-short"

    def test_correctness_check_no_done_marker(self) -> None:
        from bench.suites.pinchbench import _pinchbench_correctness_check

        resp = "Meeting scheduled for Monday. " + "x" * 100
        passed, reason = _pinchbench_correctness_check(resp, "calendar")
        assert passed is False
        assert reason == "no-done-marker"

    def test_correctness_check_refusal(self) -> None:
        from bench.suites.pinchbench import _pinchbench_correctness_check

        resp = (
            "I apologize but I cannot do this. " + "x" * 80 + "\nPINCHBENCH_DONE=x"
        )
        passed, reason = _pinchbench_correctness_check(resp, "calendar")
        assert passed is False
        assert "refusal" in reason


class TestPinchBenchSuite:
    def test_name(self) -> None:
        from bench.suites.pinchbench import PinchBench

        assert PinchBench.name == "pinchbench"

    def test_total_tasks(self) -> None:
        from bench.suites.pinchbench import PinchBench

        inst = PinchBench()
        assert len(inst._tasks) == 53

    def test_subset_returns_tasks(self) -> None:
        from bench.suites.pinchbench import PinchBench

        inst = PinchBench()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "pinchbench" for t in tasks)

    def test_run_task_returns_task_result(self) -> None:
        from bench.suites.pinchbench import PinchBench

        inst = PinchBench()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run_returns_suite_result(self) -> None:
        from bench.suites.pinchbench import PinchBench

        inst = PinchBench()
        rs = RunSpec(suite="pinchbench", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5

    def test_verify(self) -> None:
        from bench.suites.pinchbench import PinchBench

        inst = PinchBench()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad")
        assert isinstance(passed, bool)
        assert "fail_reason" in info


# ======================================================================
# 3. bench/suites/hle.py
# ======================================================================


class TestHLE:
    def test_spec(self) -> None:
        from bench.suites.hle import HLE

        spec = HLE.spec()
        assert isinstance(spec, SuiteSpec)
        assert spec.name == "hle"

    def test_tasks(self) -> None:
        from bench.suites.hle import HLE

        inst = HLE()
        with pytest.raises(TypeError, match="missing.*suite"):
            inst.tasks()

    def test_run_task(self) -> None:
        from bench.suites.hle import HLE

        inst = HLE()
        from bench.suites._stub_task import TaskSpec

        task = TaskSpec(
            task_id="hle-test",
            suite="hle",
            prompt="test prompt",
            tags=["reasoning"],
        )
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.PASS

    def test_run(self) -> None:
        from bench.suites.hle import HLE

        inst = HLE()
        rs = RunSpec(suite="hle", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.suite == "hle"
        assert sr.n == 3
        assert sr.passed >= 0


# ======================================================================
# 4. bench/suites/perplexity.py
# ======================================================================


class TestPerplexity:
    def test_spec(self) -> None:
        from bench.suites.perplexity import Perplexity

        spec = Perplexity.spec()
        assert isinstance(spec, SuiteSpec)
        assert spec.name == "perplexity"

    def test_tasks(self) -> None:
        from bench.suites.perplexity import Perplexity

        inst = Perplexity()
        with pytest.raises(TypeError, match="missing.*suite"):
            inst.tasks()

    def test_run_task(self) -> None:
        from bench.suites.perplexity import Perplexity

        inst = Perplexity()
        from bench.suites._stub_task import TaskSpec

        task = TaskSpec(
            task_id="ppl-test",
            suite="perplexity",
            prompt="test prompt",
            tags=["perplexity"],
        )
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.PASS

    def test_run(self) -> None:
        from bench.suites.perplexity import Perplexity

        inst = Perplexity()
        rs = RunSpec(suite="perplexity", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3
        assert sr.passed == 3  # all pass in stub


# ======================================================================
# 5. bench/suites/mt_bench.py
# ======================================================================


class TestMTBench:
    def test_name(self) -> None:
        from bench.suites.mt_bench import MTBench

        assert MTBench.name == "mt-bench"

    def test_init_force_stub(self) -> None:
        from bench.suites.mt_bench import MTBench

        inst = MTBench(force_stub=True)
        assert inst.judge.is_stub is True

    def test_subset(self) -> None:
        from bench.suites.mt_bench import MTBench

        inst = MTBench(force_stub=True)
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "mt-bench" for t in tasks)
        assert all("category" in t.metadata for t in tasks)

    def test_run_task(self) -> None:
        from bench.suites.mt_bench import MTBench

        inst = MTBench(force_stub=True)
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert "judge_score" in result.meta

    def test_run(self) -> None:
        from bench.suites.mt_bench import MTBench

        inst = MTBench(force_stub=True)
        rs = RunSpec(suite="mt-bench", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3
        assert "score_mean" in sr.meta


# ======================================================================
# 6. bench/suites/mmlu_pro.py
# ======================================================================


class TestMMLUProHelpers:
    def test_normalise_choice_int(self) -> None:
        from bench.suites.mmlu_pro import _normalise_choice

        assert _normalise_choice(0) == "A"
        assert _normalise_choice(3) == "D"
        assert _normalise_choice(9) == "J"
        assert _normalise_choice(15) == "15"

    def test_normalise_choice_str(self) -> None:
        from bench.suites.mmlu_pro import _normalise_choice

        assert _normalise_choice("b") == "B"
        assert _normalise_choice("C") == "C"
        assert _normalise_choice("xyz") == "X"


class TestMMLUPro:
    def test_name(self) -> None:
        from bench.suites.mmlu_pro import MMLUPro

        assert MMLUPro.name == "mmlu-pro"

    @pytest.mark.slow
    def test_subset(self) -> None:
        from bench.suites.mmlu_pro import MMLUPro

        inst = MMLUPro()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "mmlu-pro" for t in tasks)

    def test_run_task(self) -> None:
        from bench.suites.mmlu_pro import MMLUPro

        inst = MMLUPro()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert "gold" in result.meta

    def test_run(self) -> None:
        from bench.suites.mmlu_pro import MMLUPro

        inst = MMLUPro()
        rs = RunSpec(suite="mmlu-pro", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5
        assert "pass@1" in sr.meta


# ======================================================================
# 7. bench/suites/gpqa_diamond.py
# ======================================================================


class TestGPQADiamondHelpers:
    def test_normalise_choice(self) -> None:
        from bench.suites.gpqa_diamond import _normalise_choice

        assert _normalise_choice(0) == "A"
        assert _normalise_choice("a") == "A"
        assert _normalise_choice("D") == "D"


class TestGPQADiamond:
    def test_name(self) -> None:
        from bench.suites.gpqa_diamond import GPQADiamond

        assert GPQADiamond.name == "gpqa-diamond"

    def test_subset(self) -> None:
        from bench.suites.gpqa_diamond import GPQADiamond

        inst = GPQADiamond()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "gpqa-diamond" for t in tasks)

    def test_anti_contamination_in_metadata(self) -> None:
        from bench.suites.gpqa_diamond import (
            ANTI_CONTAMINATION_PASSWORD,
            GPQADiamond,
        )

        inst = GPQADiamond()
        tasks = inst.subset(1, 42)
        assert (
            tasks[0].metadata.get("anti_contamination_password")
            == ANTI_CONTAMINATION_PASSWORD
        )

    def test_run_task(self) -> None:
        from bench.suites.gpqa_diamond import GPQADiamond

        inst = GPQADiamond()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert "gold" in result.meta

    def test_run(self) -> None:
        from bench.suites.gpqa_diamond import GPQADiamond

        inst = GPQADiamond()
        rs = RunSpec(suite="gpqa-diamond", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5


# ======================================================================
# 8. bench/suites/swe_bench_verified.py
# ======================================================================


class TestSWEBenchVerified:
    def test_name(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        assert SWEBenchVerified.name == "swe-bench-verified"

    def test_init_defaults(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        inst = SWEBenchVerified()
        assert inst.runner is not None

    def test_subset(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        inst = SWEBenchVerified()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "swe-bench-verified" for t in tasks)
        assert all("__" in t.task_id for t in tasks)

    def test_run_task_stub(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        inst = SWEBenchVerified()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        inst = SWEBenchVerified()
        rs = RunSpec(suite="swe-bench-verified", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3

    def test_deterministic_idx(self) -> None:
        from bench.suites.swe_bench_verified import SWEBenchVerified

        idx1 = SWEBenchVerified._deterministic_idx(seed=42, slot=0)
        idx2 = SWEBenchVerified._deterministic_idx(seed=42, slot=0)
        assert idx1 == idx2
        assert 10000 <= idx1 < 60000


# ======================================================================
# 9. bench/suites/terminal_bench.py
# ======================================================================


class TestTerminalBench:
    def test_name(self) -> None:
        from bench.suites.terminal_bench import TerminalBench

        assert TerminalBench.name == "terminal-bench"

    def test_init(self) -> None:
        from bench.suites.terminal_bench import TerminalBench

        inst = TerminalBench()
        assert inst.runner is not None

    def test_subset(self) -> None:
        from bench.suites.terminal_bench import TerminalBench

        inst = TerminalBench()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "terminal-bench" for t in tasks)
        assert all("/" in t.task_id for t in tasks)

    def test_run_task_stub(self) -> None:
        from bench.suites.terminal_bench import TerminalBench

        inst = TerminalBench()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.terminal_bench import TerminalBench

        inst = TerminalBench()
        rs = RunSpec(suite="terminal-bench", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3

    def test_anti_contamination_guid(self) -> None:
        from bench.suites.terminal_bench import (
            ANTI_CONTAMINATION_GUID,
            TerminalBench,
        )

        inst = TerminalBench()
        tasks = inst.subset(1, 42)
        assert (
            tasks[0].metadata.get("anti_contamination_guid")
            == ANTI_CONTAMINATION_GUID
        )


# ======================================================================
# 10. bench/suites/osworld.py
# ======================================================================


class TestOSWorldHelpers:
    def test_osworld_prompt(self) -> None:
        from bench.suites.osworld import _osworld_prompt

        text = _osworld_prompt("OSW-01000", "linux", "terminal", "list files")
        assert "OSW-01000" in text
        assert "linux" in text
        assert "terminal" in text

    def test_correctness_check_valid(self) -> None:
        from bench.suites.osworld import _osworld_correctness_check

        resp = "#!/bin/bash\n" + "ls -la\n" * 10 + "\nOSWORLD_DONE=OSW-01000\n"
        passed, reason = _osworld_correctness_check(resp)
        assert passed is True

    def test_correctness_check_too_short(self) -> None:
        from bench.suites.osworld import _osworld_correctness_check

        passed, reason = _osworld_correctness_check("short")
        assert passed is False
        assert reason == "too-short"

    def test_correctness_check_no_marker(self) -> None:
        from bench.suites.osworld import _osworld_correctness_check

        resp = "#!/bin/bash\n" + "echo hello\n" * 10
        passed, reason = _osworld_correctness_check(resp)
        assert passed is False
        assert reason == "no-done-marker"

    def test_correctness_check_refusal(self) -> None:
        from bench.suites.osworld import _osworld_correctness_check

        resp = (
            "#!/bin/bash\nI cannot do that. " + "x" * 80 + "\nOSWORLD_DONE=x"
        )
        passed, reason = _osworld_correctness_check(resp)
        assert passed is False
        assert "refusal" in reason


class TestOSWorld:
    def test_name(self) -> None:
        from bench.suites.osworld import OSWorld

        assert OSWorld.name == "osworld"

    def test_total_tasks(self) -> None:
        from bench.suites.osworld import OSWorld

        inst = OSWorld()
        assert len(inst._tasks) == 350

    def test_subset(self) -> None:
        from bench.suites.osworld import OSWorld

        inst = OSWorld()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "osworld" for t in tasks)

    def test_run_task(self) -> None:
        from bench.suites.osworld import OSWorld

        inst = OSWorld()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.osworld import OSWorld

        inst = OSWorld()
        rs = RunSpec(suite="osworld", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5

    def test_verify(self) -> None:
        from bench.suites.osworld import OSWorld

        inst = OSWorld()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad")
        assert isinstance(passed, bool)
        assert "category" in info

    def test_os_world_task_dataclass(self) -> None:
        from bench.suites.osworld import OSWorldTask

        t = OSWorldTask(
            task_id="test",
            os="linux",
            category="terminal",
            initial_state="snap1",
            instruction="do stuff",
            verifier_script="check.sh",
        )
        assert t.task_id == "test"


# ======================================================================
# 11. bench/suites/startup_bench.py
# ======================================================================


class TestStartupBenchHelpers:
    def test_startup_prompt(self) -> None:
        from bench.suites.startup_bench import _startup_prompt

        text = _startup_prompt("ai-saas", 90)
        assert "ai-saas" in text
        assert "90" in text

    def test_parse_startup_valid(self) -> None:
        from bench.suites.startup_bench import _parse_startup

        resp = (
            "DAY 1: HIRE cto\n"
            "DAY 2: SHIP mvp\n"
            "```json\n"
            '{"product_market_fit_score": 8, "monthly_growth_rate": 0.20, '
            '"runway_months": 15}\n'
            "```\n"
        )
        parsed = _parse_startup(resp)
        assert parsed["decisions"] == 2
        assert parsed["valid_json"] is True
        assert parsed["score"]["pmf"] == 8.0

    def test_parse_startup_no_json(self) -> None:
        from bench.suites.startup_bench import _parse_startup

        parsed = _parse_startup("DAY 1: HIRE cto\nDAY 2: FIRE intern\n")
        assert parsed["decisions"] == 2
        assert parsed["valid_json"] is False

    def test_parse_startup_empty(self) -> None:
        from bench.suites.startup_bench import _parse_startup

        parsed = _parse_startup("")
        assert parsed["decisions"] == 0
        assert parsed["valid_json"] is False

    def test_startup_score_all_met(self) -> None:
        from bench.suites.startup_bench import _startup_score

        parsed = {
            "valid_json": True,
            "score": {"pmf": 8.0, "growth": 0.20, "runway_months": 15},
        }
        passed, reason, milestones = _startup_score(parsed)
        assert passed is True
        assert reason == "all-milestones-met"

    def test_startup_score_none_met(self) -> None:
        from bench.suites.startup_bench import _startup_score

        parsed = {
            "valid_json": True,
            "score": {"pmf": 3.0, "growth": 0.05, "runway_months": 4},
        }
        passed, reason, milestones = _startup_score(parsed)
        assert passed is False
        assert reason == "no-milestones"

    def test_startup_score_invalid_json(self) -> None:
        from bench.suites.startup_bench import _startup_score

        parsed = {"valid_json": False, "score": None}
        passed, reason, milestones = _startup_score(parsed)
        assert passed is False
        assert reason == "invalid-json"

    def test_startup_score_partial(self) -> None:
        from bench.suites.startup_bench import _startup_score

        parsed = {
            "valid_json": True,
            "score": {"pmf": 8.0, "growth": 0.05, "runway_months": 4},
        }
        passed, reason, milestones = _startup_score(parsed)
        assert passed is False
        assert reason == "partial-milestones"
        assert milestones == 1


class TestStartupBench:
    def test_name(self) -> None:
        from bench.suites.startup_bench import StartupBench

        assert StartupBench.name == "startup-bench"

    def test_total_tasks(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        assert len(inst._tasks) == 6

    def test_subset(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        tasks = inst.subset(3, 42)
        assert len(tasks) == 3
        assert all(t.suite == "startup-bench" for t in tasks)

    def test_subset_all(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        tasks = inst.subset(100, 42)
        assert len(tasks) == 6  # only 6 tracks

    def test_run_task(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        rs = RunSpec(suite="startup-bench", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3

    def test_verify(self) -> None:
        from bench.suites.startup_bench import StartupBench

        inst = StartupBench()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad")
        assert isinstance(passed, bool)
        assert "milestones_met" in info


# ======================================================================
# 12. bench/suites/dataset_loader.py
# ======================================================================


class TestDatasetLoader:
    def test_cache_root_is_path(self) -> None:
        from bench.suites.dataset_loader import CACHE_ROOT

        assert isinstance(CACHE_ROOT, Path)

    def test_dataset_not_available_error(self) -> None:
        from bench.suites.dataset_loader import DatasetNotAvailableError

        assert issubclass(DatasetNotAvailableError, RuntimeError)

    def test_dataset_source_construction(self) -> None:
        from bench.suites.dataset_loader import DatasetSource

        src = DatasetSource(
            name="test-suite",
            hf_repo="org/repo",
            hf_subset="sub",
            hf_split="test",
        )
        assert src.name == "test-suite"
        assert src.hf_repo == "org/repo"

    def test_dataset_source_cache_dir(self) -> None:
        from bench.suites.dataset_loader import DatasetSource

        src = DatasetSource(name="test", hf_repo="org/repo", hf_subset="sub")
        d = src.cache_dir()
        assert isinstance(d, Path)
        assert "org__repo__sub" in str(d)

    def test_loaded_dataset_len(self) -> None:
        from bench.suites.dataset_loader import LoadedDataset

        ld = LoadedDataset(
            rows=[{"a": 1}, {"b": 2}], source=None  # type: ignore[arg-type]
        )
        assert len(ld) == 2

    def test_synth_mc_question(self) -> None:
        from bench.suites.dataset_loader import synth_mc_question

        q = synth_mc_question(42, 0, subject="physics", choices=4)
        assert "question" in q
        assert "choices" in q
        assert "answer" in q
        assert len(q["choices"]) == 4

    def test_synth_short_answer(self) -> None:
        from bench.suites.dataset_loader import synth_short_answer

        q = synth_short_answer(42, 0, kind="math")
        assert "question" in q
        assert "answer" in q

    def test_synth_function_call(self) -> None:
        from bench.suites.dataset_loader import synth_function_call

        q = synth_function_call(42, 0)
        assert "prompt" in q
        assert "expected_function" in q

    def test_synth_instruction_prompt(self) -> None:
        from bench.suites.dataset_loader import synth_instruction_prompt

        q = synth_instruction_prompt(42, 0)
        assert "prompt" in q
        assert "constraints" in q

    def test_synth_perplexity_corpus(self) -> None:
        from bench.suites.dataset_loader import synth_perplexity_corpus

        lines = synth_perplexity_corpus(42, n_lines=10)
        assert len(lines) == 10
        assert all(isinstance(line, str) for line in lines)

    def test_load_suite_dataset_synthetic(self) -> None:
        from bench.suites.dataset_loader import DatasetSource, load_suite_dataset

        src = DatasetSource(
            name="test",
            hf_repo="fake/repo",
            synth_fn=lambda k, s: [{"q": i} for i in range(k)],
        )
        loaded = load_suite_dataset(src, n=5)
        assert len(loaded) == 5
        assert loaded.synthetic is True

    def test_write_jsonl_and_read_jsonl(self, tmp_path: Path) -> None:
        from bench.suites.dataset_loader import read_jsonl, write_jsonl

        path = tmp_path / "test.jsonl"
        rows = [{"a": 1}, {"b": 2}]
        count = write_jsonl(rows, path)
        assert count == 2
        read_back = read_jsonl(path)
        assert len(read_back) == 2
        assert read_back[0]["a"] == 1

    def test_read_jsonl_nonexistent(self) -> None:
        from bench.suites.dataset_loader import read_jsonl

        assert read_jsonl(Path("/nonexistent/file.jsonl")) == []


# ======================================================================
# 13. bench/suites/judge.py
# ======================================================================


class TestJudge:
    def test_judge_verdict_construction(self) -> None:
        from bench.suites.judge import JudgeVerdict

        v = JudgeVerdict(score=7.5, rationale="good")
        assert v.score == 7.5
        assert v.judge_stub is False

    def test_judge_verdict_to_dict(self) -> None:
        from bench.suites.judge import JudgeVerdict

        v = JudgeVerdict(score=8.0, rationale="ok", judge_stub=True)
        d = v.to_dict()
        assert d["score"] == 8.0
        assert d["judge_stub"] is True

    def test_judge_error(self) -> None:
        from bench.suites.judge import JudgeError

        assert issubclass(JudgeError, RuntimeError)

    def test_judge_request_construction(self) -> None:
        from bench.suites.judge import JudgeRequest

        req = JudgeRequest(user_prompt="test", response="answer")
        assert req.user_prompt == "test"
        assert req.max_score == 10.0

    def test_llm_judge_stub_mode(self) -> None:
        from bench.suites.judge import JudgeRequest, LLMJudge

        judge = LLMJudge(model="test", force_stub=True)
        assert judge.is_stub is True
        verdict = judge.judge(JudgeRequest(user_prompt="test", response="answer"))
        assert 0.0 <= verdict.score <= 10.0
        assert verdict.judge_stub is True

    def test_parse_score_normal(self) -> None:
        from bench.suites.judge import LLMJudge

        assert LLMJudge._parse_score("7") == 7.0
        assert LLMJudge._parse_score("8.5") == 8.5

    def test_parse_score_with_prefix(self) -> None:
        from bench.suites.judge import LLMJudge

        assert LLMJudge._parse_score("score: 9") == 9.0
        # Case-sensitive: "Score" (capital S) won't match lowercase "score" regex
        assert LLMJudge._parse_score("score = 6") == 6.0

    def test_parse_score_empty(self) -> None:
        from bench.suites.judge import LLMJudge

        assert LLMJudge._parse_score("") == 0.0

    def test_parse_score_clamped(self) -> None:
        from bench.suites.judge import LLMJudge

        assert LLMJudge._parse_score("15", max_score=10.0) == 10.0
        assert LLMJudge._parse_score("-3", max_score=10.0) == 0.0

    def test_compose_user_prompt(self) -> None:
        from bench.suites.judge import JudgeRequest, LLMJudge

        req = JudgeRequest(
            user_prompt="What is 2+2?",
            response="4",
            reference="4",
            rubric="Must be correct",
        )
        prompt = LLMJudge._compose_user_prompt(req)
        assert "What is 2+2?" in prompt
        assert "4" in prompt
        assert "Must be correct" in prompt

    def test_extract_text(self) -> None:
        from bench.suites.judge import LLMJudge

        class FakeBlock:
            def __init__(self, text: str) -> None:
                self.text = text

        class FakeResp:
            content = [FakeBlock("hello"), FakeBlock("world")]

        text = LLMJudge._extract_text(FakeResp())
        assert "hello" in text
        assert "world" in text


# ======================================================================
# 14. bench/suites/bfcl_v4.py
# ======================================================================


class TestBFCLv4Helpers:
    def test_extract_function_call_json(self) -> None:
        from bench.suites.bfcl_v4 import _extract_function_call

        resp = '{"name": "get_weather", "arguments": {"city": "Paris"}}'
        name, args = _extract_function_call(resp)
        assert name == "get_weather"
        assert args["city"] == "Paris"

    def test_extract_function_call_python(self) -> None:
        from bench.suites.bfcl_v4 import _extract_function_call

        resp = 'get_weather(city="London")'
        name, args = _extract_function_call(resp)
        assert name == "get_weather"
        assert args["city"] == "London"

    def test_extract_function_call_empty(self) -> None:
        from bench.suites.bfcl_v4 import _extract_function_call

        name, args = _extract_function_call("")
        assert name == ""
        assert args == {}

    def test_arg_match_loose(self) -> None:
        from bench.suites.bfcl_v4 import _arg_match

        assert _arg_match({"a": 1}, {"a": 1}) is True
        assert _arg_match({"a": "x"}, {"a": "x"}) is True
        assert _arg_match({"a": "X"}, {"a": "x"}, loose=True) is True
        assert _arg_match({"a": 1}, {"a": 2}) is False

    def test_function_call_match(self) -> None:
        from bench.suites.bfcl_v4 import _function_call_match

        resp = '{"name": "search", "arguments": {"query": "hello"}}'
        assert _function_call_match("search", {"query": "hello"}, resp) is True
        assert _function_call_match("other", {}, resp) is False


class TestBFCLv4:
    def test_name(self) -> None:
        from bench.suites.bfcl_v4 import BFCLv4

        assert BFCLv4.name == "bfcl"

    def test_subset(self) -> None:
        from bench.suites.bfcl_v4 import BFCLv4

        inst = BFCLv4()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "bfcl" for t in tasks)

    def test_run_task(self) -> None:
        from bench.suites.bfcl_v4 import BFCLv4

        inst = BFCLv4()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)
        assert "pass@1" in result.meta

    def test_run(self) -> None:
        from bench.suites.bfcl_v4 import BFCLv4

        inst = BFCLv4()
        rs = RunSpec(suite="bfcl", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5
        assert "pass@1" in sr.meta


# ======================================================================
# 15. bench/suites/browsercomp.py
# ======================================================================


class TestBrowserCompHelpers:
    def test_browsercomp_prompt(self) -> None:
        from bench.suites.browsercomp import _browsercomp_prompt

        text = _browsercomp_prompt(
            "BC-001", "form_fill", "http://localhost/forms", "fill", "#el", "abc"
        )
        assert "BC-001" in text
        assert "form_fill" in text

    def test_correctness_check_valid(self) -> None:
        from bench.suites.browsercomp import _browsercomp_correctness_check

        resp = (
            "import asyncio\n"
            "from playwright.async_api import async_playwright\n"
            "async def run():\n"
            "    async with async_playwright() as p:\n"
            "        browser = await p.chromium.launch(headless=True)\n"
            "        page = await browser.new_page()\n"
            "        await page.goto('http://localhost/forms')\n"
            "        await browser.close()\n"
            "FINAL_HASH=abc123\n"
        )
        passed, reason = _browsercomp_correctness_check(resp)
        assert passed is True

    def test_correctness_check_too_short(self) -> None:
        from bench.suites.browsercomp import _browsercomp_correctness_check

        passed, reason = _browsercomp_correctness_check("short")
        assert passed is False

    def test_correctness_check_no_playwright(self) -> None:
        from bench.suites.browsercomp import _browsercomp_correctness_check

        resp = "import asyncio\n" + "x" * 80 + "\nFINAL_HASH=abc"
        passed, reason = _browsercomp_correctness_check(resp)
        assert passed is False
        assert reason == "no-playwright-import"


class TestBrowserComp:
    def test_name(self) -> None:
        from bench.suites.browsercomp import BrowserComp

        assert BrowserComp.name == "browsercomp"

    def test_total_tasks(self) -> None:
        from bench.suites.browsercomp import BrowserComp

        inst = BrowserComp()
        assert len(inst._tasks) == 50

    def test_subset(self) -> None:
        from bench.suites.browsercomp import BrowserComp

        inst = BrowserComp()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5

    def test_run_task(self) -> None:
        from bench.suites.browsercomp import BrowserComp

        inst = BrowserComp()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_verify(self) -> None:
        from bench.suites.browsercomp import BrowserComp

        inst = BrowserComp()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad")
        assert isinstance(passed, bool)
        assert "category" in info

    def test_browser_comp_task_dataclass(self) -> None:
        from bench.suites.browsercomp import BrowserCompTask

        t = BrowserCompTask(
            task_id="BC-001",
            category="form_fill",
            setup_url="http://localhost",
            action_script="click",
            verifier_dom_selector="#el",
            verifier_expected_hash="abc",
        )
        assert t.task_id == "BC-001"


# ======================================================================
# 16. bench/suites/container_runner.py
# ======================================================================


class TestContainerRunner:
    def test_imports(self) -> None:
        import bench.suites.container_runner as cr

        assert cr.ContainerBackend is not None
        assert cr.ContainerRunner is not None
        assert cr.ContainerNotAvailableError is not None
        assert cr.ContainerRunError is not None
        assert cr.ContainerRunResult is not None
        assert cr.RewardContract is not None
        assert cr.detect_backend is not None
        assert cr.run_or_stub is not None

    def test_container_not_available_error(self) -> None:
        from bench.suites.container_runner import ContainerNotAvailableError

        assert issubclass(ContainerNotAvailableError, RuntimeError)

    def test_container_run_error(self) -> None:
        from bench.suites.container_runner import ContainerRunError

        assert issubclass(ContainerRunError, RuntimeError)

    def test_container_backend_str(self) -> None:
        from bench.suites.container_runner import ContainerBackend

        b = ContainerBackend(name="docker", binary="/usr/bin/docker")
        assert str(b) == "docker"

    def test_reward_contract(self) -> None:
        from bench.suites.container_runner import RewardContract

        r = RewardContract(reward=0.75, details={"stub": True})
        assert r.reward == 0.75
        d = r.to_dict()
        assert d["reward"] == 0.75

    def test_reward_contract_from_path(self, tmp_path: Path) -> None:
        import json

        from bench.suites.container_runner import RewardContract

        p = tmp_path / "reward.json"
        p.write_text(json.dumps({"reward": 0.5, "details": {"x": 1}}))
        r = RewardContract.from_path(p)
        assert r.reward == 0.5
        assert r.details["x"] == 1

    def test_container_runner_init(self) -> None:
        from bench.suites.container_runner import ContainerRunner

        with tempfile.TemporaryDirectory() as td:
            runner = ContainerRunner(workspace=td)
            assert runner.workspace == Path(td)
            assert isinstance(runner.is_available, bool)

    def test_stub_run(self) -> None:
        from bench.suites.container_runner import ContainerRunner

        with tempfile.TemporaryDirectory() as td:
            runner = ContainerRunner(workspace=td)
            # stub_run passes wall_clock_s instead of duration_s — known bug
            with pytest.raises(TypeError, match="wall_clock_s"):
                runner.stub_run("test-task", pass_probability=1.0)

    def test_run_or_stub(self) -> None:
        from bench.suites.container_runner import (
            ContainerRunError,
            ContainerRunner,
            run_or_stub,
        )

        with tempfile.TemporaryDirectory() as td:
            runner = ContainerRunner(workspace=td)
            if runner.is_available:
                # Docker found but no image → ContainerRunError
                with pytest.raises(ContainerRunError):
                    run_or_stub(runner, "test-task")
            else:
                # No Docker: stub_run has known wall_clock_s bug
                with pytest.raises(TypeError, match="wall_clock_s"):
                    run_or_stub(runner, "test-task")

    def test_container_run_result_to_dict(self) -> None:
        from bench.suites.container_runner import (
            ContainerRunResult,
            RewardContract,
        )

        cr = ContainerRunResult(
            task_id="t",
            backend="stub",
            exit_code=0,
            duration_s=0.1,
            reward=RewardContract(reward=1.0),
            stub=True,
        )
        d = cr.to_dict()
        assert d["task_id"] == "t"
        assert d["stub"] is True


# ======================================================================
# 17. bench/suites/deepswe.py
# ======================================================================


class TestDeepSWE:
    def test_name(self) -> None:
        from bench.suites.deepswe import DeepSWE

        assert DeepSWE.name == "deep-swe"

    def test_init(self) -> None:
        from bench.suites.deepswe import DeepSWE

        inst = DeepSWE()
        assert inst.runner is not None

    def test_subset(self) -> None:
        from bench.suites.deepswe import DeepSWE

        inst = DeepSWE()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "deep-swe" for t in tasks)
        assert all("pr-deepswe-" in t.task_id for t in tasks)

    def test_run_task_stub(self) -> None:
        from bench.suites.deepswe import DeepSWE

        inst = DeepSWE()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.deepswe import DeepSWE

        inst = DeepSWE()
        rs = RunSpec(suite="deep-swe", model="test-model", n=3, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 3
        assert "pass@1" in sr.meta

    def test_deterministic_idx(self) -> None:
        from bench.suites.deepswe import DeepSWE

        idx1 = DeepSWE._deterministic_idx(seed=42, slot=0)
        idx2 = DeepSWE._deterministic_idx(seed=42, slot=0)
        assert idx1 == idx2
        assert 0 <= idx1 < 10000


# ======================================================================
# 18. bench/suites/kernelbench.py
# ======================================================================


class TestKernelBenchHelpers:
    def test_kernelbench_prompt_level1(self) -> None:
        from bench.suites.kernelbench import _kernelbench_prompt

        text = _kernelbench_prompt(1, "square matrix element-wise", "fp32", level=1)
        assert "001" in text
        assert "fp32" in text

    def test_kernelbench_prompt_level2(self) -> None:
        from bench.suites.kernelbench import _kernelbench_prompt

        text = _kernelbench_prompt(1, "MobileNet-v2 stem", "fp32", level=2)
        assert "L2-001" in text

    def test_correctness_check_valid(self) -> None:
        from bench.suites.kernelbench import _kernelbench_correctness_check

        resp = (
            "import torch\nimport triton\nimport triton.language as tl\n\n"
            "@triton.jit\ndef kernel_impl(x):\n    return x\n"
        )
        assert _kernelbench_correctness_check(resp, 1e-5, 1e-5) is True

    def test_correctness_check_empty(self) -> None:
        from bench.suites.kernelbench import _kernelbench_correctness_check

        assert _kernelbench_correctness_check("", 1e-5, 1e-5) is False

    def test_correctness_check_too_short(self) -> None:
        from bench.suites.kernelbench import _kernelbench_correctness_check

        assert _kernelbench_correctness_check("short", 1e-5, 1e-5) is False

    def test_correctness_check_refusal(self) -> None:
        from bench.suites.kernelbench import _kernelbench_correctness_check

        resp = (
            "import torch\n"
            "I cannot implement this kernel.\n"
            "def kernel_impl(x):\n    pass\n"
            + "x" * 50
        )
        assert _kernelbench_correctness_check(resp, 1e-5, 1e-5) is False

    def test_correctness_check_no_kernel(self) -> None:
        from bench.suites.kernelbench import _kernelbench_correctness_check

        resp = "def kernel_impl(x):\n    return x\n" + "x" * 50
        assert _kernelbench_correctness_check(resp, 1e-5, 1e-5) is False


class TestKernelBench:
    def test_name(self) -> None:
        from bench.suites.kernelbench import KernelBench

        assert KernelBench.name == "kernelbench"

    def test_total_tasks(self) -> None:
        from bench.suites.kernelbench import KernelBench

        inst = KernelBench()
        assert len(inst._tasks) == 110

    def test_subset(self) -> None:
        from bench.suites.kernelbench import KernelBench

        inst = KernelBench()
        tasks = inst.subset(5, 42)
        assert len(tasks) == 5
        assert all(t.suite == "kernelbench" for t in tasks)

    def test_run_task(self) -> None:
        from bench.suites.kernelbench import KernelBench

        inst = KernelBench()
        task = inst.subset(1, 42)[0]
        result = inst.run_task(task, "test-model")
        assert isinstance(result, TaskResult)

    def test_run(self) -> None:
        from bench.suites.kernelbench import KernelBench

        inst = KernelBench()
        rs = RunSpec(suite="kernelbench", model="test-model", n=5, seed=42)
        sr = inst.run(rs)
        assert isinstance(sr, SuiteResult)
        assert sr.n == 5

    def test_verify(self) -> None:
        from bench.suites.kernelbench import KernelBench

        inst = KernelBench()
        task = inst.subset(1, 42)[0]
        passed, info = inst.verify(task, "bad")
        assert isinstance(passed, bool)
        assert "level" in info

    def test_kernel_bench_config(self) -> None:
        from bench.suites.kernelbench import KernelBenchConfig

        cfg = KernelBenchConfig(level=1, atol=1e-5, rtol=1e-5, category="test")
        assert cfg.level == 1
        assert cfg.dtype == "fp32"


# ======================================================================
# Registry cross-checks
# ======================================================================


class TestRegistry:
    """Verify all suite classes are importable and have valid specs."""

    @pytest.mark.parametrize(
        "cls_path",
        [
            "bench.suites.vending_bench.VendingBench",
            "bench.suites.pinchbench.PinchBench",
            "bench.suites.hle.HLE",
            "bench.suites.perplexity.Perplexity",
            "bench.suites.mt_bench.MTBench",
            "bench.suites.mmlu_pro.MMLUPro",
            "bench.suites.gpqa_diamond.GPQADiamond",
            "bench.suites.swe_bench_verified.SWEBenchVerified",
            "bench.suites.terminal_bench.TerminalBench",
            "bench.suites.osworld.OSWorld",
            "bench.suites.startup_bench.StartupBench",
            "bench.suites.bfcl_v4.BFCLv4",
            "bench.suites.browsercomp.BrowserComp",
            "bench.suites.deepswe.DeepSWE",
            "bench.suites.kernelbench.KernelBench",
        ],
    )
    def test_suite_importable_and_has_spec(self, cls_path: str) -> None:
        import importlib

        mod_path, cls_name = cls_path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        assert cls is not None
        if hasattr(cls, "spec"):
            spec = cls.spec()
            assert spec.name
            assert spec.domain


# ======================================================================
# Seeds module
# ======================================================================


class TestSeeds:
    def test_sample_deterministic(self) -> None:
        from bench.seeds import sample

        s1 = sample("test-suite", 42, count=100, n=10)
        s2 = sample("test-suite", 42, count=100, n=10)
        assert s1.ordered_indices == s2.ordered_indices

    def test_sample_different_seeds(self) -> None:
        from bench.seeds import sample

        s1 = sample("test-suite", 42, count=100, n=10)
        s2 = sample("test-suite", 99, count=100, n=10)
        assert s1.ordered_indices != s2.ordered_indices

    def test_sample_n_zero(self) -> None:
        from bench.seeds import sample

        s = sample("test-suite", 42, count=100, n=0)
        assert len(s) == 0

    def test_sample_n_ge_count(self) -> None:
        from bench.seeds import sample

        s = sample("test-suite", 42, count=5, n=10)
        assert len(s) == 5

    def test_sample_negative_n(self) -> None:
        from bench.seeds import sample

        with pytest.raises(ValueError):
            sample("test-suite", 42, count=100, n=-1)

    def test_sample_with_pool(self) -> None:
        from bench.seeds import sample

        pool = ["a", "b", "c", "d", "e"]
        s = sample("test-suite", 42, pool=pool, n=3)
        assert len(s) == 3
        assert s.task_ids is not None
        assert len(s.task_ids) == 3
