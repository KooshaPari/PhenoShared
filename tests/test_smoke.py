"""Tests for pheno-agents-md."""

import subprocess
import sys
from pathlib import Path

import pytest

# Skip these tests if cargo isn't available
CARGO_AVAILABLE = subprocess.run(["which", "cargo"], capture_output=True).returncode == 0
pytestmark = pytest.mark.skipif(not CARGO_AVAILABLE, reason="cargo not available")


def test_cargo_test():
    """Run `cargo test` in the pheno-agents-md crate."""
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["cargo", "test", "--all-targets"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"cargo test failed:\n{result.stdout}\n{result.stderr}"
    assert "test result: ok" in result.stdout


def test_cargo_lint():
    """Run `cargo clippy` to check for warnings."""
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["cargo", "clippy", "--all-targets", "--all-features", "--", "-D", "warnings"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"clippy failed:\n{result.stdout}\n{result.stderr}"
