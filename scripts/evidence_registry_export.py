"""Export methods for the evidence registry.

This module contains persistence operations for discovery pages and
record storage.
"""

from __future__ import annotations

from pheno.evidence.adapters.base import DiscoveryPage
from pheno.evidence.store import RegistryStore


def persist_page(
    store: RegistryStore,
    page: DiscoveryPage,
    normalizer,
) -> tuple[int, int]:
    snapshot = store.put_snapshot(
        source_kind=page.source_kind,
        source_url=page.final_url,
        payload=page.payload,
        media_type=page.media_type,
        retrieved_at=page.retrieved_at,
    )
    normalized = normalizer(page, raw_sha256=snapshot["sha256"])
    records = normalized if isinstance(normalized, list) else [normalized]
    for record in records:
        store.put_record(record)
    return 1, len(records)
