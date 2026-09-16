"""EnergyPort — abstract interface for energy measurement.

Concrete sources (powermetrics, nvidia-smi, no-op stub) implement this port
so the executor can swap measurement backends without coupling to any
specific OS-level tool.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EnergyPort(ABC):
    """Port for energy measurement."""

    @abstractmethod
    def start(self) -> None:
        """Begin polling.  Idempotent; safe to call once per task."""
        ...

    @abstractmethod
    def stop(self) -> Any:
        """Halt polling and return the aggregated total."""
        ...

    @abstractmethod
    def reading(self) -> Any:
        """Return the current instantaneous energy reading."""
        ...
