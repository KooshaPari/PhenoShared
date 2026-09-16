#!/usr/bin/env python3
"""Print local model bench matrix — candidates, runners, first sweep."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import CONFIG_DIR


def main() -> int:
    cfg = yaml.safe_load(
        (CONFIG_DIR / "local_model_bench_matrix.yaml").read_text(encoding="utf-8")
    )
    runners = cfg.get("runners", {})
    print("=== Inference runners (3090 Ti / TB2 agent) ===")
    for key in (
        "primary_agent",
        "secondary_batch",
        "legacy_fallback",
        "research_cpu_efficiency",
    ):
        r = runners.get(key, {})
        if r:
            print(f"  {r.get('id', key):<14} - {r.get('why', '')[:70]}")

    print("\n=== First micro-eval sweep (1 TB2 task ~5 min each) ===")
    sweep = cfg.get("first_sweep", {})
    print(f"  {sweep.get('description', '')}")
    for mid in sweep.get("models", []):
        print(f"    * {mid}")
    print("\n  Runners to A/B:")
    for rc in sweep.get("runners_to_compare", []):
        print(f"    {rc['runner']}: {', '.join(rc['models'])}")

    print("\n=== Tier A - agent-native 4B (priority) ===")
    for c in sorted(
        cfg.get("candidates_tier_a_agent_4b", []), key=lambda x: x.get("priority", 99)
    ):
        print(
            f"  P{c.get('priority')} {c['id']:<18} {c.get('hf', ''):<35} "
            f"TB:{c.get('tb_relevance', '?'):<6} {c.get('notes', '')[:40]}"
        )

    print("\n=== Tier B - MoE small (760M-3B active) ===")
    for c in sorted(
        cfg.get("candidates_tier_b_moe_small", []), key=lambda x: x.get("priority", 99)
    ):
        print(
            f"  P{c.get('priority')} {c['id']:<18} {c.get('params', ''):<22} "
            f"runner:{','.join(c.get('runner', []))[:20]}"
        )

    print(f"\nFull matrix: {CONFIG_DIR / 'local_model_bench_matrix.yaml'}")
    print(f"Runners:     {CONFIG_DIR / 'inference_runners.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
