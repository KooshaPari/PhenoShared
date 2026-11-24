"""Comprehensive unit tests for bench.rlvr_af.critic.

Covers: FAILURE_CLASSES, CriticReport, BaseCritic, HeuristicCritic,
ForgeCritic, register_critic, get_critic, and all heuristic classification paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bench.rlvr_af.critic import (
    FAILURE_CLASSES,
    BaseCritic,
    CriticReport,
    ForgeCritic,
    HeuristicCritic,
    get_critic,
    register_critic,
)
from bench.rlvr_af.trace import Artifact, JudgeVerdict, Trail, Transition

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trail(
    transitions_data: list[dict] | None = None,
    suite: str = "test-suite",
    model: str = "test-model",
    run_id: str = "run-001",
    seed: int = 42,
) -> Trail:
    """Build a Trail with the given transition data.

    Each dict in transitions_data should have:
      - task_id: str
      - completion: str
      - passed: bool
      - reward: float
      - reason: str (optional)
      - meta: dict (optional, maps to Artifact.extra)
    """
    trail = Trail(suite=suite, model=model, run_id=run_id, seed=seed)
    for i, td in enumerate(transitions_data or []):
        artifact = Artifact(
            elapsed_s=1.0,
            prompt=f"prompt-{i}",
            completion=td.get("completion", ""),
            extra=td.get("meta", {}),
        )
        # HeuristicCritic reads t.index and t.artifact.meta;
        # set them explicitly since the dataclass fields don't include them.
        verdict = JudgeVerdict(
            passed=td.get("passed", False),
            reward=td.get("reward", 0.0),
            reason=td.get("reason", ""),
        )
        t = Transition(task_id=td.get("task_id", f"t-{i}"), artifact=artifact, verdict=verdict)
        t.index = i
        t.artifact.meta = td.get("meta", {})
        t.artifact.task_id = td.get("task_id", f"t-{i}")  # critic reads artifact.task_id
        trail.add(t)
    return trail


# ---------------------------------------------------------------------------
# FAILURE_CLASSES tests
# ---------------------------------------------------------------------------


class TestFailureClasses:
    def test_all_expected_keys(self) -> None:
        expected_keys = {
            "hallucination",
            "tool_misuse",
            "context_loss",
            "instruction_following",
            "internal_error",
            "timeout",
            "empty_completion",
            "unknown",
        }
        assert set(FAILURE_CLASSES.keys()) == expected_keys

    def test_all_values_are_strings(self) -> None:
        for key, value in FAILURE_CLASSES.items():
            assert isinstance(value, str), f"{key} has non-string value"

    def test_no_empty_values(self) -> None:
        for key, value in FAILURE_CLASSES.items():
            assert len(value) > 0, f"{key} has empty value"


# ---------------------------------------------------------------------------
# CriticReport tests
# ---------------------------------------------------------------------------


class TestCriticReport:
    def test_defaults(self) -> None:
        report = CriticReport(trail_id="t1", suite_name="s1")
        assert report.trail_id == "t1"
        assert report.suite_name == "s1"
        assert report.failure_class == "unknown"
        assert report.confidence == 0.0
        assert report.root_cause == ""
        assert report.reproduction_script == ""
        assert report.fix_suggestion == ""
        assert report.meta == {}

    def test_custom_fields(self) -> None:
        report = CriticReport(
            trail_id="t1",
            suite_name="s1",
            failure_class="hallucination",
            confidence=0.9,
            root_cause="model hallucinated",
            fix_suggestion="add grounding",
            meta={"key": "val"},
        )
        assert report.failure_class == "hallucination"
        assert report.confidence == 0.9
        assert report.meta == {"key": "val"}

    def test_meta_is_mutable(self) -> None:
        report = CriticReport(trail_id="t1", suite_name="s1")
        report.meta["new_key"] = 42
        assert report.meta["new_key"] == 42


# ---------------------------------------------------------------------------
# BaseCritic tests
# ---------------------------------------------------------------------------


class TestBaseCritic:
    def test_analyze_raises_not_implemented(self) -> None:
        trail = _make_trail()
        critic = BaseCritic()
        with pytest.raises(NotImplementedError):
            critic.analyze(trail)

    def test_call_delegates_to_analyze(self) -> None:
        expected = CriticReport(trail_id="x", suite_name="y", failure_class="timeout")

        class MockCritic(BaseCritic):
            def analyze(self, trail: Trail) -> CriticReport:
                return expected

        trail = _make_trail()
        result = MockCritic()(trail)
        assert result is expected


# ---------------------------------------------------------------------------
# HeuristicCritic tests
# ---------------------------------------------------------------------------


class TestHeuristicCritic:
    def test_empty_trail(self) -> None:
        trail = _make_trail()
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "unknown"
        assert report.confidence == 1.0
        assert "No root cause identified" in report.root_cause
        assert report.meta["total_transitions"] == 0
        assert report.meta["failed"] == 0
        assert report.meta["passed"] == 0
        assert report.meta["pass_rate"] == 0.0

    def test_all_passed(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "ok", "passed": True, "reward": 1.0},
            {"task_id": "t2", "completion": "done", "passed": True, "reward": 1.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "unknown"
        assert report.confidence == 1.0
        assert report.meta["failed"] == 0
        assert report.meta["passed"] == 2
        assert report.meta["pass_rate"] == 1.0

    def test_empty_completion(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "empty_completion"
        assert report.confidence == 0.8
        assert "empty completion" in report.root_cause.lower()
        assert len(report.fix_suggestion) > 0

    def test_error_prefix_bracket(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "[error] model crashed", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "internal_error"
        assert "adapter" in report.fix_suggestion.lower() or "Check" in report.fix_suggestion

    def test_error_prefix_colon(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "error: something went wrong", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "internal_error"

    def test_timeout_in_stderr(self) -> None:
        trail = _make_trail([
            {
                "task_id": "t1",
                "completion": "some output",
                "passed": False,
                "reward": 0.0,
                "meta": {"trail_stderr": "process timeout: exceeded 30s"},
            },
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "timeout"
        assert "timed out" in report.root_cause.lower()

    def test_tool_misuse_in_completion(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "I called the wrong tool", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "tool_misuse"
        assert "tool-call syntax" in report.fix_suggestion.lower()

    def test_command_misuse_in_completion(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "ran command sudo rm -rf", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "tool_misuse"

    def test_hallucination_long_completion(self) -> None:
        long_comp = "word " * 60  # > 200 chars
        trail = _make_trail([
            {"task_id": "t1", "completion": long_comp, "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "hallucination"
        assert "hallucination" in report.root_cause.lower()

    def test_instruction_following_fallback(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "short wrong answer", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "instruction_following"
        assert "instruction-following" in report.root_cause.lower()

    def test_multiple_failed_transitions_uses_last_classification(self) -> None:
        """When multiple transitions fail, the last one's classification wins
        because the loop overwrites failure_class."""
        trail = _make_trail([
            {"task_id": "t1", "completion": "", "passed": False, "reward": 0.0},
            {"task_id": "t2", "completion": "short wrong", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        # Empty is checked first but overwritten by instruction_following
        assert report.failure_class == "instruction_following"
        assert report.meta["failed"] == 2

    def test_pass_rate_calculation(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "ok", "passed": True, "reward": 1.0},
            {"task_id": "t2", "completion": "no", "passed": False, "reward": 0.0},
            {"task_id": "t3", "completion": "ok2", "passed": True, "reward": 1.0},
            {"task_id": "t4", "completion": "ok3", "passed": True, "reward": 1.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.meta["pass_rate"] == pytest.approx(0.75)
        assert report.meta["total_transitions"] == 4
        assert report.meta["passed"] == 3
        assert report.meta["failed"] == 1

    def test_only_stderr_no_completion_issue(self) -> None:
        """Transition with non-empty, short completion but timeout in stderr."""
        trail = _make_trail([
            {
                "task_id": "t1",
                "completion": "partial output",
                "passed": False,
                "reward": 0.0,
                "meta": {"trail_stderr": "TIMEOUT: generation exceeded 60s"},
            },
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "timeout"

    def test_report_trail_id_and_suite(self) -> None:
        trail = _make_trail(
            [{"task_id": "t1", "completion": "x", "passed": False, "reward": 0.0}],
            suite="my-suite",
            run_id="run-99",
        )
        report = HeuristicCritic().analyze(trail)
        assert report.trail_id == "run-99"
        assert report.suite_name == "my-suite"


# ---------------------------------------------------------------------------
# ForgeCritic tests
# ---------------------------------------------------------------------------


class TestForgeCritic:
    def _prepare_trail(self, trail: Trail) -> Trail:
        """Set attributes ForgeCritic expects but Trail doesn't have."""
        trail.trail_id = trail.run_id
        trail.suite_name = trail.suite
        return trail

    def test_summarise_basic(self) -> None:
        trail = self._prepare_trail(_make_trail([
            {"task_id": "t1", "completion": "hello world", "passed": True, "reward": 1.0},
            {"task_id": "t2", "completion": "bad", "passed": False, "reward": 0.0},
        ]))
        critic = ForgeCritic()
        summary = critic._summarise(trail)
        assert "Trail:" in summary
        assert "test-suite" in summary
        assert "test-model" in summary
        assert "Total transitions: 2" in summary
        assert "t1" in summary
        assert "t2" in summary

    def test_summarise_long_completion_truncated(self) -> None:
        long = "x" * 200
        trail = self._prepare_trail(_make_trail([
            {"task_id": "t1", "completion": long, "passed": False, "reward": 0.0},
        ]))
        summary = ForgeCritic()._summarise(trail)
        # completion should be truncated to 80 chars
        assert "x" * 80 in summary
        assert "x" * 81 not in summary

    def test_summarise_first_5_only(self) -> None:
        transitions = [
            {"task_id": f"t{i}", "completion": f"comp-{i}", "passed": False, "reward": 0.0}
            for i in range(10)
        ]
        trail = self._prepare_trail(_make_trail(transitions))
        summary = ForgeCritic()._summarise(trail)
        assert "t0" in summary
        assert "t4" in summary
        assert "t5" not in summary

    def test_analyze_with_forge_success(self) -> None:
        trail = self._prepare_trail(_make_trail([
            {"task_id": "t1", "completion": "bad", "passed": False, "reward": 0.0},
        ]))

        mock_proc = MagicMock()
        mock_proc.stdout = "This is a timeout issue due to slow generation."

        critic = ForgeCritic()
        with patch("bench.rlvr_af.critic.subprocess.run", return_value=mock_proc):
            report = critic.analyze(trail)

        assert report.confidence == 0.7
        assert "forge_reply_length" in report.meta
        assert report.meta["forge_reply_length"] > 0

    def test_analyze_with_forge_exception(self) -> None:
        trail = self._prepare_trail(_make_trail([
            {"task_id": "t1", "completion": "", "passed": False, "reward": 0.0},
        ]))

        critic = ForgeCritic()
        with patch(
            "bench.rlvr_af.critic.subprocess.run",
            side_effect=OSError("binary not found"),
        ):
            report = critic.analyze(trail)

        # Falls back to heuristic
        assert report.failure_class == "empty_completion"
        assert "forge error" in report.root_cause.lower()
        assert report.confidence == 0.7

    def test_analyze_with_forge_empty_stdout(self) -> None:
        trail = self._prepare_trail(_make_trail([
            {"task_id": "t1", "completion": "ok", "passed": True, "reward": 1.0},
        ]))

        mock_proc = MagicMock()
        mock_proc.stdout = ""

        critic = ForgeCritic()
        with patch("bench.rlvr_af.critic.subprocess.run", return_value=mock_proc):
            report = critic.analyze(trail)

        # Heuristic says all passed, so root_cause should come from heuristic
        assert "No root cause" in report.root_cause
        assert report.confidence == 0.7

    def test_analyze_trail_attributes_used(self) -> None:
        trail = self._prepare_trail(_make_trail(
            [{"task_id": "t1", "completion": "x", "passed": False, "reward": 0.0}],
            suite="forge-suite",
            model="forge-model",
            run_id="forge-run-001",
        ))
        mock_proc = MagicMock()
        mock_proc.stdout = "analysis"

        critic = ForgeCritic()
        with patch("bench.rlvr_af.critic.subprocess.run", return_value=mock_proc):
            report = critic.analyze(trail)

        assert report.trail_id == "forge-run-001"
        assert report.suite_name == "forge-suite"

# ---------------------------------------------------------------------------
# register_critic / get_critic tests
# ---------------------------------------------------------------------------


class TestCriticRegistry:
    def test_get_default_returns_heuristic(self) -> None:
        critic = get_critic()
        assert isinstance(critic, HeuristicCritic)

    def test_get_heuristic_explicitly(self) -> None:
        critic = get_critic("heuristic")
        assert isinstance(critic, HeuristicCritic)

    def test_get_forge(self) -> None:
        critic = get_critic("forge")
        assert isinstance(critic, ForgeCritic)

    def test_get_unknown_falls_back_to_heuristic(self) -> None:
        critic = get_critic("nonexistent-key")
        assert isinstance(critic, HeuristicCritic)

    def test_register_custom_critic(self) -> None:
        class CustomCritic(BaseCritic):
            def analyze(self, trail: Trail) -> CriticReport:
                return CriticReport(trail_id="custom", suite_name="custom")

        register_critic("custom-test", CustomCritic)
        critic = get_critic("custom-test")
        assert isinstance(critic, CustomCritic)
        assert isinstance(critic.analyze(_make_trail()), CriticReport)

    def test_register_overwrites_previous(self) -> None:
        class CriticA(BaseCritic):
            def analyze(self, trail: Trail) -> CriticReport:
                return CriticReport(trail_id="A", suite_name="A")

        class CriticB(BaseCritic):
            def analyze(self, trail: Trail) -> CriticReport:
                return CriticReport(trail_id="B", suite_name="B")

        register_critic("overwrite-test", CriticA)
        register_critic("overwrite-test", CriticB)
        critic = get_critic("overwrite-test")
        report = critic.analyze(_make_trail())
        assert report.trail_id == "B"

    def test_get_returns_new_instance_each_call(self) -> None:
        a = get_critic("heuristic")
        b = get_critic("heuristic")
        assert a is not b


# ---------------------------------------------------------------------------
# Edge case: transition without verdict
# ---------------------------------------------------------------------------


class TestNoVerdictTransitions:
    def test_no_verdict_transition_index(self) -> None:
        trail = Trail(suite="s", model="m", run_id="r", seed=1)
        artifact = Artifact(elapsed_s=0.5, prompt="p", completion="hello")
        artifact.task_id = "t1"
        artifact.meta = {}
        t = Transition(task_id="t1", artifact=artifact, verdict=None)
        t.index = 0
        trail.add(t)
        report = HeuristicCritic().analyze(trail)
        assert report.meta["failed"] == 0
        assert report.meta["passed"] == 0
        assert "No root cause" in report.root_cause


# ---------------------------------------------------------------------------
# HeuristicCritic: stderr with non-lowercase timeout keyword
# ---------------------------------------------------------------------------


class TestTimeoutCaseInsensitive:
    def test_timeout_keyword_case_insensitive(self) -> None:
        trail = _make_trail([
            {
                "task_id": "t1",
                "completion": "output",
                "passed": False,
                "reward": 0.0,
                "meta": {"trail_stderr": "TIMEOUT exceeded"},
            },
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "timeout"


# ---------------------------------------------------------------------------
# HeuristicCritic: error: prefix exact
# ---------------------------------------------------------------------------


class TestErrorPrefixExact:
    def test_error_colon_prefix(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "error: model not found", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "internal_error"

    def test_bracket_error_prefix(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "[error] stack overflow", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "internal_error"


# ---------------------------------------------------------------------------
# HeuristicCritic: whitespace-only completion
# ---------------------------------------------------------------------------


class TestWhitespaceCompletion:
    def test_whitespace_only_is_empty(self) -> None:
        trail = _make_trail([
            {"task_id": "t1", "completion": "   \n\t  ", "passed": False, "reward": 0.0},
        ])
        report = HeuristicCritic().analyze(trail)
        assert report.failure_class == "empty_completion"
