"""Targeted HF family probe — uses sort='last_modified' for currency, NOT popularity.

This is the corrected ranking signal that addresses the user's 'you're still pulling
obsolete models' feedback. Result is written to
state/hf_scrape/2026-07-03/targeted_families.json so the docs can cite it.
"""

import json
import os

from huggingface_hub import HfApi

OUT = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-03\targeted_families.json"

QUERIES = [
    ("gemma-4", [("google", 80)]),
    ("gemma-3", [("google", 120)]),
    ("qwen3", [("Qwen", 120)]),
    ("qwen3-coder", [("Qwen", 120)]),
    ("lfm", [("LiquidAI", 120)]),
    ("granite", [("ibm-granite", 120), ("ibm", 80)]),
    ("nanbeige", [("Nanbeige", 120)]),
    ("zaya", [("zaya-ai", 120), ("Zaya", 60)]),
    ("ornith", [("Ornith", 80)]),
    ("kimi-linear", [("moonshotai", 60)]),
    ("kimi-k2", [("moonshotai", 80)]),
    ("mixtral", [("mistralai", 80), ("NousResearch", 80)]),
    ("phi-tiny-moe", [("microsoft", 40)]),
    ("phi-4", [("microsoft", 80)]),
    ("olmo-3", [("allenai", 120)]),
    ("olmoe", [("allenai", 80)]),
    ("deepseek-v3", [("deepseek-ai", 60)]),
    ("deepseek-v4", [("deepseek-ai", 60)]),
    ("gemma-4-rotorquant", [("majentik", 40)]),
    ("inclusionai", [("inclusionAI", 120)]),
    ("lada", [("inclusionAI", 80)]),
    ("llama-3.1", [("meta-llama", 80)]),
    ("llama-3.2", [("meta-llama", 80)]),
    ("llama-3.3", [("meta-llama", 80)]),
    ("codestral", [("mistralai", 80)]),
    ("devstral", [("mistralai", 80)]),
    ("ministral", [("mistralai", 80)]),
    ("mistral-small", [("mistralai", 80)]),
    ("gemini-nano-hf", [("google", 80)]),
    ("pali", [("google", 60)]),
    ("starcoder", [("bigcode", 60)]),
    ("yi-1.5", [("01-ai", 80)]),
    ("baichuan", [("baichuan-inc", 80)]),
]


def safe_get_params_b(info):
    st = getattr(info, "safetensors", None)
    if isinstance(st, dict):
        params = st.get("parameters")
        if isinstance(params, dict) and params:
            total = sum(v for v in params.values() if isinstance(v, (int, float)))
            return round(total / 1e9, 3)
    return None


def main() -> None:
    api = HfApi()
    out = {
        "date": "2026-07-03 (corrective probe)",
        "sort": "last_modified desc",
        "token_set": False,
        "families": {},
    }
    errs = []
    seen_ids = set()

    for nick, authors in QUERIES:
        family_records = []
        for author, lim in authors:
            try:
                # NOTE: direction=-1 invalid in this version; sort=last_modified
                # alone is descending (newest first).
                it = api.list_models(author=author, limit=lim, sort="last_modified")
                for m in it:
                    if nick not in m.id.lower():
                        continue
                    if m.id in seen_ids:
                        continue
                    seen_ids.add(m.id)
                    try:
                        info = api.model_info(m.id, expand=["safetensors"])
                        params_b = safe_get_params_b(info)
                        lm = getattr(info, "last_modified", None)
                        family_records.append(
                            {
                                "id": m.id,
                                "params_b": params_b,
                                "last_modified": str(lm) if lm else None,
                                "gated": getattr(info, "gated", None),
                                "pipeline_tag": m.pipeline_tag,
                            }
                        )
                    except Exception as e:
                        errs.append({"q": nick, "id": m.id, "err": type(e).__name__})
            except Exception as e:
                errs.append({"q": nick, "author": author, "err": type(e).__name__})
                # ALSO probe via search=nick so cross-author discoveries land
                try:
                    it2 = api.list_models(search=nick, limit=60, sort="last_modified")
                    for m in it2:
                        if m.id in seen_ids:
                            continue
                        seen_ids.add(m.id)
                        try:
                            info = api.model_info(m.id, expand=["safetensors"])
                            params_b = safe_get_params_b(info)
                            lm = getattr(info, "last_modified", None)
                            family_records.append(
                                {
                                    "id": m.id,
                                    "params_b": params_b,
                                    "last_modified": str(lm) if lm else None,
                                    "gated": getattr(info, "gated", None),
                                    "pipeline_tag": m.pipeline_tag,
                                    "via": "search",
                                }
                            )
                        except Exception as e:
                            errs.append(
                                {"q": nick, "id": m.id, "err": type(e).__name__}
                            )
                except Exception as e:
                    errs.append({"q": nick, "via": "search", "err": type(e).__name__})
        family_records.sort(key=lambda r: r.get("last_modified") or "", reverse=True)
        out["families"][nick] = family_records[:25]

    out["errors_count"] = len(errs)
    out["errors_sample"] = errs[:8]
    out["total_unique_ids_seen"] = len(seen_ids)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
    print(f"wrote {OUT}")
    print(
        f"families probed: {len(QUERIES)}  unique ids: {len(seen_ids)}  errors: {len(errs)}"
    )
    for nick, recs in out["families"].items():
        print(
            f"  {nick:24} hit={len(recs):4}  e.g. {recs[0]['id'] if recs else 'NONE'}"
        )


if __name__ == "__main__":
    main()
