from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class CostCard:
    repo: str
    ci_minutes: float
    llm_tokens_usd: float
    storage_gb: float
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    contributors: tuple[str, ...] = ()


__all__ = ["CostCard"]
