"""Render a fleet-wide cost card from a list of ``CostCard`` instances.

Usage::

    from pheno_cost_card import CostCard, render_fleet_card
    cards = [
        CostCard(repo="pheno-config", ci_minutes=120.0, storage_gb=0.5,
                 egress_gb=0.1, llm_tokens=50_000, month="2026-06"),
    ]
    print(render_fleet_card(cards))
"""

from __future__ import annotations

from pheno_cost_card import CostCard


def render_fleet_card(cards: list[CostCard]) -> str:
    """Render a Markdown table summarizing all repos in ``cards``."""
    if not cards:
        return "_no cost data available_"
    headers = ["repo", "month", "ci_min", "storage_gb", "egress_gb", "llm_tokens"]
    rows = [
        [
            c.repo,
            c.month,
            f"{c.ci_minutes:.1f}",
            f"{c.storage_gb:.2f}",
            f"{c.egress_gb:.2f}",
            f"{c.llm_tokens:,}",
        ]
        for c in cards
    ]
    total_ci = sum(c.ci_minutes for c in cards)
    total_storage = sum(c.storage_gb for c in cards)
    total_egress = sum(c.egress_gb for c in cards)
    total_tokens = sum(c.llm_tokens for c in cards)
    rows.append([
        "**TOTAL**",
        "",
        f"**{total_ci:.1f}**",
        f"**{total_storage:.2f}**",
        f"**{total_egress:.2f}**",
        f"**{total_tokens:,}**",
    ])
    return _to_markdown(headers, rows)


def render_repo_card(card: CostCard) -> str:
    """Render a single-repo Markdown card."""
    headers = ["field", "value"]
    rows = [
        ["repo", card.repo],
        ["month", card.month],
        ["ci_minutes", f"{card.ci_minutes:.1f}"],
        ["storage_gb", f"{card.storage_gb:.2f}"],
        ["egress_gb", f"{card.egress_gb:.2f}"],
        ["llm_tokens", f"{card.llm_tokens:,}"],
    ]
    return _to_markdown(headers, rows)


def _to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)