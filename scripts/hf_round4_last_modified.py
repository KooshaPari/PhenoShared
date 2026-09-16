#!/usr/bin/env python3
"""Last fix: probe with NO expand to capture last_modified + likes + downloads.
Plus a probe for protoLabsAI/Ornith-1.0-9B-MTP-GGUF (canonical MTP derivative).

Pre-MARCH-2026 deep-keep rule (the user's recency cutoff) means we still
need to surface dates for the 2 flagged models so we know exactly how old.
"""

import datetime as dt
import json
import os
from typing import Any

from huggingface_hub import HfApi

api = HfApi()
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
date = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
out: dict[str, Any] = {
    "date": date,
    "recency_cutoff_utc": "2026-03-01T00:00:00+00:00",
    "probes": [],
}


def probe_no_expand(repo_id):
    rec = {"hf_repo": repo_id}
    try:
        info = api.model_info(repo_id)  # NO expand -> get real last_modified
        rec["ok"] = True
        rec["last_modified"] = (
            info.last_modified.isoformat() if info.last_modified else None
        )
        rec["created_at"] = info.created_at.isoformat() if info.created_at else None
        rec["downloads"] = info.downloads
        rec["likes"] = info.likes
        rec["gated"] = info.gated
        rec["pipeline_tag"] = info.pipeline_tag
        rec["tags_count"] = len(info.tags or [])
        sibs = sorted(
            (
                {"rfilename": s.rfilename, "size": s.size or 0}
                for s in (info.siblings or [])
            ),
            key=lambda d: d["size"],
            reverse=True,
        )
        rec["siblings_count"] = len(sibs)
        rec["top_files"] = sibs[:8]
        rec["tags"] = (info.tags or [])[:30]
    except Exception as e:
        rec["ok"] = False
        rec["err"] = f"{type(e).__name__}: {str(e)[:200]}"
    return rec


for repo in [
    "Qwen/Qwen3.5-0.8B",
    "LiquidAI/LFM2.5-8B-A1B",
    "deepreinforce-ai/Ornith-1.0-9B",
    "deepreinforce-ai/Ornith-1.0-9B-GGUF",
    "protoLabsAI/Ornith-1.0-9B-MTP-GGUF",
    "ibm-granite/granite-4.1-8b",
    "ibm-granite/granite-4.0-h-micro",
    "LiquidAI/LFM2-24B-A2B",
    "arcee-ai/Trinity-Mini",
    "poolside/Laguna-XS-2.1",
    "tencent/HY3-Preview",
]:
    out["probes"].append(probe_no_expand(repo))

# Apply recency rule and emit recency_dlq
dlq = []
for p in out["probes"]:
    if not p.get("ok"):
        continue
    lm = p.get("last_modified")
    try:
        lm_dt = dt.datetime.fromisoformat(lm.replace("Z", "+00:00")) if lm else None
    except Exception:
        lm_dt = None
    cutoff = dt.datetime.fromisoformat(out["recency_cutoff_utc"])
    if lm_dt is None:
        recency = "unknown_lm"
    elif lm_dt >= cutoff:
        recency = "ok"
    else:
        recency = "pre_march_2026"
    p["recency_status"] = recency
    if recency != "ok":
        dlq.append(
            {
                "hf_repo": p["hf_repo"],
                "last_modified": lm,
                "recency_status": recency,
                "pipeline_tag": p.get("pipeline_tag"),
            }
        )
out["recency_dlq"] = dlq

OUT_DIR = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-04"
with open(
    os.path.join(OUT_DIR, "last_modified_probes.json"), "w", encoding="utf-8"
) as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)
print(
    f"OK wrote last_modified_probes.json  probes={len(out['probes'])}  dlq={len(dlq)}"
)
for p in out["probes"]:
    if p.get("ok"):
        lm = (p.get("last_modified") or "?")[:10]
        dl = p.get("downloads") if p.get("downloads") is not None else "?"
        lk = p.get("likes") if p.get("likes") is not None else "?"
        rec = p.get("recency_status", "?")
        sibs = p.get("siblings_count", 0)
        print(
            f"  {rec:8s} {p['hf_repo']:50s} lm={lm:10s} dl={dl:>10} lk={lk:>4} sib={sibs}"
        )
    else:
        print(f"  ERROR   {p['hf_repo']:50s} {p.get('err', '')}")
