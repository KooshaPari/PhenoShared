"""cr_router: provider rotation + rate-limit fallback router (SP2).

Public API:
    Router, QuotaStore, ProviderQueue, RouterError, QuotaExhaustedError

The router decides which code-review provider to use next, taking into account
the daily quota recorded in a file-backed QuotaStore. It does NOT make any HTTP
calls — that is deferred to SP3 (triage) and SP4 (forge).

See docs/superpowers/specs/2026-09-09-automated-code-review-workflow-orchestration-design.md
section 3 SP2 and section 6 decisions D2/D3/D4.
"""
from __future__ import annotations

from cr_router.quota_store import QuotaExhaustedError, QuotaStore
from cr_router.router import Router, RouterError
from cr_router.provider_queue import ProviderQueue

__all__ = [
    "ProviderQueue",
    "QuotaExhaustedError",
    "QuotaStore",
    "Router",
    "RouterError",
]
