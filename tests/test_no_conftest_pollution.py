"""Regression guard: no tests/conftest.py allowed.

See docs/audits/v0.12-task-86-conftest-audit.md for the rationale.

A tests/conftest.py would auto-apply to every test in tests/,
creating fixture-leak risk. Per-file fixtures are the convention.
"""

from __future__ import annotations

from pathlib import Path


def test_no_root_conftest_present() -> None:
    """tests/conftest.py must not exist (per v0.12 task 86 audit)."""
    assert not (Path(__file__).parent / "conftest.py").exists(), (
        "tests/conftest.py must not exist — see "
        "docs/audits/v0.12-task-86-conftest-audit.md for rationale. "
        "Use tests/_harness.py for shared helpers instead."
    )


def test_no_subpackage_conftest_present() -> None:
    """No tests/<subdir>/conftest.py either (none exists today)."""
    test_root = Path(__file__).parent
    subdirs = [d for d in test_root.iterdir() if d.is_dir() and d.name != "__pycache__"]
    for subdir in subdirs:
        conftest = subdir / "conftest.py"
        assert not conftest.exists(), f"unexpected conftest at {conftest}"
