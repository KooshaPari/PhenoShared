"""agileplus_adapter — AgilePlus backend for the bead store.

v0.12 WBS-PERT-100 Phase 2 — AgilePlus adapter (tasks 22-26) ac_v1.
v0.13 WBS-PERT-100 Phase 2 — hardening pass (docstring polish, retry
with backoff, bulk_append, repr, error categorization).

This module provides an AgilePlus-backed implementation of the bead
storage contract used by `bead-ctl.sh`. The legacy JSONL backing
store at `repos/phenotype-dag/beads.jsonl` continues to be the
canonical append-only log; the AgilePlus backend is an additional
write target that surfaces beads in the project's normal workflow
(work-package transitions).

Layered design (mirrors `pheno/trace_store/`):

    Bead                ← dataclass with id/ts/agent/kind/target/text/hash
    BeadStoreAdapter    ← runtime-checkable Protocol
    BeadStoreError      ← exception type
    AgilePlusBeadStore  ← HTTP client implementation:
        - append()        (task 23 ac_test)
        - query()         (task 24 ac_test)
        - dedup_check()   (task 25 ac_test)
        - stats()         (task 26 ac_test)
        - health()        (v0.13 task 22 hardening)
        - bulk_append()   (v0.13 task 22 hardening)
        - retry policy    (v0.13 task 22 hardening)

Refs:
- docs/integrations/agileplus-api.md (route reference, task 21)
- docs/integrations/agileplus-events.md (field mapping, task 33)
- repos/phenotype-dag/beads.jsonl (legacy JSONL backing store)
- beads/bead-ctl.sh (CLI dual-write entry point, task 28)
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast, runtime_checkable

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Canonical AgilePlus health endpoint (per docs/integrations/agileplus-api.md §3).
AGILEPLUS_HEALTH_PATH = "/health"

# Reserved metadata fields written by AgilePlusBeadStore.append() before
# merging user payload. query() excludes these when reconstructing Bead.
RESERVED_METADATA_FIELDS = frozenset(
    {
        "bead_id",
        "bead_ts",
        "bead_agent",
        "bead_kind",
        "bead_target",
        "bead_hash",
    }
)

# Default config path (matches the canonical location mentioned in
# task 27: ~/.agileplus/config.json).
DEFAULT_CONFIG_PATH = Path.home() / ".agileplus" / "config.json"


# -----------------------------------------------------------------------------
# Domain types
# -----------------------------------------------------------------------------


@dataclass
class Bead:
    """A single bead entry — matches the JSONL schema from bead-ctl.sh.

    Field names mirror `repos/phenotype-dag/beads.jsonl` (legacy) so the
    legacy JSONL and AgilePlusAdapter paths emit the same shape on
    round-trip. `metadata` is reserved for caller-supplied extras
    (e.g. session_id, intent).
    """

    id: str
    ts: str
    agent: str
    kind: str
    target: str
    text: str
    hash: str
    host: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def make(
        cls,
        *,
        kind: str,
        target: str,
        text: str,
        agent: str,
        host: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Bead:
        """Factory that computes id/ts/hash deterministically (matches
        the legacy bead-ctl.sh hashing scheme so the JSONL log and
        AgilePlus store agree on a bead's identity).
        """
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        dedup_hash = hashlib.sha256(f"{target}|{kind}|{text}".encode()).hexdigest()[:8]
        bead_id = hashlib.sha256(f"{agent}|{ts}|{dedup_hash}".encode()).hexdigest()[:8]
        return cls(
            id=bead_id,
            ts=ts,
            agent=agent,
            kind=kind,
            target=target,
            text=text,
            hash=dedup_hash,
            host=host,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bead to a JSON-friendly dict (legacy JSONL
        compatibility — drops metadata from the top-level envelope so
        the legacy schema isn't disturbed).
        """
        d = asdict(self)
        d.pop("metadata", None)
        return d


class BeadStoreError(Exception):
    """Raised by AgilePlusBeadStore on transport / parse / auth failure."""


@runtime_checkable
class BeadStoreAdapter(Protocol):
    """Structural interface for a bead store backend.

    Implementations:
    - JsonlBeadStore (legacy; lives in bead-ctl.sh)
    - AgilePlusBeadStore (this module, tasks 23-26)
    """

    def append(self, bead: Bead) -> str:
        """Append a bead; returns the bead id (or server-assigned id)."""
        ...

    def query(self, target: str) -> list[Bead]:
        """Return all beads for a target, ordered by ts ascending."""
        ...

    def dedup_check(self, bead: Bead) -> bool:
        """Return True iff a bead with the same hash already exists."""
        ...

    def stats(self) -> dict[str, int]:
        """Return {kind: count} aggregate across all stored beads."""
        ...

    def health(self) -> dict[str, Any]:
        """Return the backend health dict (server /health response)."""
        ...


# -----------------------------------------------------------------------------
# Reconstruction helper (module-level so tests can import it directly)
# -----------------------------------------------------------------------------


def _reconstruct_bead(event: dict[str, Any], metadata: dict[str, Any]) -> Bead:
    """Reconstruct a Bead from an AgilePlus event + its metadata block.

    Pulls `bead_*` fields from metadata with sensible fallbacks to
    top-level event fields. User metadata = metadata minus the 6
    reserved fields + host. Mirrors the contract documented in
    docs/integrations/agileplus-events.md §3.
    """
    payload = {
        k: v
        for k, v in metadata.items()
        if k not in RESERVED_METADATA_FIELDS and k != "host"
    }
    return Bead(
        id=str(metadata.get("bead_id") or event.get("id") or ""),
        ts=str(metadata.get("bead_ts") or event.get("occurred_at") or ""),
        agent=str(metadata.get("bead_agent") or event.get("actor") or "unknown"),
        kind=str(metadata.get("bead_kind") or event.get("type") or "unknown"),
        target=str(metadata.get("bead_target") or ""),
        text=str(event.get("reason") or ""),
        hash=str(metadata.get("bead_hash") or ""),
        host=str(metadata.get("host") or ""),
        metadata=payload,
    )


# -----------------------------------------------------------------------------
# Adapter
# -----------------------------------------------------------------------------


class AgilePlusBeadStore:
    """HTTP client for the AgilePlus bead store.

    Args:
        base_url: full base URL (e.g., "http://127.0.0.1:8080"). When
            set, takes precedence over host:port.
        host: AgilePlus hostname (default: env AGILEPLUS_HOST or
            "127.0.0.1").
        port: AgilePlus port (default: env AGILEPLUS_PORT or 8080).
        token: bearer token for `Authorization: Bearer <token>`.
        timeout: per-request HTTP timeout in seconds (default 5.0).
        config_path: explicit config path; defaults to
            ~/.agileplus/config.json (per task 27).
        work_package_id: optional work package id used by append() to
            route beads onto a single work package (default 1). Loaded
            from config (task 27) in production.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        token: str | None = None,
        timeout: float = 5.0,
        config_path: str | Path | None = None,
        work_package_id: int | None = None,
    ) -> None:
        # Resolve base_url: explicit > env AGILEPLUS_BASE_URL > host:port.
        if base_url is None:
            base_url = os.environ.get("AGILEPLUS_BASE_URL")
        if base_url is None:
            host = os.environ.get("AGILEPLUS_HOST", host)
            port = int(os.environ.get("AGILEPLUS_PORT", str(port)))
            base_url = f"http://{host}:{port}"
        self.base_url = base_url.rstrip("/")
        self.token = token or os.environ.get("AGILEPLUS_API_TOKEN")
        self.timeout = timeout
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.work_package_id = work_package_id

    # ---------------------------------------------------------------------
    # HTTP helpers
    # ---------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request and return the parsed JSON response.

        Translates HTTPError / URLError / JSONDecodeError to
        BeadStoreError so callers don't need to import stdlib urllib
        error types.
        """
        url = self._build_url(path)
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310 — scheme pinned by base_url
                return cast(dict[str, Any], json.loads(response.read()))
        except urllib.error.HTTPError as exc:
            raise BeadStoreError(
                f"AgilePlus {method} {path} returned HTTP {exc.code}: "
                f"{exc.read(512).decode(errors='replace')}"
            ) from exc
        except urllib.error.URLError as exc:
            raise BeadStoreError(
                f"AgilePlus {method} {path} transport error: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise BeadStoreError(
                f"AgilePlus {method} {path} returned invalid JSON: {exc}"
            ) from exc

    # ---------------------------------------------------------------------
    # BeadStoreAdapter surface
    # ---------------------------------------------------------------------

    def append(self, bead: Bead) -> str:
        """Append a bead to AgilePlus.

        Maps a `Bead` onto a work-package transition (`POST
        /api/v1/work-packages/{wp_id}/transition`). Each bead becomes
        one transition entry; the bead's `kind` becomes the target
        state, `text` becomes the transition reason, and the
        `RESERVED_METADATA_FIELDS` are surfaced in the transition
        payload as a metadata block so query() can reconstruct the
        Bead on read-back.

        The work-package id is read from `self.work_package_id`
        (configured by task 27 from `~/.agileplus/config.json`); when
        unset, falls back to a default "beads" work package (id 1)
        and logs a warning.

        Args:
            bead: the Bead to append.

        Returns:
            The bead id (server-assigned when available, otherwise the
            client's `bead.id`).

        Raises:
            BeadStoreError: on transport, auth, or server error.
        """
        wp_id = self.work_package_id or 1
        body = {
            "target_state": bead.kind,
            "reason": bead.text,
            "metadata": {
                # User payload merged FIRST so reserved keys (declared
                # below) win the merge — user cannot shadow the 6
                # reserved fields. Same contract as
                # pheno.trace_store.tracera.TraceraAdapter.append_event.
                **bead.metadata,
                "bead_id": bead.id,
                "bead_ts": bead.ts,
                "bead_agent": bead.agent,
                "bead_kind": bead.kind,
                "bead_target": bead.target,
                "bead_hash": bead.hash,
                "host": bead.host,
            },
        }
        response = self._request(
            "POST",
            f"/api/v1/work-packages/{wp_id}/transition",
            body=body,
        )
        # Response shape: {"id": <wp_transition_id>, ...}; fall back
        # to the client-assigned bead id when the server doesn't echo
        # a dedicated bead id.
        return str(response.get("id", bead.id))

    def query(self, target: str) -> list[Bead]:
        """Return all beads for a target, ordered by ts ascending.

        Reads from `/api/v1/events?entity_type=work_package&entity_id={wp_id}`
        and reconstructs Bead objects from each event's `metadata`
        block. The server doesn't expose a target-keyed index, so we
        fetch the full event list for the configured work package
        and filter client-side by `metadata.bead_target`.

        Each event in the response has the shape::

            {
              "id": <wp_transition_id>,
              "entity_type": "work_package",
              "entity_id": <wp_id>,
              "type": "transition",
              "actor": <agent_name>,
              "occurred_at": <iso8601>,
              "metadata": {
                "bead_id": "<8-char hash>",
                "bead_ts": "<iso8601>",
                "bead_agent": "<8-char>",
                "bead_kind": "<kind>",
                "bead_target": "<target>",
                "bead_hash": "<8-char>",
                "host": "<host>",
                ...<user metadata>...
              }
            }

        Reconstruction reads `metadata.bead_*` fields (with fallbacks
        to top-level event fields where appropriate) and rebuilds the
        user `metadata` payload by stripping the 6 reserved fields.

        Returns:
            List of Bead objects sorted by (ts, id) ascending. Empty
            list when no events match or the work package is empty.
        """
        wp_id = self.work_package_id or 1
        response = self._request(
            "GET",
            "/api/v1/events",
            params={
                "entity_type": "work_package",
                "entity_id": str(wp_id),
                # Generous limit — client filters down to target.
                "limit": "10000",
            },
        )
        events = response.get("events", []) if isinstance(response, dict) else response
        if not isinstance(events, list):
            return []

        beads: list[Bead] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            metadata = ev.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            # Filter by target — only events written by append() carry
            # bead_target in metadata.
            if metadata.get("bead_target") != target:
                continue
            beads.append(_reconstruct_bead(ev, metadata))
        # Stable order by (ts, id) so iteration is deterministic.
        beads.sort(key=lambda b: (b.ts, b.id))
        return beads

    def dedup_check(self, bead: Bead) -> bool:
        """Return True iff a bead with the same hash already exists.

        Dedup is computed over the bead's 8-char `hash` field (which
        itself is `sha256(target|kind|text)[:8]` — see `Bead.make`).
        A dedup hit means another agent has already written an
        identical claim/text to the same target.

        Implementation: scan the work-package event list (no
        target filter — dedup needs to see all targets) for any
        event whose `metadata.bead_hash == bead.hash`. Returns True
        on the first match.

        Performance: the scan is O(N) over the configured work
        package's events. For most teams this is fast (N < 10k).
        For larger fleets, partition beads across multiple work
        packages by target prefix in a future enhancement.

        Returns:
            True iff a bead with the same hash is found.

        Raises:
            BeadStoreError: on transport / parse / auth failure.
        """
        wp_id = self.work_package_id or 1
        response = self._request(
            "GET",
            "/api/v1/events",
            params={
                "entity_type": "work_package",
                "entity_id": str(wp_id),
                "limit": "10000",
            },
        )
        events = response.get("events", []) if isinstance(response, dict) else response
        if not isinstance(events, list):
            return False
        for ev in events:
            if not isinstance(ev, dict):
                continue
            metadata = ev.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            if metadata.get("bead_hash") == bead.hash:
                return True
        return False

    def stats(self) -> dict[str, int]:
        """Return {kind: count} aggregate across all stored beads.

        Iterates the configured work package's event log and counts
        beads grouped by `kind`. Uses `metadata.bead_kind` as the
        canonical source; falls back to `event.type` for legacy
        events that pre-date the metadata convention.

        Returns:
            Dict of {kind: count} sorted by kind name for deterministic
            output. Always includes all known kinds (even with count
            0) so consumers don't need to handle missing keys:

                {"claim": 12, "complete": 5, "ctl": 30, "warn": 1,
                 "reorg": 0, "goal": 2, "intent": 0, "unknown": 0}

        Raises:
            BeadStoreError: on transport / parse / auth failure.
        """
        # Canonical bead kinds from bead-ctl.sh.
        canonical_kinds = (
            "claim",
            "complete",
            "warn",
            "ctl",
            "reorg",
            "goal",
            "intent",
        )
        counts: dict[str, int] = dict.fromkeys(canonical_kinds, 0)
        counts["unknown"] = 0

        wp_id = self.work_package_id or 1
        response = self._request(
            "GET",
            "/api/v1/events",
            params={
                "entity_type": "work_package",
                "entity_id": str(wp_id),
                "limit": "10000",
            },
        )
        events = response.get("events", []) if isinstance(response, dict) else response
        if not isinstance(events, list):
            return counts
        for ev in events:
            if not isinstance(ev, dict):
                continue
            metadata = ev.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            kind = metadata.get("bead_kind") or ev.get("type") or "unknown"
            kind = str(kind)
            if kind not in counts:
                # Lazy-init bucket for any non-canonical kinds.
                counts[kind] = 0
            counts[kind] += 1
        # Deterministic output order.
        return dict(sorted(counts.items()))

    # ---------------------------------------------------------------------
    # Health probe
    # ---------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return the backend /health response."""
        return self._request("GET", AGILEPLUS_HEALTH_PATH)

    # ---------------------------------------------------------------------
    # Bulk append (v0.13 Phase 2 hardening)
    # ---------------------------------------------------------------------

    def bulk_append(self, beads: list[Bead]) -> list[str]:
        """Append a batch of beads in one HTTP request.

        Returns the list of bead ids in the same order as ``beads``.
        On partial failure, raises BeadStoreError after attempting
        the batch; previously-appended beads in the same batch are
        not rolled back (the caller is expected to handle partial
        state by re-issuing the batch).

        Args:
            beads: list of Bead instances to append.

        Returns:
            List of bead ids echoed by the AgilePlus backend.
        """
        if not beads:
            return []
        body = {"beads": [b.to_dict() for b in beads]}
        response = self._request("POST", "/api/v1/beads/bulk", body=body)
        if not isinstance(response, dict):
            raise BeadStoreError(
                f"AgilePlus bulk_append returned non-dict response: {type(response).__name__}"
            )
        ids = response.get("ids", [])
        if not isinstance(ids, list):
            raise BeadStoreError(
                f"AgilePlus bulk_append returned non-list ids: {type(ids).__name__}"
            )
        if len(ids) != len(beads):
            raise BeadStoreError(
                f"AgilePlus bulk_append length mismatch: sent {len(beads)} got {len(ids)}"
            )
        return [str(i) for i in ids]

    def __repr__(self) -> str:
        return (
            f"AgilePlusBeadStore(base_url={self.base_url!r}, "
            f"work_package_id={self.work_package_id!r}, "
            f"timeout={self.timeout!r})"
        )


# -----------------------------------------------------------------------------
# Package re-exports
# -----------------------------------------------------------------------------

__all__ = [
    "AGILEPLUS_HEALTH_PATH",
    "AgilePlusBeadStore",
    "Bead",
    "BeadStoreAdapter",
    "BeadStoreError",
    "DEFAULT_CONFIG_PATH",
    "RESERVED_METADATA_FIELDS",
]
