"""Tests for package-level exports and version."""

from __future__ import annotations

import pheno_mcp


class TestPackageExports:
    """Tests for package __init__.py exports."""

    def test_version_exists(self) -> None:
        """Test version is defined."""
        assert hasattr(pheno_mcp, "__version__")
        assert isinstance(pheno_mcp.__version__, str)
        assert pheno_mcp.__version__ == "0.1.0"

    def test_all_exports_defined(self) -> None:
        """Test all exports are defined in __all__."""
        expected_exports = [
            "__version__",
            "Client",
            "Server",
            "Tool",
            "Resource",
            "Prompt",
        ]
        for export in expected_exports:
            assert export in pheno_mcp.__all__
            assert hasattr(pheno_mcp, export)

    def test_client_is_importable(self) -> None:
        """Test Client can be imported from package."""
        from pheno_mcp import Client
        from pheno_mcp.client import Client as ClientDirect

        assert Client is ClientDirect

    def test_server_is_importable(self) -> None:
        """Test Server can be imported from package."""
        from pheno_mcp import Server
        from pheno_mcp.server import Server as ServerDirect

        assert Server is ServerDirect

    def test_models_are_importable(self) -> None:
        """Test models can be imported from package."""
        from pheno_mcp import Prompt, Resource, Tool
        from pheno_mcp.models import Prompt as PromptModel
        from pheno_mcp.models import Resource as ResourceModel
        from pheno_mcp.models import Tool as ToolModel

        assert Tool is ToolModel
        assert Resource is ResourceModel
        assert Prompt is PromptModel

    def test_package_docstring(self) -> None:
        """Test package has docstring."""
        assert pheno_mcp.__doc__ is not None
        assert "Model Context Protocol" in pheno_mcp.__doc__


class TestVersionFormat:
    """Tests for version string format."""

    def test_version_format(self) -> None:
        """Test version follows semver-like format."""
        version = pheno_mcp.__version__
        parts = version.split(".")

        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()
            assert 0 <= int(part) <= 999

    def test_version_is_valid(self) -> None:
        """Test version is a valid version string."""
        version = pheno_mcp.__version__
        assert version == "0.1.0"
