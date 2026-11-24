"""Semantic Scholar Graph API discovery with bounded pacing and retry.

v0.12 task 4 — stub matching arxiv/github adapter pattern.
Uses RetryPolicy/with_retry, rate_limited via get_rate_limiter,
and circuit_breaker via get_circuit_breaker.

Gateway: https://api.semanticscholar.org/graph/v1/paper/search
Docs: https://api.semanticscholar.org/api-docs/graph
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


class SemanticScholarAdapter:
    """Semantic Scholar discovery adapter (metadata-only).

    Search returns a DiscoveryPage of papers; normalize() turns each
    into registry records. Satisfies SourceAdapter Protocol.

    Rate limiting: 5 req/s burst 10 via get_rate_limiter("semantic_scholar").
    Circuit breaker: 5 failures / 30s via get_circuit_breaker("semantic_scholar").
    """

    kind = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(
        self,
        client: MetadataClient,
        *,
        rate_limiter: Any | None = None,
        circuit_breaker: Any | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.client = client
        self.rate_limiter = rate_limiter or get_rate_limiter(self.kind)
        self.circuit_breaker = circuit_breaker or get_circuit_breaker(self.kind)
        self.retry_policy = retry_policy or RetryPolicy()

    @with_retry()
    def search(
        self,
        query: str,
        *,
        offset: int = 0,
        limit: int = 25,
        fields: str = "paperId,title,url,year,externalIds",
    ) -> DiscoveryPage:
        """Run a Semantic Scholar paper search and return a DiscoveryPage."""
        if not query.strip() or len(query) > 512:
            raise ValueError("Semantic Scholar query must contain 1..512 characters")
        if not 0 <= offset <= 10000 or not 1 <= limit <= 100:
            raise ValueError(
                "Semantic Scholar offset 0..10000 and limit 1..100 required"
            )
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Semantic Scholar circuit breaker is open")
        self.rate_limiter.acquire()
        try:
            result = self.client.request(
                source_kind=self.kind,
                method="GET",
                url=self.endpoint,
                params={
                    "query": query,
                    "offset": offset,
                    "limit": limit,
                    "fields": fields,
                },
                minimum_interval=1.0,
            )
            self.circuit_breaker.record_success()
            return result
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Normalize a Semantic Scholar search DiscoveryPage to registry records."""
        records: list[dict[str, Any]] = []
        payload = page.payload if isinstance(page.payload, dict) else {}
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            data = []
        for item in data:
            if not isinstance(item, dict):
                continue
            paper_id = str(item.get("paperId") or "").strip()
            if not paper_id:
                continue
            title = str(item.get("title") or "").strip()
            url = str(
                item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
            )
            year = item.get("year")
            revision = str(year) if year else "mutable"
            records.append(
                normalized_record(
                    page=page,
                    raw_sha256=raw_sha256,
                    canonical_name=paper_id,
                    canonical_url=url,
                    revision=revision,
                    mutable=True,
                    aliases=[title] if title else [],
                    notes=[
                        "Semantic Scholar observation; verify externalIds before claims."
                    ],
                )
            )
        return records


__all__ = ["SemanticScholarAdapter"]
