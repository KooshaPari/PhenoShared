"""Centralized configuration for thegent-cli-share.

All hardcoded runtime values are defined here with environment variable overrides,
so there is a single source of truth for tuning behaviour without code changes.

Usage:
    from thegent_cli_share.config import LOCK_TIMEOUT_SECONDS

    my_timeout = LOCK_TIMEOUT_SECONDS

Environment variable names use the ``THEGENT_`` prefix and follow the pattern::

    THEGENT_<SECTION>_<KEY>

Example:
    THEGENT_LOCK_TIMEOUT=7200    # Override default lock timeout (2 hours)
"""

from __future__ import annotations

import os
from typing import Final

# ── Lock Configuration ──────────────────────────────────────────────────────

# Default timeout (seconds) before a lock is considered stale / released.
LOCK_TIMEOUT_SECONDS: Final[int] = int(
    os.environ.get("THEGENT_LOCK_TIMEOUT", "3600")
)

# Default TTL (seconds) for a freshly-acquired lock status.
LOCK_TTL_SECONDS: Final[int] = int(
    os.environ.get("THEGENT_LOCK_TTL", "3600")
)

# ── Task Queue Configuration ────────────────────────────────────────────────

# Default timeout (seconds) for a queued task before it is considered failed.
QUEUE_TIMEOUT_SECONDS: Final[int] = int(
    os.environ.get("THEGENT_QUEUE_TIMEOUT", "3600")
)

# Numeric sort-keys used when ordering the queue by priority (lower = earlier).
# These are internal implementation details; the public API uses named levels.
QUEUE_PRIORITY_SORT_CRITICAL: Final[int] = 0
QUEUE_PRIORITY_SORT_HIGH: Final[int] = 1
QUEUE_PRIORITY_SORT_NORMAL: Final[int] = 2
QUEUE_PRIORITY_SORT_LOW: Final[int] = 3

# ── Hash Configuration ──────────────────────────────────────────────────────

# Default hash algorithm used when constructing CommandHash values.
HASH_ALGORITHM: Final[str] = os.environ.get(
    "THEGENT_HASH_ALGORITHM", "sha256"
)

# ── Health Score Thresholds ─────────────────────────────────────────────────

# Minimum overall score for the system to be considered fully healthy.
HEALTH_SCORE_HEALTHY_THRESHOLD: Final[float] = float(
    os.environ.get("THEGENT_HEALTH_HEALTHY_THRESHOLD", "0.8")
)

# Minimum overall score for the system to be considered degraded (below this is unhealthy).
HEALTH_SCORE_DEGRADED_THRESHOLD: Final[float] = float(
    os.environ.get("THEGENT_HEALTH_DEGRADED_THRESHOLD", "0.5")
)

# ── Available Configuration Keys (for documentation / validation) ───────────

ALL_CONFIG_KEYS: Final[tuple[str, ...]] = (
    "THEGENT_LOCK_TIMEOUT",
    "THEGENT_LOCK_TTL",
    "THEGENT_QUEUE_TIMEOUT",
    "THEGENT_HASH_ALGORITHM",
    "THEGENT_HEALTH_HEALTHY_THRESHOLD",
    "THEGENT_HEALTH_DEGRADED_THRESHOLD",
)
