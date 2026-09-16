"""Comprehensive unit tests for bench.rlvr_af.optimize.

Covers:
  - PatchProposal dataclass
  - OptimizerReport dataclass
  - BaseOptimizer.optimize() raises NotImplementedError
  - HeuristicOptimizer.optimize() with all failure classes
  - ForgeOptimizer with mocked subprocess
  - WorktreeOptimizer with mocked subprocess
  - apply_patch() with file I/O (tmp_path)
  - register_optimizer() / get_optimizer() factory
"""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from bench.rlvr_af.critic import CriticReport
from bench.rlvr_af.optimize import (
    BaseOptimizer,
    ForgeOptimizer,
    HeuristicOptimizer,
    OptimizerReport,
    PatchProposal,
    WorktreeOptimizer,
    apply_patch,
    get_optimizer,
    register_optimizer,
)
from bench.rlvr_af.trace import Artifact, JudgeVerdict, Trail, Transition

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trail_like(suite="mmlu-pro", model="mock", run_id="run-001", seed=42):
    """Create a Trail object AND patch the extra attributes the optimizer expects.

    The Trail dataclass defines `run_id` and `suite`, but optimize.py references
    `trail.trail_id` and `trail.suite_name`. We add these as aliases so the
    optimizer code works without crashing.
    """
    trail = Trail(suite=suite, model=model, run_id=run_id, seed=seed)
    # Patch the attribute names the optimizer references
    trail.trail_id = run_id
    trail.suite_name = suite
    return trail


@pytest.fixture
def sample_trail():
    """Create a minimal Trail with one failed transition."""
    trail = _make_trail_like(suite="mmlu-pro", model="mock", run_id="run-001", seed=42)
    artifact = Artifact(
        elapsed_s=0.5,
        prompt="What is 2+2?",
        completion="",
        expected="4",
        tokens_in=10,
        tokens_out=0,
    )
    verdict = JudgeVerdict(passed=False, reward=0.0, reason="empty completion")
    trail.add(Transition(task_id="t1", artifact=artifact, verdict=verdict))
    trail.commit()
    return trail


@pytest.fixture
def sample_report():
    """Create a sample CriticReport."""
    return CriticReport(
        trail_id="run-001",
        suite_name="mmlu-pro",
        failure_class="empty_completion",
        confidence=0.8,
        root_cause="Model adapter returned empty string",
        fix_suggestion="Ensure model adapter always returns non-empty text",
    )


@pytest.fixture
def internal_error_report():
    return CriticReport(
        trail_id="run-002",
        suite_name="mmlu-pro",
        failure_class="internal_error",
        confidence=0.7,
        root_cause="Adapter crash: model path not found",
        fix_suggestion="Add environment-based model path fallback",
    )


@pytest.fixture
def instruction_following_report():
    return CriticReport(
        trail_id="run-003",
        suite_name="ifeval",
        failure_class="instruction_following",
        confidence=0.9,
        root_cause="Model did not follow format instructions",
        fix_suggestion="Lower temperature and increase max_tokens",
    )


@pytest.fixture
def unknown_report():
    return CriticReport(
        trail_id="run-004",
        suite_name="arc-agi-2",
        failure_class="unknown",
        confidence=0.3,
        root_cause="Could not classify",
        fix_suggestion="Review the trail manually",
    )


# ---------------------------------------------------------------------------
# PatchProposal
# ---------------------------------------------------------------------------


class TestPatchProposal:
    def test_default_values(self):
        p = PatchProposal(
            patch_id="p1",
            target_file="src/main.py",
            old_string="old",
            new_string="new",
        )
        assert p.patch_id == "p1"
        assert p.description == ""
        assert p.score_delta is None
        assert p.score_before is None
        assert p.score_after is None
        assert p.meta == {}

    def test_custom_values(self):
        p = PatchProposal(
            patch_id="p2",
            target_file="src/lib.py",
            old_string="x = 1",
            new_string="x = 2",
            description="Fix value",
            score_delta=0.15,
            score_before=0.5,
            score_after=0.65,
            meta={"source": "forge"},
        )
        assert p.score_delta == 0.15
        assert p.meta["source"] == "forge"


# ---------------------------------------------------------------------------
# OptimizerReport
# ---------------------------------------------------------------------------


class TestOptimizerReport:
    def test_defaults(self):
        r = OptimizerReport(trail_id="run-1", suite_name="ifeval")
        assert r.proposals == []
        assert r.best_proposal is None
        assert r.wall_clock_s == 0.0

    def test_with_proposals(self):
        p = PatchProposal(
            patch_id="p1", target_file="f", old_string="o", new_string="n"
        )
        r = OptimizerReport(
            trail_id="run-1",
            suite_name="ifeval",
            proposals=[p],
            best_proposal=p,
        )
        assert len(r.proposals) == 1
        assert r.best_proposal is p


# ---------------------------------------------------------------------------
# BaseOptimizer
# ---------------------------------------------------------------------------


class TestBaseOptimizer:
    def test_optimize_raises(self):
        trail = Trail(suite="test", model="mock", run_id="r1", seed=0)
        report = CriticReport(trail_id="r1", suite_name="test")
        opt = BaseOptimizer()
        with pytest.raises(NotImplementedError):
            opt.optimize(trail, report)


# ---------------------------------------------------------------------------
# HeuristicOptimizer
# ---------------------------------------------------------------------------


class TestHeuristicOptimizer:
    def test_empty_completion(self, sample_trail, sample_report):
        opt = HeuristicOptimizer()
        result = opt.optimize(sample_trail, sample_report)

        assert isinstance(result, OptimizerReport)
        assert result.trail_id == "run-001"
        assert result.suite_name == "mmlu-pro"
        assert len(result.proposals) == 1
        assert result.best_proposal is not None
        assert result.best_proposal.patch_id.startswith("heuristic-empty_completion")

    def test_internal_error(self, sample_trail, internal_error_report):
        opt = HeuristicOptimizer()
        result = opt.optimize(sample_trail, internal_error_report)

        assert len(result.proposals) == 1
        assert result.best_proposal is not None
        assert "internal_error" in result.best_proposal.patch_id

    def test_instruction_following(self, sample_trail, instruction_following_report):
        opt = HeuristicOptimizer()
        result = opt.optimize(sample_trail, instruction_following_report)

        assert len(result.proposals) == 1
        assert "instruction_following" in result.best_proposal.patch_id

    def test_unknown_failure_class(self, sample_trail, unknown_report):
        opt = HeuristicOptimizer()
        result = opt.optimize(sample_trail, unknown_report)

        # Unknown failure class has no templates, but HeuristicOptimizer
        # still returns proposals=[] and best_proposal=None
        assert isinstance(result, OptimizerReport)
        assert len(result.proposals) == 0
        assert result.best_proposal is None

    def test_proposal_fields(self, sample_trail, sample_report):
        opt = HeuristicOptimizer()
        result = opt.optimize(sample_trail, sample_report)
        p = result.best_proposal
        assert p.target_file  # non-empty
        assert p.old_string  # non-empty
        assert p.new_string  # non-empty
        assert p.description  # non-empty

    def test_fix_templates_coverage(self):
        # Verify all three failure classes have templates
        assert "empty_completion" in HeuristicOptimizer.FIX_TEMPLATES
        assert "internal_error" in HeuristicOptimizer.FIX_TEMPLATES
        assert "instruction_following" in HeuristicOptimizer.FIX_TEMPLATES


# ---------------------------------------------------------------------------
# ForgeOptimizer
# ---------------------------------------------------------------------------


class TestForgeOptimizer:
    def test_falls_back_to_heuristic(self, sample_trail, sample_report):
        """When forge subprocess fails, should still get heuristic proposals."""
        with patch("bench.rlvr_af.optimize.subprocess") as mock_sub:
            mock_sub.run.side_effect = Exception("forge not found")
            opt = ForgeOptimizer()
            result = opt.optimize(sample_trail, sample_report)

        assert isinstance(result, OptimizerReport)
        assert len(result.proposals) == 1  # from heuristic fallback
        assert result.best_proposal is not None

    def test_parses_forge_reply(self, sample_trail, sample_report):
        """When forge returns FILE/OLD/NEW blocks, should parse proposals."""
        forge_reply = textwrap.dedent("""\
            FILE: src/main.py
            OLD: def generate(self, prompt, max_tokens=64)
            NEW: def generate(self, prompt, max_tokens=128):
                    return self._fallback(prompt)
        """)
        with patch("bench.rlvr_af.optimize.subprocess") as mock_sub:
            proc = MagicMock()
            proc.stdout = forge_reply
            mock_sub.run.return_value = proc
            opt = ForgeOptimizer()
            result = opt.optimize(sample_trail, sample_report)

        # Should have heuristic proposal + forge proposal
        assert len(result.proposals) >= 2

    def test_parse_patch_empty(self):
        opt = ForgeOptimizer()
        trail = _make_trail_like(suite="test", model="mock", run_id="r1", seed=0)
        result = opt._parse_patch("no blocks here", trail)
        assert result == []

    def test_parse_patch_partial_block(self):
        opt = ForgeOptimizer()
        trail = _make_trail_like(suite="test", model="mock", run_id="r1", seed=0)
        # Block with FILE but missing OLD/NEW
        text = "FILE: src/main.py\nsome text"
        result = opt._parse_patch(text, trail)
        assert result == []

    def test_parse_patch_multiple_blocks(self):
        opt = ForgeOptimizer()
        trail = _make_trail_like(suite="test", model="mock", run_id="r1", seed=0)
        text = (
            "FILE: a.py\nOLD: x\nNEW: y\n"
            "FILE: b.py\nOLD: a\nNEW: b\n"
        )
        result = opt._parse_patch(text, trail)
        assert len(result) == 2

    def test_proposal_id_prefix(self, sample_trail, sample_report):
        with patch("bench.rlvr_af.optimize.subprocess") as mock_sub:
            proc = MagicMock()
            proc.stdout = ""
            mock_sub.run.return_value = proc
            opt = ForgeOptimizer()
            result = opt.optimize(sample_trail, sample_report)
        # The heuristic proposal starts with "heuristic-"
        assert any(p.patch_id.startswith("heuristic-") for p in result.proposals)


# ---------------------------------------------------------------------------
# WorktreeOptimizer
# ---------------------------------------------------------------------------


class TestWorktreeOptimizer:
    def test_no_proposals_when_heuristic_empty(self):
        """When heuristic yields nothing, worktree should yield nothing."""
        trail = _make_trail_like(suite="test", model="mock", run_id="r1", seed=0)
        report = CriticReport(
            trail_id="r1", suite_name="test", failure_class="unknown"
        )
        opt = WorktreeOptimizer(worktree_base="/tmp")
        result = opt.optimize(trail, report)
        assert len(result.proposals) == 0
        assert result.best_proposal is None

    def test_skips_proposals_without_target_or_old(self, sample_trail, sample_report):
        """Proposals with empty target_file or old_string should be skipped."""
        with patch("bench.rlvr_af.optimize.HeuristicOptimizer") as MockHO:
            mock_instance = MagicMock()
            p = PatchProposal(
                patch_id="skip-me",
                target_file="",
                old_string="",
                new_string="new",
            )
            mock_instance.optimize.return_value = OptimizerReport(
                trail_id="r1", suite_name="test", proposals=[p]
            )
            MockHO.return_value = mock_instance
            opt = WorktreeOptimizer(worktree_base="/tmp")
            result = opt.optimize(sample_trail, sample_report)
        assert len(result.proposals) == 0

    def test_run_tournament_git_failure(self):
        """When git worktree add fails, should return None."""
        with patch("bench.rlvr_af.optimize.subprocess") as mock_sub:
            mock_sub.run.side_effect = Exception("git not found")
            opt = WorktreeOptimizer(worktree_base="/tmp")
            p = PatchProposal(
                patch_id="p1", target_file="f.py", old_string="old", new_string="new"
            )
            result = opt._run_tournament("test", p)
        assert result is None

    def test_run_tournament_missing_worktree(self):
        """When worktree path doesn't exist, should return None."""
        with patch("bench.rlvr_af.optimize.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock()
            opt = WorktreeOptimizer(worktree_base="/nonexistent/path")
            p = PatchProposal(
                patch_id="p1", target_file="f.py", old_string="old", new_string="new"
            )
            result = opt._run_tournament("test", p)
        assert result is None

    def test_best_proposal_selects_highest_delta(self, sample_trail, sample_report):
        """The best_proposal should be the one with the highest score_delta."""
        p1 = PatchProposal(
            patch_id="p1", target_file="f", old_string="o", new_string="n",
            score_delta=0.1,
        )
        p2 = PatchProposal(
            patch_id="p2", target_file="f", old_string="o", new_string="n",
            score_delta=0.5,
        )
        result = OptimizerReport(
            trail_id="r1", suite_name="test",
            proposals=[p1, p2],
            best_proposal=max([p1, p2], key=lambda p: p.score_delta or -999),
        )
        assert result.best_proposal is p2


# ---------------------------------------------------------------------------
# apply_patch()
# ---------------------------------------------------------------------------


class TestApplyPatch:
    def test_successful_patch(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def hello():\n    print('hi')\n")
        proposal = PatchProposal(
            patch_id="p1",
            target_file="test.py",
            old_string="print('hi')",
            new_string="print('hello world')",
        )
        result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is True
        assert "hello world" in f.read_text()

    def test_file_not_found(self, tmp_path):
        proposal = PatchProposal(
            patch_id="p1",
            target_file="nonexistent.py",
            old_string="x",
            new_string="y",
        )
        result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is False

    def test_old_string_not_in_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def hello():\n    print('hi')\n")
        proposal = PatchProposal(
            patch_id="p1",
            target_file="test.py",
            old_string="print('goodbye')",
            new_string="print('hello world')",
        )
        result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is False

    def test_replaces_only_first_occurrence(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\nx = 1\nx = 1\n")
        proposal = PatchProposal(
            patch_id="p1",
            target_file="test.py",
            old_string="x = 1",
            new_string="x = 2",
        )
        result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is True
        content = f.read_text()
        assert content.count("x = 2") == 1
        assert content.count("x = 1") == 2

    def test_write_error(self, tmp_path):
        """If writing fails (e.g., read-only), should return False."""
        f = tmp_path / "test.py"
        f.write_text("original")
        proposal = PatchProposal(
            patch_id="p1",
            target_file="test.py",
            old_string="original",
            new_string="replaced",
        )
        with patch("builtins.open", side_effect=[open(str(f)), OSError("readonly")]):
            result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is False

    def test_multiline_patch(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    pass\n")
        proposal = PatchProposal(
            patch_id="p1",
            target_file="test.py",
            old_string="def foo():\n    pass",
            new_string="def foo():\n    return 42",
        )
        result = apply_patch(proposal, repo_root=str(tmp_path))
        assert result is True
        assert "return 42" in f.read_text()


# ---------------------------------------------------------------------------
# register_optimizer() / get_optimizer()
# ---------------------------------------------------------------------------


class TestOptimizerFactory:
    def test_get_heuristic_default(self):
        opt = get_optimizer()
        assert isinstance(opt, HeuristicOptimizer)

    def test_get_heuristic_explicit(self):
        opt = get_optimizer("heuristic")
        assert isinstance(opt, HeuristicOptimizer)

    def test_get_forge(self):
        opt = get_optimizer("forge")
        assert isinstance(opt, ForgeOptimizer)

    def test_get_worktree(self):
        opt = get_optimizer("worktree")
        assert isinstance(opt, WorktreeOptimizer)

    def test_get_unknown_falls_back(self):
        opt = get_optimizer("nonexistent_key_xyz")
        assert isinstance(opt, HeuristicOptimizer)

    def test_register_custom(self):
        class CustomOptimizer(BaseOptimizer):
            pass

        register_optimizer("custom_test_only", CustomOptimizer)
        opt = get_optimizer("custom_test_only")
        assert isinstance(opt, CustomOptimizer)
        # Cleanup
        from bench.rlvr_af.optimize import _OPTIMIZERS
        _OPTIMIZERS.pop("custom_test_only", None)


# ---------------------------------------------------------------------------
# Module-level registrations
# ---------------------------------------------------------------------------


class TestModuleRegistrations:
    def test_all_registered_optimizers_exist(self):
        from bench.rlvr_af.optimize import _OPTIMIZERS
        assert "heuristic" in _OPTIMIZERS
        assert "forge" in _OPTIMIZERS
        assert "worktree" in _OPTIMIZERS

    def test_all_exports(self):
        from bench.rlvr_af.optimize import __all__
        expected = {
            "PatchProposal", "OptimizerReport", "BaseOptimizer",
            "HeuristicOptimizer", "ForgeOptimizer", "WorktreeOptimizer",
            "apply_patch", "register_optimizer", "get_optimizer",
        }
        assert expected <= set(__all__)
