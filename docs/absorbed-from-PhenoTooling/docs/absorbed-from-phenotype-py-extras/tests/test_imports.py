"""Tests that verify each extras group is importable as a module and exposes the
expected lazy attributes.

These tests only exercise the *structure* of the package. They do NOT install
the optional dependencies; the underlying libraries may or may not be present
in the test environment. When a library is missing, accessing the lazy
attribute raises ``ImportError`` (not an import error at module load time),
which is the correct contract.
"""

from __future__ import annotations

import importlib

import pytest

from phenotype_py_extras import cli, mcp, testing, web  # type: ignore[attr-defined]
from phenotype_py_extras import __version__


def test_version_string() -> None:
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    ("module_name", "expected_names"),
    [
        ("phenotype_py_extras.cli", {"click", "rich", "typer", "pydantic"}),
        ("phenotype_py_extras.mcp", {"fastmcp", "pydantic", "pydantic_settings", "httpx"}),
        ("phenotype_py_extras.web", {"fastapi", "uvicorn", "pydantic", "pydantic_settings"}),
        ("phenotype_py_extras.testing", {"pytest", "pytest_asyncio", "pytest_cov"}),
    ],
)
def test_extras_module_is_importable(module_name: str, expected_names: set[str]) -> None:
    module = importlib.import_module(module_name)
    assert module is not None
    # __all__ should advertise every lazy attribute.
    for name in expected_names:
        assert name in module.__all__


@pytest.mark.parametrize(
    "module_name",
    [
        "phenotype_py_extras.cli",
        "phenotype_py_extras.mcp",
        "phenotype_py_extras.web",
        "phenotype_py_extras.testing",
    ],
)
def test_unknown_attribute_raises_attributeerror(module_name: str) -> None:
    module = importlib.import_module(module_name)
    with pytest.raises(AttributeError):
        module.__getattr__("definitely_not_a_real_library_xyz")


def test_lazy_attribute_resolution() -> None:
    """When the underlying lib is installed, accessing a lazy attribute returns it.

    When it is not installed, the call raises ``ImportError`` — never a
    ``ModuleNotFoundError`` at package import time. Either outcome is acceptable
    for this test, as long as it is consistent with the lazy contract.
    """
    try:
        import click  # type: ignore[import-not-found]
    except ImportError:
        with pytest.raises(ImportError):
            cli.click  # type: ignore[attr-defined]
    else:
        assert cli.click is click  # type: ignore[attr-defined]


def test_no_top_level_dependencies() -> None:
    """``phenotype_py_extras`` itself must remain importable with no extras installed."""
    import phenotype_py_extras  # noqa: F401

    # Submodules are also importable without the extras being present.
    importlib.import_module("phenotype_py_extras.cli")
    importlib.import_module("phenotype_py_extras.mcp")
    importlib.import_module("phenotype_py_extras.web")
    importlib.import_module("phenotype_py_extras.testing")
