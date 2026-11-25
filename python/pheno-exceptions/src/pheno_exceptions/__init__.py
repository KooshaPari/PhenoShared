"""
Pheno SDK Exception Hierarchy

Comprehensive, unified exception hierarchy consolidating error handling from:
- atoms_mcp-old error handling (ApiError, domain exceptions, RLS exceptions)
- pheno-sdk existing exceptions (ZenMCPError hierarchy)

This module provides a complete, extensible exception system with:
- Rich context and metadata support
- HTTP status code mapping
- Error categorization and codes
- PostgreSQL error normalization
- Retryability detection
- Backward compatibility

Exception Hierarchy:
====================

PhenoException (base)
├── RetryableError
│   ├── NetworkError
│   ├── RateLimitError
│   ├── DatabaseConnectionError
│   └── IntegrationError
│       ├── ExternalServiceError
│       └── APIError
├── NonRetryableError
│   ├── ValidationError
│   │   ├── SchemaValidationError
│   │   └── FieldValidationError
│   ├── NotFoundError
│   │   ├── EntityNotFoundError
│   │   └── ResourceNotFoundError
│   ├── AuthenticationError
│   │   ├── InvalidCredentialsError
│   │   ├── TokenExpiredError
│   │   └── MissingAuthenticationError
│   ├── AuthorizationError
│   │   ├── PermissionDeniedError
│   │   ├── InsufficientPermissionsError
│   │   └── UnauthorizedAccessError
│   ├── ConfigurationError
│   │   ├── MissingConfigurationError
│   │   └── InvalidConfigurationError
│   ├── ConstraintViolationError
│   │   ├── UniqueConstraintError
│   │   ├── ForeignKeyError
│   │   ├── CheckConstraintError
│   │   └── NotNullConstraintError
│   └── BusinessRuleViolation
│       ├── InvalidStateTransitionError
│       └── DomainError
└── InternalError
    └── NotImplementedError

Error Categories:
=================
- NETWORK: Network and communication errors
- AUTHENTICATION: Authentication failures
- AUTHORIZATION: Permission and authorization failures
- VALIDATION: Input validation failures
- RESOURCE_NOT_FOUND: Resource/entity not found
- RATE_LIMIT: Rate limiting
- EXTERNAL_SERVICE: External API/service failures
- CONFIGURATION: Configuration problems
- DATABASE: Database operation failures
- BUSINESS_RULE: Business logic violations
- INTERNAL: Internal system errors

Usage Examples:
===============

Basic usage:
```python
from pheno.exceptions import ValidationError, EntityNotFoundError

# Raise with message
raise ValidationError("Invalid email format")

# Raise with rich context
raise EntityNotFoundError(
    entity_type="User",
    entity_id="123",
    component="user_service",
    operation="get_user"
)
```

Error handling:
```python
from pheno.exceptions import PhenoException, is_retryable

try:
    do_something()
except PhenoException as e:
    if is_retryable(e):
        retry()
    else:
        return e.to_http_response()
```

PostgreSQL error normalization:
```python
from pheno.exceptions import normalize_postgres_error

try:
    db_operation()
except Exception as e:
    raise normalize_postgres_error(e)
```

Backward compatibility:
```python
# Legacy ApiError format
error.to_api_error()  # Returns: {code, message, status, details}

# Legacy DomainError
from pheno.exceptions import DomainError
raise DomainError("Business rule violated")
```
"""

from __future__ import annotations

# Base classes and utilities
from .base import (
    ERROR_STATUS_MAP,
    ErrorCategory,
    ErrorContext,
    NonRetryableError,
    PhenoException,
    RetryableError,
    is_retryable,
)

# Error handlers
from .handlers import (
    POSTGRES_ERROR_MAP,
    create_internal_error,
    normalize_error,
    normalize_postgres_error,
)

# Specific exception types
from .types import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolation,
    CheckConstraintError,
    ConfigurationError,
    ConstraintViolationError,
    DatabaseConnectionError,
    DatabaseError,
    DomainError,
    EntityNotFoundError,
    ExternalServiceError,
    FieldValidationError,
    ForeignKeyError,
    InsufficientPermissionsError,
    IntegrationError,
    InternalError,
    InvalidConfigurationError,
    InvalidCredentialsError,
    InvalidStateTransitionError,
    MissingAuthenticationError,
    MissingConfigurationError,
    NetworkError,
    NotFoundError,
    NotImplementedError,
    NotNullConstraintError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    SchemaValidationError,
    TokenExpiredError,
    UnauthorizedAccessError,
    UniqueConstraintError,
    ValidationError,
)

# Backward compatibility aliases
ZenMCPError = PhenoException  # Alias for existing code
StructuredError = PhenoException
ErrorHandlingError = InternalError


__all__ = [
    "ERROR_STATUS_MAP",
    "POSTGRES_ERROR_MAP",
    "APIError",
    # Authentication errors
    "AuthenticationError",
    # Authorization errors
    "AuthorizationError",
    # Business logic errors
    "BusinessRuleViolation",
    "CheckConstraintError",
    # Configuration errors
    "ConfigurationError",
    "ConstraintViolationError",
    "DatabaseConnectionError",
    # Database errors
    "DatabaseError",
    "DomainError",
    "EntityNotFoundError",
    "ErrorCategory",
    "ErrorContext",
    "ErrorHandlingError",
    "ExternalServiceError",
    "FieldValidationError",
    "ForeignKeyError",
    "InsufficientPermissionsError",
    # Integration errors
    "IntegrationError",
    # Internal errors
    "InternalError",
    "InvalidConfigurationError",
    "InvalidCredentialsError",
    "InvalidStateTransitionError",
    "MissingAuthenticationError",
    "MissingConfigurationError",
    # Network errors
    "NetworkError",
    "NonRetryableError",
    # Resource/entity errors
    "NotFoundError",
    "NotImplementedError",
    "NotNullConstraintError",
    "PermissionDeniedError",
    # Base classes
    "PhenoException",
    # Rate limiting errors
    "RateLimitError",
    "ResourceNotFoundError",
    "RetryableError",
    "SchemaValidationError",
    "StructuredError",
    "TokenExpiredError",
    "UnauthorizedAccessError",
    "UniqueConstraintError",
    # Validation errors
    "ValidationError",
    # Backward compatibility
    "ZenMCPError",
    "create_internal_error",
    # Utilities
    "is_retryable",
    "normalize_error",
    "normalize_postgres_error",
]
