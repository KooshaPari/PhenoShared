"""Repository-root compatibility package for the installable harness."""

from importlib import import_module
from pathlib import Path
from typing import Any


_SOURCE_PACKAGE = Path(__file__).resolve().parent / "src" / "harness"
if _SOURCE_PACKAGE.is_dir() and str(_SOURCE_PACKAGE) not in __path__:
    __path__.append(str(_SOURCE_PACKAGE))


_LAZY_EXPORTS = {
    "Discoverer": ("discoverer", "Discoverer"),
    "Runner": ("runner", "Runner"),
    "RunnerConfig": ("runner", "RunnerConfig"),
    "QualityNormalizer": ("normalizer", "QualityNormalizer"),
    "evidence_payload": ("schema", "evidence_payload"),
    "Teammate": ("teammates", "Teammate"),
    "TeammateRegistry": ("teammates", "TeammateRegistry"),
    "DelegationRequest": ("teammates", "DelegationRequest"),
    "DelegationResult": ("teammates", "DelegationResult"),
    "DelegationProtocol": ("teammates", "DelegationProtocol"),
    "CodexExecutor": ("teammates", "CodexExecutor"),
    "Priority": ("teammates", "Priority"),
    "DelegationStatus": ("teammates", "DelegationStatus"),
    "HealthStatus": ("teammates", "HealthStatus"),
    "HealthMonitor": ("teammates", "HealthMonitor"),
    "ScalingConfig": ("scaling", "ScalingConfig"),
    "ResourceSampler": ("scaling", "ResourceSampler"),
    "ResourceSnapshot": ("scaling", "ResourceSnapshot"),
    "DynamicLimitController": ("scaling", "DynamicLimitController"),
    "MemoryPressureHandler": ("scaling", "MemoryPressureHandler"),
    "FDManager": ("scaling", "FDManager"),
    "CircuitBreaker": ("scaling", "CircuitBreaker"),
    "L1Cache": ("cache", "L1Cache"),
    "L2Cache": ("cache", "L2Cache"),
    "L1CacheStats": ("cache", "L1CacheStats"),
    "RequestCoalescer": ("cache", "RequestCoalescer"),
    "CachePreWarmer": ("cache", "CachePreWarmer"),
    "SpeculativeExecutor": ("cache", "SpeculativeExecutor"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    return getattr(import_module(f".{module_name}", __name__), attribute)


__all__ = sorted(_LAZY_EXPORTS)
