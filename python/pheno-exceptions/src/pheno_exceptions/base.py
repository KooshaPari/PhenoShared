"""
Base Exception Classes for Pheno SDK

Comprehensive exception hierarchy consolidating error handling from:
- atoms_mcp-old/errors.py (ApiError, POSTGRES_ERRORS)
- atoms_mcp-old/domain/exceptions.py (DomainError hierarchy)
- atoms_mcp-old/schemas/rls/exceptions.py (PermissionDeniedError)
- pheno-sdk existing exceptions (ZenMCPError, ErrorCategory)

This module provides a unified, extensible exception hierarchy with:
- Rich context and metadata support
- HTTP status code mapping
- Error codes and categories
- Detailed error information for debugging
- User-friendly messages for clients
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """
    Categories of errors for consistent handling and routing.
    """

    # Network and communication errors
    NETWORK = "network"

    # Authentication and authorization
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"

    # Validation and input errors
    VALIDATION = "validation"

    # Resource and entity errors
    RESOURCE_NOT_FOUND = "resource_not_found"

    # Rate limiting
    RATE_LIMIT = "rate_limit"

    # External services
    EXTERNAL_SERVICE = "external_service"

    # Configuration errors
    CONFIGURATION = "configuration"

    # Database errors
    DATABASE = "database"

    # Business logic errors
    BUSINESS_RULE = "business_rule"

    # Internal errors
    INTERNAL = "internal"


# HTTP status code mapping for error categories
ERROR_STATUS_MAP = {
    ErrorCategory.NETWORK: 503,
    ErrorCategory.AUTHENTICATION: 401,
    ErrorCategory.AUTHORIZATION: 403,
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.RESOURCE_NOT_FOUND: 404,
    ErrorCategory.RATE_LIMIT: 429,
    ErrorCategory.EXTERNAL_SERVICE: 502,
    ErrorCategory.CONFIGURATION: 500,
    ErrorCategory.DATABASE: 500,
    ErrorCategory.BUSINESS_RULE: 422,
    ErrorCategory.INTERNAL: 500,
}


@dataclass
class ErrorContext:
    """
    Rich error context information for debugging and logging.
    """

    # Core identification
    error_id: str
    error_code: str
    category: ErrorCategory

    # Timing and correlation
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None

    # Component information
    component: str = "unknown"
    operation: str = "unknown"

    # Additional details
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Stack trace
    stack_trace: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "component": self.component,
            "operation": self.operation,
            "details": self.details,
            "metadata": self.metadata,
            "stack_trace": self.stack_trace,
        }


class PhenoException(Exception):
    """
    Base exception class for all Pheno SDK errors.

    Provides:
    - Rich error context and metadata
    - HTTP status code mapping
    - Error categorization
    - Detailed error information
    - User-friendly messages
    - Traceback capture
    """

    # Default category for this exception type
    default_category: ErrorCategory = ErrorCategory.INTERNAL

    # Default error code
    default_error_code: str = "PHENO_ERROR"

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        category: ErrorCategory | None = None,
        status: int | None = None,
        component: str = "unknown",
        operation: str = "unknown",
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        capture_traceback: bool = True,
    ):
        """
        Initialize Pheno exception.

        Args:
            message: Human-readable error message
            error_code: Specific error code (defaults to class default)
            category: Error category (defaults to class default)
            status: HTTP status code (defaults to category mapping)
            component: Component where error occurred
            operation: Operation being performed
            details: Additional error details
            metadata: Additional metadata
            correlation_id: Request correlation ID
            capture_traceback: Whether to capture stack trace
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self.default_error_code
        self.category = category or self.default_category
        self.status = status or ERROR_STATUS_MAP.get(self.category, 500)

        # Create error context
        self.context = ErrorContext(
            error_id=f"{component}_{operation}_{int(time.time())}",
            error_code=self.error_code,
            category=self.category,
            correlation_id=correlation_id,
            component=component,
            operation=operation,
            details=details or {},
            metadata=metadata or {},
            stack_trace=traceback.format_exc() if capture_traceback else None,
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.error_code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        """
        return {
            "error_id": self.context.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "status": self.status,
            "component": self.context.component,
            "operation": self.context.operation,
            "timestamp": self.context.timestamp.isoformat(),
            "correlation_id": self.context.correlation_id,
            "details": self.context.details,
            "metadata": self.context.metadata,
        }

    def to_http_response(self) -> dict[str, Any]:
        """
        Convert to HTTP error response format.
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "error_id": self.context.error_id,
                "timestamp": self.context.timestamp.isoformat(),
                "details": self.context.details,
            },
        }

    def to_api_error(self) -> dict[str, Any]:
        """
        Convert to legacy ApiError format for backward compatibility.
        """
        return {
            "code": self.error_code,
            "message": self.message,
            "status": self.status,
            "details": self.context.details,
        }


class RetryableError(PhenoException):
    """
    Base class for errors that should be retried.
    """


class NonRetryableError(PhenoException):
    """
    Base class for errors that should not be retried.
    """


def is_retryable(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error should be retried
    """
    if isinstance(error, NonRetryableError):
        return False
    if isinstance(error, RetryableError):
        return True
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    if isinstance(error, PhenoException):
        retryable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.EXTERNAL_SERVICE,
        }
        return error.category in retryable_categories
    return False


__all__ = [
    "ERROR_STATUS_MAP",
    "ErrorCategory",
    "ErrorContext",
    "NonRetryableError",
    "PhenoException",
    "RetryableError",
    "is_retryable",
]
