"""agileplus_adapter — AgilePlus backend for the bead store.

v0.12 WBS-PERT-100 task 22 (Phase 2 — AgilePlus adapter) ac_v1.

This module provides an AgilePlus-backed implementation of the bead
storage contract used by `bead-ctl.sh`. The legacy JSONL backing
store at `repos/phenotype-dag/beads.jsonl` continues to be the
canonical append-only log; the AgilePlus backend is an additional
write target that surfaces beads in the project's normal workflow
(cycles, work packages, governance audit).

Layered design (mirrors `pheno/trace_store/`):

    Bead                ← dataclass with id/ts/agent/kind/target/text/hash
    BeadStoreAdapter    ← runtime-checkable Protocol
    BeadStoreError      ← exception type
    AgilePlusBeadStore  ← HTTP client implementation (tasks 23-26 fill out
                           append/query/dedup/stats; this scaffold is the
                           skeleton with constructor + health probe).

Configuration (task 27):
    ~/.agileplus/config.json  ← host, port, base_url, api_token_env,
                                 timeout, project_slug, work_package_id,
                                 enabled (master switch).

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
from typing import Any, Protocol, runtime_checkable

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
# Adapter skeleton
# -----------------------------------------------------------------------------


class AgilePlusBeadStore:
    """HTTP client for the AgilePlus bead store.

    Skeleton (task 22 ac_v1). Tasks 23-26 fill out append/query/
    dedup_check/stats. Task 27 introduces config-file loading. Task
    28 wires this into bead-ctl.sh's dual-write path.

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
    ) -> None:
        # Resolve base_url: explicit > env TRACERA_BASE_URL-style env > host:port.
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
                return json.loads(response.read())
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
    # BeadStoreAdapter surface (tasks 23-26 implement these)
    # ---------------------------------------------------------------------

    def append(self, bead: Bead) -> str:
        """Append a bead to AgilePlus.

        Filled out by task 23 ac_test. Maps `Bead` to the
        `/api/v1/...` POST handler that surfaces beads as feature
        audit events + work-package updates.
        """
        raise NotImplementedError("AgilePlusBeadStore.append: task 23")

    def query(self, target: str) -> list[Bead]:
        """Return all beads for a target, ordered by ts ascending.

        Filled out by task 24 ac_test. Reads from the
        `/api/v1/events?target=...` endpoint and reconstructs Bead
        objects from the response.
        """
        raise NotImplementedError("AgilePlusBeadStore.query: task 24")

    def dedup_check(self, bead: Bead) -> bool:
        """Return True iff a bead with the same hash already exists.

        Filled out by task 25 ac_test. Checks via the audit-log
        verify endpoint.
        """
        raise NotImplementedError("AgilePlusBeadStore.dedup_check: task 25")

    def stats(self) -> dict[str, int]:
        """Return {kind: count} aggregate across all stored beads.

        Filled out by task 26 ac_test.
        """
        raise NotImplementedError("AgilePlusBeadStore.stats: task 26")

    # ---------------------------------------------------------------------
    # Health probe
    # ---------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return the backend /health response (default for skeleton)."""
        return self._request("GET", AGILEPLUS_HEALTH_PATH)


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
