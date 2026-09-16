#!/usr/bin/env python3
"""Fix expand list and retry canonical probes for Ornith base + Qwen3.5-0.8B canonical."""

import datetime as dt
import json
import os
from typing import Any

from huggingface_hub import HfApi
from huggingface_hub.errors import RepositoryNotFoundError

api = HfApi()
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
date = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
out: dict[str, Any] = {"date": date, "probes": []}


def probe(repo_id):
    rec = {"hf_repo": repo_id}
    try:
        info = api.model_info(repo_id, expand=["safetensors", "cardData", "config"])
        rec["ok"] = True
        rec["last_modified"] = (
            info.last_modified.isoformat() if info.last_modified else None
        )
        rec["created_at"] = info.created_at.isoformat() if info.created_at else None
        rec["downloads"] = info.downloads
        rec["likes"] = info.likes
        rec["gated"] = info.gated
        rec["pipeline_tag"] = info.pipeline_tag
        rec["siblings_count"] = len(info.siblings or [])
        st = getattr(info, "safetensors", None) or {}
        params = st.get("parameters", {}) if isinstance(st, dict) else {}
        rec["params_b"] = round(sum(params.values()) / 1e9, 4) if params else None
        rec["dtype_breakdown"] = params
        sibs = sorted(
            (
                {"rfilename": s.rfilename, "size": s.size or 0}
                for s in (info.siblings or [])
            ),
            key=lambda d: d["size"],
            reverse=True,
        )
        rec["top_files"] = sibs[:10]
        # Card-data snapshot (truncated)
        cd = getattr(info, "card_data", None) or {}
        if isinstance(cd, dict):
            for k in (
                "license",
                "language",
                "tags",
                "pipeline_tag",
                "base_model",
                "model_name",
                "model_type",
                "tags",
            ):
                pass
            rec["card_data_keys"] = sorted(cd.keys())[:30]
    except RepositoryNotFoundError:
        rec["ok"] = False
        rec["err"] = "404 RepositoryNotFound"
    except Exception as e:
        rec["ok"] = False
        rec["err"] = f"{type(e).__name__}: {str(e)[:200]}"
    return rec


for repo in [
    "deepreinforce-ai/Ornith-1.0-9B",
    "Qwen/Qwen3.5-0.8B",
    "LiquidAI/LFM2.5-8B-A1B",
    "protoLabsAI/Ornith-1.0-9B-MTP-GGUF",
    "ibm-granite/granite-4.0-h-micro",
    "ibm-granite/granite-4.1-8b",
    "LiquidAI/LFM2-24B-A2B",
    "arcee-ai/Trinity-Mini",
    "poolside/Laguna-XS-2.1",
    "tencent/HY3-Preview",
    # Ling — proprietary, no HF mirror
]:
    out["probes"].append(probe(repo))

# search for Ornith canonical (top by downloads, then by lm)
try:
    it = api.list_models(search="Ornith-1.0-9B", sort="downloads", limit=15)
    out["ornith_top_dl"] = [
        {
            "id": m.id,
            "downloads": m.downloads,
            "lm": m.last_modified.isoformat() if m.last_modified else None,
        }
        for m in it
    ]
except Exception as e:
    out["ornith_search_err"] = f"{type(e).__name__}: {e}"

# Also check Qwen3.5-0.8B siblings to see if MM-DL behavior or pure text
try:
    qwen_info = api.model_info("Qwen/Qwen3.5-0.8B", expand=["siblings", "cardData"])
    out["qwen3.5_0.8b_card_key_fields"] = {
        "pipeline_tag": qwen_info.pipeline_tag,
        "tags": (qwen_info.tags or [])[:20],
        "card_data_subset_keys": sorted(
            (qwen_info.card_data or {}).keys()
        )[:20],
    }
except Exception as e:
    out["qwen3.5_0.8b_carddata_err"] = f"{type(e).__name__}: {e}"

OUT_DIR = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-04"
with open(
    os.path.join(OUT_DIR, "canonical_followups_v2.json"), "w", encoding="utf-8"
) as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)
print(
    f"OK wrote canonical_followups_v2.json  probes_ok={sum(1 for p in out['probes'] if p.get('ok'))}/{len(out['probes'])}"
)
for p in out["probes"]:
    if p.get("ok"):
        params = f"{p.get('params_b', '?')}B"
        lm = (p.get("last_modified") or "?")[:10]
        print(f"  + {p['hf_repo']:50s} {params:8s} lm={lm}")
    else:
        print(f"  x {p['hf_repo']:50s} {p.get('err', '')}")
