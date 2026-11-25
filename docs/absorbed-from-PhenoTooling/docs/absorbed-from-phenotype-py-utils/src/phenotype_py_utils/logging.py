"""Logging setup with sensible defaults and optional JSON formatter.

Wraps ``logging.basicConfig`` with: a structured format string, optional
JSON output (for OTel / log aggregators), and per-call configuration of
the output stream and level. The handler list is cleared before adding the
new one so this function is idempotent.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, ClassVar

DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON.

    Useful for OTel / log aggregators (Loki, Datadog, etc.). Includes
    timestamp, level, logger name, message, and exception info when present.
    """

    DEFAULT_FIELDS: ClassVar[set[str]] = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str)


def setup_logging(
    level: str = "INFO",
    *,
    json_output: bool = False,
    format: str = DEFAULT_FORMAT,
    stream: Any = None,
) -> None:
    """Configure the root logger with a single handler.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Case-
            insensitive.
        json_output: If True, emit JSON-formatted records (for OTel).
        format: Format string for non-JSON output.
        stream: Output stream (defaults to stderr).
    """
    handler = logging.StreamHandler(stream or sys.stderr)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(format))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
