"""Unified error handling for Pheno SDK.

Provides:
- Error classification and categorization
- Retry logic with exponential backoff
- Circuit breaker pattern
- Structured error responses
"""

# Exception classes
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExternalServiceError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
    ZenMCPError,
)

# Import from unified handler (single source of truth)
from .unified import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    RetryConfig,
    RetryError,
    with_retry,
)
from .unified import UnifiedError as Error
from .unified import UnifiedErrorHandler as ErrorHandler

__all__ = [
    "AuthenticationError",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "ConfigurationError",
    "Error",
    "ErrorCategory",
    "ErrorContext",
    # Error handling
    "ErrorHandler",
    "ErrorSeverity",
    "ExternalServiceError",
    "NetworkError",
    "RateLimitError",
    "ResourceNotFoundError",
    "RetryConfig",
    "RetryError",
    "ValidationError",
    # Exception classes
    "ZenMCPError",
    "with_retry",
]
