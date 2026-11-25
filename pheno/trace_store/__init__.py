"""trace_store — persistent trace repository adapters for pheno.

Adapters in this package mirror `traces/` events to external trace
repositories:

- `tracera.TraceraAdapter` — Grapheon/Tracera persistent trace repository
  (HTTP API, see `docs/integrations/tracera-api.md`).

Future adapters may target other backends (e.g., a future local SQLite
adapter or a S3-backed archive). All adapters implement the
`TraceStoreAdapter` protocol defined in `protocols.py`.
"""

from __future__ import annotations

__all__ = ["TraceraAdapter", "TraceEvent", "TraceStoreAdapter", "TraceStoreError"]

from .protocols import TraceEvent, TraceStoreAdapter, TraceStoreError
from .tracera import TraceraAdapter
