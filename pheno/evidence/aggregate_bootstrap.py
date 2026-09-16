"""Bootstrap confidence-interval helpers for ``pheno.eval.aggregate.v2``.

This module isolates the deterministic resampling machinery so that the rest
of the aggregate pipeline can be tested without dragging in the trial-state
plumbing or the run-provenance validators.  All randomness is derived from
SHA-256 digests; no language or runtime PRNG is consumed.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import canonical_json_bytes

DEFAULT_BOOTSTRAP_RESAMPLES = 10_000
QUANTILE_METHOD = "Hyndman-Fan-type-7"
BOOTSTRAP_METHOD = "paired-task-cluster-percentile-v1"


def quantile_type7(values: Sequence[float], probability: float) -> float | None:
    """Return the deterministic Hyndman-Fan type-7 sample quantile.

    Empty input is undefined.  A singleton returns that observation.  No
    display rounding is performed here or elsewhere in the scorer.
    """

    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("quantiles require finite values")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _counter_draw(seed: bytes, replicate: int, draw: int, population: int) -> int:
    """Draw without depending on a language/runtime PRNG implementation."""

    if population < 1:
        raise ValueError("population must be positive")
    modulus = 1 << 64
    limit = modulus - (modulus % population)
    counter = 0
    while True:
        material = (
            seed
            + replicate.to_bytes(8, "big")
            + draw.to_bytes(8, "big")
            + counter.to_bytes(4, "big")
        )
        value = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        if value < limit:
            return value % population
        counter += 1


def _bootstrap_mean_ci(
    task_values: Mapping[str, float],
    *,
    seed: bytes,
    resamples: int,
) -> dict[str, Any]:
    task_ids = sorted(task_values)
    if not task_ids:
        return {
            "lower": None,
            "upper": None,
            "resamples": resamples,
            "task_clusters": 0,
            "method": BOOTSTRAP_METHOD,
            "quantile_method": QUANTILE_METHOD,
        }
    samples: list[float] = []
    count = len(task_ids)
    for replicate in range(resamples):
        total = 0.0
        for draw in range(count):
            task_id = task_ids[_counter_draw(seed, replicate, draw, count)]
            total += task_values[task_id]
        samples.append(total / count)
    return {
        "lower": quantile_type7(samples, 0.025),
        "upper": quantile_type7(samples, 0.975),
        "resamples": resamples,
        "task_clusters": count,
        "method": BOOTSTRAP_METHOD,
        "quantile_method": QUANTILE_METHOD,
    }


def _seed_digest(label: str, payload: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(
        label.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    ).digest()


__all__ = [
    "BOOTSTRAP_METHOD",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "QUANTILE_METHOD",
    "quantile_type7",
]
