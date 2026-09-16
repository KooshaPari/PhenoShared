"""Risky-action gate alias — canonical import path for the gate.

This module re-exports the gate implementation from ``verifier.risky_action``
under the canonical ``risky_action_gate`` name referenced by task 49.
"""

from __future__ import annotations

from verifier.risky_action import GateResult, check_proposal, extract_proposed_command

__all__ = ["GateResult", "check_proposal", "extract_proposed_command"]


def _load_gate_config() -> dict[str, object]:
    """Load the risky-action gate config (alias wrapper).

    Returns:
        Parsed config dict via ``verifier.risky_action._load_gate_config``.

    """
    from verifier.risky_action import _load_gate_config as _impl

    return _impl()


def _tier_for_command(cmd: str, cfg: dict[str, object]) -> str:
    """Classify a command tier (alias wrapper).

    Args:
        cmd: Proposed shell command.
        cfg: Loaded gate config.

    Returns:
        Risk tier string.

    """
    from verifier.risky_action import _tier_for_command as _impl

    return _impl(cmd, cfg)


def _check_secrets(cmd: str, cfg: dict[str, object]) -> tuple[bool, str | None]:
    """Check secrets (alias wrapper).

    Args:
        cmd: Proposed shell command.
        cfg: Loaded gate config.

    Returns:
        Tuple of (ok, error).

    """
    from verifier.risky_action import _check_secrets as _impl

    return _impl(cmd, cfg)


def _check_allowlist(cmd: str, cfg: dict[str, object]) -> tuple[bool, str | None]:
    """Check allowlist (alias wrapper).

    Args:
        cmd: Proposed shell command.
        cfg: Loaded gate config.

    Returns:
        Tuple of (ok, error).

    """
    from verifier.risky_action import _check_allowlist as _impl

    return _impl(cmd, cfg)


def _dry_run_proposal(cmd: str) -> tuple[bool, str | None]:
    """Dry-run proposal (alias wrapper).

    Args:
        cmd: Proposed shell command.

    Returns:
        Tuple of (ok, error).

    """
    from verifier.risky_action import _dry_run_proposal as _impl

    return _impl(cmd)
