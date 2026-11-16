"""
Specific Exception Types for Pheno SDK

Domain-specific exception classes for different error scenarios.
Each exception type has appropriate defaults for category, error code, and status.
"""

from __future__ import annotations

from .base import ErrorCategory, NonRetryableError, PhenoException, RetryableError

# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(NonRetryableError):
    """
    Raised when input validation fails.

    Examples:
    - Invalid input format
    - Missing required fields
    - Type mismatches
    - Schema validation failures
    """

    default_category = ErrorCategory.VALIDATION
    default_error_code = "VALIDATION_ERROR"


class SchemaValidationError(ValidationError):
    """Schema validation failed."""

    default_error_code = "SCHEMA_VALIDATION_ERROR"


class FieldValidationError(ValidationError):
    """Field-level validation failed."""

    default_error_code = "FIELD_VALIDATION_ERROR"

    def __init__(self, field: str, message: str, **kwargs):
        """Initialize with field name."""
        super().__init__(
            message,
            details={"field": field, **kwargs.get("details", {})},
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.field = field


# ============================================================================
# Resource/Entity Errors
# ============================================================================


class NotFoundError(NonRetryableError):
    """
    Raised when a requested resource is not found.

    Examples:
    - Entity not found by ID
    - File not found
    - Endpoint not found
    """

    default_category = ErrorCategory.RESOURCE_NOT_FOUND
    default_error_code = "NOT_FOUND"


class EntityNotFoundError(NotFoundError):
    """Domain entity not found."""

    default_error_code = "ENTITY_NOT_FOUND"

    def __init__(self, entity_type: str, entity_id: str, **kwargs):
        """Initialize with entity information."""
        message = kwargs.pop("message", f"{entity_type} with ID {entity_id} not found")
        super().__init__(
            message,
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                **kwargs.get("details", {}),
            },
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ResourceNotFoundError(NotFoundError):
    """Generic resource not found."""

    default_error_code = "RESOURCE_NOT_FOUND"


# ============================================================================
# Authentication Errors
# ============================================================================


class AuthenticationError(NonRetryableError):
    """
    Raised when authentication fails.

    Examples:
    - Invalid credentials
    - Missing authentication token
    - Expired token
    - Invalid API key
    """

    default_category = ErrorCategory.AUTHENTICATION
    default_error_code = "AUTHENTICATION_ERROR"


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""

    default_error_code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """Authentication token has expired."""

    default_error_code = "TOKEN_EXPIRED"


class MissingAuthenticationError(AuthenticationError):
    """No authentication credentials provided."""

    default_error_code = "MISSING_AUTHENTICATION"


# ============================================================================
# Authorization Errors
# ============================================================================


class AuthorizationError(NonRetryableError):
    """
    Raised when authorization/permission check fails.

    Examples:
    - Insufficient permissions
    - RLS policy violations
    - Role-based access denial
    - Resource ownership violations
    """

    default_category = ErrorCategory.AUTHORIZATION
    default_error_code = "AUTHORIZATION_ERROR"


class PermissionDeniedError(AuthorizationError):
    """
    Permission denied for the requested operation.

    Compatible with atoms_mcp-old RLS exceptions.
    """

    default_error_code = "PERMISSION_DENIED"

    def __init__(
        self,
        message: str | None = None,
        *,
        table: str | None = None,
        operation: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        """
        Initialize permission denied error.

        Args:
            message: Custom error message
            table: Database table/resource
            operation: Operation being performed
            reason: Reason for denial
            **kwargs: Additional arguments
        """
        if message is None and table and operation and reason:
            message = f"Permission denied for {operation} on {table}: {reason}"
        elif message is None:
            message = "Permission denied for the requested operation"

        details = kwargs.get("details", {})
        if table:
            details["table"] = table
        if operation:
            details["operation"] = operation
        if reason:
            details["reason"] = reason

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.table = table
        self.operation = operation
        self.reason = reason


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    default_error_code = "INSUFFICIENT_PERMISSIONS"


class UnauthorizedAccessError(AuthorizationError):
    """
    Unauthorized access attempt.

    Used for RLS policy violations.
    """

    default_error_code = "UNAUTHORIZED_ACCESS"


# ============================================================================
# Database Errors
# ============================================================================


class DatabaseError(PhenoException):
    """
    Raised when database operations fail.

    Examples:
    - Connection failures
    - Query execution errors
    - Transaction failures
    - Constraint violations
    """

    default_category = ErrorCategory.DATABASE
    default_error_code = "DATABASE_ERROR"


class DatabaseConnectionError(RetryableError):
    """Database connection failed."""

    default_category = ErrorCategory.DATABASE
    default_error_code = "DATABASE_CONNECTION_ERROR"


class ConstraintViolationError(NonRetryableError):
    """Database constraint violated."""

    default_category = ErrorCategory.DATABASE
    default_error_code = "CONSTRAINT_VIOLATION"

    def __init__(
        self,
        message: str,
        *,
        constraint_type: str | None = None,
        constraint_name: str | None = None,
        **kwargs,
    ):
        """Initialize with constraint information."""
        details = kwargs.get("details", {})
        if constraint_type:
            details["constraint_type"] = constraint_type
        if constraint_name:
            details["constraint_name"] = constraint_name

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.constraint_type = constraint_type
        self.constraint_name = constraint_name


class UniqueConstraintError(ConstraintViolationError):
    """Unique constraint violated (duplicate value)."""

    default_error_code = "UNIQUE_CONSTRAINT"

    def __init__(self, message: str = "Duplicate value", **kwargs):
        """Initialize with default message."""
        super().__init__(message, constraint_type="unique", **kwargs)


class ForeignKeyError(ConstraintViolationError):
    """Foreign key constraint violated (referenced item not found)."""

    default_error_code = "FOREIGN_KEY"

    def __init__(self, message: str = "Referenced item not found", **kwargs):
        """Initialize with default message."""
        super().__init__(message, constraint_type="foreign_key", **kwargs)


class CheckConstraintError(ConstraintViolationError):
    """Check constraint violated (validation rule failed)."""

    default_error_code = "CHECK_CONSTRAINT"

    def __init__(self, message: str = "Validation rule failed", **kwargs):
        """Initialize with default message."""
        super().__init__(message, constraint_type="check", **kwargs)


class NotNullConstraintError(ConstraintViolationError):
    """Not null constraint violated (required field missing)."""

    default_error_code = "NOT_NULL"

    def __init__(self, message: str = "Required field missing", **kwargs):
        """Initialize with default message."""
        super().__init__(message, constraint_type="not_null", **kwargs)


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(NonRetryableError):
    """
    Raised when configuration is invalid or missing.

    Examples:
    - Missing required configuration
    - Invalid configuration format
    - Configuration validation failures
    """

    default_category = ErrorCategory.CONFIGURATION
    default_error_code = "CONFIGURATION_ERROR"


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    default_error_code = "MISSING_CONFIGURATION"

    def __init__(self, config_key: str, **kwargs):
        """Initialize with configuration key."""
        message = kwargs.pop("message", f"Missing required configuration: {config_key}")
        super().__init__(
            message,
            details={"config_key": config_key, **kwargs.get("details", {})},
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.config_key = config_key


class InvalidConfigurationError(ConfigurationError):
    """Configuration value is invalid."""

    default_error_code = "INVALID_CONFIGURATION"


# ============================================================================
# Integration/External Service Errors
# ============================================================================


class IntegrationError(RetryableError):
    """
    Raised when external API/service integration fails.

    Examples:
    - External API failures
    - Third-party service errors
    - Integration timeout
    """

    default_category = ErrorCategory.EXTERNAL_SERVICE
    default_error_code = "INTEGRATION_ERROR"


class ExternalServiceError(IntegrationError):
    """External service error."""

    default_error_code = "EXTERNAL_SERVICE_ERROR"


class APIError(IntegrationError):
    """External API error."""

    default_error_code = "API_ERROR"

    def __init__(
        self,
        message: str,
        *,
        api_name: str | None = None,
        api_status: int | None = None,
        **kwargs,
    ):
        """Initialize with API information."""
        details = kwargs.get("details", {})
        if api_name:
            details["api_name"] = api_name
        if api_status:
            details["api_status"] = api_status

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.api_name = api_name
        self.api_status = api_status


# ============================================================================
# Business Logic Errors
# ============================================================================


class BusinessRuleViolation(NonRetryableError):
    """
    Raised when a business rule is violated.

    Examples:
    - Invalid state transitions
    - Business constraint violations
    - Domain rule failures
    """

    default_category = ErrorCategory.BUSINESS_RULE
    default_error_code = "BUSINESS_RULE_VIOLATION"


class InvalidStateTransitionError(BusinessRuleViolation):
    """Invalid state transition attempted."""

    default_error_code = "INVALID_STATE_TRANSITION"

    def __init__(
        self,
        message: str,
        *,
        from_state: str | None = None,
        to_state: str | None = None,
        **kwargs,
    ):
        """Initialize with state information."""
        details = kwargs.get("details", {})
        if from_state:
            details["from_state"] = from_state
        if to_state:
            details["to_state"] = to_state

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.from_state = from_state
        self.to_state = to_state


class DomainError(BusinessRuleViolation):
    """
    Generic domain error.

    Compatible with atoms_mcp-old domain exceptions.
    """

    default_error_code = "DOMAIN_ERROR"


# ============================================================================
# Network Errors
# ============================================================================


class NetworkError(RetryableError):
    """
    Network-related errors.

    Examples:
    - Connection timeouts
    - Network unavailable
    - DNS resolution failures
    """

    default_category = ErrorCategory.NETWORK
    default_error_code = "NETWORK_ERROR"


# ============================================================================
# Rate Limiting Errors
# ============================================================================


class RateLimitError(RetryableError):
    """
    Rate limiting errors.

    Examples:
    - Too many requests
    - Quota exceeded
    """

    default_category = ErrorCategory.RATE_LIMIT
    default_error_code = "RATE_LIMIT_ERROR"

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: int | None = None,
        **kwargs,
    ):
        """Initialize with retry information."""
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.retry_after = retry_after


# ============================================================================
# Internal Errors
# ============================================================================


class InternalError(PhenoException):
    """
    Internal system errors.

    Examples:
    - Unexpected failures
    - Programming errors
    - System errors
    """

    default_category = ErrorCategory.INTERNAL
    default_error_code = "INTERNAL_ERROR"


class NotImplementedError(InternalError):
    """Feature or operation not implemented."""

    default_error_code = "NOT_IMPLEMENTED"

    def __init__(self, feature: str | None = None, **kwargs):
        """Initialize with feature name."""
        message = kwargs.pop(
            "message", f"Not implemented: {feature}" if feature else "Not implemented"
        )
        details = kwargs.get("details", {})
        if feature:
            details["feature"] = feature

        super().__init__(
            message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.feature = feature


__all__ = [
    "APIError",
    # Authentication
    "AuthenticationError",
    # Authorization
    "AuthorizationError",
    # Business Logic
    "BusinessRuleViolation",
    "CheckConstraintError",
    # Configuration
    "ConfigurationError",
    "ConstraintViolationError",
    "DatabaseConnectionError",
    # Database
    "DatabaseError",
    "DomainError",
    "EntityNotFoundError",
    "ExternalServiceError",
    "FieldValidationError",
    "ForeignKeyError",
    "InsufficientPermissionsError",
    # Integration
    "IntegrationError",
    # Internal
    "InternalError",
    "InvalidConfigurationError",
    "InvalidCredentialsError",
    "InvalidStateTransitionError",
    "MissingAuthenticationError",
    "MissingConfigurationError",
    # Network
    "NetworkError",
    # Resources
    "NotFoundError",
    "NotImplementedError",
    "NotNullConstraintError",
    "PermissionDeniedError",
    # Rate Limiting
    "RateLimitError",
    "ResourceNotFoundError",
    "SchemaValidationError",
    "TokenExpiredError",
    "UnauthorizedAccessError",
    "UniqueConstraintError",
    # Validation
    "ValidationError",
]
