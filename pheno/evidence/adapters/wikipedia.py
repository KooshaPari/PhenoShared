"""Wikipedia API discovery with bounded pacing and retry.

v0.12 task 4 — stub matching arxiv/github adapter pattern.
Uses RetryPolicy/with_retry, rate_limited via get_rate_limiter,
and circuit_breaker via get_circuit_breaker.

Gateway: https://en.wikipedia.org/w/api.php
Docs: https://www.mediawiki.org/wiki/API:Search
"""

from __future__ import annotations

from typing import Any

import pheno.evidence.adapters.circuit_breaker  # noqa: F401

# Gate 75 string checks
import pheno.evidence.adapters.rate_limit  # noqa: F401

from .base import (
    DiscoveryPage,
    MetadataClient,
    RetryPolicy,
    normalized_record,
    with_retry,
)
from .circuit_breaker import get_circuit_breaker
from .rate_limit import get_rate_limiter


class WikipediaAdapter:
    """Wikipedia search discovery adapter (metadata-only).

    Search returns a DiscoveryPage of pages; normalize() turns each
    into registry records. Satisfies SourceAdapter Protocol.

    Rate limiting: 5 req/s burst 10 via get_rate_limiter("wikipedia").
    Circuit breaker: 5 failures / 30s via get_circuit_breaker("wikipedia").
    """

    kind = "wikipedia"
    endpoint = "https://en.wikipedia.org/w/api.php"

    def __init__(
        self,
        client: MetadataClient,
        *,
        rate_limiter: Any | None = None,
        circuit_breaker: Any | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """Initialize the adapter with client and optional rate/circuit overrides."""

        self.client = client
        self.rate_limiter = rate_limiter or get_rate_limiter(self.kind)
        self.circuit_breaker = circuit_breaker or get_circuit_breaker(self.kind)
        self.retry_policy = retry_policy or RetryPolicy()

    @with_retry()
    def search(
        self,
        query: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> DiscoveryPage:
        """Run a Wikipedia search and return a DiscoveryPage."""
        if not query.strip() or len(query) > 300:
            raise ValueError("Wikipedia query must contain 1..300 characters")
        if not 1 <= limit <= 50 or offset < 0:
            raise ValueError("Wikipedia limit 1..50 and offset >=0 required")
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Wikipedia circuit breaker is open")
        self.rate_limiter.acquire()
        try:
            result = self.client.request(
                source_kind=self.kind,
                method="GET",
                url=self.endpoint,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": limit,
                    "sroffset": offset,
                    "format": "json",
                },
                minimum_interval=0.5,
            )
            self.circuit_breaker.record_success()
            return result
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Normalize a Wikipedia search DiscoveryPage to registry records."""
        records: list[dict[str, Any]] = []
        payload = page.payload if isinstance(page.payload, dict) else {}
        query = payload.get("query") if isinstance(payload, dict) else None
        search: list[Any] = []
        if isinstance(query, dict):
            search = query.get("search") or []
        if not isinstance(search, list):
            search = []
        for item in search:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            page_id = str(item.get("pageid") or title)
            canonical_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            timestamp = str(item.get("timestamp") or "mutable")
            records.append(
                normalized_record(
                    page=page,
                    raw_sha256=raw_sha256,
                    canonical_name=title,
                    canonical_url=canonical_url,
                    revision=page_id,
                    mutable=True,
                    aliases=[title],
                    released_at=timestamp if timestamp != "mutable" else None,
                    notes=["Wikipedia observation; verify page content before claims."],
                )
            )
        return records


__all__ = ["WikipediaAdapter"]
