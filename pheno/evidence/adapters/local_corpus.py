"""Content-hash-only indexing for local ChatGPT research exports."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base import (  # noqa: F401 - retry not needed for local scan; imported for adapter parity (tasks 63-68)
    ADAPTER_VERSION,
    DiscoveryPage,
    normalized_record,
    with_retry,
)


class LocalCorpusAdapter:
    """Local ChatGPT-export corpus discovery (content-hash only).

    scan() walks a directory for matching markdown files and emits
    DiscoveryPages whose payload contains ONLY the SHA-256 hash
    (no content, no path) — preserves the no-PII boundary.

    normalize() returns a single record per DiscoveryPage.

    This adapter does NOT use MetadataClient (no network) and does NOT
    satisfy SourceAdapter because it has no ``search(query)`` method.
    """

    kind = "local_corpus"
    endpoint = "local://corpus-scan"

    @staticmethod
    def scan(root: Path, *, pattern: str = "ChatGPT-*.md") -> list[DiscoveryPage]:
        """Walk ``root`` for files matching ``pattern`` and emit DiscoveryPages."""
        base = Path(root)
        if not base.is_dir():
            raise ValueError(f"local corpus root is not a directory: {base}")
        pages: list[DiscoveryPage] = []
        for path in sorted(base.rglob(pattern)):
            if not path.is_file():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            stat = path.stat()
            retrieved_at = datetime.now(UTC).isoformat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
            payload: dict[str, Any] = {
                "content_sha256": digest,
                "basename": path.name,
                "bytes": stat.st_size,
                "modified_at": modified_at,
                "raw_content_persisted": False,
            }
            pages.append(
                DiscoveryPage(
                    source_kind="local_corpus",
                    method="LOCAL_SCAN",
                    endpoint=LocalCorpusAdapter.endpoint,
                    query={"pattern": pattern},
                    final_url=LocalCorpusAdapter.endpoint,
                    api_version=None,
                    status=200,
                    response_headers={},
                    retrieved_at=retrieved_at,
                    payload=payload,
                    media_type="application/json",
                    incomplete=False,
                )
            )
        return pages

    @staticmethod
    def normalize(page: DiscoveryPage, *, raw_sha256: str) -> dict[str, Any]:
        """Normalize a LocalCorpus DiscoveryPage to a single registry record."""
        payload = page.payload
        if not isinstance(payload, dict):
            raise ValueError("local corpus page must be metadata JSON")
        digest = str(payload["content_sha256"])
        canonical_name = f"local-chatgpt/{digest[:16]}"
        record = normalized_record(
            page=page,
            raw_sha256=raw_sha256,
            canonical_name=canonical_name,
            canonical_url=f"local://sha256/{digest}",
            revision=digest,
            mutable=False,
            evidence_class="L",
            aliases=[str(payload["basename"])],
            released_at=str(payload["modified_at"]),
            notes=[
                "Local design-lineage metadata only; raw export content remains "
                "outside the registry."
            ],
        )
        record["discovery"]["adapter_version"] = ADAPTER_VERSION
        return record


__all__ = ["LocalCorpusAdapter"]
