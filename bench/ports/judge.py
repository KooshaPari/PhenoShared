"""JudgePort — abstract interface for LLM-as-judge evaluation.

The judge runner and domain services depend on this port so different
judge backends (Anthropic, OpenAI, deterministic) can be swapped without
changing orchestration logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class JudgePort(ABC):
    """Port for LLM-as-judge evaluation."""

    @abstractmethod
    async def evaluate(self, task: Any, response: str, expected: str) -> float:
        """Evaluate a single task response and return a score in [0, 1]."""
        ...
