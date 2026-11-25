"""RLVR verifiers and reward functions (Phase 3).

This package exposes the harness, rewards, and gate primitives used by the
nested RLVR scoring in ``eval/nested_rlvr.py``.
"""

from verifier.harness import Verdict, VerifierHarness, VerifierResult
from verifier.rewards import Reward, RewardBreakdown, compute_rewards
from verifier.risky_action import GateResult, check_proposal, extract_proposed_command

__all__ = [
    "VerifierHarness",
    "VerifierResult",
    "Verdict",
    "RewardBreakdown",
    "Reward",
    "compute_rewards",
    "GateResult",
    "check_proposal",
    "extract_proposed_command",
]
