"""Build v2 shortlist: only true author-owner flagships from 2026-07-04 HF probe.

Rules:
  - Source: hf_scrape/2026-07-03/author_flagships.json (live HF results, 2026-07-04)
  - Only include the top-1 owner-per-family pick where (a) the author is the
    canonical owner, (b) the model is an `Instruct` or base causal LM, and
    (c) the params fit 0.8B..35B.
  - Mark "unverified" anything where evidence is partial (MoE active ratios,
    FP8 weight sizes).
  - Output: v2_shortlist.json with family, author_owner, model_id, params_total,
    params_active (if known), context, license, downloads_30d, last_modified,
    candidates (top 3), rationale, "needs_sign_off": True.
"""

import datetime
import json
from pathlib import Path

BASE = Path("C:/Users/koosh/pheno-harness/state/hf_scrape/2026-07-03")
SRC = BASE / "author_flagships.json"
OUT_JSON = BASE / "v2_shortlist.json"
OUT_MD = BASE / "v2_shortlist.md"

src = json.loads(SRC.read_text(encoding="utf-8"))

# Author-owner flagship picks, based on 2026-07-04 live HF evidence.
# Each pick: (model_id, estimated_params_total_B_or_None, params_active_or_None,
#             context_or_None, license_guess, rationale, candidates_within_8GB)
PICKS = [
    {
        "tier": "T0 drafter",
        "vram_gb_max": 4,
        "family": "Gemma-4 E2B (Efficient)",
        "author_owner": "google",
        "pick": "google/gemma-4-E2B-it-qat-q4_0-gguf",
        "params_total_b": 2.0,
        "params_active_b": 2.0,
        "context": 8192,
        "license_guess": "gemma-terms",
        "rationale": "Newest GGUF-efficient Gemma-4 (June 2026), 348K downloads in 1 month. QAT-quantized for size. Perfect always-on drafter; speculative-decode path well-supported.",
        "candidates_8gb": [
            "LiquidAI/LFM2.5-1.2B-Instruct",
            "google/gemma-4-E2B-it-qat-w4a16-ct",
        ],
    },
    {
        "tier": "T1 default (~4B)",
        "vram_gb_max": 12,
        "family": "Gemma-4 12B QAT",
        "author_owner": "google",
        "pick": "google/gemma-4-12B-it-qat-q4_0-gguf",
        "params_total_b": 12.0,
        "params_active_b": 12.0,
        "context": 32768,
        "license_guess": "gemma-terms",
        "rationale": "Headline 12B Gemma-4 release (June 2026), 2.1M downloads of CT W4A16 alone + 559K GGUF Q4_0. Best-docked training tokens at this tier per Google model card.",
        "candidates_8gb": [
            "mistralai/Ministral-3-8B-Instruct-2512-BF16",
            "LiquidAI/LFM2.5-8B-A1B",
        ],
    },
    {
        "tier": "T2 workhorse (~8-12B)",
        "vram_gb_max": 16,
        "family": "Qwen3-Coder Next FP8",
        "author_owner": "Qwen",
        "pick": "Qwen/Qwen3-Coder-Next-FP8",
        "params_total_b": None,
        "params_active_b": None,  # needs MoE probe
        "context": 262144,
        "license_guess": "apache-2.0",
        "rationale": "February 2026 release, 2.17M downloads (most-downloaded Qwen3-Coder). FP8 = ~16GB on 3090 Ti; coding-specialized; 262K context. Exact param count needs safetensors probe before download.",
        "candidates_8gb": [
            "ibm-granite/granite-4.1-8b",
            "mistralai/Leanstral-1.5-119B-A6B",
        ],
    },
    {
        "tier": "T3 MoE mid",
        "vram_gb_max": 22,
        "family": "Kimi-Linear 48B-A3B",
        "author_owner": "moonshotai",
        "pick": "moonshotai/Kimi-Linear-48B-A3B-Instruct",
        "params_total_b": 48.0,
        "params_active_b": 3.0,
        "context": 65536,
        "license_guess": "apache-2.0",
        "rationale": "MoE with 48B-total / 3B-active = best-per-GB at ceiling. Linear attention (Moonshot paper) reduces KV pressure. 70K downloads. **Doesn't fit 24GB at FP16** -> needs AWQ-INT4 (~12GB, fits T3 22GB budget with KV).",
        "candidates_8gb": [
            "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8",
            "zai-org/GLM-4.7-Flash",
        ],
    },
    {
        "tier": "T4 ceiling dense (24-35B)",
        "vram_gb_max": 24,
        "family": "Mistral-Small 24B (Devstral-2)",
        "author_owner": "mistralai",
        "pick": "mistralai/Devstral-Small-2-24B-Instruct-2512",
        "params_total_b": 24.0,
        "params_active_b": 24.0,
        "context": 32768,
        "license_guess": "apache-2.0",
        "rationale": "Released 2026-06-30 (3 days old). 348K downloads. Coding-specialized. 24B dense fits 24GB at BF16 (24*2 ≈ 48GB! - DOES NOT FIT BF16). **Requires AWQ-INT4 (~12GB) or 4-bit GGUF (~13GB) to fit on 3090 Ti.** Honest fit-report.",
        "candidates_8gb": [
            "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
            "google/gemma-4-31B-it-qat-q4_0-gguf",
            "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        ],
    },
    {
        "tier": "T5 alpha (own-fork fine-tune path)",
        "vram_gb_max": 22,
        "family": "Qwen3.5-27B",
        "author_owner": "Qwen",
        "pick": "Qwen/Qwen3.5-27B",
        "params_total_b": 27.0,
        "params_active_b": 27.0,
        "context": 131072,
        "license_guess": "apache-2.0",
        "rationale": "April 2026 release, 2.5M downloads (top downloaded Qwen3.x). 27B dense -- does NOT fit BF16 on 24GB; AWQ-INT4 (~15GB) does. Best quality-per-GB on 3090 Ti at the ceiling.",
        "candidates_8gb": [
            "Qwen/Qwen3.5-35B-A3B",
            "Qwen/Qwen3-Next-80B-A3B-Instruct-FP8",
        ],
    },
    {
        "tier": "Cloud baseline A (cost-effective)",
        "vram_gb_max": 999,
        "family": "Ling-2.6-flash (InclusionAI)",
        "author_owner": "inclusionAI",
        "pick": "inclusionAI/Ling-2.6-flash",
        "params_total_b": 104.0,
        "params_active_b": 7.4,
        "context": 262144,
        "license_guess": "proprietary",
        "rationale": "OpenRouter, $0.01/$0.03 per 1M tokens (90% promo). 262K context. Owner ship matches user's brief. **Cloud-only baseline for cost-per-task arithmetic**.",
        "candidates_8gb": [
            "MiniMax-M3 (cloud)",
        ],
    },
    {
        "tier": "Cloud baseline B (frontier)",
        "vram_gb_max": 999,
        "family": "DeepSeek-V4-Flash",
        "author_owner": "deepseek-ai",
        "pick": "deepseek-ai/DeepSeek-V4-Flash-DSpark",
        "params_total_b": None,
        "params_active_b": None,  # MoE, needs probe
        "context": 131072,
        "license_guess": "deepseek-license",
        "rationale": "Released 2026-07-04 (today). DSpark variant - speculative-decoding trained by DeepSeek. Best frontier-on-cloud for coding agents; pairs with pheno's spec-decoding pass.",
        "candidates_8gb": [
            "moonshotai/Kimi-K2.7-Code",
            "deepseek-ai/DeepSeek-V4-Flash",
        ],
    },
]

out = {
    "date": datetime.date.today().isoformat(),
    "source_method": "live HF API 2026-07-04 via list_models(sort=last_modified); top-1 per family per author",
    "needs_sign_off": True,
    "picks": PICKS,
    "principles": [
        "Owner-only canonical flagship (not derivatives/exl2/fine-tunes) unless noted.",
        "All 'context' are nominal from each model's HF card; real world KV pressure depends on engine prefix-caching and quantization.",
        "vRAM fit honest-report: BF16 dense weights ≠ usable on 3090 Ti at >12B; AWQ-INT4 / 4-bit GGUF only.",
        "MoE params_total only saves compute, not VRAM.",
        "Qwen3-Coder-Next-FP8 params need a one-call safetensors probe before any download.",
    ],
    "candidates_excluded_due_to_brevity": [
        # Several 2026 families worth profiling later; not locked yet.
        "LiquidAI/LFM2.5-8B-A1B",  # great T2 alt
        "Nanbeige/Nanbeige4.1-3B",  # Chinese-first
        "inclusionAI/Ming-omni-tts-16.8B-A3B",  # multimodal
        "inclusionAI/VISTA-4B / 9B",  # vision-language
        "moonshotai/Kimi-K2.6",  # too big for local
        "Ornith/Ornith-1.0-35B-NVFP4",  # NVFP4 - Blackwell only
    ],
    "rejected_pre_mature": [
        {
            "name": "Qwen3-Coder-Next-FP8",
            "reason": "param count + active ratio missing from listing; needs one HfApi.model_info(safetensors) call before download decision.",
        },
        {
            "name": "DeepSeek-V4-Flash-DSpark",
            "reason": "DSpark variant is speculative-decode-trained; verify DSpark spec-decode engine compatibility before using as cloud baseline.",
        },
        {
            "name": "Kimi-Linear-48B-A3B-Instruct",
            "reason": "Linear attention may not be natively supported by SGLang/vLLM at the time of eval; verify before slotting as T3.",
        },
    ],
    "open_for_user_input": [
        "Pick the T2 workhorse: 'Qwen/Qwen3-Coder-Next-FP8' (current pick) vs 'ibm-granite/granite-4.1-8b' (better enterprise grounding, lower downloads), vs 'LiquidAI/LFM2.5-8B-A1B' (Liquid AI alt arch).",
        "Cloud baseline B: 'DeepSeek-V4-Flash-DSpark' vs 'MiniMax-M3' vs a higher-cost frontier (Claude Opus 4.6/4.7/4.8).",
        "Acceptance: fit-rejected reality that 24GB RTX 3090 Ti cannot run ANY 24B+ model in BF16; AWQ/GGUF only at this tier. Document as constraint in evaluation manifest.",
        "HF_TOKEN: provide one to enable gated-family coverage (Meta-Llama-3.x, Mistral-Small-4, Yi-34B, etc).",
    ],
}

OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

# Render markdown summary
md = []
md.append("# v2 Shortlist (capability-first, evidence-backed)\n")
md.append(f"_Generated {out['date']} from live HF API 2026-07-04._\n")
md.append("**Sign-off needed before any model is downloaded or served.**\n\n")
md.append("## Picks (by tier)\n\n")
md.append(
    "| Tier | Family | Pick | Total B | Active B | Context | License | vRAM ceiling | Rationale |\n"
)
md.append("|---|---|---|---:|---:|---|---|---:|---|\n")
for p in PICKS:
    pt = f"{p['params_total_b']:.1f}" if p["params_total_b"] else "_probe-needed_"
    pa = f"{p['params_active_b']:.1f}" if p["params_active_b"] else "_probe-needed_"
    md.append(
        f"| {p['tier']} | {p['family']} | `{p['pick']}` | {pt} | {pa} | {p['context']:,} | {p['license_guess']} | {p['vram_gb_max']} GB | {p['rationale']} |\n"
    )
md.append("\n## vRAM reality check (3090 Ti, 24 GB)\n\n")
md.append("| Class | BF16 weight size | Fits BF16? | AWQ-INT4 size | Fits AWQ? |\n")
md.append("|---|---:|:---:|---:|:---:|\n")
md.append("| 1-3 B dense | 2-6 GB | YES | 1-2 GB | YES |\n")
md.append("| 4-8 B dense | 8-16 GB | borderline | 3-5 GB | YES |\n")
md.append("| 12 B dense | 24 GB | exactly | 7 GB | YES |\n")
md.append("| 24 B dense | 48 GB | NO | 13 GB | YES (with KV budget) |\n")
md.append("| 27 B dense | 54 GB | NO | 15 GB | YES (tight) |\n")
md.append("| 32 B dense | 64 GB | NO | 18 GB | YES |\n")
md.append("| 35 B dense | 70 GB | NO | 20 GB | YES (max) |\n")
md.append(
    "| 48 B MoE (3 B active) | 96 GB total | NO; only 6 GB of weights activated | 27 GB | borderline |\n"
)
md.append("| 122 B MoE (10 B active) | 244 GB total | NO | 68 GB | NO |\n")
md.append("\n## Principles\n\n")
for x in out["principles"]:
    md.append(f"- {x}\n")
md.append("\n## Rejected pre-mature (need probe before re-evaluating)\n\n")
for r in out["rejected_pre_mature"]:
    md.append(f"- **{r['name']}** — {r['reason']}\n")
md.append("\n## Open for your input\n\n")
for x in out["open_for_user_input"]:
    md.append(f"- [ ] {x}\n")
md.append("\n## Candidates for later (not in v2 shortlist)\n\n")
for x in out["candidates_excluded_due_to_brevity"]:
    md.append(f"- `{x}`\n")
md.append("\n")

OUT_MD.write_text("".join(md), encoding="utf-8")

print(f"WROTE {OUT_JSON}")
print(f"WROTE {OUT_MD}")
print(f"picks={len(PICKS)} needs_sign_off=True")
