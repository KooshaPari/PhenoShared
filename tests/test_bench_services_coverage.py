"""Coverage tests for bench/services/scoring.py and bench/services/evaluation.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bench.services.evaluation import EvalResult, EvaluationService
from bench.services.scoring import ScoreSummary, ScoringService

# ---------------------------------------------------------------------------
# scoring.py
# ---------------------------------------------------------------------------


class TestScoringServicePassAt1:
    """ScoringService.compute_pass_at_1 tests."""

    def test_empty_returns_zero(self) -> None:
        assert ScoringService.compute_pass_at_1([]) == 0.0

    def test_all_passed(self) -> None:
        results = [{"passed": True}, {"passed": True}]
        assert ScoringService.compute_pass_at_1(results) == 1.0

    def test_none_passed(self) -> None:
        results = [{"passed": False}, {"passed": False}]
        assert ScoringService.compute_pass_at_1(results) == 0.0

    def test_half_passed(self) -> None:
        results = [{"passed": True}, {"passed": False}]
        assert ScoringService.compute_pass_at_1(results) == 0.5

    def test_missing_passed_key_counts_as_false(self) -> None:
        results = [{"other": True}]
        assert ScoringService.compute_pass_at_1(results) == 0.0


class TestScoringServiceSummarize:
    """ScoringService.summarize tests."""

    def test_empty_results(self) -> None:
        s = ScoringService.summarize([])
        assert s.total == 0
        assert s.passed == 0
        assert s.failed == 0
        assert s.errored == 0
        assert s.pass_at_1 == 0.0
        assert s.mean_latency_ms == 0.0
        assert s.total_prompt_tokens == 0
        assert s.total_completion_tokens == 0

    def test_mixed_results(self) -> None:
        results = [
            {"passed": True, "latency_ms": 100.0, "prompt_tokens": 10, "completion_tokens": 5},
            {"passed": False, "error": "timeout"},
        ]
        s = ScoringService.summarize(results)
        assert s.total == 2
        assert s.passed == 1
        assert s.failed == 0  # the failed one has error → counted as errored
        assert s.errored == 1
        assert s.pass_at_1 == 0.5
        assert s.mean_latency_ms == 50.0
        assert s.total_prompt_tokens == 10
        assert s.total_completion_tokens == 5

    def test_all_failed_no_error(self) -> None:
        results = [{"passed": False}, {"passed": False}]
        s = ScoringService.summarize(results)
        assert s.failed == 2
        assert s.errored == 0

    def test_score_summary_defaults(self) -> None:
        s = ScoreSummary()
        assert s.total == 0
        assert s.extra == {}


# ---------------------------------------------------------------------------
# evaluation.py
# ---------------------------------------------------------------------------


def _make_inference_mock(text: str = "hello", prompt_tokens: int = 10,
                         completion_tokens: int = 5) -> AsyncMock:
    """Return an AsyncMock InferencePort whose agenerate returns *text*."""
    inf = AsyncMock()
    inf.agenerate.return_value = MagicMock(
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=50.0,
    )
    return inf


def _make_judge_mock(score: float = 0.8) -> AsyncMock:
    """Return an AsyncMock JudgePort whose evaluate returns *score*."""
    j = AsyncMock()
    j.evaluate.return_value = score
    return j


class TestEvalResult:
    """EvalResult dataclass construction."""

    def test_defaults(self) -> None:
        r = EvalResult(task_id="t1", text="")
        assert r.task_id == "t1"
        assert r.text == ""
        assert r.prompt_tokens == 0
        assert r.completion_tokens == 0
        assert r.latency_ms == 0.0
        assert r.score == 0.0
        assert r.passed is False
        assert r.error is None
        assert r.metrics == {}

    def test_custom_values(self) -> None:
        r = EvalResult(
            task_id="t2",
            text="world",
            prompt_tokens=20,
            completion_tokens=10,
            latency_ms=123.4,
            score=0.9,
            passed=True,
            error="boom",
            metrics={"k": "v"},
        )
        assert r.score == 0.9
        assert r.error == "boom"


class TestEvaluationServiceInit:
    def test_init_with_all(self) -> None:
        inf = AsyncMock()
        j = AsyncMock()
        vf = MagicMock(return_value=True)
        svc = EvaluationService(inference=inf, judge=j, verify_fn=vf)
        assert svc.inference is inf
        assert svc.judge is j
        assert svc.verify_fn is vf

    def test_init_defaults(self) -> None:
        svc = EvaluationService(inference=AsyncMock())
        assert svc.judge is None
        assert svc.verify_fn is None


class TestEvaluationServiceGenerateAndScore:
    """EvaluationService.generate_and_score tests."""

    @pytest.mark.asyncio
    async def test_verify_fn_true(self) -> None:
        verify = MagicMock(return_value=True)
        svc = EvaluationService(
            inference=_make_inference_mock(text="hi"),
            verify_fn=verify,
        )
        result = await svc.generate_and_score("t1", "prompt", expected="hi")
        assert result.passed is True
        assert result.score == 1.0
        assert result.text == "hi"

    @pytest.mark.asyncio
    async def test_verify_fn_false(self) -> None:
        verify = MagicMock(return_value=False)
        svc = EvaluationService(
            inference=_make_inference_mock(text="wrong"),
            verify_fn=verify,
        )
        result = await svc.generate_and_score("t1", "prompt", expected="right")
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_no_verify_fn_string_match(self) -> None:
        svc = EvaluationService(inference=_make_inference_mock(text="The answer is 42"))
        result = await svc.generate_and_score("t1", "prompt", expected="42")
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_no_verify_fn_string_mismatch(self) -> None:
        svc = EvaluationService(inference=_make_inference_mock(text="no match here"))
        result = await svc.generate_and_score("t1", "prompt", expected="42")
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_judge_overrides_verify(self) -> None:
        verify = MagicMock(return_value=True)
        svc = EvaluationService(
            inference=_make_inference_mock(text="answer"),
            judge=_make_judge_mock(score=0.8),
            verify_fn=verify,
        )
        result = await svc.generate_and_score("t1", "prompt", expected="answer")
        # judge.score=0.8 >= 0.5 → passed=True, score=0.8
        assert result.score == 0.8
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_judge_low_score_overrides(self) -> None:
        verify = MagicMock(return_value=True)
        svc = EvaluationService(
            inference=_make_inference_mock(text="answer"),
            judge=_make_judge_mock(score=0.3),
            verify_fn=verify,
        )
        result = await svc.generate_and_score("t1", "prompt", expected="answer")
        assert result.score == 0.3
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_no_judge_no_verify_fn(self) -> None:
        svc = EvaluationService(inference=_make_inference_mock(text="output"))
        result = await svc.generate_and_score("t1", "prompt", expected="something")
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_no_expected_skips_judge(self) -> None:
        svc = EvaluationService(
            inference=_make_inference_mock(text="output"),
            judge=_make_judge_mock(score=0.9),
        )
        result = await svc.generate_and_score("t1", "prompt")
        # expected is None → judge path not entered, no verify → passed=False
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_inference_exception(self) -> None:
        inf = AsyncMock()
        inf.agenerate.side_effect = RuntimeError("model down")
        svc = EvaluationService(inference=inf)
        result = await svc.generate_and_score("t1", "prompt")
        assert result.error is not None
        assert "RuntimeError" in result.error
        assert "model down" in result.error
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_judge_exception_keeps_previous_state(self) -> None:
        """If judge raises, the result keeps verify_fn/score state."""
        verify = MagicMock(return_value=True)
        j = AsyncMock()
        j.evaluate.side_effect = RuntimeError("judge crash")
        svc = EvaluationService(
            inference=_make_inference_mock(text="ans"),
            judge=j,
            verify_fn=verify,
        )
        result = await svc.generate_and_score("t1", "prompt", expected="ans")
        # verify_fn said passed=True, score=1.0; judge crashed → kept
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_tokens_extracted(self) -> None:
        svc = EvaluationService(
            inference=_make_inference_mock(text="ok", prompt_tokens=42, completion_tokens=7),
        )
        result = await svc.generate_and_score("t1", "prompt")
        assert result.prompt_tokens == 42
        assert result.completion_tokens == 7

    @pytest.mark.asyncio
    async def test_system_kwarg_forwarded(self) -> None:
        inf = AsyncMock()
        inf.agenerate.return_value = MagicMock(text="y", prompt_tokens=1, completion_tokens=1)
        svc = EvaluationService(inference=inf)
        await svc.generate_and_score("t1", "prompt", system="You are helpful")
        _, kwargs = inf.agenerate.call_args
        assert kwargs.get("system") == "You are helpful"
