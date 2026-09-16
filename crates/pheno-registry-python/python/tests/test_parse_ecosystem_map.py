"""Comprehensive tests for the pheno_registry_python native module."""

import pytest

try:
    from pheno_registry_python import (
        RepoEntryPy,
        parse_ecosystem_map_py,
        __version__,
    )

    _HAS_NATIVE = True
except ImportError:
    _HAS_NATIVE = False

pytestmark = pytest.mark.skipif(
    not _HAS_NATIVE,
    reason="native module not built (run: maturin develop)",
)


# -- Module-level ---------------------------------------------------------------


def test_module_version():
    assert isinstance(__version__, str)
    assert __version__  # non-empty


def test_version_format():
    parts = __version__.split(".")
    assert len(parts) >= 2, "version should have at least major.minor"


# -- Empty / whitespace input ---------------------------------------------------


def test_empty_input_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        parse_ecosystem_map_py("")


def test_whitespace_only_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        parse_ecosystem_map_py("   \n  \n  ")


# -- Role classification table --------------------------------------------------


def test_single_role_row():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **shared-lib** | 2 | alpha, beta |\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 2
    assert entries[0].name == "alpha"
    assert entries[0].role == "shared-lib"
    assert entries[1].name == "beta"
    assert entries[1].role == "shared-lib"


def test_role_row_bold_names():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **SDK** | 1 | **MyCrate** |\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    assert entries[0].name == "MyCrate"
    assert entries[0].role == "SDK"


def test_role_multiple_repos():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **tooling** | 3 | forge, anvil, smith |\n"
    )
    entries = parse_ecosystem_map_py(md)
    names = {e.name for e in entries}
    assert names == {"forge", "anvil", "smith"}
    for e in entries:
        assert e.role == "tooling"


# -- Triage table ---------------------------------------------------------------


def test_triage_row():
    md = (
        "| Repo | Lang | Pushed | Proposed role | Notes |\n"
        "|------|------|--------|---------------|-------|\n"
        "| `my-repo` | Rust | 2026-06-23 | shared-lib | some notes |\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "my-repo"
    assert e.role == "shared-lib"
    assert e.language == "Rust"
    assert e.notes == "some notes"


def test_triage_row_no_notes():
    md = (
        "| Repo | Lang | Pushed | Proposed role | Notes |\n"
        "|------|------|--------|---------------|-------|\n"
        "| `bare-repo` | Python | 2026-01-01 | SDK | |\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    assert entries[0].name == "bare-repo"


# -- Cluster table --------------------------------------------------------------


def test_cluster_row():
    md = (
        "| Repo | Status | Verdict |\n"
        "|------|--------|---------|\n"
        "| **Agentora** | Active, Rust, hexagonal-arch | **CANONICAL** |\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "Agentora"
    assert e.language == "Rust"
    assert e.status == "Active"


# -- Dependency edge parsing ----------------------------------------------------


def test_dep_edge_basic():
    md = "foo -> bar, baz\n"
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    assert entries[0].name == "foo"
    assert entries[0].dependencies == ["bar", "baz"]


def test_dep_edge_with_inline_notes():
    md = "phenotype-registry -> PhenoSpecs, HexaKit [doc links]\n"
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    assert entries[0].dependencies == ["PhenoSpecs", "HexaKit"]


def test_dep_edge_standalone_note():
    md = "phenotype-infra -> (standalone IaC/spec, no code deps)\n"
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    assert entries[0].dependencies == []


# -- Merging of role + dep data ------------------------------------------------


def test_merge_role_and_dep():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **shared-lib** | 1 | foo |\n"
        "\n"
        "foo -> bar\n"
    )
    entries = parse_ecosystem_map_py(md)
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "foo"
    assert e.role == "shared-lib"
    assert e.dependencies == ["bar"]


# -- RepoEntryPy attribute access -----------------------------------------------


def test_entry_attributes():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **SDK** | 1 | mylib |\n"
    )
    entries = parse_ecosystem_map_py(md)
    e = entries[0]
    assert e.name == "mylib"
    assert e.role == "SDK"
    assert e.language is None
    assert e.status is None
    assert e.notes is None
    assert e.dependencies == []


def test_entry_to_dict():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **shared-lib** | 1 | alpha |\n"
    )
    entries = parse_ecosystem_map_py(md)
    d = entries[0].to_dict()
    assert isinstance(d, dict)
    assert d["name"] == "alpha"
    assert d["role"] == "shared-lib"
    assert d["language"] is None
    assert d["status"] is None
    assert d["notes"] is None
    assert d["dependencies"] == []


def test_entry_to_dict_full():
    md = (
        "| Repo | Lang | Pushed | Proposed role | Notes |\n"
        "|------|------|--------|---------------|-------|\n"
        "| `x` | Go | 2026-01-01 | tooling | build helper |\n"
    )
    entries = parse_ecosystem_map_py(md)
    d = entries[0].to_dict()
    assert d["name"] == "x"
    assert d["language"] == "Go"
    assert d["notes"] == "build helper"


def test_entry_repr():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **SDK** | 1 | mylib |\n"
    )
    entries = parse_ecosystem_map_py(md)
    r = repr(entries[0])
    assert "RepoEntryPy" in r
    assert "mylib" in r
    assert "SDK" in r


def test_entry_str():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **SDK** | 1 | mylib |\n"
    )
    entries = parse_ecosystem_map_py(md)
    s = str(entries[0])
    assert "RepoEntry" in s
    assert "mylib" in s
    assert "SDK" in s


# -- Results are sorted by name -------------------------------------------------


def test_results_sorted():
    md = (
        "| Role | Count | Repos |\n"
        "|------|-------|-------|\n"
        "| **tooling** | 3 | zeta, alpha, mu |\n"
    )
    entries = parse_ecosystem_map_py(md)
    names = [e.name for e in entries]
    assert names == sorted(names)
