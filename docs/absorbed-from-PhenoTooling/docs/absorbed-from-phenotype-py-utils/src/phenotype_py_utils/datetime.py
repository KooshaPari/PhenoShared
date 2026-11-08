"""Datetime helpers: ISO 8601 ``now()`` and ``from_unix``.

Both functions return UTC and use a ``Z`` suffix for browser / JSON
interop. Use :func:`iso_now` for the current time and :func:`from_unix`
to convert a Unix timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone


def iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string with 'Z' suffix.

    Example: ``2026-06-11T02:30:00.123456Z``
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def from_unix(ts: float) -> str:
    """Convert a Unix timestamp to an ISO 8601 UTC string with 'Z' suffix."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
