#!/usr/bin/env python3
"""Project full Terminal-Bench 2.0 cost for OpenRouter models.

Uses scraped OpenRouter pricing plus conservative token assumptions. This does
not call model completions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import PHENO_ROOT


def _per_token_usd(value: str | float | int | None) -> float:
    return float(value or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Project OpenRouter TB2.0 eval cost")
    parser.add_argument("--scrape-dir", default="")
    parser.add_argument("--tasks", type=int, default=89)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--prompt-tokens", type=int, default=50000)
    parser.add_argument("--completion-tokens", type=int, default=3000)
    parser.add_argument("--max-usd", type=float, default=1.0)
    args = parser.parse_args()

    scrape_dir = (
        Path(args.scrape_dir)
        if args.scrape_dir
        else PHENO_ROOT / "state" / "openrouter_scrape" / "2026-07-04"
    )
    rows = []
    for path in sorted(scrape_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        api = rec.get("api") or {}
        pricing = api.get("pricing") or {}
        prompt_price = _per_token_usd(pricing.get("prompt"))
        completion_price = _per_token_usd(pricing.get("completion"))
        cost = (
            args.tasks
            * args.attempts
            * (
                args.prompt_tokens * prompt_price
                + args.completion_tokens * completion_price
            )
        )
        rows.append(
            {
                "id": rec["id"],
                "tasks": args.tasks,
                "attempts": args.attempts,
                "prompt_tokens_per_task": args.prompt_tokens,
                "completion_tokens_per_task": args.completion_tokens,
                "projected_usd": round(cost, 6),
                "enabled": cost <= args.max_usd,
            }
        )

    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rule": f"enabled only when projected full TB2.0 cost <= ${args.max_usd:.2f}",
        "rows": rows,
    }
    out_path = scrape_dir / "tbench20_cost_projection.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
