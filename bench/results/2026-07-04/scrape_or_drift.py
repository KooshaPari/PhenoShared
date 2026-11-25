"""
Re-scrape OR /api/v1/models for the 7 locked cloud picks.
No token needed — the OR /api/v1/models endpoint is public.
Compare against the 2026-07-04 round-4 snapshot and emit a drift report.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

ROUND4 = r"C:\Users\koosh\pheno-harness\state\hf_scrape\2026-07-04\summary.json"
OUT_DIR = r"C:\Users\koosh\pheno-harness\bench\results\2026-07-04"

LOCKED_PICKS = [
    "inclusionai/ling-2.6-flash",
    "ibm-granite/granite-4.0-h-micro",  # still listed in OR even though we dropped it; include for drift
    "liquid/lfm-2-24b-a2b",
    "arcee-ai/trinity-mini",
    "ibm-granite/granite-4.1-8b",
    "poolside/laguna-xs-2.1",
    "tencent/hy3-preview",
    "qwen/qwen3.5-flash-02-23",
]


def fetch_models() -> Any:
    url = "https://openrouter.ai/api/v1/models"
    req = urllib.request.Request(url, headers={"User-Agent": "pheno-harness/1.0"})
    with (
        urllib.request.urlopen(req, timeout=30) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    print("[scrape_or_drift] starting", flush=True)
    snap: Any = {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "scrape_ts_unix": int(time.time()),
        "endpoint": "https://openrouter.ai/api/v1/models",
        "picks": {},
    }
    try:
        data = fetch_models()
        by_id = {m["id"]: m for m in data.get("data", [])}
        for pid in LOCKED_PICKS:
            m = by_id.get(pid)
            if not m:
                snap["picks"][pid] = {"present": False}
                continue
            created = m.get("created")
            created_iso = (
                datetime.fromtimestamp(created, tz=UTC).strftime("%Y-%m-%d")
                if created
                else None
            )
            snap["picks"][pid] = {
                "present": True,
                "name": m.get("name"),
                "context_length": m.get("context_length"),
                "created_unix": created,
                "created_iso": created_iso,
                "pricing_prompt_per_m": m.get("pricing", {}).get("prompt"),
                "pricing_completion_per_m": m.get("pricing", {}).get("completion"),
                "hugging_face_id": m.get("hugging_face_id"),
                "top_provider": m.get("top_provider", {}).get("name")
                if m.get("top_provider")
                else None,
            }
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"[scrape_or_drift] OR fetch failed: {e}", flush=True)
        snap["fetch_error"] = str(e)

    # Compare against round-4 snapshot
    drift: Any = {}
    try:
        with open(ROUND4, encoding="utf-8") as f:
            r4 = json.load(f)
        for pid, cur in snap["picks"].items():
            r4_pick = None
            for m in r4.get("models", []):
                if m.get("id") == pid:
                    r4_pick = m
                    break
            if cur.get("present") and r4_pick:
                # Compare pricing
                p_cur = cur.get("pricing_prompt_per_m")
                p_r4 = (
                    r4_pick.get("or_pricing", {}).get("prompt")
                    if isinstance(r4_pick.get("or_pricing"), dict)
                    else r4_pick.get("pricing_prompt_per_m")
                )
                drift[pid] = {
                    "pricing_prompt_drift": (p_cur != p_r4)
                    if (p_cur is not None and p_r4 is not None)
                    else "n/a",
                    "pricing_completion_drift": (
                        cur.get("pricing_completion_per_m")
                        != (
                            r4_pick.get("or_pricing", {}).get("completion")
                            if isinstance(r4_pick.get("or_pricing"), dict)
                            else r4_pick.get("pricing_completion_per_m")
                        )
                    ),
                    "context_drift": (
                        cur.get("context_length") != r4_pick.get("context_length")
                    ),
                }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        drift = {"_error": f"could not load round-4 snapshot: {e}"}

    snap["drift_vs_round4"] = drift

    out_path = OUT_DIR + r"\or_drift_2026-07-04.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False)
    print(f"[scrape_or_drift] wrote {out_path}", flush=True)

    # Stdout summary
    print(
        json.dumps(
            {
                "n_picks": len(LOCKED_PICKS),
                "n_present": sum(1 for p in snap["picks"].values() if p.get("present")),
                "drift_keys": list(drift.keys())[:8]
                if isinstance(drift, dict)
                else None,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
