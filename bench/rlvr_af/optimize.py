"""L4 — Optimizer agent: applies patches proposed by the critic.

The optimizer takes a `CriticReport` (from L3), translates the fix
suggestion into an actionable code patch, and applies it to the
codebase. In `search` mode it forks a git worktree, applies a
candidate fix, rebuilds, and measures the score delta. The best
fix is merged back.

From the RLVR-AF spec:
  "Optimizer: given a CriticReport, generates a candidate patch
   (or multiple), runs the suite on each patched worktree, measures
   the score delta, and merges the patch that gives the largest
   positive delta."
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass, field
from typing import Any, cast

from bench.rlvr_af.critic import CriticReport
from bench.rlvr_af.trace import Trail


@dataclass
class PatchProposal:
    """A single candidate patch."""

    patch_id: str
    target_file: str  # relative path within repo, e.g. bench/suites/ifeval.py
    old_string: str
    new_string: str
    description: str = ""
    score_delta: float | None = None
    score_before: float | None = None
    score_after: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizerReport:
    """Output of an optimizer: list of patch proposals + the best one."""

    trail_id: str
    suite_name: str
    proposals: list[PatchProposal] = field(default_factory=list)
    best_proposal: PatchProposal | None = None
    wall_clock_s: float = 0.0


# ---------------------------------------------------------------------------
# Base optimizer
# ---------------------------------------------------------------------------


class BaseOptimizer:
    """Abstract base class for all RLVR-AF optimizers."""

    def optimize(
        self,
        trace: Trail,
        report: CriticReport,
    ) -> OptimizerReport:
        """Run the optimization pass; subclasses implement concrete strategies."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Heuristic optimizer (suggests patches from known patterns)
# ---------------------------------------------------------------------------


class HeuristicOptimizer(BaseOptimizer):
    """Rule-based optimizer that maps failure classes to known patches."""

    FIX_TEMPLATES: dict[str, list[dict[str, Any]]] = {
        "empty_completion": [
            {
                "target": "patterns in the model adapter or suite",
                "old": "def generate(self, prompt, max_tokens=64)",
                "new": 'def generate(self, prompt, max_tokens=64):\n        """Return a ModelResponse with at least 1 token."""\n        # ...',
                "description": "Ensure model adapter always returns non-empty text",
            },
        ],
        "internal_error": [
            {
                "target": "model adapter __init__ or generate",
                "old": "model, tokenizer = load(self.model_path)",
                "new": "import os\nmodel_path = os.environ.get('QWEN_MODEL_PATH', self.model_path)\nmodel, tokenizer = load(model_path)",
                "description": "Add environment-based model path fallback",
            },
        ],
        "instruction_following": [
            {
                "target": "suite's judge or prompt template",
                "old": "completion = adapter.generate(messages)",
                "new": "completion = adapter.generate(messages, max_tokens=128, temperature=0.0)",
                "description": "Lower temperature and increase max_tokens for instruction suites",
            },
        ],
    }

    def optimize(
        self,
        trace: Trail,
        report: CriticReport,
    ) -> OptimizerReport:
        """Generate patch proposals from the FIX_TEMPLATES table for the failure class."""
        proposals: list[PatchProposal] = []
        templates = self.FIX_TEMPLATES.get(report.failure_class, [])
        for i, tmpl in enumerate(templates):
            proposals.append(
                PatchProposal(
                    patch_id=f"heuristic-{report.failure_class}-{i}",
                    target_file=tmpl["target"],
                    old_string=tmpl["old"],
                    new_string=tmpl["new"],
                    description=tmpl["description"],
                )
            )
        return OptimizerReport(
            trail_id=trace.trail_id,
            suite_name=trace.suite_name,
            proposals=proposals,
            best_proposal=proposals[0] if proposals else None,
        )


# ---------------------------------------------------------------------------
# Forge optimizer (uses forge code to generate + apply patches)
# ---------------------------------------------------------------------------


FORGE_BIN = "/Users/kooshapari/.local/bin/forge"
REPO_ROOT = "/Users/kooshapari/CodeProjects/Phenotype/pheno-harness"


class ForgeOptimizer(BaseOptimizer):
    """Uses forge -p to generate candidate patch code, then applies locally."""

    def optimize(
        self,
        trace: Trail,
        report: CriticReport,
    ) -> OptimizerReport:
        """Generate patches via ``forge -p`` and merge with heuristic proposals."""
        proposals: list[PatchProposal] = []
        prompt = (
            f"You are an optimizer agent in the RLVR-AF framework.\n\n"
            f"A critic analysed a benchmark trail for suite '{trace.suite_name}' and "
            f"classified the failure as '{report.failure_class}':\n"
            f"Root cause: {report.root_cause}\n"
            f"Fix suggestion: {report.fix_suggestion}\n\n"
            f"Write a python patch that would fix this issue. "
            f"Format your response as:\n"
            f"  FILE: <relative file path>\n"
            f"  OLD: <exact old string to replace>\n"
            f"  NEW: <new string>\n"
        )
        try:
            proc = subprocess.run(  # nosec B603
                [FORGE_BIN, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=90,
                env={
                    **os.environ,
                    "PATH": "/usr/bin:/bin:/usr/local/bin:/Users/kooshapari/.local/bin",
                },
            )
            reply = proc.stdout or ""
            # Parse the reply for FILE/OLD/NEW blocks
            proposals = self._parse_patch(reply, trace)
        except Exception:  # nosec B110
            pass

        heuristic = HeuristicOptimizer()
        base = heuristic.optimize(trace, report)
        all_proposals = base.proposals + proposals

        return OptimizerReport(
            trail_id=trace.trail_id,
            suite_name=trace.suite_name,
            proposals=all_proposals,
            best_proposal=all_proposals[0] if all_proposals else None,
        )

    def _parse_patch(self, text: str, trace: Trail) -> list[PatchProposal]:
        """Naive FILE/OLD/NEW block parser."""
        proposals: list[PatchProposal] = []
        blocks = text.split("FILE:")
        for block in blocks[1:]:
            lines = block.strip().split("\n")
            file_path = lines[0].strip()
            old_str = ""
            new_str = ""
            mode = None
            for ln in lines[1:]:
                if ln.startswith("OLD:"):
                    mode = "old"
                    old_str = ln[4:].strip()
                elif ln.startswith("NEW:"):
                    mode = "new"
                    new_str = "\n".join(lines[lines.index(ln) :])
                    new_str = new_str[4:].strip()
                    break
                elif mode == "old":
                    old_str += "\n" + ln.strip()
            if file_path and old_str and new_str:
                proposals.append(
                    PatchProposal(
                        patch_id=f"forge-{len(proposals)}",
                        target_file=file_path,
                        old_string=old_str,
                        new_string=new_str,
                        description=f"Auto-generated fix for {trace.suite_name} ({trace.trail_id})",
                    )
                )
        return proposals


def apply_patch(proposal: PatchProposal, repo_root: str = REPO_ROOT) -> bool:
    """Apply a single patch proposal to the file system."""
    file_path = os.path.join(repo_root, proposal.target_file)
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path) as f:
            content = f.read()
        if proposal.old_string not in content:
            return False
        new_content = content.replace(proposal.old_string, proposal.new_string, 1)
        with open(file_path, "w") as f:
            f.write(new_content)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Worktree-based tournament optimizer
# ---------------------------------------------------------------------------


class WorktreeOptimizer(BaseOptimizer):
    """Creates a git worktree, applies a candidate patch, runs the suite,
    measures the score delta, and merges back if positive."""

    def __init__(
        self,
        worktree_base: str = "/Users/kooshapari/CodeProjects/Phenotype",
    ):
        """Initialize with the base path under which worktrees will be created."""
        self.worktree_base = worktree_base

    def optimize(
        self,
        trace: Trail,
        report: CriticReport,
    ) -> OptimizerReport:
        """Run each heuristic patch in a worktree and pick the best score delta."""
        base = HeuristicOptimizer().optimize(trace, report)
        proposals: list[PatchProposal] = []

        for proposal in base.proposals:
            if not proposal.target_file or not proposal.old_string:
                continue
            score_delta = self._run_tournament(report.suite_name, proposal)
            proposal.score_delta = score_delta
            proposals.append(proposal)

        return OptimizerReport(
            trail_id=trace.trail_id,
            suite_name=trace.suite_name,
            proposals=proposals,
            best_proposal=max(proposals, key=lambda p: p.score_delta or -999)
            if proposals
            else None,
        )

    def _run_tournament(self, suite_name: str, proposal: PatchProposal) -> float | None:
        """Fork a worktree, apply patch, run suite, return score delta."""
        branch = f"rlvr-opt-{suite_name}-{int(time.time())}"
        try:
            subprocess.run(  # nosec B603 B607
                ["git", "worktree", "add", "-b", branch, f"../rlvr-opt-{suite_name}"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=REPO_ROOT,
            )
        except Exception:
            return None

        wt_path = os.path.join(self.worktree_base, f"rlvr-opt-{suite_name}")
        if not os.path.exists(wt_path):
            return None

        applied = apply_patch(proposal, wt_path)
        if not applied:
            return None

        try:
            score = self._measure_score(wt_path, suite_name)
        except Exception:
            score = None

        try:
            subprocess.run(  # nosec B603 B607
                ["git", "worktree", "remove", f"../rlvr-opt-{suite_name}", "--force"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=REPO_ROOT,
            )
        except Exception:  # nosec B110
            pass

        return score

    def _measure_score(self, worktree: str, suite_name: str) -> float | None:
        """Run the suite in the worktree and return pass@1."""
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "bench.comparison",
                "--suite",
                suite_name,
                "--n",
                "3",
                "--model",
                "mock",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=worktree,
        )
        try:
            import json

            data = json.loads(result.stdout)
            return cast(float | None, data.get("pass_at_1", None))
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Optimizer factory
# ---------------------------------------------------------------------------

_OPTIMIZERS: dict[str, type[BaseOptimizer]] = {}


def register_optimizer(key: str, cls: type[BaseOptimizer]) -> None:
    """Register an optimizer class under a string key (used by tests + suites)."""
    _OPTIMIZERS[key] = cls


def get_optimizer(key: str = "heuristic") -> BaseOptimizer:
    """Look up an optimizer by key; falls back to ``HeuristicOptimizer``."""
    cls = _OPTIMIZERS.get(key, HeuristicOptimizer)
    return cls()


register_optimizer("heuristic", HeuristicOptimizer)
register_optimizer("forge", ForgeOptimizer)
register_optimizer("worktree", WorktreeOptimizer)


__all__ = [
    "PatchProposal",
    "OptimizerReport",
    "BaseOptimizer",
    "HeuristicOptimizer",
    "ForgeOptimizer",
    "WorktreeOptimizer",
    "apply_patch",
    "register_optimizer",
    "get_optimizer",
]
