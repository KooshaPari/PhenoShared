"""phenotype-request-id: zero-dep request-ID propagation for ASGI services.

Public surface lives in the submodules:
    - context: ContextVar store
    - fastapi: ASGI middleware (requires fastapi/starlette)
    - logging: structlog binder (requires structlog)
"""

from phenotype_request_id.context import (
    get_request_id,
    set_request_id,
    with_request_id,
)

__all__ = [
    "get_request_id",
    "set_request_id",
    "with_request_id",
]

__version__ = "0.1.0"
