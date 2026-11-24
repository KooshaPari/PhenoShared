"""Coverage tests for pheno.serve.__init__.

Locks the public surface of pheno.serve. The package is a thin facade that
re-exports five submodules; these tests pin the __all__ contract and verify
that each named submodule can be imported without side effects.

No subprocess, no network. Module references only.
"""

from __future__ import annotations

import importlib

import pytest

import pheno.serve
import pheno.serve.config
import pheno.serve.events
import pheno.serve.metrics
import pheno.serve.registry
import pheno.serve.server


class TestPackageSurface:
    """pheno.serve must re-export the five submodules in __all__."""

    def test_all_is_list(self) -> None:
        assert isinstance(pheno.serve.__all__, list)

    def test_all_contents(self) -> None:
        assert set(pheno.serve.__all__) == {
            "config",
            "events",
            "metrics",
            "registry",
            "server",
        }

    def test_all_is_sorted_unique(self) -> None:
        assert pheno.serve.__all__ == sorted(set(pheno.serve.__all__))

    def test_dunder_docstring_present(self) -> None:
        assert pheno.serve.__doc__ is not None
        assert "pheno-serve-dev" in pheno.serve.__doc__

    @pytest.mark.parametrize(
        "submodule_name",
        ["config", "events", "metrics", "registry", "server"],
    )
    def test_submodule_importable(self, submodule_name: str) -> None:
        module = importlib.import_module(f"pheno.serve.{submodule_name}")
        assert module.__name__ == f"pheno.serve.{submodule_name}"

    @pytest.mark.parametrize(
        "submodule_name",
        ["config", "events", "metrics", "registry", "server"],
    )
    def test_submodule_in_all(self, submodule_name: str) -> None:
        assert submodule_name in pheno.serve.__all__

    def test_no_unlisted_submodules_exposed(self) -> None:
        """Only the five named submodules are part of the public surface."""
        # Sanity check: pick a known-absent name (lifecycle is private).
        assert "lifecycle" not in pheno.serve.__all__
        assert "supervisor" not in pheno.serve.__all__
        assert "router" not in pheno.serve.__all__

    def test_package_can_be_reimported(self) -> None:
        """Re-importing the package must not raise and must keep the same __all__."""
        importlib.reload(pheno.serve)
        assert pheno.serve.__all__ == ["config", "events", "metrics", "registry", "server"]

    def test_each_submodule_has_public_path(self) -> None:
        """The five named submodules must each have a __file__ attribute."""
        for name in pheno.serve.__all__:
            module = getattr(pheno.serve, name)
            assert module.__file__ is not None
            assert module.__file__.endswith(f"{name}.py")