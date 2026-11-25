"""String helpers: :func:`truncate` and :func:`slugify`."""

from __future__ import annotations

import re

__all__ = ["slugify", "truncate"]


def truncate(s: str, max_len: int = 80, suffix: str = "...") -> str:
    """Truncate ``s`` to at most ``max_len`` characters, appending ``suffix`` if cut.

    Args:
        s: Input string.
        max_len: Maximum total length of the result (including suffix).
        suffix: Suffix to append when truncation occurs. Default ``"..."``.

    Returns:
        The original string if it fits, otherwise truncated + suffix.

    Raises:
        ValueError: If ``max_len`` is less than the length of ``suffix``.
    """
    if max_len < len(suffix):
        raise ValueError(f"max_len ({max_len}) must be >= len(suffix) ({len(suffix)})")
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(s: str) -> str:
    """Convert ``s`` to a URL-safe lowercase slug.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("  !!Phenotype  v2  ")
        'phenotype-v2'
        >>> slugify("")
        'untitled'
    """
    slug = _SLUG_RE.sub("-", s.lower()).strip("-")
    return slug or "untitled"
