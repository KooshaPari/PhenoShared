"""Exception classes for Pheno SDK.

Extracted from handler.py as part of Phase 1 consolidation. These exception classes are
preserved for backwards compatibility.
"""

import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """
    Categories of errors for consistent handling.
    """

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"


class ZenMCPError(Exception):
    """
    Base exception class for PyDevKit errors.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        component: str = "unknown",
        operation: str = "unknown",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.component = component
        self.operation = operation
        self.details = details
        self.correlation_id = correlation_id
        self.error_id = f"{component}_{operation}_{int(time.time())}"
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        """
        return {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "component": self.component,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "details": self.details,
        }

    def to_http_response(self) -> dict[str, Any]:
        """
        Convert to HTTP error response format.
        """
        return {
            "error": {
                "code": self.category.value,
                "message": self.message,
                "error_id": self.error_id,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details,
            },
        }


class NetworkError(ZenMCPError):
    """
    Network-related errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class AuthenticationError(ZenMCPError):
    """
    Authentication-related errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, **kwargs)


class ValidationError(ZenMCPError):
    """
    Input validation errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


class ResourceNotFoundError(ZenMCPError):
    """
    Resource not found errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.RESOURCE_NOT_FOUND, **kwargs)


class RateLimitError(ZenMCPError):
    """
    Rate limiting errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.RATE_LIMIT, **kwargs)


class ExternalServiceError(ZenMCPError):
    """
    External service errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.EXTERNAL_SERVICE, **kwargs)


class ConfigurationError(ZenMCPError):
    """
    Configuration-related errors.
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONFIGURATION, **kwargs)


# Additional exception classes for compatibility
class StructuredError(ZenMCPError):
    """
    Structured error with enhanced context (from enhanced.py).
    """


class ErrorHandlingError(ZenMCPError):
    """
    Base exception for error handling errors (from core/types.py).
    """

    def __init__(self, message: str, error_code: str | None = None, **kwargs):
        super().__init__(message, category=ErrorCategory.INTERNAL, **kwargs)
        self.error_code = error_code


class RetryableError(ZenMCPError):
    """
    Base class for errors that should be retried (from retry.py).
    """


class NonRetryableError(ZenMCPError):
    """
    Base class for errors that should not be retried (from retry.py).
    """


def is_retryable(error: Exception) -> bool:
    """
    Check if an error is retryable.
    """
    if isinstance(error, NonRetryableError):
        return False
    if isinstance(error, RetryableError):
        return True
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    if isinstance(error, ZenMCPError):
        retryable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.EXTERNAL_SERVICE,
        }
        return error.category in retryable_categories
    return False


__all__ = [
    "AuthenticationError",
    "ConfigurationError",
    "ErrorCategory",
    "ErrorHandlingError",
    "ExternalServiceError",
    "NetworkError",
    "NonRetryableError",
    "RateLimitError",
    "ResourceNotFoundError",
    "RetryableError",
    "StructuredError",
    "ValidationError",
    "ZenMCPError",
    "is_retryable",
]
