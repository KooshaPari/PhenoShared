"""Tests for bench.rlvr_af.tournament — targeting 80%+ coverage.

Covers TournamentIteration, TournamentResult dataclasses, TournamentRunner
init/run logic, critic/optimizer dispatch, patch application, exception
handling, and iteration tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bench.rlvr_af.critic import CriticReport, HeuristicCritic
from bench.rlvr_af.optimize import (
    HeuristicOptimizer,
    OptimizerReport,
    PatchProposal,
)
from bench.rlvr_af.tournament import (
    TournamentIteration,
    TournamentResult,
    TournamentRunner,
)
from bench.rlvr_af.trace import JudgeVerdict, Trail
from bench.rlvr_af.verify import HeuristicVerifier

# ---------------------------------------------------------------------------
# Helpers — plain objects instead of nested MagicMock to avoid Py3.14 issues
# ---------------------------------------------------------------------------


@dataclass
class _FakeTaskResult:
    """Lightweight stand-in for a task result with a status attribute."""

    status_value: str

    @property
    def status(self) -> Any:
        """Return an object whose .value matches the stored status string."""

        class _Status:
            def __init__(self, v: str) -> None:
                self.value = v

        return _Status(self.status_value)


@dataclass
class _FakeSuiteResult:
    """Lightweight stand-in for a suite.run() return value."""

    task_results: list[Any] = field(default_factory=list)


def _make_task_result(status_value: str) -> _FakeTaskResult:
    """Return a FakeTaskResult with the given status value."""
    return _FakeTaskResult(status_value=status_value)


def _make_suite_run_result(status_values: list[str]) -> _FakeSuiteResult:
    """Return a FakeSuiteResult with the given task statuses."""
    return _FakeSuiteResult(
        task_results=[_make_task_result(v) for v in status_values],
    )


class _FakeSuite:
    """Lightweight stand-in for a suite object used by TournamentRunner."""

    def __init__(self, name: str = "test-suite", results: list[_FakeSuiteResult] | None = None) -> None:
        self.name = name
        self._results = list(results) if results else []
        self._call_count = 0

    def run(self, spec: Any) -> _FakeSuiteResult:
        """Return the next pre-configured result."""
        if self._call_count < len(self._results):
            r = self._results[self._call_count]
        else:
            r = _FakeSuiteResult()
        self._call_count += 1
        return r


def _make_passing_suite(name: str = "test-suite", n_calls: int = 5) -> _FakeSuite:
    """Return a suite whose run() yields all-passing tasks."""
    return _FakeSuite(
        name=name,
        results=[_make_suite_run_result(["pass", "ok", "pass"]) for _ in range(n_calls)],
    )


def _make_failing_suite(name: str = "test-suite", n_calls: int = 5) -> _FakeSuite:
    """Return a suite whose run() yields some failing tasks."""
    return _FakeSuite(
        name=name,
        results=[_make_suite_run_result(["pass", "wrong", "pass"]) for _ in range(n_calls)],
    )


def _make_mock_critic(trail_id: str = "mock-trail", suite_name: str = "test-suite") -> MagicMock:
    """Return a mock critic whose analyze() returns a CriticReport."""
    critic = MagicMock()
    critic.analyze.return_value = CriticReport(
        trail_id=trail_id,
        suite_name=suite_name,
        failure_class="unknown",
        confidence=1.0,
    )
    return critic


def _make_mock_optimizer(
    trail_id: str = "mock-trail",
    suite_name: str = "test-suite",
    best_proposal: PatchProposal | None = None,
) -> MagicMock:
    """Return a mock optimizer whose optimize() returns an OptimizerReport."""
    optimizer = MagicMock()
    optimizer.optimize.return_value = OptimizerReport(
        trail_id=trail_id,
        suite_name=suite_name,
        best_proposal=best_proposal,
    )
    return optimizer


# ---------------------------------------------------------------------------
# TournamentIteration dataclass
# ---------------------------------------------------------------------------


class TestTournamentIteration:
    """Verify TournamentIteration dataclass field defaults."""

    def test_tournament_iteration_defaults(self) -> None:
        ti = TournamentIteration(
            iteration=0,
            trace=Trail(suite="s", model="m", run_id="r", seed=42),
            verdict=JudgeVerdict(passed=True, reward=1.0),
            critic_report=CriticReport(trail_id="t", suite_name="s"),
            optimizer_report=OptimizerReport(trail_id="t", suite_name="s"),
        )
        assert ti.patch_applied is False
        assert ti.score_before == 0.0
        assert ti.score_after == 0.0
        assert ti.wall_clock_s == 0.0
        assert ti.meta == {}

    def test_tournament_iteration_explicit_values(self) -> None:
        trail = Trail(suite="s", model="m", run_id="r", seed=42)
        verdict = JudgeVerdict(passed=False, reward=0.5)
        critic = CriticReport(trail_id="t", suite_name="s")
        optimizer = OptimizerReport(trail_id="t", suite_name="s")
        ti = TournamentIteration(
            iteration=2,
            trace=trail,
            verdict=verdict,
            critic_report=critic,
            optimizer_report=optimizer,
            patch_applied=True,
            score_before=0.3,
            score_after=0.7,
            wall_clock_s=1.5,
            meta={"key": "val"},
        )
        assert ti.iteration == 2
        assert ti.patch_applied is True
        assert ti.score_before == 0.3
        assert ti.score_after == 0.7
        assert ti.wall_clock_s == 1.5
        assert ti.meta == {"key": "val"}


# ---------------------------------------------------------------------------
# TournamentResult dataclass
# ---------------------------------------------------------------------------


class TestTournamentResult:
    """Verify TournamentResult dataclass field defaults."""

    def test_tournament_result_defaults(self) -> None:
        tr = TournamentResult(
            suite_name="s",
            model="m",
            n_iterations=1,
        )
        assert tr.iterations == []
        assert tr.final_score == 0.0
        assert tr.cumulative_delta == 0.0
        assert tr.total_wall_clock_s == 0.0
        assert tr.metadata == {}

    def test_tournament_result_explicit_values(self) -> None:
        tr = TournamentResult(
            suite_name="s",
            model="m",
            n_iterations=3,
            iterations=[],
            final_score=0.9,
            cumulative_delta=0.4,
            total_wall_clock_s=12.5,
            metadata={"a": 1},
        )
        assert tr.final_score == 0.9
        assert tr.cumulative_delta == 0.4
        assert tr.total_wall_clock_s == 12.5
        assert tr.metadata == {"a": 1}


# ---------------------------------------------------------------------------
# TournamentRunner.__init__
# ---------------------------------------------------------------------------


class TestTournamentRunnerInit:
    """Verify TournamentRunner constructor sets defaults correctly."""

    def test_tournament_runner_init_defaults(self) -> None:
        suite = _make_passing_suite()
        runner = TournamentRunner(suite)
        assert runner.suite is suite
        assert runner.model == "mock"
        assert isinstance(runner.verifier, HeuristicVerifier)
        assert isinstance(runner.critic, HeuristicCritic)
        assert isinstance(runner.optimizer, HeuristicOptimizer)
        assert runner.n == 3
        assert runner.score == 0.0

    def test_tournament_runner_custom_init(self) -> None:
        suite = _make_passing_suite("custom-suite")
        mock_verifier = MagicMock()
        mock_critic = MagicMock()
        mock_optimizer = MagicMock()
        runner = TournamentRunner(
            suite,
            model="gpt-4",
            verifier=mock_verifier,
            critic=mock_critic,
            optimizer=mock_optimizer,
            n=5,
            repo_root="/tmp/repo",
        )
        assert runner.model == "gpt-4"
        assert runner.verifier is mock_verifier
        assert runner.critic is mock_critic
        assert runner.optimizer is mock_optimizer
        assert runner.n == 5
        assert runner.repo_root == "/tmp/repo"


# ---------------------------------------------------------------------------
# TournamentRunner.run — dry / passing
# ---------------------------------------------------------------------------


class TestTournamentRunnerDryRun:
    """Verify run() with all-passing tasks produces a valid TournamentResult."""

    def test_tournament_runner_run_dry(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite,
            model="mock",
            critic=critic,
            optimizer=optimizer,
            n=1,
        )

        result = runner.run()

        assert isinstance(result, TournamentResult)
        assert result.suite_name == "test-suite"
        assert result.model == "mock"
        assert result.n_iterations == 1
        assert len(result.iterations) == 1
        assert result.final_score == 1.0  # all tasks pass -> reward 3/3
        # score_before == score_after in current impl -> delta == 0
        assert result.cumulative_delta == 0.0

        # Iteration fields populated
        it = result.iterations[0]
        assert it.iteration == 0
        assert it.verdict.passed is True
        assert it.verdict.reward == 1.0
        assert isinstance(it.trace, Trail)
        assert isinstance(it.critic_report, CriticReport)
        assert isinstance(it.optimizer_report, OptimizerReport)


# ---------------------------------------------------------------------------
# TournamentRunner.run — failures
# ---------------------------------------------------------------------------


class TestTournamentRunnerFailures:
    """Verify run() correctly marks verdict.passed=False for failing suites."""

    def test_tournament_runner_run_with_failures(self) -> None:
        suite = _make_failing_suite()  # pass, wrong, pass
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite,
            model="mock",
            critic=critic,
            optimizer=optimizer,
            n=1,
        )

        result = runner.run()

        it = result.iterations[0]
        assert it.verdict.passed is False  # 2/3 pass != 3/3 total
        assert it.verdict.reward == pytest.approx(2 / 3)
        assert result.final_score == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Multiple iterations
# ---------------------------------------------------------------------------


class TestTournamentRunnerMultipleIterations:
    """Verify run() with n>1 produces the correct number of iterations."""

    def test_tournament_runner_multiple_iterations(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite,
            model="mock",
            critic=critic,
            optimizer=optimizer,
            n=3,
        )

        result = runner.run()

        assert result.n_iterations == 3
        assert len(result.iterations) == 3
        for idx, it in enumerate(result.iterations):
            assert it.iteration == idx
        assert suite._call_count == 3


# ---------------------------------------------------------------------------
# Score tracking
# ---------------------------------------------------------------------------


class TestTournamentRunnerScoreTracking:
    """Verify final_score is set from the last iteration's verdict reward."""

    def test_tournament_runner_score_tracking(self) -> None:
        suite = _FakeSuite(
            name="score-suite",
            results=[
                _make_suite_run_result(["pass", "wrong", "wrong"]),
                _make_suite_run_result(["pass", "pass", "pass"]),
            ],
        )

        critic = _make_mock_critic(suite_name="score-suite")
        optimizer = _make_mock_optimizer(suite_name="score-suite")
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=2
        )

        result = runner.run()

        assert result.final_score == 1.0  # last iteration reward
        assert result.iterations[0].verdict.reward == pytest.approx(1 / 3)
        assert result.iterations[1].verdict.reward == 1.0


# ---------------------------------------------------------------------------
# Cumulative delta
# ---------------------------------------------------------------------------


class TestTournamentRunnerCumulativeDelta:
    """Verify cumulative_delta sums (score_after - score_before) across iterations.

    In the current implementation score_before == score_after (both set from
    the *same* verdict.reward), so cumulative_delta is always 0.0.
    """

    def test_tournament_runner_cumulative_delta(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=3
        )

        result = runner.run()

        expected_delta = sum(
            it.score_after - it.score_before for it in result.iterations
        )
        assert result.cumulative_delta == pytest.approx(expected_delta)


# ---------------------------------------------------------------------------
# Wall clock
# ---------------------------------------------------------------------------


class TestTournamentRunnerWallClock:
    """Verify total_wall_clock_s > 0 after a run."""

    def test_tournament_runner_wall_clock(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=2
        )

        result = runner.run()

        assert result.total_wall_clock_s > 0
        # Each iteration's wall clock should also be positive
        for it in result.iterations:
            assert it.wall_clock_s >= 0


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------


class TestTournamentRunnerPatchApplication:
    """Verify apply_patch is called when reward < 1.0 and best_proposal exists."""

    def test_tournament_runner_patch_applied(self) -> None:
        suite = _make_failing_suite()  # reward < 1.0
        critic = _make_mock_critic()

        proposal = PatchProposal(
            patch_id="p1",
            target_file="bench/suites/test.py",
            old_string="old",
            new_string="new",
        )
        optimizer = _make_mock_optimizer(best_proposal=proposal)

        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=1
        )

        with patch("bench.rlvr_af.tournament.apply_patch", return_value=True) as mock_apply:
            result = runner.run()

        mock_apply.assert_called_once_with(proposal)
        assert result.iterations[0].patch_applied is True

    def test_tournament_runner_no_patch_when_perfect(self) -> None:
        suite = _make_passing_suite()  # reward == 1.0
        critic = _make_mock_critic()

        proposal = PatchProposal(
            patch_id="p1",
            target_file="bench/suites/test.py",
            old_string="old",
            new_string="new",
        )
        optimizer = _make_mock_optimizer(best_proposal=proposal)

        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=1
        )

        with patch("bench.rlvr_af.tournament.apply_patch") as mock_apply:
            result = runner.run()

        mock_apply.assert_not_called()
        assert result.iterations[0].patch_applied is False


# ---------------------------------------------------------------------------
# Exception in suite.run
# ---------------------------------------------------------------------------


class TestTournamentRunnerExceptionHandling:
    """Verify the runner handles suite.run() exceptions gracefully."""

    def test_tournament_runner_exception_in_suite(self) -> None:

        class _ErrorSuite:
            name = "error-suite"

            def run(self, spec: Any) -> Any:
                raise RuntimeError("suite crashed")

        suite = _ErrorSuite()

        critic = _make_mock_critic(suite_name="error-suite")
        optimizer = _make_mock_optimizer(suite_name="error-suite")
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=2
        )

        result = runner.run()

        assert isinstance(result, TournamentResult)
        assert result.suite_name == "error-suite"
        assert len(result.iterations) == 2
        # Each iteration should have a failed verdict (reward 0.0)
        for it in result.iterations:
            assert it.verdict.passed is False
            assert it.verdict.reward == 0.0
        assert result.final_score == 0.0
        # The error message should be captured in trail.meta["output"]
        for it in result.iterations:
            assert "error" in it.trace.meta.get("output", {})


# ---------------------------------------------------------------------------
# Critic / optimizer dispatch
# ---------------------------------------------------------------------------


class TestTournamentRunnerComponentDispatch:
    """Verify critic.analyze() and optimizer.optimize() are called each iteration."""

    def test_tournament_runner_critic_called(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=3
        )

        runner.run()

        assert critic.analyze.call_count == 3
        # Each call should receive a Trail instance
        for call_args in critic.analyze.call_args_list:
            trail = call_args[0][0]
            assert isinstance(trail, Trail)

    def test_tournament_runner_optimizer_called(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=3
        )

        runner.run()

        assert optimizer.optimize.call_count == 3
        for call_args in optimizer.optimize.call_args_list:
            trail, critic_report = call_args[0]
            assert isinstance(trail, Trail)
            assert isinstance(critic_report, CriticReport)


# ---------------------------------------------------------------------------
# Trail structure
# ---------------------------------------------------------------------------


class TestTournamentRunnerTrailStructure:
    """Verify trail (Trace L1) is properly constructed with transitions."""

    def test_tournament_runner_trial_structure(self) -> None:
        suite = _make_passing_suite()
        critic = _make_mock_critic()
        optimizer = _make_mock_optimizer()
        runner = TournamentRunner(
            suite, model="mock", critic=critic, optimizer=optimizer, n=2
        )

        result = runner.run()

        from bench.rlvr_af.trace import Artifact

        for idx, it in enumerate(result.iterations):
            trail = it.trace
            # Trail should have correct metadata
            assert trail.suite == "test-suite"
            assert trail.model == "mock"
            assert trail.seed == 42
            # Trail should be committed (has committed_at set)
            assert trail.committed_at is not None
            # Trail should have at least one transition
            assert len(trail.transitions) >= 1
            # Transition should carry the artifact
            first_transition = trail.transitions[0]
            assert first_transition.task_id == f"iter-{idx}"
            assert isinstance(first_transition.artifact, Artifact)
            # Trail meta should contain suite output
            assert "output" in trail.meta


# ---------------------------------------------------------------------------
# run_tournament convenience function
# ---------------------------------------------------------------------------


class TestRunTournament:
    """Verify the run_tournament convenience function with mocked imports."""

    def test_run_tournament_module_path_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """run_tournament imports the suite module and uses registry fallback."""
        import importlib

        from bench.rlvr_af.critic import CriticReport
        from bench.rlvr_af.optimize import OptimizerReport

        # Create a fake module with a Suite class that has matching name
        # Use a plain class (not MagicMock) because dir() on MagicMock fails in Py3.14
        class _FakeSuiteClass:
            name = "my-suite"

            def __new__(cls) -> _FakeSuite:
                return _make_passing_suite("my-suite")

        class _FakeModule:
            MySuite = _FakeSuiteClass  # the class itself, not an instance

        # Mock importlib.import_module
        monkeypatch.setattr(importlib, "import_module", lambda path: _FakeModule)

        # Mock bench.registry.get_suite to return a passing suite factory
        from bench import registry

        def _fake_get_suite(name: str) -> MagicMock:
            mock_cls = MagicMock()
            mock_cls.return_value = _make_passing_suite(name)
            return mock_cls

        monkeypatch.setattr(registry, "get_suite", _fake_get_suite)

        # Mock HeuristicCritic.analyze and HeuristicOptimizer.optimize
        # to avoid Trail attribute errors (Trail has run_id not trail_id)
        from bench.rlvr_af import critic as critic_mod
        from bench.rlvr_af import optimize as optimize_mod

        def _mock_analyze(self, trail: Trail) -> CriticReport:
            return CriticReport(
                trail_id="mock", suite_name=trail.suite,
                failure_class="unknown", confidence=1.0,
            )

        def _mock_optimize(self, trail: Trail, report: CriticReport) -> OptimizerReport:
            return OptimizerReport(
                trail_id="mock", suite_name=trail.suite,
            )

        monkeypatch.setattr(critic_mod.HeuristicCritic, "analyze", _mock_analyze)
        monkeypatch.setattr(
            optimize_mod.HeuristicOptimizer, "optimize", _mock_optimize
        )

        from bench.rlvr_af.tournament import run_tournament

        result = run_tournament("my-suite", model="mock")

        assert isinstance(result, TournamentResult)
        assert result.model == "mock"
        # Note: run_tournament ignores n param — runner defaults to n=3
        assert result.n_iterations == 3

    def test_run_tournament_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """run_tournament re-raises ImportError for unknown suite modules."""
        import importlib

        def _fail_import(path: str) -> None:
            raise ImportError(f"No module named '{path}'")

        monkeypatch.setattr(importlib, "import_module", _fail_import)

        # Also mock registry.get_suite to raise
        from bench import registry

        def _fail_get_suite(name: str) -> None:
            raise ValueError(f"no suite: {name}")

        monkeypatch.setattr(registry, "get_suite", _fail_get_suite)

        from bench.rlvr_af.tournament import run_tournament

        with pytest.raises((ImportError, ValueError)):
            run_tournament("nonexistent-suite")
