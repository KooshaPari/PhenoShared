#!/usr/bin/env python3
"""
Round-4 follow-up: probe Ornith canonical base + LFM2.5 official lineage + Qwen3.5-0.8B canonical.
Then print a frozen, summary-only manifest so no token / no body / no large field appears in stdout.
"""

import datetime as dt
import json
import os
from typing import Any

from huggingface_hub import HfApi
from huggingface_hub.errors import RepositoryNotFoundError, RevisionNotFoundError

api = HfApi()
date = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
out: dict[str, Any] = {
    "date": date,
    "token_present": bool(os.environ.get("HF_TOKEN")),
    "probes": [],
}

# Ensure cache_dir & no progress
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


# Helpers
def probe_repo(repo_id, expect_pipeline=None):
    rec = {"label": repo_id, "attempts": []}
    try:
        info = api.model_info(repo_id, expand=["config", "safetensors"])
        rec["hf_repo"] = repo_id
        rec["last_modified"] = (
            info.last_modified.isoformat() if info.last_modified else None
        )
        rec["created_at"] = info.created_at.isoformat() if info.created_at else None
        rec["downloads"] = info.downloads
        rec["likes"] = info.likes
        rec["gated"] = info.gated
        rec["pipeline_tag"] = info.pipeline_tag
        rec["tags_count"] = len(info.tags or [])
        rec["tags_sample"] = (info.tags or [])[:18]
        st = getattr(info, "safetensors", None)
        if isinstance(st, dict):
            params = st.get("parameters", {}) if "parameters" in st else st
            if isinstance(params, dict):
                rec["params_b"] = round(sum(params.values()) / 1e9, 4)
                rec["dtype_breakdown"] = dict(params.items())
        rec["files_count"] = len(info.siblings or [])
        # Top-N siblings by rfilename so we know what quant formats exist
        sibs = sorted(
            (
                {"rfilename": s.rfilename, "size": s.size or 0}
                for s in (info.siblings or [])
            ),
            key=lambda d: d["size"],
            reverse=True,
        )
        rec["top_files"] = sibs[:12]
        rec["ok"] = True
    except (RepositoryNotFoundError, RevisionNotFoundError) as e:
        rec["ok"] = False
        rec["err"] = f"404 {type(e).__name__}"
    except Exception as e:
        rec["ok"] = False
        rec["err"] = f"{type(e).__name__}: {e}"
    return rec


probes = [
    ("deepreinforce-ai/Ornith-1.0-9B", "text-generation"),
    ("deepreinforce-ai/Ornith-1.0", "text-generation"),
    ("OrnithAI/Ornith-1.0", "text-generation"),
    ("protoLabsAI/Ornith-1.0-9B-MTP-GGUF", "text-generation"),
    ("LiquidAI/LFM2-8B-A1B", "text-generation"),
    ("LiquidAI/LFM2-MoE", "text-generation"),
    ("LiquidAI/LFM2.5-8B-A1B-Instruct", "text-generation"),
    ("Qwen/Qwen3.5-0.8B-Instruct", "text-generation"),
    ("Qwen/Qwen3.5-0.8B-Base", "text-generation"),
]

for repo_id, expect_pipeline in probes:
    out["probes"].append(probe_repo(repo_id, expect_pipeline))

# Also scan 'Ornith' top-of-list using search
try:
    iterator = api.list_models(search="Ornith", sort="downloads", limit=30)
    out["ornith_search_top_downloads"] = [
        {
            "id": m.id,
            "downloads": m.downloads,
            "last_modified": m.last_modified.isoformat() if m.last_modified else None,
            "pipeline_tag": m.pipeline_tag,
        }
        for m in iterator
        if m.pipeline_tag in ("text-generation", "text2text-generation", None)
    ][:15]
except Exception as e:
    out["ornith_search_err"] = f"{type(e).__name__}: {e}"

OUT_DIR = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-04"
os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "ornith_lfm_canonical_probes.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)

print(f"OK wrote {out_path}")
print(
    f"probes={len(out['probes'])}  ornith_top_dl_hits={len(out.get('ornith_search_top_downloads', []))}"
)
for p in out["probes"]:
    if p.get("ok"):
        print(
            f"  + {p['hf_repo']:50s} params={p.get('params_b', '?')}B lm={p.get('last_modified', '?')[:10]}"
        )
    else:
        print(f"  x {p['label']:50s} {p.get('err', '')}")
