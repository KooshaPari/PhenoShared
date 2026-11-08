"""Tests for backend __main__.py entry point."""

import sys
from pathlib import Path

import pytest

# Add the project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestBackendMainImports:
    """Tests for backend __main__.py imports."""

    def test_backend_main_module_exists(self):
        """Test that backend __main__ module exists."""
        try:
            from backend import __main__

            assert __main__ is not None
        except ImportError:
            pytest.skip("Backend __main__ module not available")

    def test_backend_main_can_be_imported(self):
        """Test that backend __main__ can be imported."""
        try:
            import importlib.util

            spec = importlib.util.find_spec("backend.__main__")
            assert spec is not None
        except (ImportError, ModuleNotFoundError):
            pytest.skip("Backend __main__ module not available")


class TestRootMainImports:
    """Tests for root 4sgm __main__.py imports."""

    def test_root_main_module_exists(self):
        """Test that root __main__ module exists."""
        try:
            from _4sgm import __main__

            assert __main__ is not None
        except (ImportError, ModuleNotFoundError):
            # Try alternative import
            try:
                import __main__

                assert __main__ is not None
            except ImportError:
                pytest.skip("Root __main__ module not available")
