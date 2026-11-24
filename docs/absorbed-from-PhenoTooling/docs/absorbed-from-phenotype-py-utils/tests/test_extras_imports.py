"""Tests that verify each extras group is importable as a module and exposes the
expected lazy attributes.

These tests only exercise the *structure* of the package. They do NOT install
the optional dependencies; the underlying libraries may or may not be present
in the test environment.
"""

from __future__ import annotations

import importlib

import pytest

from phenotype_py_utils.extras import cli, mcp, testing, web  # type: ignore[attr-defined]


def test_extras_subpackage_importable() -> None:
    """The extras subpackage itself must be importable with no extras installed."""
    import phenotype_py_utils.extras  # noqa: F401


@pytest.mark.parametrize(
    ("module_name", "expected_names"),
    [
        ("phenotype_py_utils.extras.cli", {"click", "rich", "typer", "pydantic"}),
        ("phenotype_py_utils.extras.mcp", {"fastmcp", "pydantic", "pydantic_settings", "httpx"}),
        ("phenotype_py_utils.extras.web", {"fastapi", "uvicorn", "pydantic", "pydantic_settings"}),
        ("phenotype_py_utils.extras.testing", {"pytest", "pytest_asyncio", "pytest_cov"}),
    ],
)
def test_extras_module_is_importable(module_name: str, expected_names: set[str]) -> None:
    module = importlib.import_module(module_name)
    assert module is not None
    for name in expected_names:
        assert name in module.__all__


@pytest.mark.parametrize(
    "module_name",
    [
        "phenotype_py_utils.extras.cli",
        "phenotype_py_utils.extras.mcp",
        "phenotype_py_utils.extras.web",
        "phenotype_py_utils.extras.testing",
    ],
)
def test_unknown_attribute_raises_attributeerror(module_name: str) -> None:
    module = importlib.import_module(module_name)
    with pytest.raises(AttributeError):
        module.__getattr__("definitely_not_a_real_library_xyz")


def test_lazy_attribute_resolution() -> None:
    """When the underlying lib is installed, accessing a lazy attribute returns it.

    When it is not installed, the call raises ``ImportError``. Either outcome
    is acceptable for this test, as long as it is consistent with the lazy contract.
    """
    try:
        import click  # type: ignore[import-not-found]
    except ImportError:
        with pytest.raises(ImportError):
            cli.click  # type: ignore[attr-defined]
    else:
        assert cli.click is click  # type: ignore[attr-defined]


def test_no_top_level_dependencies() -> None:
    """Submodules are importable without the extras being present."""
    importlib.import_module("phenotype_py_utils.extras.cli")
    importlib.import_module("phenotype_py_utils.extras.mcp")
    importlib.import_module("phenotype_py_utils.extras.web")
    importlib.import_module("phenotype_py_utils.extras.testing")
