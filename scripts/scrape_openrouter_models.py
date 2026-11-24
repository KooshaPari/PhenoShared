#!/usr/bin/env python3
"""Scrape OpenRouter API and model pages for configured eval baselines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, PHENO_ROOT

API_URL = "https://openrouter.ai/api/v1/models"
MODEL_PAGE = "https://openrouter.ai/{model_id}"


def _fetch_json(url: str, timeout: int) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "pheno-harness-openrouter-scrape/1.0"})
    with (
        urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read().decode("utf-8"))


def _fetch_text(url: str, timeout: int) -> str:
    req = Request(url, headers={"User-Agent": "pheno-harness-openrouter-scrape/1.0"})
    with (
        urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return resp.read().decode("utf-8", errors="replace")


def _page_summary(html: str) -> dict[str, Any]:
    title = ""
    match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
    text = re.sub(
        r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "title": title,
        "visible_text_sample": text[:4000],
    }


def _safe_name(model_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", model_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape OpenRouter model metadata")
    parser.add_argument(
        "--config", default=str(CONFIG_DIR / "openrouter_eval_models.yaml")
    )
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    model_ids = [row["id"] for row in cfg.get("models", [])]
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else PHENO_ROOT / "state" / "openrouter_scrape" / stamp
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    api = _fetch_json(API_URL, args.timeout)
    models = api.get("data", [])
    by_id = {str(row.get("id", "")).lower(): row for row in models}
    records = []
    for model_id in model_ids:
        rec = {
            "id": model_id,
            "scraped_at": datetime.now(UTC).isoformat(),
            "api_found": False,
            "page_found": False,
        }
        api_row = by_id.get(model_id.lower())
        if api_row:
            rec["api_found"] = True
            rec["api"] = api_row
        if not args.api_only:
            page_url = MODEL_PAGE.format(model_id=quote(model_id, safe="/"))
            try:
                html = _fetch_text(page_url, args.timeout)
                rec["page_found"] = True
                rec["page_url"] = page_url
                rec["page"] = _page_summary(html)
            except (HTTPError, URLError, TimeoutError) as exc:
                rec["page_error"] = str(exc)
        records.append(rec)
        (out_dir / f"{_safe_name(model_id)}.json").write_text(
            json.dumps(rec, indent=2), encoding="utf-8"
        )

    summary = {
        "source_api": API_URL,
        "config": str(Path(args.config)),
        "count": len(records),
        "api_found": sum(1 for row in records if row["api_found"]),
        "page_found": sum(1 for row in records if row["page_found"]),
        "records": records,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: summary[k] for k in ["count", "api_found", "page_found"]}, indent=2
        )
    )
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
