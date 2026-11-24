"""
Unified Error Handler - Consolidates all error handling functionality.

This module combines:
- Error classification and categorization
- Retry logic with exponential backoff
- Circuit breaker pattern
- Error recovery strategies
- Structured error responses

Replaces:
- errors/enhanced.py
- errors/handler.py
- errors/core/handler.py
- errors/retry.py (partially)
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

# Try to import tenacity for retry logic
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Core Types
# ============================================================================


class ErrorCategory(Enum):
    """
    Unified error categories.
    """

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """
    Error severity levels.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """
    Context information for an error.
    """

    error: Exception
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    operation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    retry_attempt: int = 0
    total_attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "error_type": type(self.error).__name__,
            "message": str(self.error),
            "category": self.category.value,
            "severity": self.severity.value,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "retry_attempt": self.retry_attempt,
            "total_attempts": self.total_attempts,
            "metadata": self.metadata,
        }


@dataclass
class RetryConfig:
    """
    Configuration for retry logic.
    """

    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_categories: set[ErrorCategory] = field(
        default_factory=lambda: {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.SERVICE_UNAVAILABLE,
        },
    )


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker.
    """

    failure_threshold: int = 5
    timeout: float = 60.0
    success_threshold: int = 3
    half_open_max_calls: int = 3


# ============================================================================
# Exceptions
# ============================================================================


class UnifiedError(Exception):
    """
    Base exception with context.
    """

    def __init__(self, context: ErrorContext):
        self.context = context
        super().__init__(str(context.error))


class RetryError(UnifiedError):
    """
    Raised when retry attempts are exhausted.
    """


class CircuitBreakerError(UnifiedError):
    """
    Raised when circuit breaker is open.
    """


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """
    Circuit breaker implementation.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = "closed"  # closed, open, half_open
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0

    def is_open(self) -> bool:
        """
        Check if circuit breaker is open.
        """
        if self._state == "closed":
            return False

        if self._state == "open":
            # Check if timeout has elapsed
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.config.timeout:
                    self._state = "half_open"
                    self._half_open_calls = 0
                    logger.info(f"Circuit breaker {self.name} entering half-open state")
                    return False
            return True

        # half_open state
        return self._half_open_calls >= self.config.half_open_max_calls

    def record_success(self) -> None:
        """
        Record a successful call.
        """
        if self._state == "half_open":
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = "closed"
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit breaker {self.name} closed")
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed call.
        """
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == "half_open":
            self._state = "open"
            logger.warning(f"Circuit breaker {self.name} reopened")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = "open"
            logger.warning(
                f"Circuit breaker {self.name} opened after {self._failure_count} failures",
            )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        """
        if self.is_open():
            raise CircuitBreakerError(
                ErrorContext(
                    error=Exception(f"Circuit breaker {self.name} is open"),
                    category=ErrorCategory.SERVICE_UNAVAILABLE,
                    severity=ErrorSeverity.HIGH,
                ),
            )

        if self._state == "half_open":
            self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


# ============================================================================
# Unified Error Handler
# ============================================================================


class UnifiedErrorHandler:
    """Unified error handler combining all error handling functionality.

    Features:
    - Error classification
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Structured error responses
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        enable_circuit_breaker: bool = True,
    ):
        self.retry_config = retry_config or RetryConfig()
        self.enable_circuit_breaker = enable_circuit_breaker
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify an error into a category.
        """
        error_type = type(error).__name__.lower()
        error_msg = str(error).lower()

        # Network errors
        if any(x in error_type for x in ["network", "connection", "socket"]):
            return ErrorCategory.NETWORK

        # Authentication/Authorization
        if any(x in error_type for x in ["auth", "permission", "forbidden"]):
            if "forbidden" in error_type or "403" in error_msg:
                return ErrorCategory.AUTHORIZATION
            return ErrorCategory.AUTHENTICATION

        # Validation
        if any(x in error_type for x in ["validation", "invalid", "schema"]):
            return ErrorCategory.VALIDATION

        # Timeout
        if "timeout" in error_type or "timeout" in error_msg:
            return ErrorCategory.TIMEOUT

        # Rate limit
        if "rate" in error_msg or "429" in error_msg or "quota" in error_msg:
            return ErrorCategory.RATE_LIMIT

        # Service unavailable
        if "503" in error_msg or "unavailable" in error_msg:
            return ErrorCategory.SERVICE_UNAVAILABLE

        return ErrorCategory.UNKNOWN

    def create_context(self, error: Exception, operation: str = "", **metadata) -> ErrorContext:
        """
        Create error context.
        """
        return ErrorContext(
            error=error,
            category=self.classify_error(error),
            severity=ErrorSeverity.MEDIUM,
            operation=operation,
            metadata=metadata,
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        """
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name)
        return self._circuit_breakers[name]


# ============================================================================
# Decorators
# ============================================================================


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exponential_base: float = 2.0,
    config: RetryConfig | None = None,
) -> Callable[[F], F]:
    """
    Decorator to add retry logic with exponential backoff.
    """
    cfg = config or RetryConfig(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        exponential_base=exponential_base,
    )

    if TENACITY_AVAILABLE:
        # Use tenacity if available
        return retry(
            stop=stop_after_attempt(cfg.max_attempts),
            wait=wait_exponential(
                multiplier=cfg.min_wait,
                max=cfg.max_wait,
                exp_base=cfg.exponential_base,
            ),
        )

    # Fallback implementation
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(cfg.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < cfg.max_attempts - 1:
                        delay = min(cfg.min_wait * (cfg.exponential_base**attempt), cfg.max_wait)
                        if cfg.jitter:
                            delay *= 0.5 + random.random() * 0.5
                        await asyncio.sleep(delay)
            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(cfg.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < cfg.max_attempts - 1:
                        delay = min(cfg.min_wait * (cfg.exponential_base**attempt), cfg.max_wait)
                        if cfg.jitter:
                            delay *= 0.5 + random.random() * 0.5
                        time.sleep(delay)
            raise last_error

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "ErrorCategory",
    "ErrorContext",
    "ErrorSeverity",
    "RetryConfig",
    "RetryError",
    "UnifiedError",
    "UnifiedErrorHandler",
    "with_retry",
]
