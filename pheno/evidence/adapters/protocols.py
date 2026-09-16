"""Adapter Protocol contracts — structural typing for evidence adapters.

This module defines the runtime-checkable Protocols that all evidence
adapters should satisfy. The Protocols are intentionally narrow: they
specify the *minimum* contract, leaving source-specific extensions
(e.g. ``HuggingFaceAdapter.detail``) as separate Protocols layered on
top.

Why a Protocol rather than an ABC?
  - Adapters live in separate modules and are imported lazily
  - Structural typing lets us add a new adapter without editing base.py
  - ``runtime_checkable`` lets us write adapter assertions in tests

The Protocols defined here correspond to the WBS v0.10 Phase 4
"pheno/evidence adapter hardening" subphase (tasks 61-75).
"""

from __future__ import annotations

from typing import Any, Protocol, TypedDict, runtime_checkable


class NormalizedRecord(TypedDict, total=False):
    """Output shape of ``SourceAdapter.normalize`` (one of N).

    Required keys:
      - schema_version: pinned to ``"pheno.evidence.v1"``
      - record_id: deterministic hash from ``(source_kind, canonical_name, revision)``
      - source: {kind, url, revision, evidence_class, raw_sha256}
      - subject: {canonical_name, aliases, released_at, license}
      - gates: {metadata_only, license, execution}
    """

    schema_version: str
    record_id: str
    retrieved_at: str
    source: dict[str, Any]
    subject: dict[str, Any]
    model: dict[str, Any] | None
    artifacts: list[dict[str, Any]]
    runtime_support: list[dict[str, Any]]
    benchmark_claims: list[dict[str, Any]]
    gates: dict[str, Any]
    discovery: dict[str, Any]
    resolved: dict[str, Any]
    license: dict[str, Any]
    quality: dict[str, Any]
    compliance: dict[str, Any]
    notes: list[str]


@runtime_checkable
class SourceAdapter(Protocol):
    """Minimum contract for any evidence source adapter.

    All adapters are expected to expose:
      - ``kind``: short identifier (e.g. ``"hf"``, ``"arxiv"``)
      - ``endpoint``: canonical base URL for the metadata API
      - ``search``: bounded metadata search returning a DiscoveryPage
      - ``normalize``: turn one DiscoveryPage into one or more
        ``pheno.evidence.v1`` registry records (list of NormalizedRecord)
    """

    kind: str
    endpoint: str

    def search(self, query: str, *, limit: int = 25) -> DiscoveryPage:
        """Run a bounded metadata search and return a DiscoveryPage."""
        ...

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[NormalizedRecord]:
        """Normalize a DiscoveryPage into one or more pheno.evidence.v1 records."""
        ...


@runtime_checkable
class ResolvableAdapter(Protocol):
    """Adapter that supports resolving a canonical identity to a revision.

    Implementations: HF (model_id + revision), GitHub (repo + ref),
    ArXiv (paper_id), ModelScope (model_id).
    """

    def resolve(self, identity: str, *, revision: str | None = None) -> DiscoveryPage:
        """Resolve a canonical identity to a revision-pinned DiscoveryPage."""
        ...


@runtime_checkable
class HydratableAdapter(Protocol):
    """Adapter that supports an extra detail/config hydration step.

    Implementations: HuggingFaceAdapter (config fetch after detail).
    """

    def hydrate(self, page: DiscoveryPage) -> DiscoveryPage:
        """Run extra detail/config hydration on a DiscoveryPage."""
        ...


@runtime_checkable
class CandidateExtractor(Protocol):
    """Adapter that exposes candidate ids from a search DiscoveryPage.

    Used by registry merges to enumerate every model that the page
    might describe without forcing a full hydrate round-trip.
    """

    def candidate_ids(self, page: DiscoveryPage) -> list[str]:
        """Extract candidate model ids from a DiscoveryPage without full hydrate."""
        ...


# Aliases kept for forward references in Protocols.
DiscoveryPage = Any  # forward ref — see pheno.evidence.adapters.base.DiscoveryPage


__all__ = [
    "CandidateExtractor",
    "DiscoveryPage",
    "HydratableAdapter",
    "NormalizedRecord",
    "ResolvableAdapter",
    "SourceAdapter",
]
