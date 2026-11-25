"""Energy result schema for energy-aware benchmarking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EnergyResult:
    """Single-task energy measurement result."""

    model: str
    backend: str
    suite: str
    task_id: str
    latency_ms: float
    tokens_per_sec: float
    energy_mj: float
    energy_per_token_mj: float
    peak_rss_mb: float
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the EnergyResult to a plain dict (uses asdict)."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize the EnergyResult to a pretty JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EnergyResult:
        """Reconstruct an EnergyResult from a dict, ignoring unknown keys."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
