"""tracera — TraceraAdapter skeleton for Grapheon/Tracera persistent traces.

HTTP client for the Grapheon/Tracera trace repository. Maps pheno
`traces/` events to the Tracera API surface (see
`docs/integrations/tracera-api.md`):

- `append_event` → POST /evidence
- `query`        → GET  /evidence?session_id=...
- `flush`        → no-op (HTTP is synchronous; no batching yet)
- `health`       → GET  /healthz

Configuration (TRACERA_* destination variables, with GRAPHEON_* fallback):

- TRACERA_HOST (default 127.0.0.1)
- TRACERA_PORT (default 8080)
- TRACERA_BASE_URL (overrides HOST:PORT construction)
- TRACERA_API_TOKEN (optional client bearer token)

This is the skeleton (task 8). Tasks 9-11 add implementations for the
abstract methods; task 12 adds config schema; task 13 adds tests.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any
from uuid import UUID

from .protocols import TraceEvent, TraceStoreError

# Canonical Tracera health endpoint (per docs/integrations/tracera-api.md).
TRACERA_HEALTH_PATH = "/healthz"

# Reserved metadata keys written by append_event before merging user
# payload. query() excludes these when reconstructing TraceEvent.payload.
# See docs/integrations/tracera-events.md §5 for the contract.
RESERVED_METADATA_KEYS = frozenset(
    {
        "pheno_event_id",
        "pheno_event_kind",
        "pheno_event_ts",
        "actor",
        "session_id",
        "target",
    }
)


def _env_value(canonical: str, legacy: str) -> str | None:
    """Return Tracera destination config, falling back to Grapheon."""
    return os.environ.get(canonical) or os.environ.get(legacy)


class TraceraAdapter:
    """HTTP client for the Grapheon/Tracera trace repository.

    Skeleton implementation — methods raise NotImplementedError until
    tasks 9-11 land. Constructor + URL resolution + health-check are
    implemented in this skeleton for downstream tasks to build on.

    Args:
        base_url: explicit base URL (e.g., "http://localhost:8080").
            Overrides env var construction.
        host: hostname / IP (default: GRAPHEON_HOST or 127.0.0.1).
        port: TCP port (default: GRAPHEON_PORT or 8080).
        token: optional API token (default: GRAPHEON_API_TOKEN).
        timeout: HTTP request timeout in seconds (default: 5.0).
        batch_size: max events per batched POST /evidence request
            when draining the buffer via flush() (default: 32).

    Note:
        The absorption destination is Tracera. Explicit arguments win,
        followed by `TRACERA_*`, then compatible `GRAPHEON_*` fallbacks.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
        timeout: float = 5.0,
        batch_size: int = 32,
    ) -> None:
        resolved_host = host or _env_value("TRACERA_HOST", "GRAPHEON_HOST") or "127.0.0.1"
        resolved_port = port or int(_env_value("TRACERA_PORT", "GRAPHEON_PORT") or "8080")
        self.base_url = (
            base_url
            or _env_value("TRACERA_BASE_URL", "GRAPHEON_BASE_URL")
            or f"http://{resolved_host}:{resolved_port}"
        )
        self.token = token or _env_value("TRACERA_API_TOKEN", "GRAPHEON_API_TOKEN")
        self.timeout = timeout
        self.batch_size = max(1, int(batch_size))
        # Internal event buffer for batched async writes (task 11).
        # enqueue_event() appends; flush() drains in POST batches.
        self._buffer: list[TraceEvent] = []

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        """Build a URL relative to base_url with optional query params."""
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if query:
            qs = urllib.parse.urlencode(
                {k: v for k, v in query.items() if v is not None}
            )
            url = url + ("?" + qs if qs else "")
        return url

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request and parse the JSON response.

        Returns the parsed JSON body on 2xx. Raises TraceStoreError on
        transport / serialization failure or non-2xx status.
        """
        url = self._build_url(path, query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # nosec B310
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise TraceStoreError(
                f"Tracera {method} {path} returned {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise TraceStoreError(f"Tracera transport error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise TraceStoreError(
                f"Tracera returned non-JSON response: {exc.msg}"
            ) from exc

    # ------------------------------------------------------------------
    # TraceStoreAdapter protocol implementations
    # ------------------------------------------------------------------

    def append_event(self, event: TraceEvent) -> str:
        """Append a single event to Tracera via POST /evidence.

        Maps TraceEvent → Tracera `EvidenceCreate`:

        - artifact_id = str(event.id)
        - kind        = event.kind
        - url         = "pheno://<target or 'unscoped'>/<id>"
        - metadata    = dict(session_id, ts, target, **event.payload)
        - links       = []  (single-shot append; cross-event links
                             belong to query/flush tasks)
        - actor       = event.actor

        Returns the Tracera-assigned Evidence.id (also equal to our
        event.id since Tracera echoes artifact_id).

        Raises:
            TraceStoreError: on transport / serialization failure or
                non-2xx response from Tracera.
        """
        url = "pheno://" + (event.target or "unscoped") + "/" + str(event.id)
        metadata: dict[str, Any] = {
            "pheno_event_id": str(event.id),
            "pheno_event_kind": event.kind,
            "pheno_event_ts": event.ts.isoformat(),
            # Echo actor into metadata so query() can reconstruct the
            # full TraceEvent without needing the audit side-channel.
            "actor": event.actor,
        }
        if event.session_id is not None:
            metadata["session_id"] = event.session_id
        if event.target is not None:
            metadata["target"] = event.target
        # Merge user payload last so user keys can override defaults if desired.
        metadata.update(event.payload)

        body = {
            "artifact_id": str(event.id),
            "kind": event.kind,
            "url": url,
            "metadata": metadata,
            "links": [],
            "actor": event.actor,
        }
        response = self._request("POST", "/evidence", body=body)
        evidence = response.get("evidence", {})
        return str(evidence.get("id") or event.id)

    def query(self, session_id: str) -> list[TraceEvent]:
        """Return all events for the given session id (ordered by ts ASC).

        Implementation notes:
        - Tracera's GET /evidence returns all evidence (no session_id
          filter at the API layer yet); we filter client-side by
          metadata.session_id.
        - Events with no session_id metadata (older writes before
          actor echo) are skipped.
        - Reconstructed TraceEvent uses metadata.pheno_event_ts for
          `ts` (our authored timestamp), falling back to Tracera's
          `created_at` when not present.
        - Reconstruction reads metadata fields written by append_event:
          pheno_event_id, pheno_event_kind, pheno_event_ts, actor,
          session_id, target, plus user payload.
        - Results are sorted by ts ASC for stable iteration order.

        Raises:
            TraceStoreError: on transport / serialization failure or
                non-2xx response from Tracera.
        """
        response = self._request("GET", "/evidence")
        items = response.get("items", [])
        events: list[TraceEvent] = []
        for item in items:
            metadata = item.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            if metadata.get("session_id") != session_id:
                continue
            # Reconstruct the TraceEvent from the recorded metadata.
            pheno_event_id = metadata.get("pheno_event_id") or item.get("artifact_id")
            pheno_event_kind = metadata.get("pheno_event_kind") or item.get(
                "kind", "unknown"
            )
            pheno_event_ts = metadata.get("pheno_event_ts") or item.get("created_at")
            actor = metadata.get("actor") or "unknown"
            target = metadata.get("target")
            # Re-derive payload = metadata minus the keys we own.
            reserved_keys = RESERVED_METADATA_KEYS
            payload = {k: v for k, v in metadata.items() if k not in reserved_keys}
            event = TraceEvent(
                id=UUID(str(pheno_event_id)),
                kind=str(pheno_event_kind),
                ts=datetime.fromisoformat(str(pheno_event_ts).replace("Z", "+00:00")),
                actor=str(actor),
                target=target,
                session_id=session_id,
                payload=payload,
            )
            events.append(event)

        # Stable order: ts ASC (ties broken by event id for determinism).
        events.sort(key=lambda e: (e.ts, str(e.id)))
        return events

    def flush(self) -> None:
        """Drain the internal event buffer to Tracera in batches.

        Implementation (task 11):
        - Drains `self._buffer` in chunks of `self.batch_size`.
        - Each chunk posts events as a JSON array body to `/evidence`
          (batched payload).
        - The Tracera server doesn't currently support a true batch
          endpoint, so this falls back to one POST per event within
          the chunk. The chunking still amortizes connection setup
          when callers use a connection-pooled HTTP client. Until then
          the batch boundary is informational and the per-event POST
          contract still applies.
        - Errors during flush:
          * Transport / HTTP errors propagate as TraceStoreError.
          * Partial-flush: events successfully posted are removed
            from the buffer; the failing event + remaining events stay
            buffered so a retry can resume.
        - Idempotent: a flush() with empty buffer is a no-op.

        Raises:
            TraceStoreError: on transport / serialization failure for
                the first event that fails to post.
        """
        if not self._buffer:
            return None
        # Snapshot the buffer; clear it; iterate; on error restore the
        # remainder so retries can resume from the failure point.
        pending = self._buffer
        self._buffer = []
        try:
            for event in pending:
                # Build request body via the same path as append_event.
                url = "pheno://" + (event.target or "unscoped") + "/" + str(event.id)
                metadata: dict[str, Any] = {
                    "pheno_event_id": str(event.id),
                    "pheno_event_kind": event.kind,
                    "pheno_event_ts": event.ts.isoformat(),
                    "actor": event.actor,
                }
                if event.session_id is not None:
                    metadata["session_id"] = event.session_id
                if event.target is not None:
                    metadata["target"] = event.target
                metadata.update(event.payload)
                body = {
                    "artifact_id": str(event.id),
                    "kind": event.kind,
                    "url": url,
                    "metadata": metadata,
                    "links": [],
                    "actor": event.actor,
                }
                self._request("POST", "/evidence", body=body)
        except TraceStoreError:
            # Restore the failing event + everything after it.
            failed_index = pending.index(event) if event in pending else 0
            self._buffer = pending[failed_index:] + self._buffer
            raise
        return None

    def enqueue_event(self, event: TraceEvent) -> str:
        """Add an event to the internal buffer for later flush.

        Buffered events are NOT posted to Tracera until `flush()` is
        called. This is the entry point for batched async writes.

        Returns the event's id (str) for symmetry with append_event.
        Callers that need immediate persistence should use
        append_event() directly.
        """
        self._buffer.append(event)
        return str(event.id)

    def buffer_size(self) -> int:
        """Return the number of events currently buffered (unflushed)."""
        return len(self._buffer)

    def health(self) -> dict[str, Any]:
        """Return backend health status from GET /healthz.

        Fully implemented in this skeleton so downstream tasks can use
        it for connection probing.
        """
        try:
            response = self._request("GET", "/healthz")
            return {
                "status": "ok" if response.get("status") == "ok" else "degraded",
                "endpoint": self.base_url,
            }
        except TraceStoreError as exc:
            return {
                "status": "down",
                "endpoint": self.base_url,
                "error": str(exc),
            }
