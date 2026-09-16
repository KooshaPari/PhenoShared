"""Tokn L14 query helpers.

Thin functions over the pricing book + cost ledger. Designed to be ergonomic
for both CLI and library consumers, with no global state and explicit
connection management.

All functions take a `sqlite3.Connection` so the caller controls transaction
boundaries and connection lifetime.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class PricingSnapshot:
    """Most recent pricing snapshot for a model at or before `as_of` (ms)."""

    model_id: str
    input_usd_1k: float
    output_usd_1k: float
    currency: str
    effective_at: int


@dataclass(frozen=True)
class LedgerEntry:
    """One cost calculation recorded in the ledger."""

    id: int
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    computed_at: int
    note: str | None


@dataclass(frozen=True)
class SpendSummary:
    """Aggregated spend for a model over an inclusive time window."""

    model_id: str
    total_cost_usd: float
    entry_count: int
    total_input_tokens: int
    total_output_tokens: int


def get_pricing(
    conn: sqlite3.Connection, model_id: str, as_of: int | None = None
) -> PricingSnapshot | None:
    """Return the latest pricing snapshot for a model as of `as_of` (ms epoch)."""
    if as_of is None:
        as_of = int(time.time() * 1000)
    row = conn.execute(
        """
        SELECT model_id, input_usd_1k, output_usd_1k, currency, effective_at
        FROM pricing_book
        WHERE model_id = ? AND effective_at <= ?
        ORDER BY effective_at DESC
        LIMIT 1
        """,
        (model_id, as_of),
    ).fetchone()
    if row is None:
        return None
    return PricingSnapshot(
        model_id=row[0],
        input_usd_1k=row[1],
        output_usd_1k=row[2],
        currency=row[3],
        effective_at=row[4],
    )


def record_cost(
    conn: sqlite3.Connection,
    *,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    note: str | None = None,
) -> int:
    """Insert one ledger entry. Returns the new row id."""
    cur = conn.execute(
        """
        INSERT INTO cost_ledger
            (model_id, input_tokens, output_tokens, cost_usd, computed_at, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            model_id,
            input_tokens,
            output_tokens,
            cost_usd,
            int(time.time() * 1000),
            note,
        ),
    )
    return int(cur.lastrowid)


def summarize_spend(
    conn: sqlite3.Connection,
    *,
    model_id: str,
    since_ms: int,
    until_ms: int | None = None,
) -> SpendSummary:
    """Aggregate spend for a model over [since_ms, until_ms]. Defaults to now."""
    if until_ms is None:
        until_ms = int(time.time() * 1000)
    row = conn.execute(
        """
        SELECT
            COUNT(*)                    AS entry_count,
            COALESCE(SUM(cost_usd), 0)  AS total_cost_usd,
            COALESCE(SUM(input_tokens), 0)  AS total_in,
            COALESCE(SUM(output_tokens), 0) AS total_out
        FROM cost_ledger
        WHERE model_id = ? AND computed_at BETWEEN ? AND ?
        """,
        (model_id, since_ms, until_ms),
    ).fetchone()
    return SpendSummary(
        model_id=model_id,
        total_cost_usd=float(row[1]),
        entry_count=int(row[0]),
        total_input_tokens=int(row[2]),
        total_output_tokens=int(row[3]),
    )
