from datetime import datetime, timezone

from pheno_cost_card import CostCard
from pheno_cost_card.render import render_fleet_card, render_repo_card


def test_repo_card_renders_core_metrics():
    card = CostCard(
        repo="example",
        ci_minutes=120.0,
        llm_tokens_usd=4.25,
        storage_gb=1.5,
        computed_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
        contributors=("a", "b", "a"),
    )

    markdown = render_repo_card(card, previous_total_usd=3.0)

    assert "# Cost Card: example" in markdown
    assert "| CI minutes | 120 |" in markdown
    assert "| LLM token spend | $4.25 |" in markdown
    assert "| Storage | 1.50 GB |" in markdown
    assert "| Contributors | 2 |" in markdown
    assert "Trend: ↑" in markdown


def test_fleet_card_aggregates_cards():
    cards = [
        CostCard("one", 10, 1.0, 2.0, contributors=("a",)),
        CostCard("two", 20, 2.5, 3.0, contributors=("a", "b")),
    ]

    markdown = render_fleet_card(cards, previous_total_usd=4.0)

    assert "# Fleet Cost Card" in markdown
    assert "| Repositories | 2 |" in markdown
    assert "| CI minutes | 30 |" in markdown
    assert "| LLM token spend | $3.50 |" in markdown
    assert "| Storage | 5.00 GB |" in markdown
    assert "| Contributors | 2 |" in markdown
    assert "Trend: ↓" in markdown
