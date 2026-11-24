#!/usr/bin/env python3
"""Wastage + motion analysis report from unified traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from eval.budget import estimate_from_omniroute
from eval.pillars import score_from_wastage
from pheno.paths import EVAL_RESULTS_DIR, TRAINING_DIR
from traces.wastage import analyze_file


def _latest_traces() -> Path | None:
    files = sorted(TRAINING_DIR.glob("traces_unified_*.jsonl"))
    return files[-1] if files else None


def _to_markdown(report: dict[str, Any], pillars: dict[str, Any], budget: dict[str, Any]) -> str:
    lines = [
        "# Pheno Wastage Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Token burn",
        f"- Events: {report['total_events']:,}",
        f"- Input tokens: {report['total_tokens_in']:,}",
        f"- Output tokens: {report['total_tokens_out']:,}",
        f"- Cache reads: {report['total_cache_read']:,}",
        f"- Giant calls (>=32k): {report['giant_calls_32k_plus']:,}",
        "",
        "## Motion",
        f"- Forward: {report['motion'].get('forward', 0):.1%}",
        f"- Stagnate: {report['motion'].get('stagnate', 0):.1%}",
        f"- Regress: {report['motion'].get('regress', 0):.1%}",
        f"- Avg ROI: {report['motion'].get('avg_roi', 0):.3f}",
        "",
        "## Pillar composite",
        f"- Score: **{pillars['composite']:.3f}**",
        "",
        "## Budget",
        f"- Est. monthly: ${budget['estimated_monthly_usd']:.0f} ({budget['alert_level']})",
        f"- Codex cut progress: {budget['codex_cut_progress']:.1%}",
        "",
        "## Recommendations",
    ]
    for r in report.get("recommendations", []):
        lines.append(f"- {r}")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--traces", type=Path, default=None)
    args = p.parse_args()
    path = args.traces or _latest_traces()
    if not path or not path.exists():
        print("No traces file. Run: python scripts/collect_traces.py")
        sys.exit(1)
    report = analyze_file(path)
    budget = estimate_from_omniroute().to_dict()
    pillars = score_from_wastage(report.to_dict(), budget).to_dict()

    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = EVAL_RESULTS_DIR / "wastage_latest.json"
    payload = {"wastage": report.to_dict(), "pillars": pillars, "budget": budget}
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = _to_markdown(report.to_dict(), pillars, budget)
    (EVAL_RESULTS_DIR / "wastage_latest.md").write_text(md, encoding="utf-8")
    summary = (
        f"Pillar composite: {pillars['composite']:.3f} | "
        f"Budget est: ${budget['estimated_monthly_usd']:.0f} ({budget['alert_level']}) | "
        f"Giant calls: {report.giant_calls_32k_plus}"
    )
    print(summary)
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()
