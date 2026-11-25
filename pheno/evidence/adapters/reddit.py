"""Deletion-aware Reddit discovery for anecdotal citations only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

from .base import (
    DiscoveryPage,
    MetadataClient,
    normalized_record,
    payload_items,
    with_retry,
)

REDDIT_CITATION_MEDIA_TYPE = "application/vnd.pheno.reddit-citation+json"


class RedditAdapter:
    """Deletion-aware Reddit discovery for anecdotal citations only.

    Records produced from RedditAdapter pages are flagged as anecdotal
    citations (evidence_class='A') and never feed into reproducible
    benchmark claims. Reddit posts can be deleted by their authors,
    so retention_class='ephemeral_citation' is applied by normalize().

    Satisfies SourceAdapter (kind, endpoint, search, normalize). Requires
    OAuth credentials at construction time.
    """

    kind = "reddit"
    endpoint = "https://oauth.reddit.com/search"

    def __init__(
        self, client: MetadataClient, *, access_token: str, user_agent: str
    ) -> None:
        """Initialize the adapter with OAuth credentials."""
        if not access_token or not user_agent:
            raise ValueError(
                "Reddit requires an OAuth access token and descriptive User-Agent"
            )
        self.client = client
        self.access_token = access_token
        self.user_agent = user_agent

    @with_retry()
    def search(
        self,
        query: str,
        *,
        limit: int = 25,
        sort: str = "new",
        time_filter: str = "month",
        after: str | None = None,
        subreddit: str | None = None,
    ) -> DiscoveryPage:
        """Run a Reddit OAuth search and return a DiscoveryPage."""
        if not query.strip() or len(query) > 512 or not 1 <= limit <= 100:
            raise ValueError(
                "Reddit query must contain 1..512 characters and limit 1..100"
            )
        if sort not in {"relevance", "hot", "top", "new", "comments"}:
            raise ValueError("unsupported Reddit sort")
        if time_filter not in {"hour", "day", "week", "month", "year", "all"}:
            raise ValueError("unsupported Reddit time filter")
        endpoint = (
            f"https://oauth.reddit.com/r/{subreddit}/search"
            if subreddit
            else self.endpoint
        )
        params: dict[str, Any] = {
            "q": query,
            "limit": limit,
            "sort": sort,
            "t": time_filter,
            "raw_json": 1,
        }
        if subreddit:
            params["restrict_sr"] = 1
        if after:
            params["after"] = after
        return self.client.request(
            source_kind=self.kind,
            method="GET",
            url=endpoint,
            params=params,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            },
        )

    @staticmethod
    def citation_pages(page: DiscoveryPage) -> list[DiscoveryPage]:
        """Discard raw user text and return minimal deletion-aware citations."""

        pages: list[DiscoveryPage] = []
        for child in payload_items(page.payload, ("data", "children")):
            data = child.get("data")
            if not isinstance(data, Mapping):
                continue
            fullname = str(data.get("name") or "").strip()
            permalink = str(data.get("permalink") or "").strip()
            if not fullname or not permalink:
                continue
            now = datetime.now(UTC)
            citation = {
                "fullname": fullname,
                "permalink": permalink,
                "retrieved_at": page.retrieved_at,
                "observed_at": page.retrieved_at,
                "subreddit": str(data.get("subreddit") or "unknown"),
                "paraphrased_claim": (
                    "A Reddit post matched the configured discovery query; "
                    "inspect the live source before using the claim."
                ),
                "tombstone_state": "live_at_observation",
                "needs_revalidation_at": (now + timedelta(hours=48)).isoformat(),
            }
            pages.append(
                replace(
                    page,
                    final_url=f"https://www.reddit.com{permalink}",
                    payload=citation,
                    media_type=REDDIT_CITATION_MEDIA_TYPE,
                    incomplete=True,
                )
            )
        return pages

    @staticmethod
    def normalize_citation(page: DiscoveryPage, *, raw_sha256: str) -> dict[str, Any]:
        """Convert a citation DiscoveryPage to one ephemeral-citation record."""
        citation = page.payload
        if not isinstance(citation, Mapping):
            raise ValueError("Reddit citation page must contain citation metadata")
        fullname = str(citation["fullname"])
        record = normalized_record(
            page=page,
            raw_sha256=raw_sha256,
            canonical_name=fullname,
            canonical_url=str(page.final_url),
            revision=fullname,
            mutable=True,
            evidence_class="A",
            aliases=[],
            notes=[str(citation["paraphrased_claim"])],
            compliance={
                "retention_class": "durable_metadata",
                "purge_after": str(citation["needs_revalidation_at"]),
                "tombstoned_at": None,
            },
        )
        record["quality"]["confidence"] = "low"
        record["quality"]["needs_revalidation_at"] = str(
            citation["needs_revalidation_at"]
        )
        return record


__all__ = ["REDDIT_CITATION_MEDIA_TYPE", "RedditAdapter"]
