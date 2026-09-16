"""Budget tracking toward <$200/mo ideal, <$400 max.

This module estimates monthly spend from OmniRoute logs and emits a
``BudgetSnapshot`` dataclass used by pillar scoring and the budget gate.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR, EVAL_DIR, OMNIROUTE_DB, TRAINING_DIR

# Rough $/1M token estimates for burn attribution (adjust from invoices)
PROVIDER_COST_PER_M: dict[str, float] = {
    "openai": 2.50,
    "codex": 2.50,
    "anthropic": 15.0,
    "claude": 15.0,
    "minimax": 1.0,
    "kimi": 0.5,
    "local": 0.0,
    "unknown": 1.0,
}


@dataclass
class BudgetSnapshot:
    """Point-in-time budget estimate derived from provider token usage.

    Attributes:
        generated_at: ISO-8601 timestamp when the snapshot was created.
        estimated_monthly_usd: Estimated spend for the trailing window in USD.
        tokens_in_month: Total input tokens observed in the window.
        tokens_out_month: Total output tokens observed in the window.
        by_provider_usd: Spend attribution per normalized provider.
        targets: Budget target thresholds loaded from config.
        alert_level: One of green/yellow/red/blackout.
        codex_cut_progress: Progress toward halving Codex/OpenAI spend (0-1).

    """

    generated_at: str
    estimated_monthly_usd: float
    tokens_in_month: int
    tokens_out_month: int
    by_provider_usd: dict[str, float]
    targets: dict[str, Any]
    alert_level: str
    codex_cut_progress: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot to a JSON-compatible dict.

        Returns:
            Dict with rounded monetary fields and original targets preserved.

        """
        return {
            "generated_at": self.generated_at,
            "estimated_monthly_usd": round(self.estimated_monthly_usd, 2),
            "tokens_in_month": self.tokens_in_month,
            "tokens_out_month": self.tokens_out_month,
            "by_provider_usd": {
                k: round(v, 2) for k, v in self.by_provider_usd.items()
            },
            "targets": self.targets,
            "alert_level": self.alert_level,
            "codex_cut_progress": round(self.codex_cut_progress, 4),
        }


def _provider_key(p: str) -> str:
    """Normalize a raw provider string to a canonical cost bucket.

    Args:
        p: Raw provider identifier from logs or config.

    Returns:
        Canonical provider key used in ``PROVIDER_COST_PER_M``.

    """
    pl = (p or "").lower()
    if "codex" in pl or "gpt" in pl or "openai" in pl:
        return "openai"
    if "claude" in pl or "anthropic" in pl or "opus" in pl:
        return "claude"
    if "minimax" in pl:
        return "minimax"
    if "kimi" in pl:
        return "kimi"
    if not pl or pl == "local":
        return "local"
    return pl


def estimate_from_omniroute(db: Path | None = None, days: int = 30) -> BudgetSnapshot:
    """Estimate monthly spend from OmniRoute call logs.

    Reads ``budget_targets.yaml`` for thresholds, aggregates tokens per
    provider from the SQLite call log, applies per-provider rates, and
    writes both a JSONL snapshot and ``budget_latest.json``.

    Args:
        db: Optional override path for the OmniRoute DB. Defaults to
            the configured ``OMNIROUTE_DB``.
        days: Trailing window in days (reserved for future filtering,
            currently aggregated over all rows).

    Returns:
        A ``BudgetSnapshot`` dataclass with estimates and alert level.

    """
    cfg: dict[str, Any] = yaml.safe_load(
        (CONFIG_DIR / "budget_targets.yaml").read_text(encoding="utf-8")
    )
    targets: dict[str, Any] = cfg["targets"]
    baseline: float = float(cfg["baseline"]["monthly_usd"])
    db = db or OMNIROUTE_DB
    by_prov_tokens: dict[str, int] = {}
    tin = tout = 0
    if db.exists():
        conn = sqlite3.connect(db)
        rows = conn.execute("""
            SELECT provider, SUM(tokens_in), SUM(tokens_out), COUNT(*)
            FROM call_logs
            GROUP BY provider
        """).fetchall()
        conn.close()
        for prov, pi, po, _ in rows:
            key = _provider_key(prov or "")
            by_prov_tokens[key] = (
                by_prov_tokens.get(key, 0) + int(pi or 0) + int(po or 0)
            )
            tin += int(pi or 0)
            tout += int(po or 0)

    by_usd: dict[str, float] = {}
    for prov, tok in by_prov_tokens.items():
        rate = PROVIDER_COST_PER_M.get(prov, 1.0)
        by_usd[prov] = (tok / 1_000_000) * rate

    estimated = sum(by_usd.values())
    if estimated < 50:
        estimated = float(baseline)

    ideal: float = float(targets["ideal_monthly_usd"])
    max_usd: float = float(targets["max_monthly_usd"])
    if estimated <= ideal:
        alert = "green"
    elif estimated <= max_usd * 0.75:
        alert = "yellow"
    elif estimated <= max_usd:
        alert = "red"
    else:
        alert = "blackout"

    cfg["codex_openai"]["cut_scenarios"]["half_bill"]["target_usd"]
    codex_current: float = float(
        by_usd.get("openai", cfg["codex_openai"]["current_monthly_usd"])
    )
    codex_progress = 1.0 - min(
        codex_current / max(float(cfg["codex_openai"]["current_monthly_usd"]), 1), 1.0
    )

    snap = BudgetSnapshot(
        generated_at=datetime.now(UTC).isoformat(),
        estimated_monthly_usd=estimated,
        tokens_in_month=tin,
        tokens_out_month=tout,
        by_provider_usd=by_usd,
        targets=targets,
        alert_level=alert,
        codex_cut_progress=codex_progress,
    )
    out = EVAL_DIR / "results"
    out.mkdir(parents=True, exist_ok=True)
    log = TRAINING_DIR / "budget_snapshots.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snap.to_dict()) + "\n")
    (out / "budget_latest.json").write_text(
        json.dumps(snap.to_dict(), indent=2), encoding="utf-8"
    )
    return snap
