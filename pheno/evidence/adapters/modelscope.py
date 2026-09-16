"""ModelScope OpenAPI metadata discovery."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from urllib.parse import quote

from .base import (
    DiscoveryPage,
    MetadataClient,
    normalized_record,
    payload_items,
    with_retry,
)


class ModelScopeAdapter:
    """ModelScope OpenAPI metadata discovery adapter.

    Search and detail return DiscoveryPages; normalize() and
    candidate_ids() enumerate the registry records.

    Satisfies both SourceAdapter (kind, endpoint, search, normalize)
    AND CandidateExtractor (candidate_ids for bulk enumeration).
    """

    kind = "modelscope"
    endpoint = "https://modelscope.cn/openapi/v1/models"

    def __init__(self, client: MetadataClient) -> None:
        """Initialize the ModelScope adapter with the shared metadata client."""
        self.client = client

    @with_retry()
    def search(
        self,
        query: str,
        *,
        page_number: int = 1,
        page_size: int = 25,
        owner: str | None = None,
        sort: str | None = None,
        filters: Mapping[str, str] | None = None,
    ) -> DiscoveryPage:
        """Run a ModelScope API model search and return a DiscoveryPage."""
        if not query.strip() or page_number < 1 or page_size < 1:
            raise ValueError(
                "ModelScope search requires a query and positive page values"
            )
        if page_number * page_size > 3000:
            raise ValueError("ModelScope page_number * page_size must be <= 3000")
        params: dict[str, Any] = {
            "search": query,
            "page_number": page_number,
            "page_size": page_size,
        }
        if owner:
            params["owner"] = owner
        if sort:
            params["sort"] = sort
        allowed_filters = {
            "task",
            "library",
            "model_type",
            "custom_tag",
            "license",
            "deploy",
        }
        for name, value in (filters or {}).items():
            if name not in allowed_filters:
                raise ValueError(f"unsupported ModelScope filter: {name}")
            params[f"filter.{name}"] = value
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=self.endpoint,
            params=params,
            api_version="20260413",
        )
        return replace(page, incomplete=True)

    @with_retry()
    def detail(self, model_id: str) -> DiscoveryPage:
        """Fetch a single ModelScope model record by id (``owner/repository``)."""
        if not model_id or "/" not in model_id:
            raise ValueError("ModelScope detail requires owner/repository")
        endpoint = f"{self.endpoint}/{quote(model_id, safe='/')}"
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=endpoint,
            api_version="20260413",
        )
        return replace(page, incomplete=True)

    @classmethod
    def candidate_ids(cls, page: DiscoveryPage) -> list[str]:
        """Extract ``owner/repository`` identifiers from a DiscoveryPage payload."""
        identifiers: list[str] = []
        for item in cls._items(page):
            owner = str(item.get("owner") or item.get("namespace") or "").strip()
            name = str(item.get("name") or item.get("repo_name") or "").strip()
            identifier = str(item.get("id") or item.get("model_id") or "").strip()
            canonical = (
                identifier
                if "/" in identifier
                else "/".join(filter(None, (owner, name)))
            )
            if canonical and "/" in canonical:
                identifiers.append(canonical)
        return identifiers

    @staticmethod
    def _items(page: DiscoveryPage) -> list[Mapping[str, Any]]:
        if isinstance(page.payload, list):
            return [item for item in page.payload if isinstance(item, Mapping)]
        if isinstance(page.payload, Mapping) and any(
            key in page.payload for key in ("id", "model_id", "owner", "repo_name")
        ):
            return [page.payload]
        if isinstance(page.payload, Mapping):
            detail = page.payload.get("data")
            if isinstance(detail, Mapping) and any(
                key in detail for key in ("id", "model_id", "owner", "repo_name")
            ):
                return [detail]
        return payload_items(
            page.payload,
            ("data", "models"),
            ("data", "items"),
            ("models",),
            ("items",),
        )

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Convert a DiscoveryPage into pheno.evidence.v1 NormalizedRecord dicts."""
        records: list[dict[str, Any]] = []
        for item in self._items(page):
            owner = str(item.get("owner") or item.get("namespace") or "").strip()
            name = str(item.get("name") or item.get("repo_name") or "").strip()
            identifier = str(item.get("id") or item.get("model_id") or "").strip()
            canonical_name = (
                identifier
                if "/" in identifier
                else "/".join(filter(None, (owner, name)))
            )
            if not canonical_name or "/" not in canonical_name:
                continue
            immutable = str(
                item.get("revision") or item.get("sha") or item.get("commit") or ""
            ).strip()
            revision = immutable or str(
                item.get("last_modified") or item.get("updated_at") or "mutable"
            )
            license_value = item.get("license")
            licenses = [str(license_value)] if license_value else []
            params = item.get("params")
            total_parameters = (
                int(params)
                if isinstance(params, int)
                and not isinstance(params, bool)
                and params > 0
                else None
            )
            model = {
                "architecture": (
                    str(item.get("model_type")) if item.get("model_type") else None
                ),
                "total_parameters": total_parameters,
                "active_parameters": None,
                "context_tokens": None,
                "modalities": ["text"],
                "mtp_or_draft": None,
            }
            records.append(
                normalized_record(
                    page=page,
                    raw_sha256=raw_sha256,
                    canonical_name=canonical_name,
                    canonical_url=(
                        "https://modelscope.cn/models/"
                        f"{quote(canonical_name, safe='/')}"
                    ),
                    revision=revision,
                    mutable=not bool(immutable),
                    released_at=item.get("created_at"),
                    declared_licenses=licenses,
                    model=model,
                    notes=[
                        "Search metadata only; resolve repository revision and file inventory before admission."
                    ],
                )
            )
        return records


__all__ = ["ModelScopeAdapter"]
