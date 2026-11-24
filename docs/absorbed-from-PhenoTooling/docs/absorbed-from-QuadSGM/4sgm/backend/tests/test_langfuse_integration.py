"""Integration tests for Langfuse observability."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from agents.callbacks.langfuse import (
    get_langfuse_client,
    get_langfuse_handler,
    is_langfuse_enabled,
)

# Check if langfuse is available
try:
    import langfuse  # noqa: F401 -- used to test availability

    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False

# Create mock langfuse module for testing
mock_langfuse_module = MagicMock()
mock_langfuse_langchain = MagicMock()
mock_langfuse_module.langchain = mock_langfuse_langchain


class TestLangfuseConfiguration:
    """Test Langfuse configuration and initialization."""

    def test_credentials_not_configured(self):
        """Test behavior when Langfuse credentials are not configured."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_langfuse_enabled() is False
            assert get_langfuse_handler() is None
            assert get_langfuse_client() is None

    def test_partial_credentials(self):
        """Test behavior when only one credential is provided."""
        # Only public key
        with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-lf-xxx"}, clear=True):
            assert is_langfuse_enabled() is False

        # Only secret key
        with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-lf-xxx"}, clear=True):
            assert is_langfuse_enabled() is False

    def test_credentials_configured(self):
        """Test behavior when both credentials are configured."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        }

        with patch.dict(os.environ, env):
            assert is_langfuse_enabled() is True

    def test_handler_initialization_success(self):
        """Test successful Langfuse callback handler initialization."""
        mock_handler_instance = MagicMock()
        mock_callback_handler = MagicMock(return_value=mock_handler_instance)

        # Create mock module structure
        mock_langfuse = MagicMock()
        mock_langfuse_langchain = MagicMock()
        mock_langfuse_langchain.CallbackHandler = mock_callback_handler

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
        }

        with patch.dict(os.environ, env):
            with patch.dict(
                sys.modules,
                {
                    "langfuse": mock_langfuse,
                    "langfuse.langchain": mock_langfuse_langchain,
                },
            ):
                # Re-import to get the patched version
                import importlib

                from agents.callbacks import langfuse as langfuse_module

                importlib.reload(langfuse_module)

                handler = langfuse_module.get_langfuse_handler()

                assert handler is not None
                assert handler == mock_handler_instance

    def test_handler_initialization_without_langfuse_package(self):
        """Test handler initialization when langfuse package is not installed."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
        }

        with patch.dict(os.environ, env):
            with patch.dict("sys.modules", {"langfuse": None, "langfuse.langchain": None}):
                handler = get_langfuse_handler()
                assert handler is None


class TestLangfuseEnvironmentVariables:
    """Test Langfuse environment variable handling."""

    def test_default_host(self):
        """Test default host when not specified."""
        mock_callback_handler = MagicMock()
        mock_langfuse = MagicMock()
        mock_langfuse_langchain = MagicMock()
        mock_langfuse_langchain.CallbackHandler = mock_callback_handler

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
        }

        with patch.dict(os.environ, env):
            with patch.dict(
                sys.modules,
                {"langfuse": mock_langfuse, "langfuse.langchain": mock_langfuse_langchain},
            ):
                import importlib

                from agents.callbacks import langfuse as langfuse_module

                importlib.reload(langfuse_module)

                langfuse_module.get_langfuse_handler()
                # Verify handler was called
                mock_callback_handler.assert_called_once()

    def test_custom_host(self):
        """Test custom host configuration."""
        mock_callback_handler = MagicMock()
        mock_langfuse = MagicMock()
        mock_langfuse_langchain = MagicMock()
        mock_langfuse_langchain.CallbackHandler = mock_callback_handler

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
            "LANGFUSE_HOST": "https://langfuse.company.com",
        }

        with patch.dict(os.environ, env):
            with patch.dict(
                sys.modules,
                {"langfuse": mock_langfuse, "langfuse.langchain": mock_langfuse_langchain},
            ):
                import importlib

                from agents.callbacks import langfuse as langfuse_module

                importlib.reload(langfuse_module)

                langfuse_module.get_langfuse_handler()
                # Verify handler was called with custom host
                call_kwargs = mock_callback_handler.call_args.kwargs
                assert call_kwargs["host"] == "https://langfuse.company.com"

    def test_sample_rate_validation(self):
        """Test sample rate validation."""
        mock_callback_handler = MagicMock()
        mock_langfuse = MagicMock()
        mock_langfuse_langchain = MagicMock()
        mock_langfuse_langchain.CallbackHandler = mock_callback_handler

        env_base = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
        }

        # Valid sample rates
        for rate in [0.0, 0.5, 1.0]:
            env = {**env_base, "LANGFUSE_SAMPLE_RATE": str(rate)}
            with patch.dict(os.environ, env):
                with patch.dict(
                    sys.modules,
                    {"langfuse": mock_langfuse, "langfuse.langchain": mock_langfuse_langchain},
                ):
                    import importlib

                    from agents.callbacks import langfuse as langfuse_module

                    importlib.reload(langfuse_module)

                    handler = langfuse_module.get_langfuse_handler()
                    assert handler is not None

        # Invalid sample rates should be clamped
        for rate in [-0.5, 1.5]:
            env = {**env_base, "LANGFUSE_SAMPLE_RATE": str(rate)}
            with patch.dict(os.environ, env):
                with patch.dict(
                    sys.modules,
                    {"langfuse": mock_langfuse, "langfuse.langchain": mock_langfuse_langchain},
                ):
                    import importlib

                    from agents.callbacks import langfuse as langfuse_module

                    importlib.reload(langfuse_module)

                    handler = langfuse_module.get_langfuse_handler()
                    # Should not raise, rate is clamped internally
                    assert handler is not None


class TestLangfuseClient:
    """Test direct Langfuse client initialization."""

    def test_client_initialization_success(self):
        """Test successful Langfuse client initialization."""
        mock_client = MagicMock()
        mock_langfuse_class = MagicMock(return_value=mock_client)
        mock_langfuse = MagicMock()
        mock_langfuse.Langfuse = mock_langfuse_class

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        }

        with patch.dict(os.environ, env):
            with patch.dict(sys.modules, {"langfuse": mock_langfuse}):
                import importlib

                from agents.callbacks import langfuse as langfuse_module

                importlib.reload(langfuse_module)

                client = langfuse_module.get_langfuse_client()

                assert client is not None
                assert client == mock_client
                mock_langfuse_class.assert_called_once()

    def test_client_initialization_without_credentials(self):
        """Test client initialization when credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            client = get_langfuse_client()
            assert client is None

    def test_client_initialization_with_custom_host(self):
        """Test client initialization with custom host."""
        mock_client = MagicMock()
        mock_langfuse_class = MagicMock(return_value=mock_client)
        mock_langfuse = MagicMock()
        mock_langfuse.Langfuse = mock_langfuse_class

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
            "LANGFUSE_HOST": "https://self-hosted.langfuse.com",
        }

        with patch.dict(os.environ, env):
            with patch.dict(sys.modules, {"langfuse": mock_langfuse}):
                import importlib

                from agents.callbacks import langfuse as langfuse_module

                importlib.reload(langfuse_module)

                client = langfuse_module.get_langfuse_client()
                assert client is not None


class TestDeepAgentIntegration:
    """Test Langfuse integration with DeepAgent."""

    def test_agent_callbacks_attached(self):
        """Test that callbacks are properly attached to agent when Langfuse is enabled."""
        from agents.deep_agent import create_4sgm_agent

        mock_handler = MagicMock()

        # Mock all dependencies to allow agent creation
        with patch("agents.deep_agent.create_react_agent") as mock_react:
            mock_agent = MagicMock()
            mock_react.return_value = mock_agent

            with patch("agents.deep_agent.get_composite_backend"):
                with patch("agents.deep_agent.order_workflow.compile"):
                    with patch("agents.deep_agent.shipping_workflow.compile"):
                        with patch("agents.deep_agent.rfq_workflow.compile"):
                            # Mock get_langfuse_handler to return our mock handler
                            with patch(
                                "agents.deep_agent.get_langfuse_handler",
                                return_value=mock_handler,
                            ):
                                agent = create_4sgm_agent(mcp_tools=[], enable_langfuse=True)

                                # Check callbacks are attached to the returned agent
                                assert hasattr(agent, "_callbacks")
                                assert mock_handler in agent._callbacks

    def test_agent_without_langfuse(self):
        """Test agent creation without Langfuse."""
        from agents.deep_agent import create_4sgm_agent

        # Mock all dependencies
        with patch("agents.deep_agent.create_react_agent") as mock_react:
            mock_agent = MagicMock()
            mock_react.return_value = mock_agent

            with patch("agents.deep_agent.get_composite_backend"):
                with patch("agents.deep_agent.order_workflow.compile"):
                    with patch("agents.deep_agent.shipping_workflow.compile"):
                        with patch("agents.deep_agent.rfq_workflow.compile"):
                            agent = create_4sgm_agent(mcp_tools=[], enable_langfuse=False)

                            # Check no callbacks are attached when disabled
                            assert hasattr(agent, "_callbacks")
                            assert len(agent._callbacks) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
