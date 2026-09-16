"""GitHub repository discovery using the versioned REST API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .base import (
    DiscoveryPage,
    MetadataClient,
    normalized_record,
    payload_items,
    with_retry,
)


class GitHubAdapter:
    """GitHub repository + commit discovery adapter.

    Search returns a DiscoveryPage of repository search results;
    resolve_commit returns a DiscoveryPage for a single repo+ref;
    normalize() and normalize_commit() turn each into registry records.

    Satisfies the SourceAdapter Protocol (kind, endpoint, search,
    normalize). Does NOT satisfy CandidateExtractor — instead exposes
    ``candidates(page) -> list[(name, sha)]`` for repo enumeration.

    Optional ``token`` increases the unauthenticated 60 req/hr rate limit
    to 5000 req/hr; never required for read-only metadata fetches.
    """

    kind = "github"
    endpoint = "https://api.github.com/search/repositories"
    api_version = "2026-03-10"

    def __init__(self, client: MetadataClient, *, token: str | None = None) -> None:
        """Initialize the adapter with client and optional token."""

        self.client = client
        self.token = token

    @with_retry()
    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 30,
        sort: str = "updated",
        order: str = "desc",
    ) -> DiscoveryPage:
        """Run a GitHub repository search query and return a DiscoveryPage."""
        if not query.strip() or len(query) > 256:
            raise ValueError("GitHub query must contain 1..256 characters")
        if not 1 <= per_page <= 100 or page < 1:
            raise ValueError("GitHub page must be positive and per_page must be 1..100")
        if sort not in {"stars", "forks", "help-wanted-issues", "updated"}:
            raise ValueError("unsupported GitHub repository sort")
        if order not in {"asc", "desc"}:
            raise ValueError("GitHub order must be asc or desc")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        result = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=self.endpoint,
            params={
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": per_page,
                "page": page,
            },
            headers=headers,
            api_version=self.api_version,
        )
        incomplete = bool(
            isinstance(result.payload, Mapping)
            and result.payload.get("incomplete_results")
        )
        return replace(result, incomplete=incomplete)

    @staticmethod
    def candidates(page: DiscoveryPage) -> list[tuple[str, str]]:
        """Extract ``(full_name, default_branch)`` pairs from a search DiscoveryPage."""
        result: list[tuple[str, str]] = []
        for item in payload_items(page.payload, ("items",)):
            full_name = str(item.get("full_name") or "").strip()
            branch = str(item.get("default_branch") or "HEAD").strip()
            if full_name and "/" in full_name:
                result.append((full_name, branch))
        return result

    @with_retry()
    def resolve_commit(self, full_name: str, ref: str = "HEAD") -> DiscoveryPage:
        """Resolve a single commit SHA for ``full_name`` at ``ref``."""
        if not full_name or "/" not in full_name:
            raise ValueError("GitHub resolution requires owner/repository")
        endpoint = f"https://api.github.com/repos/{full_name}/commits/{ref}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        result = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=endpoint,
            headers=headers,
            api_version=self.api_version,
        )
        payload = result.payload if isinstance(result.payload, Mapping) else {}
        return replace(result, incomplete=not bool(payload.get("sha")))

    def normalize_commit(
        self, page: DiscoveryPage, *, raw_sha256: str, full_name: str
    ) -> list[dict[str, Any]]:
        """Normalize a resolved-commit DiscoveryPage to a registry record."""
        if not isinstance(page.payload, Mapping):
            return []
        full_name = full_name.strip()
        revision = str(page.payload.get("sha") or "").strip()
        if not full_name or not revision:
            return []
        return [
            normalized_record(
                page=page,
                raw_sha256=raw_sha256,
                canonical_name=full_name,
                canonical_url=f"https://github.com/{full_name}",
                revision=revision,
                mutable=False,
                notes=[
                    "Default-branch commit resolved through the versioned GitHub REST API."
                ],
            )
        ]

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Normalize a search DiscoveryPage to a list of mutable registry records."""
        records: list[dict[str, Any]] = []
        for item in payload_items(page.payload, ("items",)):
            full_name = str(item.get("full_name") or "").strip()
            if not full_name or "/" not in full_name:
                continue
            # Search output has no commit SHA. Hydration must resolve the default
            # branch through /commits/{ref}; until then this observation is mutable.
            revision = str(item.get("pushed_at") or item.get("updated_at") or "mutable")
            license_value = item.get("license")
            licenses: list[str] = []
            if isinstance(license_value, Mapping) and license_value.get("spdx_id"):
                licenses.append(str(license_value["spdx_id"]))
            records.append(
                normalized_record(
                    page=page,
                    raw_sha256=raw_sha256,
                    canonical_name=full_name,
                    canonical_url=str(
                        item.get("html_url") or f"https://github.com/{full_name}"
                    ),
                    revision=revision,
                    mutable=True,
                    released_at=item.get("created_at"),
                    declared_licenses=licenses,
                    license_urls=[f"https://github.com/{full_name}/blob/HEAD/LICENSE"],
                    notes=[
                        "Repository search observation; resolve a commit SHA and hash "
                        "license/releases before support claims."
                    ],
                )
            )
        return records


__all__ = ["GitHubAdapter"]
