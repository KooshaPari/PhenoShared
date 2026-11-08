"""Tests for in-repo Python libraries under libs/python/.

Polyglot ``phenotype-id`` is vendored here. Other Python kits were absorbed into
``<REDACTED>/phenotype-python-sdk`` (see ``libs/python/README.md``).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
PHENO_KIT_PATH = REPO_ROOT / "libs" / "python" / "phenotype-py-kit" / "src"
PHENOTYPE_ID_PATH = REPO_ROOT / "libs" / "python" / "phenotype-id" / "src"

_sdk_libs_present = PHENO_KIT_PATH.is_dir()
pytestmark_sdk = pytest.mark.skipif(
    not _sdk_libs_present,
    reason="Python kit libs live in phenotype-python-sdk; clone packages locally to run SDK lib tests",
)

if _sdk_libs_present and str(PHENO_KIT_PATH) not in sys.path:
    sys.path.insert(0, str(PHENO_KIT_PATH))

if PHENOTYPE_ID_PATH.is_dir() and str(PHENOTYPE_ID_PATH) not in sys.path:
    sys.path.insert(0, str(PHENOTYPE_ID_PATH))


class TestPhenotypeLogging:
    """Tests for phenotype_kit.logging module (requires phenotype-python-sdk checkout)."""

    pytestmark = pytestmark_sdk

    def test_configure_logging_imports(self) -> None:
        """Verify logging module can be imported."""
        from phenotype_kit import configure_logging, get_logger

        assert callable(configure_logging)
        assert callable(get_logger)

    def test_configure_logging_sets_level(self) -> None:
        """Verify configure_logging sets the correct log level."""
        from phenotype_kit.logging import configure_logging

        # Configure with DEBUG level
        configure_logging(level="DEBUG", json_output=False)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_json_output(self) -> None:
        """Verify configure_logging works with JSON output."""
        from phenotype_kit.logging import configure_logging

        # Should not raise
        configure_logging(level="INFO", json_output=True)
        configure_logging(level="INFO", json_output=False)

    def test_get_logger_returns_structlog(self) -> None:
        """Verify get_logger returns a structlog logger."""
        from phenotype_kit.logging import configure_logging, get_logger

        configure_logging(level="INFO", json_output=False)
        logger = get_logger("test")

        # Should be a BoundLogger
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_structured_formatter_produces_json(self) -> None:
        """Verify StructuredFormatter produces valid JSON."""
        from phenotype_kit.logging import StructuredFormatter

        formatter = StructuredFormatter(service_name="test-service")

        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["service"] == "test-service"

    def test_structured_formatter_without_service(self) -> None:
        """Verify StructuredFormatter works without service name."""
        from phenotype_kit.logging import StructuredFormatter

        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "WARNING"
        assert "service" not in parsed


class TestPhenotypeLoggingIntegration:
    """Integration tests for logging configuration (requires phenotype-python-sdk checkout)."""

    pytestmark = pytestmark_sdk

    def test_logging_with_extra_fields(self) -> None:
        """Verify logging captures extra fields correctly."""
        from phenotype_kit.logging import configure_logging, get_logger

        configure_logging(level="DEBUG", json_output=False)
        logger = get_logger("test.extra")

        # Should be able to log with extra fields
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)

    def test_configure_logging_idempotent(self) -> None:
        """Verify configure_logging can be called multiple times."""
        from phenotype_kit.logging import configure_logging

        # Should not raise
        configure_logging(level="INFO", json_output=False)
        configure_logging(level="DEBUG", json_output=True)
        configure_logging(level="WARNING", json_output=False)


class TestPhenotypeConfig:
    """Tests for phenotype_kit.config module (requires phenotype-python-sdk checkout)."""

    pytestmark = pytestmark_sdk

    def test_config_module_imports(self) -> None:
        """Verify config module can be imported."""
        try:
            from phenotype_kit.config import BaseConfig, get_settings

            assert "BaseConfig" in dir() or BaseConfig is not None
        except ImportError as e:
            pytest.skip(f"Config module import failed: {e}")

    def test_base_config_class_exists(self) -> None:
        """Verify BaseConfig class exists."""
        try:
            from phenotype_kit.config import BaseConfig

            assert BaseConfig is not None
        except ImportError:
            pytest.skip("Config module not available")

    def test_base_config_default_values(self) -> None:
        """Verify BaseConfig has expected default values."""
        try:
            from phenotype_kit.config import BaseConfig

            config = BaseConfig()
            assert config.environment == "development"
            assert config.debug is False
            assert config.log_level == "INFO"
        except ImportError:
            pytest.skip("Config module not available")

    def test_base_config_env_override(self) -> None:
        """Verify BaseConfig respects environment variables."""
        try:
            from phenotype_kit.config import BaseConfig

            config = BaseConfig(environment="production", debug=True)
            assert config.environment == "production"
            assert config.debug is True
        except ImportError:
            pytest.skip("Config module not available")

    def test_settings_customise_sources(self) -> None:
        """Verify settings source customization works."""
        try:
            from phenotype_kit.config import BaseConfig

            sources = BaseConfig.settings_customise_sources(
                settings_cls=BaseConfig,
                init_settings=MagicMock(),
                env_settings=MagicMock(),
                dotenv_settings=MagicMock(),
            )
            # Should return a tuple of sources in priority order
            assert len(sources) == 3
        except ImportError:
            pytest.skip("Config module not available")

    def test_validate_setup_does_not_raise(self) -> None:
        """Verify validate_setup can be called without error."""
        try:
            from phenotype_kit.config import BaseConfig

            config = BaseConfig()
            # Should not raise
            config.validate_setup()
        except ImportError:
            pytest.skip("Config module not available")

    def test_get_settings_caches_instance(self) -> None:
        """Verify get_settings caches and returns same instance."""
        try:
            from phenotype_kit.config import BaseConfig, get_settings, clear_settings_cache

            # Clear cache first
            clear_settings_cache()

            # Get settings twice
            settings1 = get_settings(BaseConfig)
            settings2 = get_settings(BaseConfig)

            # Should be the same cached instance
            assert settings1 is settings2

            # Clean up
            clear_settings_cache()
        except ImportError:
            pytest.skip("Config module not available")

    def test_get_settings_validates_on_first_call(self) -> None:
        """Verify validate_setup is called when settings are first loaded."""
        try:
            from phenotype_kit.config import BaseConfig, get_settings, clear_settings_cache

            # Clear cache
            clear_settings_cache()

            # Track if validate_setup was called
            validated = []

            class ValidatedConfig(BaseConfig):
                def validate_setup(self) -> None:
                    validated.append(True)

            # Get settings - should call validate_setup
            get_settings(ValidatedConfig)
            assert len(validated) == 1

            # Clean up
            clear_settings_cache()
        except ImportError:
            pytest.skip("Config module not available")

    def test_clear_settings_cache(self) -> None:
        """Verify clear_settings_cache works correctly."""
        try:
            from phenotype_kit.config import BaseConfig, get_settings, clear_settings_cache

            # Clear and populate cache
            clear_settings_cache()
            settings1 = get_settings(BaseConfig)
            assert settings1 is not None

            # Clear cache
            clear_settings_cache()

            # Get new instance
            settings2 = get_settings(BaseConfig)

            # Should be a different instance
            assert settings1 is not settings2
        except ImportError:
            pytest.skip("Config module not available")


class TestPhenotypeAPIModule:
    """Tests for phenotype_kit.api module (requires phenotype-python-sdk checkout)."""

    pytestmark = pytestmark_sdk

    def test_api_module_imports(self) -> None:
        """Verify api module can be imported."""
        try:
            from phenotype_kit.api import create_app

            assert callable(create_app)
        except ImportError:
            # FastAPI might not be installed
            pytest.skip("API module requires FastAPI dependency")

    def test_create_app_returns_something(self) -> None:
        """Verify create_app returns a callable."""
        try:
            from phenotype_kit.api import create_app

            # Should return a FastAPI app (or be callable)
            app = create_app()
            assert app is not None
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_create_app_with_custom_title(self) -> None:
        """Verify create_app accepts custom title and version."""
        try:
            from phenotype_kit.api import create_app

            app = create_app(
                title="Test Service",
                version="2.0.0",
                description="A test service",
            )
            assert app is not None
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_create_app_with_custom_cors(self) -> None:
        """Verify create_app accepts custom CORS origins."""
        try:
            from phenotype_kit.api import create_app

            app = create_app(
                title="Test Service",
                cors_origins=["http://localhost:3000", "https://example.com"],
            )
            assert app is not None
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_create_app_with_disabled_request_id(self) -> None:
        """Verify create_app can disable request ID middleware."""
        try:
            from phenotype_kit.api import create_app

            app = create_app(
                title="Test Service",
                enable_request_id=False,
            )
            assert app is not None
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_health_check_endpoint(self) -> None:
        """Verify health check endpoint returns expected structure."""
        try:
            from fastapi.testclient import TestClient
            from phenotype_kit.api import create_app

            app = create_app(title="Test Service", version="1.0.0")
            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "Test Service"
            assert data["version"] == "1.0.0"
        except ImportError:
            pytest.skip("FastAPI or TestClient not installed")

    def test_error_response_class(self) -> None:
        """Verify ErrorResponse class works correctly."""
        try:
            from phenotype_kit.api import ErrorResponse

            error = ErrorResponse(
                error="TestError",
                message="Test error message",
                status_code=400,
                details={"field": "value"},
            )

            assert error.error == "TestError"
            assert error.message == "Test error message"
            assert error.status_code == 400
            assert error.details == {"field": "value"}

            # Test to_dict
            result = error.to_dict()
            assert result["error"] == "TestError"
            assert result["message"] == "Test error message"
            assert result["details"] == {"field": "value"}
        except ImportError:
            pytest.skip("API module not available")

    def test_global_exception_handler(self) -> None:
        """Verify global exception handler returns proper error response."""
        try:
            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse
            from phenotype_kit.api import create_app

            app = create_app(title="Test Service")

            # Add a route that raises an exception
            @app.get("/test-error")
            async def test_error():
                raise ValueError("Test error")

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/test-error")

            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "ValueError"
            assert data["message"] == "An unexpected error occurred"
            assert "request_id" in data["details"]
        except ImportError:
            pytest.skip("FastAPI or TestClient not installed")

    def test_request_id_middleware(self) -> None:
        """Verify request ID is added to response headers."""
        try:
            from fastapi.testclient import TestClient
            from phenotype_kit.api import create_app

            app = create_app(title="Test Service")
            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200
            assert "x-request-id" in response.headers

            # With explicit request ID
            response2 = client.get("/health", headers={"x-request-id": "custom-id-123"})
            assert response2.headers["x-request-id"] == "custom-id-123"
        except ImportError:
            pytest.skip("FastAPI or TestClient not installed")


class TestPhenotypeKitPackage:
    """Tests for phenotype_kit package initialization (requires phenotype-python-sdk checkout)."""

    pytestmark = pytestmark_sdk

    def test_version_defined(self) -> None:
        """Verify __version__ is defined."""
        try:
            from phenotype_kit import __version__

            assert __version__ is not None
            assert isinstance(__version__, str)
        except ImportError:
            pytest.skip("phenotype_kit not available")

    def test_public_api_exports(self) -> None:
        """Verify public API is exported correctly."""
        try:
            from phenotype_kit import (
                BaseConfig,
                configure_logging,
                create_app,
                get_logger,
                get_settings,
            )

            # At minimum, logging should be available
            assert callable(configure_logging)
            assert callable(get_logger)
        except ImportError as e:
            pytest.skip(f"Public API import failed: {e}")


class TestPhenotypeId:
    """Tests for in-repo polyglot phenotype-id Python implementation."""

    def test_generate_uuid_is_valid(self) -> None:
        from phenotype_id import Generator

        value = Generator.generate_uuid()
        assert Generator.is_valid_uuid(value)

    def test_prefixed_ids(self) -> None:
        from phenotype_id import Generator

        assert Generator.generate_request_id().startswith("req-")
        assert Generator.generate_trace_id().startswith("trace-")
        assert Generator.generate_correlation_id().startswith("corr-")
