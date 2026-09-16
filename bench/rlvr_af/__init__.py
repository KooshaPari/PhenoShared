"""RLVR-AF optimization framework (5-layer architecture).

L1 — trace.py:   Trail → Transition → Artifact (structured transition/artifact trail)
L2 — verify.py:  JudgeVerdict → BaseVerifier / HeuristicVerifier / MLXVerifier
L3 — critic.py:  CriticReport → BaseCritic / HeuristicCritic
L4 — optimize.py: PatchProposal → OptimizerReport → BaseOptimizer / HeuristicOptimizer
L5 — tournament.py: TournamentRunner (orchestrates N iterations of L1-L4)

Usage:
    from bench.rlvr_af.tournament import TournamentRunner
    runner = TournamentRunner(suite=my_suite, model="mlx")
    result = runner.run()

    # Or one-shot:
    from bench.rlvr_af.tournament import run_tournament
    result = run_tournament("ifeval", model="mlx", n=3)
"""

from bench.rlvr_af.critic import (
    FAILURE_CLASSES,
    BaseCritic,
    CriticReport,
    ForgeCritic,
    HeuristicCritic,
    get_critic,
    register_critic,
)
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
from bench.rlvr_af.tournament import (
    TournamentIteration,
    TournamentResult,
    TournamentRunner,
    run_tournament,
)
from bench.rlvr_af.trace import Artifact, JudgeVerdict, Recorder, Trail, Transition
from bench.rlvr_af.verify import (
    BaseVerifier,
    HeuristicVerifier,
    MLXVerifier,
    get_verifier,
    register_verifier,
)

__all__ = [
    # L1 — trace
    "Artifact",
    "JudgeVerdict",
    "Transition",
    "Trail",
    "Recorder",
    # L2 — verify
    "BaseVerifier",
    "HeuristicVerifier",
    "MLXVerifier",
    "register_verifier",
    "get_verifier",
    # L3 — critic
    "FAILURE_CLASSES",
    "CriticReport",
    "BaseCritic",
    "HeuristicCritic",
    "ForgeCritic",
    "register_critic",
    "get_critic",
    # L4 — optimize
    "PatchProposal",
    "OptimizerReport",
    "BaseOptimizer",
    "HeuristicOptimizer",
    "ForgeOptimizer",
    "WorktreeOptimizer",
    "apply_patch",
    "register_optimizer",
    "get_optimizer",
    # L5 — tournament
    "TournamentIteration",
    "TournamentResult",
    "TournamentRunner",
    "run_tournament",
]
