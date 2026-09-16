#!/usr/bin/env python3
"""MoE prep gate: REAP checkpoint check, RIY reminder, PTQ scheme validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR


def _load_policy() -> dict[str, Any]:
    return yaml.safe_load(
        (CONFIG_DIR / "moe_deploy_policy.yaml").read_text(encoding="utf-8")
    )


def _load_bench() -> dict[str, Any]:
    return yaml.safe_load(
        (CONFIG_DIR / "local_model_bench_matrix.yaml").read_text(encoding="utf-8")
    )


def _moe_candidates() -> list[dict]:
    bench = _load_bench()
    out = []
    for tier in ("candidates_tier_b_moe_small",):
        out.extend(bench.get(tier, []))
    return out


def cmd_check(model_id: str) -> int:
    pol = _load_policy()
    models = pol.get("models", {})
    rec = models.get(model_id)
    if not rec:
        # try bench id
        for c in _moe_candidates():
            if c["id"] == model_id:
                rec = {
                    "hf": c.get("hf"),
                    "reap_checkpoint": None,
                    "policy": "riy_then_ptq",
                }
                break
    if not rec:
        print(f"Unknown MoE model: {model_id}")
        return 1

    reap = rec.get("reap_checkpoint")
    policy = rec.get("policy", "riy_then_ptq")
    print(f"Model: {model_id}")
    print(f"  HF: {rec.get('hf')}")
    print(f"  REAP checkpoint: {reap or 'NONE'}")
    print(f"  Policy: {policy}")

    if not reap and policy != "prebuilt_reap_then_nvfp4":
        print("\n  ACTION REQUIRED: REAP-it-Yourself (RIY) before PTQ/TB2 eval")
        print("  See config/moe_deploy_policy.yaml -> reap_policy.riy_workflow")
        for step in pol.get("reap_policy", {}).get("riy_workflow", {}).get("steps", []):
            print(f"    - {step}")
        print("\n  Then PTQ: INT4 AWQ/GPTQ on 3090 Ti (NVFP4 = Blackwell only)")
    elif reap:
        print(f"\n  OK: use prebuilt REAP -> {reap}")
        print("  Optional: layer NVFP4 on Blackwell; on 3090 use INT4 AWQ")

    out = EVAL_RESULTS_DIR / "moe_prepare_status.json"
    status = {}
    if out.exists():
        status = json.loads(out.read_text(encoding="utf-8"))
    status[model_id] = {
        "reap_checkpoint": reap,
        "policy": policy,
        "riy_required": not bool(reap) and "prebuilt" not in policy,
        "ptq_3090": rec.get("ptq_3090") or rec.get("ptq_upgrade"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


def cmd_list() -> int:
    pol = _load_policy()
    print("MoE deploy policy (3090 Ti = INT4/AWQ; NVFP4 = Blackwell only)\n")
    print(f"{'ID':<22} {'REAP ckpt':<12} {'Policy'}")
    print("-" * 60)
    for mid, rec in pol.get("models", {}).items():
        reap = "yes" if rec.get("reap_checkpoint") else "RIY req"
        print(f"{mid:<22} {reap:<12} {rec.get('policy', '')}")
    return 0


def cmd_verify(model_id: str) -> int:
    status_path = EVAL_RESULTS_DIR / "moe_prepare_status.json"
    if not status_path.exists():
        print(
            "No moe_prepare_status.json — run: moe_prepare.py check --model", model_id
        )
        return 1
    st = json.loads(status_path.read_text(encoding="utf-8")).get(model_id)
    if not st:
        print(f"No status for {model_id}")
        return 1
    if st.get("riy_required") and not st.get("riy_profile_done"):
        print(f"BLOCKED: {model_id} needs RIY before TB2 eval")
        return 1
    print(f"OK to micro-eval {model_id} (ptq={st.get('ptq_3090')})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="MoE REAP + PTQ prep gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Check REAP availability; emit RIY requirement")
    c.add_argument("--model", required=True)

    sub.add_parser("list", help="List MoE models and REAP policy")

    v = sub.add_parser("verify", help="Gate before TB2 micro-eval")
    v.add_argument("--model", required=True)

    riy = sub.add_parser(
        "riy-profile", help="Print RIY workflow (vllm-riy manual step)"
    )
    riy.add_argument("--model", required=True)

    ptq = sub.add_parser("ptq", help="Print PTQ command template for 3090")
    ptq.add_argument("--model", required=True)
    ptq.add_argument(
        "--scheme", default="int4_awq", choices=["int4_awq", "int4_gptq", "q4_k_m_gguf"]
    )

    args = p.parse_args()
    if args.cmd == "check":
        return cmd_check(args.model)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "verify":
        return cmd_verify(args.model)
    if args.cmd == "riy-profile":
        return cmd_check(args.model)
    if args.cmd == "ptq":
        pol = _load_policy()
        rec = pol.get("models", {}).get(args.model, {})
        hf = rec.get("hf", "HF_MODEL")
        print(f"# After RIY profile locked for {args.model}")
        print(f"# llm-compressor / AWQ on {hf}")
        print("python -m llmcompressor.entrypoints.oneshot \\")
        print(f"  --model {hf} \\")
        print(f"  --scheme {args.scheme} \\")
        print("  --dataset ultrachat_200k --num-samples 64")
        print("export LLMCOMPRESSOR_MOE_CALIBRATE_ALL_EXPERTS=1")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
