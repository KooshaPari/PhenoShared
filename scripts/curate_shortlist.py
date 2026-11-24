"""Summarize the 2026-07-03 HF scrape into a curated shortlist for the
local loadout, grouped by tier (T0..T5) per docs/specs/003.

Inputs:
  state/hf_scrape/2026-07-03/models.jsonl   (244 models, full breadth)
Outputs (stdout):
  one row per curated model with: tier, params_b, vram_estimate_gb
  for the FP8/BF16/AWQ variants, plus a one-line summary.
"""

import json
from collections import defaultdict

MODELS = "C:/Users/koosh/pheno-harness/state/hf_scrape/2026-07-03/models.jsonl"


# vRAM rough estimate (GB): params_B * dtype_bytes + 20% activation/KV headroom
#  dtype_bytes: fp32=4, bf16=2, fp16=2, fp8=1, int8=1, int4=0.5
def vram_gb(params_b, dtype_bytes, headroom=0.20, ctx_kv_gb=1.5):
    weights = params_b * dtype_bytes
    return round(weights * (1 + headroom) + ctx_kv_gb, 2)


# Curated shortlist: (tier, hf_id, expected_dtype, role_hint)
SHORTLIST = [
    # ---- T0: sub-1B drafter / classifier ----
    ("T0", "Qwen/Qwen3-0.6B", "bf16", "always-on drafter (EAGLE-2)"),
    ("T0", "google/gemma-3-1b-it-qat-q4_0-gguf", "q4_0", "alt drafter on llama.cpp"),
    # ---- T1: 1-3B primary local coder / fast subagent ----
    (
        "T1",
        "Qwen/Qwen2.5-Coder-3B-Instruct",
        "awq",
        "fast coder / subagent",
    ),  # placeholder; surface on next pass
    ("T1", "Qwen/Qwen2.5-Coder-1.5B-Instruct", "bf16", "tiny coding workhorse"),
    ("T1", "meta-llama/Llama-3.2-3B-Instruct", "bf16", "tiny chat generalist"),
    # ---- T2: 4-8B sweet-spot coder ----
    ("T2", "Qwen/Qwen3-8B", "bf16", "primary local coder"),
    (
        "T2",
        "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "fp8",
        "MoE 30B/3B coder (preferred T2 if MoE accepted)",
    ),
    ("T2", "Qwen/Qwen2.5-Coder-7B-Instruct", "bf16", "stable dense coding baseline"),
    ("T2", "meta-llama/Llama-3.1-8B-Instruct", "bf16", "generalist 8B"),
    ("T2", "microsoft/Phi-3.5-mini-instruct", "bf16", "long-context 128K alt"),
    # ---- T3: 12-15B bigger coder (AWQ to fit 24 GB) ----
    ("T3", "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", "awq", "AWQ-INT4 14B coder"),
    ("T3", "Qwen/Qwen3-14B-AWQ", "awq", "AWQ-INT4 14B generalist"),
    # ---- T4: 27-34B very large coder (AWQ / FP8 only) ----
    ("T4", "Qwen/Qwen3-32B", "awq", "AWQ-INT4 32B generalist"),
    ("T4", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ", "awq", "AWQ-INT4 32B coder"),
    ("T4", "Qwen/Qwen2.5-32B-Instruct-AWQ", "awq", "AWQ-INT4 32B generalist"),
    ("T4", "google/gemma-2-27b-it", "awq", "AWQ-INT4 27B alt"),
    ("T4", "allenai/Olmo-3.1-32B-Instruct", "awq", "open 32B"),
    # ---- T5: MoE in the 30-35B total band ----
    (
        "T5",
        "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8",
        "fp8",
        "FP8 30B/3B MoE coder (best fit 3090 Ti)",
    ),
    ("T5", "Qwen/Qwen3-30B-A3B-Instruct-2507", "fp8", "FP8 30B/3B MoE generalist"),
    ("T5", "zai-org/GLM-4.7-Flash", "bf16", "MoE-flash 31B"),
    ("T5", "inclusionAI/LLaDA2.0-mini", "bf16", "16B MoE-style (diffusion-flavored)"),
    ("T5", "allenai/OLMoE-1B-7B-0125", "bf16", "open 6.9B/1B MoE"),
]

DTYPE_BYTES = {
    "fp32": 4,
    "bf16": 2,
    "fp16": 2,
    "fp8": 1,
    "awq": 0.5,
    "q4_0": 0.5,
    "int8": 1,
    "int4": 0.5,
}


def main() -> None:
    with open(MODELS, encoding="utf-8") as f:
        records = {
            json.loads(line)["id"]: json.loads(line) for line in f if line.strip()
        }
    print(f"# Loaded {len(records)} records from {MODELS}\n")
    header = "Tier  HF-ID                                       Params(B)  DType  vRAM(GB)  Notes"
    print(header)
    print("-" * len(header))
    for tier, hf_id, dtype, role in SHORTLIST:
        rec = records.get(hf_id)
        if rec is None:
            params_b = None
            note = f"NOT IN SCRAPE ({role})"
        else:
            params_b = rec.get("params_b")
            note = role
        if params_b is None or dtype not in DTYPE_BYTES:
            vram = "n/a"
        else:
            vram = str(vram_gb(params_b, DTYPE_BYTES[dtype]))
        params_s = f"{params_b:>7.2f}" if params_b else "  ------"
        print(f"{tier:<5} {hf_id:<45} {params_s}  {dtype:<6} {vram:<9} {note}")
    print()
    # group counts
    by_tier = defaultdict(int)
    for tier, *_ in SHORTLIST:
        by_tier[tier] += 1
    print("# Count per tier:", dict(by_tier))


if __name__ == "__main__":
    main()
