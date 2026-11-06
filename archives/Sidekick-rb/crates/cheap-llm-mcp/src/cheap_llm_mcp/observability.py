"""Structured observability helpers for cheap-llm-mcp.

Traces to: docs/remediation/OBSERVABILITY.md, SIDE-OBS-004
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .logging_util import request_scope

log = logging.getLogger("cheap-llm-mcp.observability")

STANDARD_FIELDS = ("op", "provider", "model", "request_id", "duration_ms")


@contextmanager
def operation_span(op: str, **fields: Any) -> Iterator[dict[str, Any]]:
    """Emit start/complete structured log records for an operation."""
    rid: str | None = None
    with request_scope() as bound_id:
        rid = bound_id
        start = time.monotonic()
        payload = {"op": op, "request_id": rid, **fields}
        log.info("op.start", extra=payload)
        try:
            yield payload
        except Exception:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            log.exception(
                "op.error",
                extra={**payload, "duration_ms": elapsed_ms},
            )
            raise
        else:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            log.info("op.complete", extra={**payload, "duration_ms": elapsed_ms})


def standard_field_names() -> tuple[str, ...]:
    """Return documented standard fields for audit contract checks."""
    return STANDARD_FIELDS
