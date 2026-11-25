"""SQLite-backed response cache for model-API calls.

Keys are `(suite, task_id, model, prompt_hash, temperature)` per spec rule §6.
The cache is intentionally minimal: a single SQLite table with `(key, value,
expires_at)` columns plus a tiny `json` value column.

We pick SQLite over `diskcache` for two reasons:

1. Zero extra runtime dependencies (the harness ships with stdlib only).
2. The schema is trivial so a busy hash-collision causing replay bugs is
   easily auditable via `sqlite3 .dump`.

The cache is thread-safe via a single connection guarded by Python's GIL plus
an explicit `check_same_thread=False` so the asyncio-threadpool bridge in
`parallel.py` can read/write concurrently.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

DEFAULT_TTL_S = 7 * 24 * 60 * 60  # spec rule §6: 7 days


def make_cache_key(
    *,
    suite: str,
    task_id: str,
    model: str,
    prompt: str,
    temperature: float,
    extra: dict[str, Any] | None = None,
) -> str:
    """Return a stable cache key for the given call inputs.

    The key is a SHA-256 of the JSON-encoded tuple `(suite, task_id, model,
    temperature, prompt_hash, extra_hash)` truncated to 32 hex chars.
    `extra` is included so callers can bust the cache by adjusting any
    field without rebuilding the suite fingerprint.
    """
    payload = {
        "suite": suite,
        "task_id": task_id,
        "model": model,
        "temperature": float(temperature),
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "extra": dict(extra or {}),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]


@dataclass
class CacheEntry:
    """A single decoded cache entry."""

    key: str
    value: dict[str, Any]
    created_at: float
    expires_at: float

    def __iter__(self) -> Iterator[Any]:
        """Expose the legacy ``(text, metadata)`` tuple view."""
        yield self.value.get("text", "")
        yield self.value.get("meta", {})

    def is_fresh(self, now: float | None = None) -> bool:
        """Return True iff `now <= expires_at` (so the entry is reusable)."""
        cur = time.time() if now is None else now
        return cur <= self.expires_at


def default_cache_path() -> str:
    """Return a per-user cache file path under `$XDG_CACHE_HOME/pheno-harness`.

    Falls back to `~/.cache/pheno-harness/bench-cache.sqlite3`. Created lazily
    by `ResponseCache`.
    """
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return os.path.join(base, "pheno-harness", "bench-cache.sqlite3")


class ResponseCache:
    """SQLite-backed cache for model-API responses.

    Public surface is deliberately tiny (`get`, `put`, `invalidate`,
    `clear`, `stats`) and is closed under `no_cache=True` via a stub cache
    (use the `disabled()` factory).
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS responses (
        key TEXT PRIMARY KEY,
        suite TEXT NOT NULL,
        task_id TEXT NOT NULL,
        model TEXT NOT NULL,
        temperature REAL NOT NULL,
        value TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_responses_expires_at ON responses(expires_at);
    """

    def __init__(
        self,
        path: str | None = None,
        *,
        ttl_s: float = DEFAULT_TTL_S,
        no_cache: bool = False,
    ) -> None:
        self.ttl_s = ttl_s
        self.no_cache = no_cache
        if no_cache:
            self.path = ":memory:"
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._lock = threading.RLock()
        else:
            self.path = os.fspath(path or default_cache_path())
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._lock = threading.RLock()
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------ I/O

    def _row_to_entry(self, row: sqlite3.Row | tuple[str, ...]) -> CacheEntry:
        key, _, _, _, _, value_blob, created_at, expires_at = row
        return CacheEntry(
            key=key,
            value=json.loads(value_blob),
            created_at=float(created_at),
            expires_at=float(expires_at),
        )

    def get(self, key: str, *, now: float | None = None) -> CacheEntry | None:
        """Return a fresh entry or None."""
        if self.no_cache:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT key, suite, task_id, model, temperature, value, created_at, expires_at "
                "FROM responses WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        entry = self._row_to_entry(row)
        if not entry.is_fresh(now=now):
            return None
        return entry

    def put(
        self,
        *legacy_args: Any,
        key: str | None = None,
        suite: str = "",
        task_id: str = "",
        model: str = "",
        temperature: float = 0.0,
        value: dict[str, Any] | None = None,
        ttl_s: float | None = None,
        now: float | None = None,
    ) -> None:
        """Insert or overwrite the entry and reset its TTL."""
        if legacy_args:
            if len(legacy_args) != 2 or key is not None:
                raise TypeError("put expects either keyword fields or (key, value)")
            key = str(legacy_args[0])
            legacy_value = legacy_args[1]
            value = {
                "text": legacy_value[0]
                if isinstance(legacy_value, tuple)
                else legacy_value,
                "meta": legacy_value[1]
                if isinstance(legacy_value, tuple) and len(legacy_value) > 1
                else {},
            }
            suite = task_id = model = "legacy"
            temperature = 0.0
        if key is None or value is None:
            raise TypeError("put requires key and value")
        if self.no_cache:
            return
        cur = time.time() if now is None else now
        ttl = self.ttl_s if ttl_s is None else ttl_s
        blob = json.dumps(value, sort_keys=True, separators=(",", ":"))
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses "
                "(key, suite, task_id, model, temperature, value, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (key, suite, task_id, model, float(temperature), blob, cur, cur + ttl),
            )
            self._conn.commit()

    def invalidate(self, key: str) -> int:
        """Delete one entry; returns rows affected."""
        if self.no_cache:
            return 0
        with self._lock:
            cur = self._conn.execute("DELETE FROM responses WHERE key = ?", (key,))
            self._conn.commit()
            return cur.rowcount

    def clear(self) -> int:
        """Drop every entry; returns rows removed."""
        if self.no_cache:
            return 0
        with self._lock:
            cur = self._conn.execute("DELETE FROM responses")
            self._conn.commit()
            return cur.rowcount

    def prune(self, *, now: float | None = None) -> int:
        """Delete expired rows; returns rows removed."""
        if self.no_cache:
            return 0
        cur = time.time() if now is None else now
        with self._lock:
            cur_obj = self._conn.execute(
                "DELETE FROM responses WHERE expires_at <= ?", (cur,)
            )
            self._conn.commit()
            return cur_obj.rowcount

    def stats(self) -> dict[str, int | str]:
        """Return a small summary, useful for telemetry hooks."""
        if self.no_cache:
            return {"rows": 0, "path": "disabled"}
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM responses")
            (count,) = cur.fetchone()
        return {"rows": int(count), "path": self.path}

    def close(self) -> None:
        """Close the underlying connection (idempotent)."""
        with contextlib.suppress(Exception):
            self._conn.close()


@contextlib.contextmanager
def open_cache(
    path: str | None = None, *, ttl_s: float = DEFAULT_TTL_S, no_cache: bool = False
) -> Iterator[ResponseCache]:
    """Context manager that opens + closes a ResponseCache."""
    cache = ResponseCache(path=path, ttl_s=ttl_s, no_cache=no_cache)
    try:
        yield cache
    finally:
        cache.close()


def disabled() -> ResponseCache:
    """Construct a no-op cache (`--no-cache`) backed by an in-memory DB."""
    return ResponseCache(path=":memory:", no_cache=True)


def prune(path: str | None = None, *, now: float | None = None) -> int:
    """Convenience wrapper: open a `ResponseCache`, drop expired rows, return count."""
    with open_cache(path) as c:
        return c.prune(now=now)


def temp_cache_path() -> str:
    """Return a temporary file path suitable for tests."""
    fd, path = tempfile.mkstemp(prefix="bench-cache-", suffix=".sqlite3")
    os.close(fd)
    return path


__all__ = [
    "DEFAULT_TTL_S",
    "CacheEntry",
    "ResponseCache",
    "default_cache_path",
    "disabled",
    "make_cache_key",
    "open_cache",
    "prune",
    "temp_cache_path",
]
