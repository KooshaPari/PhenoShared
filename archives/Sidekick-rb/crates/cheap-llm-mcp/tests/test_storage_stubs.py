"""Storage stubs for SIDE-DATA-004 (audit remediation)."""

from __future__ import annotations

import json
from pathlib import Path

from cheap_llm_mcp.cache import TTLCache
from cheap_llm_mcp.ledger import Ledger, LedgerEntry, estimate_cost_usd


def test_storage_stub_ttl_cache_roundtrip() -> None:
    cache = TTLCache(ttl_seconds=60.0, max_entries=8)
    key = TTLCache.key("prompt", "model-x")
    cache.set(key, {"text": "cached"})
    assert cache.get(key) == {"text": "cached"}


def test_storage_stub_ledger_append_only(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = Ledger(ledger_path, cap_usd=100.0)
    entry = ledger.record("stub", "stub-model", input_tokens=1, output_tokens=2)
    assert isinstance(entry, LedgerEntry)
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["provider"] == "stub"
    assert parsed["cost_usd"] >= 0.0


def test_storage_stub_estimate_cost_is_non_negative() -> None:
    cost = estimate_cost_usd("MiniMax-M2", input_tokens=1000, output_tokens=500)
    assert cost >= 0.0
