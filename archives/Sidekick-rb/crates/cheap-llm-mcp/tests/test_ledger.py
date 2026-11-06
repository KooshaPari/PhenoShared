from __future__ import annotations

import pytest

from cheap_llm_mcp.ledger import Ledger, estimate_cost_usd


@pytest.mark.requirement("FR-LLM-030")
def test_estimate_cost_known_model():
    cost = estimate_cost_usd("MiniMax-M2", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.30 + 1.20)


@pytest.mark.requirement("FR-LLM-031")
def test_estimate_cost_unknown_model_falls_back():
    cost = estimate_cost_usd("unknown-model", 1_000_000, 1_000_000)
    assert cost == pytest.approx(1.0 + 3.0)


@pytest.mark.requirement("FR-LLM-032")
def test_ledger_record_and_aggregate(tmp_path):
    ledger = Ledger(path=tmp_path / "ledger.jsonl")
    ledger.record("minimax", "MiniMax-M2", 1000, 500)
    ledger.record("minimax", "MiniMax-M2", 2000, 1000)
    agg = ledger.month_total()
    assert agg.calls == 2
    assert agg.total_usd > 0
    assert "minimax" in agg.by_provider


@pytest.mark.requirement("FR-LLM-034")
def test_ledger_cap_enforcement(tmp_path):
    ledger = Ledger(path=tmp_path / "ledger.jsonl", cap_usd=0.000001)
    ledger.record("minimax", "MiniMax-M2", 1_000_000, 1_000_000)
    with pytest.raises(RuntimeError, match="monthly cap"):
        ledger.check_cap()


@pytest.mark.requirement("FR-LLM-035")
def test_ledger_no_cap(tmp_path):
    ledger = Ledger(path=tmp_path / "ledger.jsonl", cap_usd=None)
    ledger.record("minimax", "MiniMax-M2", 1_000_000, 1_000_000)
    ledger.check_cap()  # should not raise
