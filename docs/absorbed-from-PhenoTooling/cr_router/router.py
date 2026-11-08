"""Router: composes ProviderQueue + QuotaStore to answer "who's next?".

Public API:
    Router.pick()     → returns the next provider, rotating on quota exhaustion
    Router.status()   → returns a structured summary of all providers' state
    Router.dry_run    → bool toggle; when True, pick() does NOT record consumption

The router does NOT make HTTP calls. It only decides which provider *would*
be called next. Real provider invocation lands in SP3 / SP4.
"""
from __future__ import annotations

from typing import Any

from cr_router.provider_queue import ProviderQueue
from cr_router.quota_store import QuotaStore


class RouterError(Exception):
    """Raised for router-level misuse (e.g. no providers configured)."""


class Router:
    """Composes a ProviderQueue with a QuotaStore to drive rotation."""

    def __init__(
        self,
        providers: list[dict[str, Any]] | None = None,
        quota_store: QuotaStore | None = None,
        state_root: Any = None,
        dry_run: bool = False,
    ) -> None:
        self.queue = ProviderQueue(providers=providers)
        if quota_store is not None:
            self.quota_store = quota_store
        elif state_root is not None:
            self.quota_store = QuotaStore(state_root=state_root)
        else:
            raise RouterError("Router requires either quota_store or state_root")
        self.dry_run = dry_run

    def pick(self) -> dict[str, Any] | None:
        """Return the next provider, rotating past exhausted ones.

        Returns None if every provider is exhausted.
        In dry-run mode, picks without recording consumption.
        """
        exhausted: set[str] = set()
        while True:
            candidate = self.queue.next(exhausted=exhausted)
            if candidate is None:
                return None
            limit = candidate.get("quota_per_day")
            remaining = self.quota_store.remaining(candidate["id"], limit)
            if remaining <= 0:
                exhausted.add(candidate["id"])
                continue
            if not self.dry_run:
                self.quota_store.consume(candidate["id"], limit)
            return candidate

    def status(self) -> dict[str, Any]:
        """Return a structured summary of every provider's current state."""
        providers_status = []
        for p in self.queue.iter():
            limit = p.get("quota_per_day")
            used = self.quota_store.usage(p["id"])
            remaining = self.quota_store.remaining(p["id"], limit)
            providers_status.append({
                "id": p["id"],
                "name": p.get("name", p["id"]),
                "priority": p.get("priority"),
                "limit": limit,
                "used": used,
                "remaining": remaining if remaining != float("inf") else None,
                "exhausted": (remaining == 0) if limit is not None else False,
            })
        return {"providers": providers_status, "dry_run": self.dry_run}
