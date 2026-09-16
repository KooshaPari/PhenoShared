"""Tests for bench/rlvr_af/verify.py — verifier + heuristic verifier."""
from __future__ import annotations

from bench.rlvr_af.trace import Artifact, JudgeVerdict, Transition
from bench.rlvr_af.verify import (
    BaseVerifier,
    HeuristicVerifier,
    MLXVerifier,
    get_verifier,
    register_verifier,
)


def _make_transition(completion: str, expected: str | None = "hello") -> Transition:
    return Transition(
        task_id="t1",
        artifact=Artifact(
            elapsed_s=0.1,
            prompt="test",
            completion=completion,
            expected=expected,
        ),
    )


class TestBaseVerifier:
    def test_not_implemented(self):
        bv = BaseVerifier()
        t = _make_transition("hello", "hello")
        try:
            bv.verify(t)
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

    def test_call_delegates_to_verify(self):
        class TestVerifier(BaseVerifier):
            def verify(self, t):
                return JudgeVerdict(passed=True, reward=1.0, reason="test")

        tv = TestVerifier()
        t = _make_transition("hello", "hello")
        v = tv(t)
        assert v.passed is True
        assert v.reward == 1.0


class TestHeuristicVerifier:
    def setup_method(self):
        self.v = HeuristicVerifier()

    def test_empty_completion(self):
        t = _make_transition("", "hello")
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.0

    def test_error_prefix(self):
        t = _make_transition("[error] something went wrong", "hello")
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.0

    def test_error_prefix_colon(self):
        t = _make_transition("error: bad request", "hello")
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.0

    def test_expected_found(self):
        t = _make_transition("the answer is HELLO world", "hello")
        v = self.v.verify(t)
        assert v.passed is True
        assert v.reward == 1.0
        assert "found" in v.reason.lower()

    def test_expected_not_found_long(self):
        t = _make_transition("this is a long completion that does not match", "hello")
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.5

    def test_expected_not_found_short(self):
        t = _make_transition("short", "hello")
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.0

    def test_no_expected_long(self):
        t = _make_transition("a" * 64, None)
        v = self.v.verify(t)
        assert v.passed is True
        assert v.reward == 1.0

    def test_no_expected_short(self):
        t = _make_transition("a" * 10, None)
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward < 1.0

    def test_no_expected_empty(self):
        t = _make_transition("", None)
        v = self.v.verify(t)
        assert v.passed is False
        assert v.reward == 0.0

    def test_case_insensitive_match(self):
        t = _make_transition("HELLO", "hello")
        v = self.v.verify(t)
        assert v.passed is True

    def test_meta_contains_expected(self):
        t = _make_transition("test", "hello")
        v = self.v.verify(t)
        assert v.meta["expected"] == "hello"
        assert v.meta["completion_len"] == 4


class TestMLXVerifier:
    def test_falls_back_to_heuristic(self):
        """MLXVerifier should fall back to heuristic when mlx is not available."""
        v = MLXVerifier()
        t = _make_transition("the answer is HELLO", "hello")
        verdict = v.verify(t)
        assert verdict.passed is True
        assert verdict.reward == 1.0

    def test_falls_back_on_empty(self):
        v = MLXVerifier()
        t = _make_transition("", "hello")
        verdict = v.verify(t)
        assert verdict.passed is False


class TestRegisterAndGetVerifier:
    def test_register_custom(self):
        class CustomVerifier(BaseVerifier):
            def verify(self, t):
                return JudgeVerdict(passed=True, reward=0.42, reason="custom")

        register_verifier("test_custom", CustomVerifier)
        v = get_verifier("test_custom")
        assert isinstance(v, CustomVerifier)
        t = _make_transition("x", "y")
        assert v.verify(t).reward == 0.42

    def test_get_default_heuristic(self):
        v = get_verifier("nonexistent_key")
        assert isinstance(v, HeuristicVerifier)

    def test_get_explicit_heuristic(self):
        v = get_verifier("heuristic")
        assert isinstance(v, HeuristicVerifier)

    def test_get_mlx(self):
        v = get_verifier("mlx")
        assert isinstance(v, MLXVerifier)
