"""
Doc-test + unit test + property-based test for detect_repo_type.

This is the primary public function in pheno_scaffold_kit — it detects basic
repository traits (git, python, node, rust, go) used by ergonomic scaffold
defaults.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from pheno_scaffold_kit import detect_repo_type

# ---------------------------------------------------------------------------
# Unit test — primary business logic
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = ["exists", "git", "go", "node", "python", "rust"]


def test_detect_repo_type_empty_dir(tmp_path: Path) -> None:
    """An empty directory exists but has no repo markers."""
    result = detect_repo_type(tmp_path)
    assert result == {
        "exists": True,
        "git": False,
        "python": False,
        "node": False,
        "rust": False,
        "go": False,
    }


def test_detect_repo_type_python(tmp_path: Path) -> None:
    """A dir with pyproject.toml is detected as Python."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
    result = detect_repo_type(tmp_path)
    assert result["python"] is True
    assert result["exists"] is True


def test_detect_repo_type_git(tmp_path: Path) -> None:
    """A dir with .git/ is detected as git."""
    (tmp_path / ".git").mkdir()
    result = detect_repo_type(tmp_path)
    assert result["git"] is True


def test_detect_repo_type_node(tmp_path: Path) -> None:
    """A dir with package.json is detected as Node."""
    (tmp_path / "package.json").write_text('{"name": "foo"}\n')
    result = detect_repo_type(tmp_path)
    assert result["node"] is True


def test_detect_repo_type_rust(tmp_path: Path) -> None:
    """A dir with Cargo.toml is detected as Rust."""
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'foo'\n")
    result = detect_repo_type(tmp_path)
    assert result["rust"] is True


def test_detect_repo_type_go(tmp_path: Path) -> None:
    """A dir with go.mod is detected as Go."""
    (tmp_path / "go.mod").write_text("module foo\n")
    result = detect_repo_type(tmp_path)
    assert result["go"] is True


def test_detect_repo_type_polyglot(tmp_path: Path) -> None:
    """A dir with multiple markers has all relevant flags True."""
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "package.json").write_text("{}\n")
    result = detect_repo_type(tmp_path)
    assert result["rust"] is True
    assert result["python"] is True
    assert result["node"] is True


def test_detect_repo_type_nonexistent() -> None:
    """A non-existent path returns exists=False, everything else False."""
    result = detect_repo_type("/tmp/this-path-does-not-exist-987654321")
    assert result["exists"] is False
    for key in _EXPECTED_KEYS:
        assert result[key] is False


def test_detect_repo_type_deterministic(tmp_path: Path) -> None:
    """Calling detect_repo_type twice on the same dir returns identical results."""
    (tmp_path / ".git").mkdir()
    first = detect_repo_type(tmp_path)
    second = detect_repo_type(tmp_path)
    assert first == second


# ---------------------------------------------------------------------------
# Property-based test — roundtrip / invariants
# ---------------------------------------------------------------------------


@settings(deadline=None)
@given(st.text(min_size=1, max_size=64, alphabet=st.characters(blacklist_categories=("Cc",))))
def test_detect_repo_type_always_returns_valid_shape(name: str) -> None:
    """For any input string, detect_repo_type always returns the 6-key dict
    with boolean values."""
    result = detect_repo_type(f"/tmp/{name}")
    assert isinstance(result, dict)
    assert sorted(result.keys()) == _EXPECTED_KEYS
    for v in result.values():
        assert isinstance(v, bool)
