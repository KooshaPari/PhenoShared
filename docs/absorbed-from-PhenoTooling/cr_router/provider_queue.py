"""ProviderQueue: wraps cr_roster.load_providers() and answers "who's next?".

Decoupled from QuotaStore on purpose — the queue only knows about ordering
and the exhausted-set filter. The Router composes the two.
"""
from __future__ import annotations

from typing import Any, Iterable

from cr_roster import load_providers


class ProviderQueue:
    """An ordered, iterable wrapper around the SP1 provider catalog."""

    def __init__(self, providers: list[dict[str, Any]] | None = None) -> None:
        if providers is None:
            providers = load_providers(validate_schema=True)
        self._providers = list(providers)

    def iter(self) -> Iterable[dict[str, Any]]:
        """Yield providers in D3 priority order (1 = highest)."""
        return iter(self._providers)

    def next(self, exhausted: set[str] | None = None) -> dict[str, Any] | None:
        """Return the first provider whose id is not in ``exhausted``.

        Returns None if every provider is exhausted.
        """
        exhausted = exhausted or set()
        for p in self._providers:
            if p["id"] not in exhausted:
                return p
        return None

    def all_ids(self) -> list[str]:
        """Convenience: list every provider id in priority order."""
        return [p["id"] for p in self._providers]
