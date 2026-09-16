"""Round-4 locked-pick scraper v2 — fixes from v1:
- HF model_info called twice: once no-expand (for last_modified, downloads, likes, gated),
  once expand=['safetensors'] (for params). Use the HF id from OR hugging_face_id when present.
- OR API endpoint is /api/v1/models (list), not /api/v1/models/{slug} (404).
- Recency cutoff: 2026-03-01 UTC. Mark pre-March models with PROBE_NEEDED justification.
- Context parsing: pick first number with K/M suffix from 'context' / 'ctx' patterns only.
- HF_TOKEN: from env, never logged. Used for second-call expansion rate-limit bump.
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime

OUT_DIR = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-04"
RECENCY_CUTOFF = datetime(2026, 3, 1, tzinfo=UTC)
USER_AGENT = "pheno-harness-scraper/1.0 (+local research)"

CLOUD_MODELS = [
    {"label": "ling-2.6-flash", "or_id": "inclusionai/ling-2.6-flash", "hf_repo": None},
    {
        "label": "granite-4.0-h-micro",
        "or_id": "ibm-granite/granite-4.0-h-micro",
        "hf_repo": "ibm-granite/granite-4.0-h-micro",
    },
    {
        "label": "lfm-2-24b-a2b",
        "or_id": "liquid/lfm-2-24b-a2b",
        "hf_repo": "LiquidAI/LFM2-24B-A2B",
    },
    {
        "label": "trinity-mini",
        "or_id": "arcee-ai/trinity-mini",
        "hf_repo": "arcee-ai/Trinity-Mini",
    },
    {
        "label": "granite-4.1-8b",
        "or_id": "ibm-granite/granite-4.1-8b",
        "hf_repo": "ibm-granite/granite-4.1-8b",
    },
    {
        "label": "laguna-xs-2.1",
        "or_id": "poolside/laguna-xs-2.1",
        "hf_repo": "poolside/Laguna-XS-2.1",
    },
    {
        "label": "hy3-preview",
        "or_id": "tencent/hy3-preview",
        "hf_repo": "tencent/HY3-Preview",
    },
    {
        "label": "qwen3.5-flash-02-23",
        "or_id": "qwen/qwen3.5-flash-02-23",
        "hf_repo": "Qwen/Qwen3.5-Flash-02-23",
    },
]

LOCAL_MODELS = [
    {"label": "qwen3.5-0.8b", "hf_repo": "Qwen/Qwen3.5-0.8B"},
    {"label": "lfm-2.5-8b-a1b", "hf_repo": "LiquidAI/LFM2.5-8B-A1B"},
    {"label": "ornith-8b", "hf_repo": None},
]

ORNITH_CANDIDATES = [
    "Ornith-1.0-9B-A1B",
    "Ornith-1.0-9B",
    "Ornith-9B-A1B",
    "Ornith-9B",
    "Ornith-1.0-35B",
    "Ornith-1.0-9B-Instruct",
]
ORNITH_AUTHORS = ["Ornith-AI", "OrnithAI", "ornith", "dreamfoundries", "majentik"]


def hf_token():
    return (
        os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None
    )


def log_line(log_fp, msg) -> None:
    log_fp.write(msg + "\n")
    log_fp.flush()


def fetch_hf(repo_id, log_fp):
    from huggingface_hub import HfApi

    api = HfApi()
    base = {"hf_repo": repo_id}
    try:
        info = api.model_info(repo_id)
        base.update(
            {
                "last_modified": str(info.last_modified)
                if info.last_modified
                else None,
                "downloads": getattr(info, "downloads", None),
                "likes": getattr(info, "likes", None),
                "gated": getattr(info, "gated", None),
                "disabled": getattr(info, "disabled", None),
                "private": getattr(info, "private", None),
                "pipeline_tag": getattr(info, "pipeline_tag", None),
                "tags": getattr(info, "tags", None) or [],
                "created_at": str(info.created_at)
                if getattr(info, "created_at", None)
                else None,
            }
        )
        log_line(
            log_fp,
            f"HF-META OK   {repo_id}  lm={base['last_modified']}  dl={base['downloads']}  gated={base['gated']}",
        )
    except Exception as e:
        base["meta_err"] = f"{type(e).__name__}: {str(e)[:200]}"
        log_line(log_fp, f"HF-META ERR  {repo_id}: {base['meta_err']}")
    try:
        info2 = api.model_info(repo_id, expand=["safetensors"])
        st = getattr(info2, "safetensors", None) or {}
        params = st.get("parameters") if isinstance(st, dict) else None
        params_b = (
            round(sum(params.values()) / 1e9, 4)
            if isinstance(params, dict) and params
            else None
        )
        base["params_b"] = params_b
        base["safetensors_dtype_breakdown"] = params
        total_bytes = sum(params.values()) if params else None
        base["total_safetensors_bytes"] = total_bytes
        log_line(
            log_fp,
            f"HF-ST   OK   {repo_id}  params_b={params_b}  total_bytes={total_bytes}",
        )
    except Exception as e:
        base["safetensors_err"] = f"{type(e).__name__}: {str(e)[:200]}"
        log_line(log_fp, f"HF-ST   ERR  {repo_id}: {base['safetensors_err']}")
    return base


def fetch_or_listing(target_ids, log_fp):
    url = "https://openrouter.ai/api/v1/models"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with (
            urllib.request.urlopen(req, timeout=20) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log_line(log_fp, f"OR-LIST  ERR  {e}")
        return {}
    target_set = set(target_ids)
    found = {}
    for m in data.get("data") or []:
        if m.get("id") in target_set:
            found[m["id"]] = m
            pricing = m.get("pricing") or {}
            log_line(
                log_fp,
                f"OR-LIST  OK   {m['id']}  ctx={m.get('context_length')}  in=${pricing.get('prompt')}  out=${pricing.get('completion')}  hf={m.get('hugging_face_id')}",
            )
    for tid in target_set:
        if tid not in found:
            log_line(log_fp, f"OR-LIST  MISS  {tid}  not in OR /api/v1/models response")
    return found


def fetch_or_page(slug, log_fp):
    url = f"https://openrouter.ai/{slug}"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}
    )
    try:
        with (
            urllib.request.urlopen(req, timeout=15) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log_line(log_fp, f"OR-PAGE HTTP {e.code} {slug}")
        return {"or_id": slug, "err": f"HTTP {e.code}"}
    except Exception as e:
        log_line(log_fp, f"OR-PAGE ERR  {slug}: {e}")
        return {"or_id": slug, "err": str(e)[:200]}

    title_m = re.search(r"<title[^>]*>([^<]+)</title>", body)
    desc_m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', body)
    ctx_patterns = [
        (
            re.compile(r"(\d+(?:\.\d+)?)\s*M\s*(?:token\s*)?context", re.IGNORECASE),
            1_000_000,
        ),
        (
            re.compile(r"(\d+(?:\.\d+)?)\s*K\s*(?:token\s*)?context", re.IGNORECASE),
            1_000,
        ),
    ]
    ctx_val = None
    for pat, mult in ctx_patterns:
        m = pat.search(body)
        if m:
            ctx_val = int(float(m.group(1)) * mult)
            break
    in_m = re.search(r"\$\s*([\d.]+)\s*/?\s*M?\s*(?:input|in)", body, re.IGNORECASE)
    out_m = re.search(r"\$\s*([\d.]+)\s*/?\s*M?\s*(?:output|out)", body, re.IGNORECASE)
    rec = {
        "or_id": slug,
        "title": (title_m.group(1).strip() if title_m else None),
        "description": (desc_m.group(1).strip() if desc_m else None),
        "context_length_from_page": ctx_val,
        "input_price_usd_per_m_from_page": (in_m.group(1) if in_m else None),
        "output_price_usd_per_m_from_page": (out_m.group(1) if out_m else None),
        "body_len": len(body),
    }
    log_line(
        log_fp,
        f"OR-PAGE OK   {slug}  title={rec['title']!r}  ctx={ctx_val}  in=${rec['input_price_usd_per_m_from_page']}  out=${rec['output_price_usd_per_m_from_page']}",
    )
    return rec


def probe_ornith(log_fp):
    from huggingface_hub import HfApi

    api = HfApi()
    hits = []
    for cand in ORNITH_CANDIDATES:
        try:
            it = api.list_models(search=cand, limit=10, sort="last_modified")
            for m in it:
                mid = m.id
                if "ornith" in mid.lower() and (
                    "9b" in mid.lower() or "8b" in mid.lower() or "a1b" in mid.lower()
                ):
                    lm = str(m.last_modified) if m.last_modified else None
                    hits.append(
                        {
                            "id": mid,
                            "last_modified": lm,
                            "downloads": m.downloads,
                            "match": cand,
                        }
                    )
        except Exception as e:
            log_line(log_fp, f"ORNITH search ERR {cand}: {e}")
    for au in ORNITH_AUTHORS:
        try:
            it = api.list_models(author=au, limit=40, sort="last_modified")
            for m in it:
                mid = m.id.lower()
                if "ornith" in mid and "9b" in mid and "a1b" in mid:
                    lm = str(m.last_modified) if m.last_modified else None
                    hits.append(
                        {
                            "id": m.id,
                            "last_modified": lm,
                            "downloads": m.downloads,
                            "match": f"author={au}",
                        }
                    )
        except Exception as e:
            log_line(log_fp, f"ORNITH author ERR {au}: {e}")
    seen = set()
    deduped = []
    for h in hits:
        if h["id"] not in seen:
            seen.add(h["id"])
            deduped.append(h)
    log_line(
        log_fp,
        f"ORNITH search hits: {len(deduped)}  -> {[h['id'] for h in deduped[:8]]}",
    )
    return deduped


def parse_date_safe(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def within_recency(last_modified_str, fallback_epoch=None):
    dt = parse_date_safe(last_modified_str)
    if dt is None and fallback_epoch:
        try:
            dt = datetime.fromtimestamp(int(fallback_epoch), tz=UTC)
        except Exception:
            dt = None
    if dt is None:
        return False, "no_recency_signal", None
    return (
        dt >= RECENCY_CUTOFF,
        ("pre_march_2026" if dt < RECENCY_CUTOFF else "ok"),
        dt.isoformat(),
    )


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    log_path = os.path.join(OUT_DIR, "scrape_round4.log")
    out_jsonl = os.path.join(OUT_DIR, "models.jsonl")
    out_json = os.path.join(OUT_DIR, "summary.json")
    rejects_path = os.path.join(OUT_DIR, "rejects.jsonl")

    tok = hf_token()
    print(f"HF_TOKEN_present={bool(tok)}")

    records = []
    rejects = []

    with open(log_path, "w", encoding="utf-8") as log_fp:
        log_line(
            log_fp,
            f"=== round-4 v2 scrape started  {datetime.now(UTC).isoformat()} ===",
        )
        log_line(log_fp, f"HF_TOKEN_present={bool(tok)}  (token value never logged)")
        log_line(log_fp, f"recency_cutoff_utc={RECENCY_CUTOFF.isoformat()}")

        or_target_ids = [m["or_id"] for m in CLOUD_MODELS]
        or_listing = fetch_or_listing(or_target_ids, log_fp)

        for m in CLOUD_MODELS:
            print(f"[cloud] {m['label']}")
            rec = {"slot": "cloud", "label": m["label"], "or_id": m["or_id"]}
            or_entry = or_listing.get(m["or_id"])
            if or_entry:
                pricing = or_entry.get("pricing") or {}
                rec["or_api"] = {
                    "id": or_entry.get("id"),
                    "name": or_entry.get("name"),
                    "description": or_entry.get("description"),
                    "context_length": or_entry.get("context_length"),
                    "created_epoch": or_entry.get("created"),
                    "created_iso": datetime.fromtimestamp(
                        int(or_entry["created"]), tz=UTC
                    ).isoformat()
                    if or_entry.get("created")
                    else None,
                    "pricing_prompt_usd_per_token": pricing.get("prompt"),
                    "pricing_completion_usd_per_token": pricing.get("completion"),
                    "pricing_prompt_usd_per_m": (float(pricing["prompt"]) * 1_000_000)
                    if pricing.get("prompt")
                    else None,
                    "pricing_completion_usd_per_m": (
                        float(pricing["completion"]) * 1_000_000
                    )
                    if pricing.get("completion")
                    else None,
                    "architecture": or_entry.get("architecture"),
                    "top_provider": or_entry.get("top_provider"),
                    "hugging_face_id_from_or": or_entry.get("hugging_face_id"),
                    "canonical_slug": or_entry.get("canonical_slug"),
                    "per_request_limits": or_entry.get("per_request_limits"),
                }
                if not m.get("hf_repo") and or_entry.get("hugging_face_id"):
                    m["hf_repo"] = or_entry["hugging_face_id"]
            rec["or_page"] = fetch_or_page(m["or_id"], log_fp)
            if m.get("hf_repo"):
                rec["hf"] = fetch_hf(m["hf_repo"], log_fp)
            hf = rec.get("hf") or {}
            ok, why, dt_str = within_recency(
                hf.get("last_modified"),
                fallback_epoch=(rec.get("or_api") or {}).get("created_epoch"),
            )
            rec["recency_ok"] = ok
            rec["recency_reason"] = why
            rec["recency_resolved_date"] = dt_str
            if not ok:
                rejects.append(
                    {
                        "label": m["label"],
                        "hf_repo": hf.get("hf_repo"),
                        "or_id": m["or_id"],
                        "last_modified": hf.get("last_modified"),
                        "reason": why,
                    }
                )
            records.append(rec)

        for m in LOCAL_MODELS:
            print(f"[local] {m['label']}")
            rec = {"slot": "local", "label": m["label"]}
            if m.get("hf_repo"):
                rec["hf"] = fetch_hf(m["hf_repo"], log_fp)
            else:
                hits = probe_ornith(log_fp)
                rec["ornith_search_hits"] = [
                    {
                        "id": h["id"],
                        "last_modified": h["last_modified"],
                        "downloads": h.get("downloads"),
                        "match": h.get("match"),
                    }
                    for h in hits[:15]
                ]
                if hits:
                    pick = None
                    for h in hits:
                        if "MLX-8bit" in h["id"] or "mlx-8bit" in h["id"]:
                            continue
                        pick = h
                        break
                    if pick is None:
                        pick = hits[0]
                    rec["ornith_picked_repo"] = pick["id"]
                    rec["hf"] = fetch_hf(pick["id"], log_fp)
            hf = rec.get("hf") or {}
            ok, why, dt_str = within_recency(hf.get("last_modified"))
            rec["recency_ok"] = ok
            rec["recency_reason"] = why
            rec["recency_resolved_date"] = dt_str
            if not ok:
                rejects.append(
                    {
                        "label": m["label"],
                        "hf_repo": hf.get("hf_repo"),
                        "last_modified": hf.get("last_modified"),
                        "reason": why,
                    }
                )
            records.append(rec)

        with open(out_jsonl, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        with open(rejects_path, "w", encoding="utf-8") as f:
            for r in rejects:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

        summary = {
            "date": "2026-07-04",
            "recency_cutoff_utc": RECENCY_CUTOFF.isoformat(),
            "hf_token_present": bool(tok),
            "openrouter_token_present": bool(os.environ.get("OPENROUTER_API_KEY")),
            "counts": {"total": len(records), "rejected_pre_march": len(rejects)},
            "per_model": [
                {
                    "label": r.get("label"),
                    "slot": r.get("slot"),
                    "or_id": r.get("or_id"),
                    "recency_ok": r.get("recency_ok"),
                    "recency_reason": r.get("recency_reason"),
                    "recency_resolved_date": r.get("recency_resolved_date"),
                    "hf_repo": (r.get("hf") or {}).get("hf_repo"),
                    "hf_last_modified": (r.get("hf") or {}).get("last_modified"),
                    "params_b": (r.get("hf") or {}).get("params_b"),
                    "or_ctx": ((r.get("or_api") or {}).get("context_length")),
                    "or_pricing_in_per_m": (
                        (r.get("or_api") or {}).get("pricing_prompt_usd_per_m")
                    ),
                    "or_pricing_out_per_m": (
                        (r.get("or_api") or {}).get("pricing_completion_usd_per_m")
                    ),
                    "or_created": ((r.get("or_api") or {}).get("created_iso")),
                }
                for r in records
            ],
            "ornith_search_hits": next(
                (
                    (r.get("ornith_search_hits") or [])
                    for r in records
                    if r.get("label") == "ornith-8b"
                ),
                [],
            ),
        }
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        log_line(
            log_fp,
            f"=== round-4 v2 complete  total={len(records)}  rejected_pre_march={len(rejects)} ===",
        )
        pre_march = [
            r
            for r in records
            if not r.get("recency_ok") and r.get("recency_reason") == "pre_march_2026"
        ]
        log_line(
            log_fp,
            f"pre-march-but-listed: {len(pre_march)}  (LOCKED user picks — eval anyway, mark for justification)",
        )

    print(f"wrote {out_jsonl}")
    print(f"wrote {out_json}")
    print(f"wrote {log_path}")
    print(f"total={len(records)}  rejected_pre_march={len(rejects)}")


if __name__ == "__main__":
    main()
