"""Static guard for the no-launch desktop CI coverage."""

import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _shell_tokens(command: str) -> list[str]:
    """Tokenize shell punctuation so attached separators remain boundaries."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    return list(lexer)


def _pytest_command_arguments(run: str) -> list[str]:
    """Return arguments from the pytest command, excluding shell/comments."""
    command_lines: list[str] = []
    collecting = False
    for raw_line in run.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        logical_line = line.removesuffix("\\").strip()
        tokens = _shell_tokens(logical_line)
        if not collecting:
            if "pytest" not in tokens:
                continue
            collecting = True
        command_lines.append(logical_line)
        if not line.endswith("\\"):
            break

    tokens = _shell_tokens(" ".join(command_lines))
    pytest_index = tokens.index("pytest")
    arguments = tokens[pytest_index + 1 :]
    for index, token in enumerate(arguments):
        if token and set(token) <= {";", "&", "|"}:
            return arguments[:index]
    return arguments


def test_pytest_command_arguments_ignore_workflow_comments() -> None:
    """A documentation comment must not be treated as an executed command."""
    arguments = _pytest_command_arguments(
        """\
        set -euo pipefail
        # This no-launch test must not execute nvidia-smi.
        .venv/bin/python -m pytest tests/test_desktop_ci.py -q
        """
    )

    assert arguments == ["tests/test_desktop_ci.py", "-q"]


def test_pytest_command_arguments_stop_before_a_later_shell_command() -> None:
    """Only the pytest invocation can satisfy the CI-coverage invariant."""
    arguments = _pytest_command_arguments(
        ".venv/bin/python -m pytest tests/test_desktop_ci.py -q "
        "&& echo tests/test_desktop_nvidia_lane.py"
    )

    assert arguments == ["tests/test_desktop_ci.py", "-q"]


def test_pytest_command_arguments_stop_at_an_attached_shell_separator() -> None:
    """A separator adjacent to an argument still ends the pytest command."""
    arguments = _pytest_command_arguments(
        ".venv/bin/python -m pytest tests/test_desktop_ci.py -q; "
        "echo tests/test_desktop_nvidia_lane.py"
    )

    assert arguments == ["tests/test_desktop_ci.py", "-q"]


def test_pytest_command_arguments_stop_at_a_background_separator() -> None:
    """A backgrounded pytest command cannot absorb a later reporting command."""
    arguments = _pytest_command_arguments(
        ".venv/bin/python -m pytest tests/test_desktop_ci.py -q& "
        "echo tests/test_desktop_nvidia_lane.py"
    )

    assert arguments == ["tests/test_desktop_ci.py", "-q"]


def test_core_ci_runs_the_offline_desktop_contract_suite() -> None:
    """The Ubuntu core job must enforce policy without invoking a desktop."""
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["install-smoke"]["steps"]
    pytest_step = next(
        step for step in steps if step["name"] == "pytest (core-safe suite)"
    )
    pytest_command = _pytest_command_arguments(pytest_step["run"])

    for test_file in (
        "tests/test_desktop_ci.py",
        "tests/test_desktop_nvidia_lane.py",
        "tests/test_desktop_lane_eval.py",
        "tests/test_desktop_agentic_fixture.py",
        "tests/test_desktop_evidence.py",
        "tests/test_desktop_execution_policy.py",
        "tests/test_desktop_promotion_readiness.py",
    ):
        assert test_file in pytest_command

    assert not {"ssh", "nvidia-smi", "powershell", "pwsh"}.intersection(pytest_command)
