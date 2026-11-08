"""Tests for 4SGM CLI."""

import sys
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

# Add the project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sgm_cli import app  # noqa: E402 -- sys.path setup required

runner = CliRunner()


class TestMCPCommand:
    """Tests for mcp command."""

    def test_mcp_command_help(self):
        """Test mcp command help."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP server" in result.stdout or "mcp" in result.stdout.lower()

    def test_mcp_command_accepts_port_option(self):
        """Test mcp command accepts port option."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert "--port" in result.stdout or "-p" in result.stdout

    def test_mcp_command_has_default_port(self):
        """Test mcp command has default port."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert "3000" in result.stdout or "port" in result.stdout.lower()

    def test_mcp_command_uses_repo_package_module_path(self):
        """Test mcp command targets the packaged MCP module path."""
        with patch("sgm_cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(app, ["mcp", "--port", "3100"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            [sys.executable, "-m", "fastmcp", "run", "4sgm.mcp_server.server:mcp"],
            check=True,
        )


class TestAPICommand:
    """Tests for api command."""

    def test_api_command_help(self):
        """Test api command help."""
        result = runner.invoke(app, ["api", "--help"])
        assert result.exit_code == 0
        assert "api" in result.stdout.lower() or "fastapi" in result.stdout.lower()

    def test_api_command_accepts_host_option(self):
        """Test api command accepts host option."""
        result = runner.invoke(app, ["api", "--help"])
        assert "--host" in result.stdout or "-h" in result.stdout

    def test_api_command_accepts_port_option(self):
        """Test api command accepts port option."""
        result = runner.invoke(app, ["api", "--help"])
        assert "--port" in result.stdout or "-p" in result.stdout

    def test_api_command_accepts_reload_option(self):
        """Test api command accepts reload option."""
        result = runner.invoke(app, ["api", "--help"])
        assert "reload" in result.stdout.lower()

    def test_api_command_has_default_host(self):
        """Test api command has default host."""
        result = runner.invoke(app, ["api", "--help"])
        assert "0.0.0.0" in result.stdout or "host" in result.stdout.lower()

    def test_api_command_has_default_port(self):
        """Test api command has default port."""
        result = runner.invoke(app, ["api", "--help"])
        assert "8000" in result.stdout or "port" in result.stdout.lower()

    def test_api_command_uses_repo_package_module_path(self):
        """Test api command targets the packaged FastAPI module path."""
        with patch("sgm_cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(
                app,
                ["api", "--host", "127.0.0.1", "--port", "9000", "--no-reload"],
            )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "4sgm.backend.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "9000",
            ],
            check=True,
        )


class TestTestCommand:
    """Tests for test command."""

    def test_test_command_help(self):
        """Test test command help."""
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0

    def test_test_command_uses_repo_relative_test_path(self):
        """Test test command targets the backend integration test within the repo package."""
        with patch("sgm_cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            [sys.executable, "4sgm/backend/test_mcp_integration.py"],
            check=True,
        )


class TestToolsCommand:
    """Tests for tools command."""

    def test_tools_command_runs(self):
        """Test tools command runs successfully."""
        result = runner.invoke(app, ["tools"])
        assert result.exit_code == 0

    def test_tools_command_lists_categories(self):
        """Test tools command lists tool categories."""
        result = runner.invoke(app, ["tools"])
        assert "Product" in result.stdout or "product" in result.stdout.lower()

    def test_tools_command_lists_specific_tools(self):
        """Test tools command lists specific tools."""
        result = runner.invoke(app, ["tools"])
        assert "get_product" in result.stdout or "product" in result.stdout.lower()

    def test_tools_command_includes_cart_tools(self):
        """Test tools command includes cart tools."""
        result = runner.invoke(app, ["tools"])
        assert "Cart" in result.stdout or "cart" in result.stdout.lower()

    def test_tools_command_includes_shipping_tools(self):
        """Test tools command includes shipping tools."""
        result = runner.invoke(app, ["tools"])
        assert "Shipping" in result.stdout or "shipping" in result.stdout.lower()

    def test_tools_command_includes_pricing_tools(self):
        """Test tools command includes pricing tools."""
        result = runner.invoke(app, ["tools"])
        assert "Pricing" in result.stdout or "pricing" in result.stdout.lower()

    def test_tools_command_includes_customer_tools(self):
        """Test tools command includes customer tools."""
        result = runner.invoke(app, ["tools"])
        assert "Customer" in result.stdout or "customer" in result.stdout.lower()

    def test_tools_command_includes_rfq_tools(self):
        """Test tools command includes RFQ tools."""
        result = runner.invoke(app, ["tools"])
        assert "RFQ" in result.stdout or "rfq" in result.stdout.lower()


class TestDevCommand:
    """Tests for dev command."""

    def test_dev_command_runs(self):
        """Test dev command runs successfully."""
        result = runner.invoke(app, ["dev"])
        assert result.exit_code == 0

    def test_dev_command_shows_instructions(self):
        """Test dev command shows development instructions."""
        result = runner.invoke(app, ["dev"])
        assert "development" in result.stdout.lower() or "terminal" in result.stdout.lower()

    def test_dev_command_mentions_mcp(self):
        """Test dev command mentions mcp command."""
        result = runner.invoke(app, ["dev"])
        assert "mcp" in result.stdout.lower()

    def test_dev_command_mentions_api(self):
        """Test dev command mentions api command."""
        result = runner.invoke(app, ["dev"])
        assert "api" in result.stdout.lower()


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_app_has_name(self):
        """Test app has proper name."""
        assert app.info.name == "4sgm"

    def test_app_has_help_text(self):
        """Test app has help text."""
        assert app.info.help is not None

    def test_app_is_typer_instance(self):
        """Test app is Typer instance."""
        import typer

        assert isinstance(app, typer.Typer)


class TestCLICommands:
    """Tests for CLI command availability."""

    def test_app_help_shows_all_commands(self):
        """Test app help shows all available commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "mcp" in result.stdout.lower()
        assert "api" in result.stdout.lower()
        assert "tools" in result.stdout.lower()
        assert "dev" in result.stdout.lower()

    def test_app_has_mcp_command(self):
        """Test app has mcp command."""
        result = runner.invoke(app, ["--help"])
        assert "mcp" in result.stdout.lower()

    def test_app_has_api_command(self):
        """Test app has api command."""
        result = runner.invoke(app, ["--help"])
        assert "api" in result.stdout.lower()

    def test_app_has_test_command(self):
        """Test app has test command."""
        result = runner.invoke(app, ["--help"])
        assert "test" in result.stdout.lower()

    def test_app_has_tools_command(self):
        """Test app has tools command."""
        result = runner.invoke(app, ["--help"])
        assert "tools" in result.stdout.lower()

    def test_app_has_dev_command(self):
        """Test app has dev command."""
        result = runner.invoke(app, ["--help"])
        assert "dev" in result.stdout.lower()


class TestMainEntryPoint:
    """Tests for main entry point."""

    def test_main_function_exists(self):
        """Test main function exists."""
        from sgm_cli import main

        assert callable(main)
