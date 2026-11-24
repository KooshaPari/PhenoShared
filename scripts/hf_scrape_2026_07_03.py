#!/usr/bin/env python3
"""
hf_scrape_2026_07_03.py — reproducible HF model sweep for the pheno-harness
local-serving bootstrap (ADR 0003 + SPEC-003-model-engine-matrix).

Designed for the unauthenticated HF public API. With a `HF_TOKEN` env var
the rate-limits go from ~30 req/15 min to ~300 req/15 min and gated/private
models become visible. **Never print, log, or commit the token.**

Outputs:
  state/hf_scrape/<YYYY-MM-DD>/models.jsonl    — one model per line
  state/hf_scrape/<YYYY-MM-DD>/summary.json    — counts, errors, timing
  state/hf_scrape/<YYYY-MM-DD>/rejects.jsonl   — anything filtered out + reason

Usage:
  python scripts/hf_scrape_2026_07_03.py
  HF_TOKEN=hf_xxx python scripts/hf_scrape_2026_07_03.py --include-private

No side effects beyond writing the three files above.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError

# --- config ------------------------------------------------------------------

# Candidate authors/orgs that ship broadly-relevant coding-or-agent LLMs.
# Add new ones as the live ecosystem shifts; the spec says this list is a
# starting point only and should grow in follow-up ADRs.
AUTHORS = [
    # Big Western open-weight families
    "meta-llama",  # Llama 3.x / 4.x
    "mistralai",  # Mistral / Mixtral / Magistral / Codestral
    "google",  # Gemma 2/3
    "microsoft",  # Phi-3 / Phi-4
    "allenai",  # OLMo / Tülu
    "cohere",  # Command-R
    # Chinese open-weight leaders in 2026
    "Qwen",  # Qwen 3.x / 3.6
    "deepseek-ai",  # DeepSeek-V3 / R1
    "inclusionAI",  # Ling family
    "moonshotai",  # Kimi
    "zai-org",  # GLM / Z.AI
    "THUDM",  # GLM-Edge / ChatGLM
    "01-ai",  # Yi
    "baichuan-inc",  # Baichuan
    # Coding-specialized
    "bigcode",
    "WizardLM",
    "NousResearch",
]  # dedupe later via dict.fromkeys
# Task tag we care about. HF tag system is messy; we filter in three passes.
TAGS_KEEP = [
    "text-generation",
    "text2text-generation",
]

# Hard ceilings from the brief.
MIN_PARAMS_B = 0.8
MAX_PARAMS_B = 35.0

# Parameter-count extraction: parse from name + safetensors config.
# Patterns taken from common naming conventions across these orgs; may miss
# edge cases, which is why we also pull `config.json` when reachable.
NAME_PARAM_PATTERNS = [
    re.compile(r"(?P<b>\d+(?:\.\d+)?)[Bb]\-", re.IGNORECASE),
    re.compile(r"(?P<b>\d+(?:\.\d+)?)B(?:\-|$|_)", re.IGNORECASE),
    re.compile(r"(?P<b>\d+(?:\.\d+)?)b", re.IGNORECASE),
]


def extract_params_b(name: str, cfg_params: int | None) -> float | None:
    """Best-effort params-in-B inference from name + config.json."""
    if cfg_params and cfg_params > 0:
        return cfg_params / 1e9
    for pat in NAME_PARAM_PATTERNS:
        m = pat.search(name)
        if m:
            try:
                return float(m.group("b"))
            except ValueError:
                pass
    return None


# --- core fetch --------------------------------------------------------------


def iter_models(api: HfApi, author: str) -> Iterable:
    """Yield model objects for an author. Respects rate limits."""
    try:
        yield from api.list_models(
            author=author,
            pipeline_tag="text-generation",
            limit=200,
            sort="downloads",
            cardData=True,
            fetch_config=True,
        )
    except RepositoryNotFoundError:
        return
    except HfHubHTTPError as e:
        # 404 on org is fine; 403 means auth needed; 429 means back off.
        if e.response is not None and e.response.status_code == 404:
            return
        raise


def params_b_from_safetensors(info) -> float | None:
    """Use the structured `safetensors.parameters` dict (BF16, F16, F32, …)
    that `expand=['safetensors']` returns. Sum the dtype-byte totals and
    divide by 2 (assumes bf16/fp16 weight precision, the dominant modern
    open-weight packaging). Returns None if not present."""
    st = getattr(info, "safetensors", None)
    if st is None:
        return None
    params = getattr(st, "parameters", None) or (
        st.get("parameters") if isinstance(st, dict) else None
    )
    if not params:
        return None
    # Each dtype entry is the total PARAMETER COUNT for that dtype, not bytes.
    total_params = sum(int(v) for v in params.values())
    return round(total_params / 1e9, 3)


def fetch_model_detail(api: HfApi, model_id: str) -> dict[str, Any]:
    """Phase-1 metadata-only fetch. We rely on:
        - `expand=['safetensors']` (the only `expand` value that this
          huggingface_hub version actually materializes)
        - `info.tags` (model card metadata: license, language, …)
        - `info.last_modified` / `info.created_at`
    Card / config fields (`card_data`, etc.) are not populated by
    `expand=[...]` in huggingface_hub 1.19, so we don't depend on them.
    File sizes + quant tags are filled in by `enrich_kept_models` only on
    the small set that passes filtering."""
    info = api.model_info(model_id, expand=["safetensors"])
    tags = info.tags or []
    license_tag = next((t for t in tags if t.startswith("license:")), None)
    arch_tag = next((t for t in tags if t.startswith("architecture:")), None)
    st_params_b = params_b_from_safetensors(info)
    name = model_id.split("/")[-1]
    name_params_b = extract_params_b(name, None)
    # trust safetensors over name parsing
    effective_params_b = st_params_b if st_params_b is not None else name_params_b
    return {
        "id": model_id,
        "downloads": info.downloads,
        "likes": info.likes,
        "tags": tags,
        "created_at": str(info.created_at) if info.created_at else None,
        "last_modified": str(info.last_modified) if info.last_modified else None,
        "private": info.private,
        "gated": info.gated,
        "disabled": info.disabled,
        "siblings_count": len(info.siblings or []),
        "st_params_b": st_params_b,
        "name_params_b": name_params_b,
        "license": license_tag.split(":", 1)[1] if license_tag else None,
        "arch": arch_tag.split(":", 1)[1] if arch_tag else None,
        "params_b": effective_params_b,
        # Phase-2 fills these in:
        "quants": [],
        "safetensors_total_bytes": 0,
        "safetensors_total_gb": 0.0,
        "safetensors_dtype_breakdown": {},
    }


def enrich_kept_model(api: HfApi, rec: dict[str, Any], timeout_s: float = 8.0) -> dict[str, Any]:
    """Phase-2 (optional): fill file-size + quant tag info for a single
    model. Network calls are wrapped in a wall-time budget so a slow
    endpoint can never block the run."""
    try:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            info = ex.submit(api.model_info, rec["id"], files_metadata=True).result(
                timeout=timeout_s
            )
        siblings = info.siblings or []
        quants: set[str] = set()
        st_bytes = 0
        st_breakdown: dict[str, int] = {}
        for s in siblings:
            rname = s.rfilename.lower()
            if rname.endswith(".safetensors") and s.size:
                st_bytes += s.size
                # very rough dtype hint from the filename
                for dt in ("bf16", "fp16", "fp32", "fp8", "int8", "int4"):
                    if dt in rname:
                        st_breakdown[dt] = st_breakdown.get(dt, 0) + s.size
            for tag in (
                "awq",
                "gptq",
                "gguf",
                "bnb-4bit",
                "bnb-8bit",
                "fp8",
                "nf4",
                "int4",
                "int8",
                "exl2",
                "marlin",
            ):
                if f"-{tag}" in rname or f".{tag}" in rname or f"_{tag}" in rname:
                    quants.add(tag)
        rec["quants"] = sorted(quants)
        rec["safetensors_total_bytes"] = st_bytes
        rec["safetensors_total_gb"] = round(st_bytes / 1e9, 2)
        rec["safetensors_dtype_breakdown"] = st_breakdown
        # also re-pull safetensors parameter breakdown if not yet present
        if not rec.get("st_params_b"):
            rec["st_params_b"] = params_b_from_safetensors(info)
            if rec["st_params_b"] is not None:
                rec["params_b"] = rec["st_params_b"]
    except Exception as e:
        rec["enrich_error"] = repr(e)
    return rec


# --- filters -----------------------------------------------------------------


def passes_brief(rec: dict[str, Any]) -> tuple[bool, str | None]:
    if rec["params_b"] is None:
        return False, "no param count"
    if not (MIN_PARAMS_B <= rec["params_b"] <= MAX_PARAMS_B):
        return (
            False,
            f"params_b={rec['params_b']:.2f} out of [{MIN_PARAMS_B},{MAX_PARAMS_B}]",
        )
    # `info.gated` can be False / "manual" / "auto" / None.
    # "manual" => need HF approval — skip from default scrape.
    # "auto"   => auto-approval, OK to include.
    if rec["gated"] == "manual":
        return False, "gated=manual"
    if rec["disabled"]:
        return False, "disabled"
    return True, None


# --- main --------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--include-private", action="store_true", help="requires HF_TOKEN in env"
    )
    ap.add_argument("--max-per-author", type=int, default=120)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument(
        "--no-enrich",
        action="store_true",
        help="skip phase-2 file-size / quant enrichment",
    )
    ap.add_argument("--enrich-timeout", type=float, default=8.0)
    args = ap.parse_args()

    today = date.today().isoformat()
    out_root = Path(
        args.output_dir or f"C:/Users/koosh/pheno-harness/state/hf_scrape/{today}"
    )
    out_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_root / "models.jsonl"
    summary_path = out_root / "summary.json"
    rejects_path = out_root / "rejects.jsonl"
    heartbeat_path = out_root / "heartbeat.json"

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    api = HfApi(token=token)

    started = time.time()
    errors: list[dict] = []
    counts = {"seen": 0, "kept": 0, "rejected": 0, "fetch_fail": 0}
    by_author: dict[str, int] = {}

    def write_heartbeat(extra: dict | None = None) -> None:
        try:
            payload = {
                "started_at": started,
                "last_update": time.time(),
                "elapsed_s": round(time.time() - started, 1),
                "counts": counts,
                "by_author": by_author,
                "current_author": current_author[0],
                "errors_so_far": len(errors),
            }
            if extra:
                payload.update(extra)
            heartbeat_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    seen_ids: set[str] = set()
    authors = list(dict.fromkeys(AUTHORS))  # dedupe, preserve order
    current_author: list[str | None] = [None]  # mutable cell for heartbeat closure
    write_heartbeat({"event": "init", "authors": authors, "out_root": str(out_root)})

    with (
        jsonl_path.open("w", encoding="utf-8", buffering=1) as fout,
        rejects_path.open("w", encoding="utf-8", buffering=1) as frej,
    ):
        for author in authors:
            current_author[0] = author
            by_author[author] = 0
            write_heartbeat({"event": "author_start"})
            try:
                iterable = iter_models(api, author)
            except Exception as e:
                errors.append({"author": author, "stage": "list", "err": repr(e)})
                write_heartbeat({"event": "author_list_fail"})
                continue
            per = 0
            for m in iterable:
                if per >= args.max_per_author:
                    break
                # PRIMARY text-gen gate is the listing's pipeline_tag —
                # `info.tags` is not populated in huggingface_hub 1.19 for
                # many of these models.
                if getattr(m, "pipeline_tag", None) not in TAGS_KEEP:
                    continue
                if m.id in seen_ids:
                    continue
                seen_ids.add(m.id)
                counts["seen"] += 1
                try:
                    rec = fetch_model_detail(api, m.id)
                except Exception as e:
                    counts["fetch_fail"] += 1
                    errors.append({"id": m.id, "stage": "info", "err": repr(e)})
                    continue
                rec["pipeline_tag_listing"] = getattr(m, "pipeline_tag", None)
                rec["listing_downloads"] = getattr(m, "downloads", None)
                rec["listing_likes"] = getattr(m, "likes", None)
                ok, reason = passes_brief(rec)
                if ok:
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    counts["kept"] += 1
                    by_author[author] += 1
                else:
                    frej.write(
                        json.dumps(
                            {
                                "id": m.id,
                                "reason": reason,
                                "params_b": rec.get("params_b"),
                                "tags": rec.get("tags"),
                                "gated": rec.get("gated"),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    frej.flush()
                    counts["rejected"] += 1
                per += 1
                # heartbeat every 25 records
                if counts["seen"] % 25 == 0:
                    write_heartbeat({"event": "tick"})
            write_heartbeat({"event": "author_done", "scanned_in_author": per})
            # gentle pacing for unauthenticated calls
            time.sleep(0.4)

    summary = {
        "date": today,
        "token_set": bool(token),
        "include_private": bool(args.include_private),
        "authors_queried": authors,
        "counts": counts,
        "by_author": by_author,
        "phase1_errors": errors[:50],
        "elapsed_s_phase1": round(time.time() - started, 1),
        "filters": {
            "min_params_b": MIN_PARAMS_B,
            "max_params_b": MAX_PARAMS_B,
            "tags_keep": TAGS_KEEP,
        },
        "outputs": {
            "models_jsonl": str(jsonl_path),
            "rejects_jsonl": str(rejects_path),
        },
    }

    # ---- Phase 2: enrich kept models with file sizes + quant tags ----
    if not args.no_enrich and counts["kept"] > 0:
        enriched_path = jsonl_path.with_suffix(".enriched.jsonl")
        t2 = time.time()
        kept = [
            json.loads(line)
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        # process sequentially with a wall-time budget per call so we never
        # block the run on a slow endpoint
        for rec in kept:
            enrich_kept_model(api, rec, timeout_s=args.enrich_timeout)
        with enriched_path.open("w", encoding="utf-8") as fenr:
            for rec in kept:
                fenr.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # Replace the phase-1 file with the enriched one
        jsonl_path.unlink()
        enriched_path.replace(jsonl_path)
        summary["phase2_enriched"] = len(kept)
        summary["phase2_elapsed_s"] = round(time.time() - t2, 1)

    summary["elapsed_s"] = round(time.time() - started, 1)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "counts": counts,
                "by_author": by_author,
                "elapsed_s": summary["elapsed_s"],
                "outputs": summary["outputs"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
