"""Author-scoped probe — get the canonical model IDs by author.

Only lists; no model_info. Uses recent edits per organization to surface the
current generation flagship from each lab.
"""

import json
import os
import time

from huggingface_hub import HfApi

OUT = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-03\author_flagships.json"

ORGS = {
    "google": [
        ("gemma-4", 25),
        ("gemma-3", 25),
        ("codegemma", 25),
    ],
    "Qwen": [
        ("Qwen3", 25),
        ("Qwen3-Coder", 30),
        ("Qwen2.5-Coder", 25),
        ("Qwen3-Next", 25),
    ],
    "mistralai": [
        ("Ministral", 20),
        ("Mistral-Small", 20),
        ("Devstral", 20),
        ("Codestral", 20),
        ("Mistral", 15),
    ],
    "LiquidAI": [
        ("LFM2", 20),
        ("LFM2.5", 20),
    ],
    "ibm-granite": [
        ("granite", 30),
    ],
    "allenai": [
        ("OLMo-3", 15),
        ("OLMoE", 15),
    ],
    "moonshotai": [
        ("Kimi-Linear", 25),
        ("Kimi-K2", 25),
    ],
    "microsoft": [
        ("Phi-4", 15),
        ("Phi", 15),
    ],
    "deepseek-ai": [
        ("DeepSeek", 25),
    ],
    "inclusionAI": [
        ("inclusionAI", 30),
        ("LLaDA", 20),
    ],
    "Zaya": [
        ("Zaya", 15),
    ],
    "Nanbeige": [
        ("Nanbeige", 15),
    ],
}


def main() -> None:
    api = HfApi()
    out = {
        "date": "2026-07-04",
        "method": "list_models(author=..., search=..., sort=last_modified)",
        "orgs": {},
    }
    t0 = time.time()
    for org, queries in ORGS.items():
        out["orgs"][org] = {}
        for q, lim in queries:
            recs = []
            try:
                it = api.list_models(
                    author=org, search=q, limit=lim, sort="last_modified"
                )
                for m in it:
                    recs.append(
                        {
                            "id": m.id,
                            "last_modified": str(m.last_modified)
                            if m.last_modified
                            else None,
                            "downloads": m.downloads,
                        }
                    )
                out["orgs"][org][q] = recs
            except Exception as e:
                out["orgs"][org][q] = [{"err": type(e).__name__, "msg": str(e)[:120]}]
    out["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
    # Compact summary
    summaries = []
    for org, qd in out["orgs"].items():
        for q, recs in qd.items():
            if not recs:
                continue
            if isinstance(recs, list) and recs and isinstance(recs[0], dict):
                first = recs[0].get("id", "ERR")
                lastm = recs[0].get("last_modified", "?")
                n = len(recs)
                summaries.append(f"{org:14} {q:14} n={n:3} first={first:55} lm={lastm}")
            elif isinstance(recs, list) and recs and "err" in recs[0]:
                summaries.append(f"{org:14} {q:14} ERR={recs[0]['err']}")
    print(f"elapsed={out['elapsed_sec']}s")
    for s in summaries:
        print(s)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
