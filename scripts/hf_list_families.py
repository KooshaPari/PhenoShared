"""FAST family listing probe — list_models(search=...) only, no model_info.

Run after _tiny_probe proved search-API works in ~1s. Goal: ~30 family queries,
listing only (no safetensors fetch), produce targeted_families.json with
current-generation model IDs for the matrix doc.
"""

import json
import os
import time

from huggingface_hub import HfApi

OUT = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-03\targeted_families.json"
LOG = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-03\targeted_families.log"

FAMILIES = [
    "gemma-4",
    "gemma-3",
    "gemma-2",
    "Qwen3",
    "Qwen3-Coder",
    "Qwen2.5-Coder",
    "Qwen2.5",
    "LFM2",
    "LFM2.5",
    "Liquid",
    "Granite-3",
    "Granite-4",
    "granite-3b",
    "granite-4b",
    "ibm-granite",
    "Nanbeige",
    "nanbeige",
    "zaya",
    "Zaya",
    "Ornith",
    "kimi-linear",
    "Kimi-K2",
    "Kimi",
    "ministral",
    "codestral",
    "devstral",
    "mistral-small",
    "Mixtral",
    "Phi-4",
    "Phi-3.5",
    "Phi-tiny-MoE",
    "OLMo-3",
    "OLMoE",
    "OLMo-2",
    "DeepSeek-V3",
    "DeepSeek-V4",
    "DeepSeek-R1",
    "Llama-3.1",
    "Llama-3.2",
    "Llama-3.3",
    "CodeLlama",
    "Yi-1.5",
    "Baichuan2",
    "LLaDA",
    "LLaMA",
    "inclusionAI",
    "Qwen3-Next",
    "Qwen3.5",
    "Qwen3-Max",
    "MiniMax",
    "minimax",
    "minimax-m3",
    "Pythia",
    "BLOOM",
    "Falcon",
    "Gemma-3n",
    "gemma-4n",
    "gemma-3-4b",
    "gemma-3-12b",
]


def main() -> None:
    api = HfApi()
    out = {
        "date": "2026-07-04",
        "method": "list_models(search=..., sort=last_modified)",
        "limit_per_family": 15,
        "families": {},
    }
    logs = []
    t0 = time.time()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for fam in FAMILIES:
        try:
            it = api.list_models(search=fam, limit=15, sort="last_modified")
            cnt = 0
            recs = []
            for m in it:
                cnt += 1
                recs.append(
                    {
                        "id": m.id,
                        "last_modified": str(m.last_modified)
                        if m.last_modified
                        else None,
                        "downloads": m.downloads,
                        "gated": getattr(m, "gated", None),
                    }
                )
            out["families"][fam] = recs
            logs.append(
                f"{fam:24} hits={cnt:3} first={recs[0]['id'] if recs else 'NONE'}"
            )
        except Exception as e:
            out["families"][fam] = [{"err": type(e).__name__, "msg": str(e)[:120]}]
            logs.append(f"{fam:24} ERR={type(e).__name__}")
    out["elapsed_sec"] = round(time.time() - t0, 2)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    print(f"wrote {OUT}  elapsed={out['elapsed_sec']}s")


if __name__ == "__main__":
    main()
