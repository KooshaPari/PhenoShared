"""structlog integration: bind the current request id to every log call.

Lazy import: if `structlog` is not installed, `bind_request_id` returns
the logger object unchanged so that callers don't need to feature-check
the integration at every use site.
"""

from __future__ import annotations

import functools
from typing import Any

from phenotype_request_id.context import get_request_id

_LOG_METHODS = ("debug", "info", "warn", "warning", "error", "critical")


def _try_structlog() -> Any | None:
    try:
        import structlog  # type: ignore[import-not-found]

        return structlog
    except Exception:
        return None


def _make_bound_logger(logger: Any) -> Any:
    """Return a structlog-style bound logger that auto-includes request_id.

    The returned object proxies attribute access to the original logger
    while injecting the current `request_id` from the contextvar at
    every call. If the contextvar is unset, the call is forwarded
    unchanged.
    """

    def _bind(rid: str | None) -> Any:
        if rid is None or not hasattr(logger, "bind"):
            return logger
        return logger.bind(request_id=rid)

    class _Bound:
        __slots__ = ("_logger",)

        def __init__(self, base: Any) -> None:
            self._logger = base

        def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
            target = _bind(get_request_id())
            fn = getattr(target, method, None)
            if fn is None and callable(target):
                return target(*args, **kwargs)
            if fn is None:
                return None
            return fn(*args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            if name in _LOG_METHODS:
                return functools.partial(self._call, name)
            return getattr(self._logger, name)

        def bind(self, **kwargs: Any) -> "_Bound":
            merged = logger.bind(**kwargs) if hasattr(logger, "bind") else logger
            return _Bound(merged)

    return _Bound(logger)


def bind_request_id(logger: Any) -> Any:
    """Wrap a structlog-style logger so every call includes `request_id`.

    If `structlog` is not installed, the logger is returned unchanged
    (no exception, no side effect). When structlog is present, the
    returned object auto-injects the current `request_id` from the
    contextvar at call time.
    """
    if _try_structlog() is None:
        return logger
    return _make_bound_logger(logger)
