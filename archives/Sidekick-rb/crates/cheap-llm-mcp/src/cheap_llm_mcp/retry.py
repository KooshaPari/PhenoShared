from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx

log = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


async def with_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    **kwargs: Any,
) -> T:
    """Exponential backoff with jitter for HTTP provider calls."""
    for i in range(attempts):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in RETRYABLE_STATUS or i == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2**i)) + random.uniform(0, 0.25)
            log.warning(
                "retryable HTTP %s, attempt %d/%d, sleeping %.2fs",
                e.response.status_code,
                i + 1,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)
        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            if i == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2**i)) + random.uniform(0, 0.25)
            log.warning(
                "transient %s, attempt %d/%d, sleeping %.2fs",
                type(e).__name__,
                i + 1,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")
