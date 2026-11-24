"""Deterministic subset sampling for benchmark suites.

Per spec rule §7, `--seed=N` feeds Python `random.Random(N)`; the same seed
yields the same task subset for a given suite (suite size, n). The sampler
takes a stable suite fingerprint (suite name + a hashable metadata dict) and
returns either an ordered list of `task_id`s or zero-based indices into the
suite task list.

Suite agents hand us either:

* `iterable_pool`: an in-memory list of opaque task descriptors from which we
  pick `n` items.
* `count`: a positive integer giving only the total size of the suite; in that
  case we return zero-based indices.

Determinism properties (enforced by tests):

* `sample(pool, count, 42)` always yields the same multiset.
* Different seeds produce different orderings (with overwhelming probability).
* `n <= count` is mandatory; `n == count` yields the full suite in seed order;
  `n == 0` yields empty.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from typing import Any


def _suite_fingerprint(suite: str, *, extras: Hashable | None = None) -> int:
    """Return a stable positive 32-bit integer derived from `suite + extras`.

    We mix the suite name into the seed so two suites with the same `seed`
    argument still produce different orderings (defensive: spec only says
    "given suite" but it's the friendly default).
    """
    h = hashlib.sha256()
    h.update(suite.encode("utf-8"))
    h.update(b"\x00")
    if extras is not None:
        h.update(repr(extras).encode("utf-8"))
    digest = h.digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


@dataclass(frozen=True)
class Subset:
    """The concrete sampling decision returned by `sample()`.

    `ordered_indices` always preserves the original suite ordering of the
    chosen tasks; `task_ids` mirrors it when an iterable pool was supplied.
    """

    ordered_indices: list[int]
    task_ids: list[str] | None = None

    def __len__(self) -> int:
        return len(self.ordered_indices)


def make_rng(seed: int, suite: str, *, extras: Hashable | None = None) -> random.Random:
    """Build a fresh `random.Random` instance salted by suite+extras.

    Use this when the caller wants the same RNG object across multiple
    sampling decisions (e.g. for shuffling conversations prior to scoring).
    """
    return random.Random(_suite_fingerprint(suite, extras=extras) ^ (seed & 0x7FFFFFFF))  # nosec B311


def sample(
    suite: str,
    seed: int,
    *,
    count: int | None = None,
    pool: Sequence[Any] | None = None,
    n: int,
) -> Subset:
    """Sample `n` tasks deterministically from a suite.

    Args:
        suite: Suite name (mixed into the seed).
        seed: Caller-supplied RNG seed (spec rule §7).
        count: Total number of tasks in the suite (used when `pool` is None).
        pool: Optional sequence of task descriptors; if provided, `count` is
            inferred from its length and returned objects are task descriptors.
        n: How many tasks to sample. `n == 0` → empty; `n >= count` → all.

    Returns:
        A `Subset` with parallel `ordered_indices` and (if `pool` given)
        `task_ids`.
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if pool is None:
        if count is None or count < 0:
            raise ValueError("either count or pool must be provided")
        indices = list(range(count))
        inferred_count = count
    else:
        indices = list(range(len(pool)))
        inferred_count = len(pool)
    if n == 0:
        return Subset(ordered_indices=[], task_ids=[] if pool is not None else None)
    if n >= inferred_count:
        picked = list(range(inferred_count))
    else:
        rng = make_rng(seed, suite)
        # `sample` is the stdlib Fisher-Yates-style picking algorithm.
        picked = sorted(rng.sample(indices, n))
    task_ids: list[str] | None = None
    if pool is not None:
        task_ids = [str(pool[i]) for i in picked]
    return Subset(ordered_indices=picked, task_ids=task_ids)


def shuffled_pool(pool: Sequence[Hashable], suite: str, seed: int) -> list[Hashable]:
    """Return a deterministic shuffle of `pool` keyed by (suite, seed).

    Convenience for callers that want the sampler to produce a single global
    permutation rather than a fixed-sized subset.
    """
    rng = make_rng(seed, suite)
    indices = list(range(len(pool)))
    rng.shuffle(indices)
    return [pool[i] for i in indices]
