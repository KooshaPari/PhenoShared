"""Ports: pure ABC contracts for domain operations (hexagonal architecture)."""

from .inference import (
    CachePort,
    DispatchPort,
    InferencePort,
    InferenceRequest,
    InferenceResponse,
)

__all__ = [
    "CachePort",
    "DispatchPort",
    "InferencePort",
    "InferenceRequest",
    "InferenceResponse",
]
