"""Metadata-only discovery adapters.

Adapters expose search/list metadata only.  They intentionally contain no
model-artifact download, snapshot restore, inference, or server APIs.
"""

from __future__ import annotations

from typing import Any

from .arxiv import ArxivAdapter
from .base import MetadataClient
from .github import GitHubAdapter
from .huggingface import HuggingFaceAdapter
from .local_corpus import LocalCorpusAdapter
from .modelscope import ModelScopeAdapter
from .openalex import OpenAlexAdapter
from .protocols import (
    CandidateExtractor,
    DiscoveryPage,
    HydratableAdapter,
    NormalizedRecord,
    ResolvableAdapter,
    SourceAdapter,
)
from .reddit import RedditAdapter
from .semantic_scholar import SemanticScholarAdapter
from .wikipedia import WikipediaAdapter


def build_adapter(
    kind: str,
    *,
    client: MetadataClient | None = None,
    **kwargs: Any,
) -> object:
    """Look up and construct an adapter by ``kind`` identifier.

    Supported kinds:
      - ``"hf"`` → HuggingFaceAdapter(client)
      - ``"modelscope"`` → ModelScopeAdapter(client)
      - ``"arxiv"`` → ArxivAdapter(client)
      - ``"github"`` → GitHubAdapter(client, token=kwargs.get("token"))
      - ``"reddit"`` → RedditAdapter(client, access_token, user_agent)
      - ``"local_corpus"`` → LocalCorpusAdapter (class, no instance needed)

    Returns the constructed adapter object (no Protocol guarantee —
    callers should ``isinstance(adapter, SourceAdapter)`` if needed).

    Raises ``ValueError`` for unknown kinds or missing required kwargs.
    """
    if kind == "hf":
        if client is None:
            raise ValueError("HuggingFaceAdapter requires a MetadataClient")
        return HuggingFaceAdapter(client)
    if kind == "modelscope":
        if client is None:
            raise ValueError("ModelScopeAdapter requires a MetadataClient")
        return ModelScopeAdapter(client)
    if kind == "arxiv":
        if client is None:
            raise ValueError("ArxivAdapter requires a MetadataClient")
        return ArxivAdapter(client)
    if kind == "github":
        if client is None:
            raise ValueError("GitHubAdapter requires a MetadataClient")
        return GitHubAdapter(client, token=kwargs.get("token"))
    if kind == "reddit":
        if client is None:
            raise ValueError("RedditAdapter requires a MetadataClient")
        access_token = kwargs.get("access_token")
        user_agent = kwargs.get("user_agent")
        if not access_token or not user_agent:
            raise ValueError(
                "RedditAdapter requires access_token and user_agent kwargs"
            )
        return RedditAdapter(client, access_token=access_token, user_agent=user_agent)
    if kind == "local_corpus":
        return LocalCorpusAdapter
    if kind == "openalex":
        if client is None:
            raise ValueError("OpenAlexAdapter requires a MetadataClient")
        return OpenAlexAdapter(
            client,
            **{
                k: v
                for k, v in kwargs.items()
                if k in {"rate_limiter", "circuit_breaker", "retry_policy"}
            },
        )
    if kind == "semantic_scholar":
        if client is None:
            raise ValueError("SemanticScholarAdapter requires a MetadataClient")
        return SemanticScholarAdapter(
            client,
            **{
                k: v
                for k, v in kwargs.items()
                if k in {"rate_limiter", "circuit_breaker", "retry_policy"}
            },
        )
    if kind == "wikipedia":
        if client is None:
            raise ValueError("WikipediaAdapter requires a MetadataClient")
        return WikipediaAdapter(
            client,
            **{
                k: v
                for k, v in kwargs.items()
                if k in {"rate_limiter", "circuit_breaker", "retry_policy"}
            },
        )
    raise ValueError(f"unknown adapter kind: {kind!r}")


def supported_kinds() -> list[str]:
    """Return the list of supported adapter kinds (for docs/registry UI)."""
    return [
        "hf",
        "modelscope",
        "arxiv",
        "github",
        "reddit",
        "local_corpus",
        "openalex",
        "semantic_scholar",
        "wikipedia",
    ]


def search(
    kind: str,
    query: str,
    *,
    client: MetadataClient | None = None,
    limit: int = 25,
    **kwargs: Any,
) -> DiscoveryPage:
    """Dispatch a search call to the adapter identified by ``kind``.

    Convenience wrapper around ``build_adapter`` + ``adapter.search``.
    Returns the ``DiscoveryPage`` from the underlying adapter.
    """
    adapter = build_adapter(kind, client=client, **kwargs)
    if not isinstance(adapter, SourceAdapter):
        raise TypeError(
            f"adapter {kind!r} does not satisfy SourceAdapter (no search(query) method)"
        )
    return adapter.search(query, limit=limit)


def normalize(
    kind: str,
    page: DiscoveryPage,
    *,
    raw_sha256: str,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Dispatch a normalize call to the adapter identified by ``kind``.

    Convenience wrapper around ``build_adapter`` + ``adapter.normalize``.
    Returns the list of registry records.
    """
    client = kwargs.pop("client", None)
    adapter = build_adapter(kind, client=client, **kwargs)
    if not isinstance(adapter, SourceAdapter):
        raise TypeError(
            f"adapter {kind!r} does not satisfy SourceAdapter "
            "(no normalize(page) method)"
        )
    return adapter.normalize(page, raw_sha256=raw_sha256)  # type: ignore[return-value]


def candidate_ids(
    kind: str,
    page: DiscoveryPage,
    *,
    client: MetadataClient | None = None,
    **kwargs: Any,
) -> list[str]:
    """Dispatch a candidate_ids call to the adapter identified by ``kind``.

    Only adapters that satisfy ``CandidateExtractor`` are supported; others
    raise ``TypeError``.
    """
    adapter = build_adapter(kind, client=client, **kwargs)
    if not isinstance(adapter, CandidateExtractor):
        raise TypeError(
            f"adapter {kind!r} does not satisfy CandidateExtractor "
            "(no candidate_ids method)"
        )
    return adapter.candidate_ids(page)


__all__ = [
    "ArxivAdapter",
    "CandidateExtractor",
    "DiscoveryPage",
    "GitHubAdapter",
    "HuggingFaceAdapter",
    "HydratableAdapter",
    "LocalCorpusAdapter",
    "ModelScopeAdapter",
    "NormalizedRecord",
    "OpenAlexAdapter",
    "ResolvableAdapter",
    "RedditAdapter",
    "SemanticScholarAdapter",
    "SourceAdapter",
    "WikipediaAdapter",
    "build_adapter",
    "candidate_ids",
    "normalize",
    "search",
    "supported_kinds",
]
