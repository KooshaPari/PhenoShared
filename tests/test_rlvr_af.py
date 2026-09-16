"""Smoke tests for the RLVR-AF module structure.

Import all RLVR-AF submodules and verify expected classes/functions exist.
These are import-level checks — no behavioral assertions.
"""

from __future__ import annotations

import inspect


def test_import_critic_module():
    from bench.rlvr_af import critic

    assert hasattr(critic, "FAILURE_CLASSES")
    assert isinstance(critic.FAILURE_CLASSES, dict)
    assert hasattr(critic, "CriticReport")
    assert hasattr(critic, "BaseCritic")
    assert hasattr(critic, "HeuristicCritic")
    assert hasattr(critic, "ForgeCritic")
    assert hasattr(critic, "register_critic")
    assert hasattr(critic, "get_critic")
    assert inspect.isclass(critic.CriticReport)
    assert inspect.isclass(critic.BaseCritic)
    assert inspect.isclass(critic.HeuristicCritic)
    assert inspect.isclass(critic.ForgeCritic)
    assert callable(critic.register_critic)
    assert callable(critic.get_critic)


def test_import_optimize_module():
    from bench.rlvr_af import optimize

    assert hasattr(optimize, "PatchProposal")
    assert hasattr(optimize, "OptimizerReport")
    assert hasattr(optimize, "BaseOptimizer")
    assert hasattr(optimize, "HeuristicOptimizer")
    assert hasattr(optimize, "ForgeOptimizer")
    assert hasattr(optimize, "WorktreeOptimizer")
    assert hasattr(optimize, "apply_patch")
    assert hasattr(optimize, "register_optimizer")
    assert hasattr(optimize, "get_optimizer")
    assert inspect.isclass(optimize.PatchProposal)
    assert inspect.isclass(optimize.OptimizerReport)
    assert inspect.isclass(optimize.BaseOptimizer)
    assert inspect.isclass(optimize.HeuristicOptimizer)
    assert callable(optimize.apply_patch)
    assert callable(optimize.register_optimizer)
    assert callable(optimize.get_optimizer)


def test_import_tournament_module():
    from bench.rlvr_af import tournament

    assert hasattr(tournament, "TournamentIteration")
    assert hasattr(tournament, "TournamentResult")
    assert hasattr(tournament, "TournamentRunner")
    assert hasattr(tournament, "run_tournament")
    assert inspect.isclass(tournament.TournamentIteration)
    assert inspect.isclass(tournament.TournamentResult)
    assert inspect.isclass(tournament.TournamentRunner)
    assert callable(tournament.run_tournament)


def test_import_trace_module():
    from bench.rlvr_af import trace

    assert hasattr(trace, "Artifact")
    assert hasattr(trace, "JudgeVerdict")
    assert hasattr(trace, "Transition")
    assert hasattr(trace, "Trail")
    assert hasattr(trace, "Recorder")
    assert inspect.isclass(trace.Artifact)
    assert inspect.isclass(trace.JudgeVerdict)
    assert inspect.isclass(trace.Transition)
    assert inspect.isclass(trace.Trail)
    assert inspect.isclass(trace.Recorder)


def test_import_verify_module():
    from bench.rlvr_af import verify

    assert hasattr(verify, "BaseVerifier")
    assert hasattr(verify, "HeuristicVerifier")
    assert hasattr(verify, "MLXVerifier")
    assert hasattr(verify, "register_verifier")
    assert hasattr(verify, "get_verifier")
    assert inspect.isclass(verify.BaseVerifier)
    assert inspect.isclass(verify.HeuristicVerifier)
    assert inspect.isclass(verify.MLXVerifier)
    assert callable(verify.register_verifier)
    assert callable(verify.get_verifier)


def test_import_package():
    from bench import rlvr_af

    assert hasattr(rlvr_af, "Artifact")
    assert hasattr(rlvr_af, "CriticReport")
    assert hasattr(rlvr_af, "PatchProposal")
    assert hasattr(rlvr_af, "TournamentRunner")
    assert hasattr(rlvr_af, "BaseVerifier")
