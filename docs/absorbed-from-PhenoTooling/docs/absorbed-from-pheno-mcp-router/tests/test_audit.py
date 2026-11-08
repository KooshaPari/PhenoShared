"""Tests for the :mod:`pheno_mcp_router.audit` trail.

The audit trail is the canonical record of every dispatch decision
(allowed, blocked, dry-run). These tests pin the small public
surface (``record``, ``entries``, ``filter``, ``summarize``,
``clear``, ``close``) and the invariants of the append-only model.
A small thread fan-out covers the concurrent record race, and a
temporary-file fixture covers the JSONL persistence sink.

Ported from dispatch-mcp W2-1 (test_core_audit.py @ 6aad7fa) per
L5-104.1 with import rewrite.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from pheno_mcp_router.audit import (
    AuditEntry,
    AuditLog,
)


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------


def test_audit_entry_creation_minimal() -> None:
    """A minimal AuditEntry has the documented required fields."""
    entry = AuditEntry(
        request_id="r-1",
        timestamp=1.0,
        tier="haiku",
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        decision="allowed",
        reason="ok",
        is_priced=True,
    )
    assert entry.request_id == "r-1"
    assert entry.tier == "haiku"
    assert entry.decision == "allowed"
    assert entry.detail == {}


def test_audit_entry_rejects_invalid_decision() -> None:
    """An unknown decision value is rejected at construction."""
    with pytest.raises(ValueError, match="decision must be one of"):
        AuditEntry(
            request_id="r",
            timestamp=1.0,
            tier="t",
            model="m",
            provider="p",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            decision="maybe",  # not in the allowed set
            reason="ok",
            is_priced=True,
        )


def test_audit_entry_rejects_negative_tokens() -> None:
    """Negative input or output tokens are not allowed."""
    with pytest.raises(ValueError, match="input_tokens must be >= 0"):
        AuditEntry(
            request_id="r",
            timestamp=1.0,
            tier="t",
            model="m",
            provider="p",
            input_tokens=-1,
            output_tokens=0,
            cost_usd=0.0,
            decision="allowed",
            reason="ok",
            is_priced=True,
        )
    with pytest.raises(ValueError, match="output_tokens must be >= 0"):
        AuditEntry(
            request_id="r",
            timestamp=1.0,
            tier="t",
            model="m",
            provider="p",
            input_tokens=0,
            output_tokens=-1,
            cost_usd=0.0,
            decision="allowed",
            reason="ok",
            is_priced=True,
        )


def test_audit_entry_rejects_negative_cost() -> None:
    """A negative cost is not allowed (spend is non-negative)."""
    with pytest.raises(ValueError, match="cost_usd must be >= 0"):
        AuditEntry(
            request_id="r",
            timestamp=1.0,
            tier="t",
            model="m",
            provider="p",
            input_tokens=0,
            output_tokens=0,
            cost_usd=-0.001,
            decision="allowed",
            reason="ok",
            is_priced=True,
        )


def test_audit_entry_to_dict_includes_iso_timestamp() -> None:
    """The serialized shape includes a human-readable ISO timestamp."""
    entry = AuditEntry(
        request_id="r",
        timestamp=0.0,  # epoch — deterministic for the test
        tier="haiku",
        model="m",
        provider="p",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.001,
        decision="allowed",
        reason="ok",
        is_priced=True,
    )
    payload = entry.to_dict()
    assert payload["request_id"] == "r"
    assert payload["tier"] == "haiku"
    assert payload["decision"] == "allowed"
    assert "timestamp_iso" in payload
    assert payload["timestamp"] == 0.0


# ---------------------------------------------------------------------------
# AuditLog: record / entries
# ---------------------------------------------------------------------------


def test_audit_log_starts_empty() -> None:
    """A fresh log has no entries."""
    log = AuditLog()
    assert log.entries() == ()


def test_audit_log_record_returns_entry() -> None:
    """``record`` returns the entry it just stored."""
    log = AuditLog()
    entry = log.record(
        tier="haiku",
        model="m",
        provider="p",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.001,
        decision="allowed",
    )
    assert isinstance(entry, AuditEntry)
    assert log.entries() == (entry,)


def test_audit_log_assigns_request_id_when_omitted() -> None:
    """A fresh UUID is generated when ``request_id`` is not provided."""
    log = AuditLog()
    e1 = log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    e2 = log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    assert e1.request_id != e2.request_id
    # Both are non-empty strings (UUID hex).
    assert e1.request_id
    assert e2.request_id


def test_audit_log_preserves_explicit_request_id() -> None:
    """A caller-supplied request_id is honored for correlation."""
    log = AuditLog()
    entry = log.record(
        tier="haiku",
        model="m",
        provider="p",
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.0,
        decision="allowed",
        request_id="upstream-req-42",
    )
    assert entry.request_id == "upstream-req-42"


def test_audit_log_uses_injected_clock() -> None:
    """The injectable clock is used for timestamps (deterministic tests)."""
    times = iter([100.0, 200.0])
    log = AuditLog(clock=lambda: next(times))
    e1 = log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    e2 = log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    assert e1.timestamp == 100.0
    assert e2.timestamp == 200.0


def test_audit_log_respects_max_entries() -> None:
    """When the cap is reached, the oldest entries are evicted first."""
    log = AuditLog(max_entries=3)
    for i in range(5):
        log.record(
            tier="haiku", model="m", provider="p",
            input_tokens=1, output_tokens=1, cost_usd=0.0,
            decision="allowed", request_id=f"r-{i}",
        )
    retained_ids = [e.request_id for e in log.entries()]
    assert retained_ids == ["r-2", "r-3", "r-4"]


def test_audit_log_rejects_negative_max_entries() -> None:
    """``max_entries`` is validated at construction time."""
    with pytest.raises(ValueError, match="max_entries must be >= 0"):
        AuditLog(max_entries=-1)


# ---------------------------------------------------------------------------
# AuditLog: filter
# ---------------------------------------------------------------------------


def test_audit_log_filter_by_tier() -> None:
    """``filter(tier=...)`` returns only matching entries."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    log.record(
        tier="opus", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    only_haiku = log.filter(tier="haiku")
    assert [e.tier for e in only_haiku] == ["haiku"]


def test_audit_log_filter_by_decision() -> None:
    """``filter(decision=...)`` returns only matching entries."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="blocked",
        reason="quota",
    )
    blocked = log.filter(decision="blocked")
    assert len(blocked) == 1
    assert blocked[0].reason == "quota"


def test_audit_log_filter_by_time_window() -> None:
    """``filter(since=..., until=...)`` returns entries in the inclusive range."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        timestamp=100.0,
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        timestamp=200.0,
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        timestamp=300.0,
    )
    in_window = log.filter(since=150.0, until=250.0)
    assert [e.timestamp for e in in_window] == [200.0]


def test_audit_log_filter_combines_criteria() -> None:
    """Multiple filter criteria are AND-combined."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        timestamp=100.0,
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="blocked",
        timestamp=200.0,
    )
    log.record(
        tier="opus", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        timestamp=200.0,
    )
    result = log.filter(tier="haiku", decision="allowed", since=50.0, until=150.0)
    assert [e.timestamp for e in result] == [100.0]


# ---------------------------------------------------------------------------
# AuditLog: summarize
# ---------------------------------------------------------------------------


def test_audit_log_summarize_aggregates_spend_by_tier() -> None:
    """Summarize produces per-tier and per-model spend aggregates."""
    log = AuditLog()
    log.record(
        tier="haiku", model="claude-3-5-haiku-20241022", provider="anthropic",
        input_tokens=1000, output_tokens=500, cost_usd=0.001, decision="allowed",
    )
    log.record(
        tier="haiku", model="claude-3-5-haiku-20241022", provider="anthropic",
        input_tokens=2000, output_tokens=1000, cost_usd=0.002, decision="allowed",
    )
    log.record(
        tier="opus", model="claude-opus-4", provider="anthropic",
        input_tokens=500, output_tokens=250, cost_usd=0.05, decision="allowed",
    )
    summary = log.summarize()
    assert summary.total_entries == 3
    assert summary.allowed_entries == 3
    assert summary.blocked_entries == 0
    assert summary.total_input_tokens == 3500
    assert summary.total_output_tokens == 1750
    assert summary.total_spend_usd == pytest.approx(0.053)
    assert summary.spend_by_tier == {"haiku": pytest.approx(0.003), "opus": pytest.approx(0.05)}
    assert summary.requests_by_tier == {"haiku": 2, "opus": 1}
    assert summary.spend_by_model == {
        "claude-3-5-haiku-20241022": pytest.approx(0.003),
        "claude-opus-4": pytest.approx(0.05),
    }


def test_audit_log_summarize_excludes_blocked_from_spend() -> None:
    """Blocked dispatches do not contribute to spend aggregates."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=100, output_tokens=50, cost_usd=0.001, decision="allowed",
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=999, output_tokens=999, cost_usd=0.0, decision="blocked",
        reason="quota",
    )
    summary = log.summarize()
    assert summary.total_entries == 2
    assert summary.allowed_entries == 1
    assert summary.blocked_entries == 1
    # Total spend is the allowed entry only.
    assert summary.total_spend_usd == pytest.approx(0.001)
    # But the per-tier request count includes both.
    assert summary.requests_by_tier == {"haiku": 1}


def test_audit_log_summarize_to_dict_shape() -> None:
    """The serialized shape is stable for downstream reports."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=10, output_tokens=5, cost_usd=0.001, decision="allowed",
    )
    payload = log.summarize().to_dict()
    assert "total_entries" in payload
    assert "allowed_entries" in payload
    assert "blocked_entries" in payload
    assert "total_input_tokens" in payload
    assert "total_output_tokens" in payload
    assert "total_spend_usd" in payload
    assert "spend_by_tier" in payload
    assert "requests_by_tier" in payload
    assert "spend_by_model" in payload
    assert payload["total_spend_usd"] == pytest.approx(0.001)


def test_audit_log_summarize_filters_match_filter_signature() -> None:
    """``summarize`` accepts the same filter kwargs as ``filter``."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.001, decision="allowed",
        timestamp=100.0,
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.002, decision="allowed",
        timestamp=300.0,
    )
    summary = log.summarize(since=200.0)
    assert summary.total_entries == 1
    assert summary.total_spend_usd == pytest.approx(0.002)


# ---------------------------------------------------------------------------
# AuditLog: clear
# ---------------------------------------------------------------------------


def test_audit_log_clear_drops_all_in_memory_entries() -> None:
    """``clear`` empties the in-memory log (does not affect the JSONL sink)."""
    log = AuditLog()
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
    )
    log.clear()
    assert log.entries() == ()


# ---------------------------------------------------------------------------
# AuditLog: JSONL sink
# ---------------------------------------------------------------------------


def test_audit_log_jsonl_sink_writes_one_line_per_entry(tmp_path: Path) -> None:
    """Each record appends a JSON line to the configured sink file."""
    path = tmp_path / "audit.jsonl"
    log = AuditLog(jsonl_path=path)
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        request_id="r-1",
    )
    log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        request_id="r-2",
    )
    log.close()
    # File exists, one line per entry, each line valid JSON.
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    payloads = [json.loads(line) for line in lines]
    assert [p["request_id"] for p in payloads] == ["r-1", "r-2"]
    assert all(p["decision"] == "allowed" for p in payloads)


def test_audit_log_jsonl_sink_appends_across_reopens(tmp_path: Path) -> None:
    """A re-opened sink appends rather than overwrites prior entries."""
    path = tmp_path / "audit.jsonl"
    log1 = AuditLog(jsonl_path=path)
    log1.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        request_id="r-1",
    )
    log1.close()
    log2 = AuditLog(jsonl_path=path)
    log2.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
        request_id="r-2",
    )
    log2.close()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["request_id"] for line in lines] == ["r-1", "r-2"]


def test_audit_log_close_is_idempotent() -> None:
    """``close`` is a no-op the second time (no error on the closed file)."""
    log = AuditLog()
    log.close()
    log.close()  # second call must not raise


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_audit_log_concurrent_record_preserves_all_entries() -> None:
    """A burst of concurrent ``record`` calls must not lose entries."""
    log = AuditLog()
    per_thread = 200
    threads = []
    for _ in range(5):
        t = threading.Thread(
            target=lambda: [
                log.record(
                    tier="haiku", model="m", provider="p",
                    input_tokens=1, output_tokens=1, cost_usd=0.0, decision="allowed",
                )
                for _ in range(per_thread)
            ]
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert len(log.entries()) == 5 * per_thread


def test_audit_log_dry_run_decision_is_accepted() -> None:
    """The ``dry_run`` decision value is part of the allowed set."""
    log = AuditLog()
    entry = log.record(
        tier="haiku", model="m", provider="p",
        input_tokens=1, output_tokens=1, cost_usd=0.0, decision="dry_run",
    )
    assert entry.decision == "dry_run"
