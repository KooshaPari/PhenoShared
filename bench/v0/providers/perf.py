"""Default providers delegating to ``perf`` implementations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from perf.heterogeneous import run_heterogeneous
from perf.resources import ResourceSampler
from perf.streaming import stream_chat
from perf.sweep import run_sweep


class DefaultStreamingProvider:
    """Concrete ``StreamingProvider`` that delegates to ``perf.streaming.stream_chat``."""

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
        """Stream chat completions via the perf.streaming backend."""
        return cast(Mapping[str, Any], stream_chat(
            base_url,
            model,
            prompt,
            max_tokens,
            temperature,
            timeout_s,
            api_key=api_key,
        ))


class DefaultSweepProvider:
    """Concrete ``SweepProvider`` that delegates to ``perf.sweep.run_sweep``."""

    def run_sweep(
        self,
        caller: Callable[[dict[str, Any]], dict[str, Any]],
        tasks: list[dict[str, Any]],
        levels: list[int],
        warmup: int = 0,
    ) -> Mapping[str, Any]:
        """Run a multi-level sweep via the perf.sweep backend."""
        return cast(Mapping[str, Any], run_sweep(caller, tasks, levels, warmup=warmup))


class DefaultHeterogeneousProvider:
    """Concrete ``HeterogeneousProvider`` that delegates to ``perf.heterogeneous``."""

    def run_heterogeneous(
        self,
        workers: list[dict[str, str]],
        tasks: list[dict[str, Any]],
        concurrency: int,
        caller: Callable[[dict[str, str], dict[str, Any]], dict[str, Any]],
    ) -> Mapping[str, Any]:
        """Run heterogeneous workers via perf.heterogeneous."""
        return cast(Mapping[str, Any], run_heterogeneous(workers, tasks, concurrency, caller))


class DefaultResourceProvider:
    """Concrete ``ResourceProvider`` that samples GPU stats via ``perf.resources``."""

    def sample_gpu_summary(
        self,
        *,
        include_gpu: bool = True,
        interval: float = 0.5,
    ) -> Mapping[str, Any]:
        """Sample a single GPU summary at the given interval."""
        sampler = ResourceSampler(interval=interval, include_gpu=include_gpu)
        sampler.start()
        sampler.collect()
        return sampler.stop(timeout=interval * 2)


__all__ = [
    "DefaultHeterogeneousProvider",
    "DefaultResourceProvider",
    "DefaultStreamingProvider",
    "DefaultSweepProvider",
]
