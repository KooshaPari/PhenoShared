"""Input validation helpers for MCP tool parameters.

Defence-in-depth: validate user-supplied strings before they reach gRPC.
"""

from __future__ import annotations

import os
import re

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_TRANSITION_RE = re.compile(r"^[a-z_]+->[a-z_]+$")

MAX_SLUG_LENGTH = 128
MAX_TEXT_LENGTH = 4096
MAX_BATCH_IMPORT_SIZE = 100

VALID_ITEM_TYPES = frozenset({"task", "bug", "story", "epic", "spike", "chore"})


class InputValidationError(ValueError):
    """Raised when an MCP tool input fails validation."""


def validate_slug(value: str, field_name: str = "slug") -> str:
    """Validate a kebab-case slug identifier.

    Raises InputValidationError if the value is empty, too long,
    or contains characters outside ``[a-z0-9-]``.
    """
    if not value:
        raise InputValidationError(f"{field_name} must not be empty")
    if not _SLUG_RE.match(value):
        raise InputValidationError(
            f"{field_name} must be kebab-case (lowercase alphanumeric and hyphens), "
            f"1–{MAX_SLUG_LENGTH} characters; got {value!r}"
        )
    return value


def validate_transition(value: str) -> str:
    """Validate a state transition string like ``specified->planned``."""
    if not _TRANSITION_RE.match(value):
        raise InputValidationError(
            f"transition must match 'state->state' pattern; got {value!r}"
        )
    return value


def validate_text(value: str, field_name: str = "text", max_length: int = MAX_TEXT_LENGTH) -> str:
    """Validate a free-text field against a length limit."""
    if len(value) > max_length:
        raise InputValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters"
        )
    return value


def validate_file_path(path: str, allowed_roots: tuple[str, ...] = ("kitty-specs",)) -> str:
    """Validate a file path to prevent path-traversal attacks.

    The resolved path must reside under one of the *allowed_roots*
    (relative to the current working directory).

    Raises InputValidationError if the path escapes the allowed directories.
    """
    if not path:
        raise InputValidationError("file path must not be empty")

    normalised = os.path.normpath(path)

    if ".." in normalised.split(os.sep):
        raise InputValidationError(
            f"file path must not contain '..' components; got {path!r}"
        )

    for root in allowed_roots:
        if normalised == root or normalised.startswith(root + os.sep):
            return normalised

    raise InputValidationError(
        f"file path must be under one of {allowed_roots}; got {path!r}"
    )


def validate_batch_size(items: list, max_size: int = MAX_BATCH_IMPORT_SIZE) -> list:
    """Validate that a batch does not exceed the maximum size."""
    if len(items) > max_size:
        raise InputValidationError(
            f"batch size {len(items)} exceeds maximum of {max_size}"
        )
    return items


def validate_item_type(value: str) -> str:
    """Validate a backlog item type against the allowlist."""
    if value and value not in VALID_ITEM_TYPES:
        raise InputValidationError(
            f"invalid item_type {value!r}; must be one of {sorted(VALID_ITEM_TYPES)}"
        )
    return value
