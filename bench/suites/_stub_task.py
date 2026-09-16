"""TaskSpec and task-level helpers for pheno-harness benchmark suites.

This module contains the data model and synthetic-data utilities that
concrete suites consume.  Split out of ``_stub.py`` for modularity.
"""

from __future__ import annotations

import random

from bench.types import TaskSpec

# ---------------------------------------------------------------------------
# Synthetic data generation (no network, no HF download)
# ---------------------------------------------------------------------------


_SYNTHETIC_PROMPTS: tuple[str, ...] = (
    "Fix the off-by-one error in `process(items)` so the loop returns the correct subset.",
    "Refactor the duplicated validation logic in module X into a shared helper.",
    "Add a type annotation to `parse_payload` so mypy is happy on the v2 contract.",
    "The CLI hangs on `--watch` mode; please find the race condition and patch it.",
    "Translate the French error message at line 42 to English for the i18n sweep.",
    "Implement a breadth-first traversal in `graph.py` that returns shortest path lengths.",
    "Replace the deprecated `datetime.utcnow()` call with the recommended timezone-aware API.",
    "Compute the median absolute deviation of the attached numerical column.",
    "Add a property-based test that the encoder is the inverse of the decoder.",
    "Explain the difference between eager and lazy evaluation in this query plan.",
)


# ---------------------------------------------------------------------------
# process(items) — synthetic off-by-one example (referenced by prompt #0)
# ---------------------------------------------------------------------------


def process(items: list[int]) -> list[int]:
    """Return a subset containing items at even indices (0, 2, 4, …).

    Returns items at even indices (0, 2, 4, …).
    """
    result: list[int] = []
    for i in range(len(items)):
        if i % 2 == 0:  # even indices only
            result.append(items[i])
    return result


def synthetic_prompt(seed: int, idx: int) -> str:
    """Deterministically pick a prompt from the embedded synthetic corpus."""
    # Python 3.14 forbids tuple seeds; hash the tuple explicitly.
    rng = random.Random()  # nosec B311
    rng.seed(hash((seed, idx)) & 0xFFFFFFFFFFFFFFFF)
    return _SYNTHETIC_PROMPTS[rng.randint(0, len(_SYNTHETIC_PROMPTS) - 1)]


def synthetic_response(seed: int, idx: int) -> str:
    """Deterministically pick a synthetic assistant response (stub-mode only)."""
    rng = random.Random()  # nosec B311
    rng.seed(hash((seed, idx, "resp")) & 0xFFFFFFFFFFFFFFFF)
    length = rng.randint(40, 200)
    alphabet = "abcdefghijklmnopqrstuvwxyz .,!?"
    return "".join(rng.choice(alphabet) for _ in range(length))


# Back-compat alias: suites written against the skeleton's richer API used
# `Task` (the skeleton's name).  We export `TaskSpec` as `Task` so those
# suites continue to work without changes.
Task = TaskSpec

__all__ = [
    "Task",
    "TaskSpec",
    "synthetic_prompt",
    "synthetic_response",
    "process",
]
