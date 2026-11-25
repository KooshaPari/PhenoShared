"""
Convenience helpers for vector search and embedding configuration.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pheno.plugins.supabase.client import MissingSupabaseConfig, get_supabase
from pheno.vector.providers.factory import (
    get_available_providers as _get_available_embedding_providers,
)
from pheno.vector.providers.factory import (
    get_embedding_service as _get_embedding_service,
)
from pheno.vector.search.enhanced import EnhancedVectorSearchService

try:  # Optional dependency for typing only
    from supabase import Client as SupabaseClient  # type: ignore
except Exception:  # pragma: no cover - fallback for typing
    SupabaseClient = Any  # type: ignore


@lru_cache(maxsize=1)
def _cached_embedding_service() -> Any:
    """
    Return the default embedding service (Vertex AI if available).
    """
    return _get_embedding_service()


def get_vector_embedding_service(*, refresh: bool = False) -> Any:
    """
    Return the shared embedding service instance.
    """
    if refresh:
        _cached_embedding_service.cache_clear()
    return _cached_embedding_service()


@lru_cache(maxsize=1)
def _cached_vector_search_service() -> EnhancedVectorSearchService:
    """
    Return a cached vector search service using the default Supabase client.
    """
    client = get_supabase()
    return EnhancedVectorSearchService(client, get_vector_embedding_service())


def get_vector_search_service(
    supabase_client: SupabaseClient | None = None,
    *,
    cache: bool = True,
) -> EnhancedVectorSearchService:
    """Return a configured vector search service.

    Args:
        supabase_client: Optional Supabase client to use. When omitted, a cached
            service bound to the default service-role client is returned.
        cache: If False, always create a new service even for the default client.
    """
    if supabase_client is None and cache:
        return _cached_vector_search_service()

    try:
        client = supabase_client or get_supabase()
    except MissingSupabaseConfig as exc:
        raise RuntimeError(
            "Supabase configuration is required for vector search. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.",
        ) from exc
    return EnhancedVectorSearchService(client, get_vector_embedding_service())


def reset_vector_services() -> None:
    """
    Reset cached embedding and vector search services.
    """
    _cached_embedding_service.cache_clear()
    _cached_vector_search_service.cache_clear()


def vector_provider_status() -> dict[str, bool]:
    """
    Return availability flags for known embedding providers.
    """
    return _get_available_embedding_providers()


__all__ = [
    "get_vector_embedding_service",
    "get_vector_search_service",
    "reset_vector_services",
    "vector_provider_status",
]
