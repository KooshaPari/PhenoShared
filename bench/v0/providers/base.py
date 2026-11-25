"""Protocol-style provider interfaces for V0 benchmark execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol


class StreamingProvider(Protocol):
    """Protocol for a streaming chat-completion backend."""

    def stream_chat(
        self,
        base_url: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        timeout_s: float,
        api_key: str | None = None,
    ) -> Mapping[str, Any]:
        """Stream chat completions; returns a Mapping (typically a generator wrapper)."""
        ...


class SweepProvider(Protocol):
    """Protocol for a multi-level sweep runner."""

    def run_sweep(
        self,
        caller: Callable[[dict[str, Any]], dict[str, Any]],
        tasks: list[dict[str, Any]],
        levels: list[int],
        warmup: int = 0,
    ) -> Mapping[str, Any]:
        """Run a sweep over tasks at the given levels; returns aggregated metrics."""
        ...


class HeterogeneousProvider(Protocol):
    """Protocol for a heterogeneous worker pool runner."""

    def run_heterogeneous(
        self,
        workers: list[dict[str, str]],
        tasks: list[dict[str, Any]],
        concurrency: int,
        caller: Callable[[dict[str, str], dict[str, Any]], dict[str, Any]],
    ) -> Mapping[str, Any]:
        """Run tasks across heterogeneous workers with bounded concurrency."""
        ...


class ResourceProvider(Protocol):
    """Protocol for a GPU / resource sampler."""

    def sample_gpu_summary(
        self,
        *,
        include_gpu: bool = True,
        interval: float = 0.5,
    ) -> Mapping[str, Any]:
        """Sample GPU summary stats at the given interval."""
        ...


__all__ = [
    "HeterogeneousProvider",
    "ResourceProvider",
    "StreamingProvider",
    "SweepProvider",
]
