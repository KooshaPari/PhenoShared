"""
Error Handlers and Utilities

Utilities for normalizing and handling errors, including PostgreSQL error mapping.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from .types import (
    CheckConstraintError,
    ForeignKeyError,
    NotNullConstraintError,
    PermissionDeniedError,
    PhenoException,
    UnauthorizedAccessError,
    UniqueConstraintError,
)

logger = logging.getLogger(__name__)


# PostgreSQL error code mappings
# Mapped from atoms_mcp-old/errors.py POSTGRES_ERRORS
POSTGRES_ERROR_MAP = {
    "23514": (CheckConstraintError, "Validation rule failed", 400),
    "23505": (UniqueConstraintError, "Duplicate value", 409),
    "23503": (ForeignKeyError, "Referenced item not found", 400),
    "23502": (NotNullConstraintError, "Required field missing", 400),
    "42501": (PermissionDeniedError, "Permission denied", 403),
}


def normalize_postgres_error(
    err: Exception, fallback_message: str = "Database error"
) -> PhenoException:
    """
    Normalize PostgreSQL exceptions to Pheno exceptions.

    Maps PostgreSQL error codes to appropriate exception types.

    Args:
        err: Original exception
        fallback_message: Fallback error message

    Returns:
        Normalized Pheno exception
    """
    error_str = str(err)

    # Check PostgreSQL error codes
    for code, (exception_class, default_message, status) in POSTGRES_ERROR_MAP.items():
        if code in error_str:
            tb = traceback.format_exc()
            logger.exception("PostgreSQL error %s: %s", code, error_str)

            return exception_class(
                message=default_message,
                status=status,
                component="database",
                operation="postgres_operation",
                details={"postgres_error": error_str, "postgres_code": code},
                metadata={"traceback": tb},
            )

    # Check for RLS policy violations
    if "row-level security" in error_str.lower():
        message = "Permission denied. Check your organization membership."
        if "projects" in error_str:
            message = "You don't have permission to access this organization."

        tb = traceback.format_exc()
        logger.exception("RLS policy violation: %s", error_str)

        return UnauthorizedAccessError(
            message=message,
            component="database",
            operation="rls_policy",
            details={"postgres_error": error_str},
            metadata={"traceback": tb},
        )

    # Return generic database error
    from .types import DatabaseError

    tb = traceback.format_exc()
    logger.exception("Unhandled database error: %s", error_str)

    return DatabaseError(
        message=error_str or fallback_message,
        component="database",
        operation="unknown",
        details={"error": error_str},
        metadata={"traceback": tb},
    )


def normalize_error(
    err: Exception | str,
    fallback_message: str = "Internal server error",
    component: str = "unknown",
    operation: str = "unknown",
) -> PhenoException:
    """
    Normalize any exception to a Pheno exception.

    This function provides backward compatibility with atoms_mcp-old/errors.py normalize_error.

    Args:
        err: Exception or error string
        fallback_message: Fallback error message
        component: Component where error occurred
        operation: Operation being performed

    Returns:
        Normalized Pheno exception
    """
    # Already a Pheno exception
    if isinstance(err, PhenoException):
        return err

    # String error
    if not isinstance(err, Exception):
        from .types import InternalError

        return InternalError(
            message=fallback_message,
            component=component,
            operation=operation,
        )

    error_str = str(err)

    # Check for PostgreSQL errors
    for code in POSTGRES_ERROR_MAP:
        if code in error_str:
            return normalize_postgres_error(err, fallback_message)

    # Check for RLS violations
    if "row-level security" in error_str.lower():
        return normalize_postgres_error(err, fallback_message)

    # Default to internal error
    from .types import InternalError

    tb = traceback.format_exc()
    logger.exception("Unhandled error: %s", error_str)

    return InternalError(
        message=error_str or fallback_message,
        component=component,
        operation=operation,
        details={"error": error_str},
        metadata={"traceback": tb},
    )


def create_internal_error(
    message: str,
    component: str = "unknown",
    operation: str = "unknown",
    details: dict[str, Any] | None = None,
) -> PhenoException:
    """
    Create an internal server error.

    Provides backward compatibility with atoms_mcp-old/errors.py create_api_error_internal.

    Args:
        message: Error message
        component: Component where error occurred
        operation: Operation being performed
        details: Additional error details

    Returns:
        Internal error exception
    """
    from .types import InternalError

    return InternalError(
        message=message,
        component=component,
        operation=operation,
        details=details or {},
        status=500,
    )


__all__ = [
    "POSTGRES_ERROR_MAP",
    "create_internal_error",
    "normalize_error",
    "normalize_postgres_error",
]
