from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from contextlib import contextmanager

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = _request_id.get()
        if rid is not None:
            payload["request_id"] = rid
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k in (
                "args",
                "msg",
                "levelname",
                "name",
                "created",
                "msecs",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "pathname",
                "filename",
                "module",
                "levelno",
                "funcName",
                "processName",
                "process",
                "threadName",
                "thread",
                "relativeCreated",
                "getMessage",
                "taskName",
            ):
                continue
            if not k.startswith("_"):
                try:
                    json.dumps(v)
                    payload[k] = v
                except (TypeError, ValueError):
                    payload[k] = repr(v)
        return json.dumps(payload)


@contextmanager
def request_scope(rid: str | None = None):
    """Bind a request_id to log records emitted inside this block."""
    token = _request_id.set(rid or uuid.uuid4().hex[:12])
    try:
        yield _request_id.get()
    finally:
        _request_id.reset(token)


def setup_json_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root.addHandler(h)
    root.setLevel(level)
