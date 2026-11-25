from __future__ import annotations

from collections.abc import Iterable

from pheno_cost_card import CostCard


def cost_trend_arrow(current_usd: float, previous_usd: float | None = None) -> str:
    if previous_usd is None:
        return "->"
    if current_usd > previous_usd:
        return "↑"
    if current_usd < previous_usd:
        return "↓"
    return "->"


def render_repo_card(card: CostCard, previous_total_usd: float | None = None) -> str:
    total_usd = card.llm_tokens_usd
    arrow = cost_trend_arrow(total_usd, previous_total_usd)
    contributors = len(set(card.contributors))
    computed = card.computed_at.isoformat()
    return "\n".join(
        [
            f"# Cost Card: {card.repo}",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| CI minutes | {card.ci_minutes:,.0f} |",
            f"| LLM token spend | ${card.llm_tokens_usd:,.2f} |",
            f"| Storage | {card.storage_gb:,.2f} GB |",
            f"| Contributors | {contributors:,} |",
            "",
            f"Trend: {arrow}",
            f"Computed: {computed}",
            "",
        ]
    )


def render_fleet_card(cards: Iterable[CostCard], previous_total_usd: float | None = None) -> str:
    card_list = list(cards)
    repos = len(card_list)
    ci_minutes = sum(card.ci_minutes for card in card_list)
    llm_tokens_usd = sum(card.llm_tokens_usd for card in card_list)
    storage_gb = sum(card.storage_gb for card in card_list)
    contributors = len({name for card in card_list for name in card.contributors})
    arrow = cost_trend_arrow(llm_tokens_usd, previous_total_usd)
    return "\n".join(
        [
            "# Fleet Cost Card",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Repositories | {repos:,} |",
            f"| CI minutes | {ci_minutes:,.0f} |",
            f"| LLM token spend | ${llm_tokens_usd:,.2f} |",
            f"| Storage | {storage_gb:,.2f} GB |",
            f"| Contributors | {contributors:,} |",
            "",
            f"Trend: {arrow}",
            "",
        ]
    )
