"""N08 re-baseline driver (durable harness artifact).

Waits for both serving lanes to bind, then fires the TB2.0 representative-6
baseline eval against the live gateway. The 1080 Ti helper lane (Qwen on
:19001) must be healthy first -- see scripts/recover_1080ti_elevated.cmd.

Exit codes:
  0  eval fired (or dry_run completed)
  2  lanes never bound within the timeout
  3  preflight failed (no N08 sub-manifest, bad manifest, import error)

Usage:
  python scripts/run_n08_rebaseline.py [--dry-run] [--timeout-min 40]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

RUNTIME = REPO / ".runtime"
EVAL_JOBS = REPO / "state" / "eval_jobs"
LANES = {
    "qwen_helper": ("http://127.0.0.1:19001/v1/models", "Qwen/Qwen3.5-0.8B"),
    "lfm_primary": ("http://127.0.0.1:19000/v1/models", "lfm25-8b-a1b"),
}

# When the WSL NVIDIA driver stack is broken (vLLM/transformers inside WSL), the
# Qwen model is reachable via a Windows-side llama-server on :8080 instead.  Set
# QWEN_FALLBACK_URL to skip the inbound WSL lane check and use that proxy route.
QWEN_FALLBACK_URL = os.environ.get("QWEN_FALLBACK_URL")


def log(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with open(RUNTIME / "n08-rebaseline.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def lane_up(url: str, want: str) -> bool:
    try:
        with (
            urllib.request.urlopen(url, timeout=5) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = r.read().decode("utf-8", "replace")
            return r.status == 200 and want.lower() in body.lower()
    except Exception:
        return False


def wait_for_lanes(timeout_min: int) -> bool:
    deadline = time.time() + timeout_min * 60
    while time.time() < deadline:
        if QWEN_FALLBACK_URL:
            q = lane_up(QWEN_FALLBACK_URL + "/v1/models", "qwen")
            log(
                f"poll qwen_fallback={q} (primary lane skipped) ({int(deadline - time.time())}s left)"
            )
            if q:
                return True
        else:
            q = lane_up(*LANES["qwen_helper"])
            l = lane_up(*LANES["lfm_primary"])
            log(f"poll qwen={q} lfm={l} ({int(deadline - time.time())}s left)")
            if q and l:
                return True
        time.sleep(20)
    return False


def newest_sub_manifest() -> Path | None:
    hits = sorted(
        glob.glob(str(EVAL_JOBS / "N08_tb20_local_qwen35_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )
    return Path(hits[0]) if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout-min", type=int, default=40)
    args = ap.parse_args()

    log(f"=== N08 re-baseline driver start (dry_run={args.dry_run}) ===")

    manifest = newest_sub_manifest()
    if manifest is None:
        log("ERROR: no N08 sub-manifest found under state/eval_jobs")
        return 3
    log(f"sub-manifest: {manifest.name}")

    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: cannot parse sub-manifest: {exc}")
        return 3

    log(
        f"model_alias={m.get('model_alias')} suite={m.get('suite')} "
        f"tasks={len(m.get('task_names', []))}"
    )

    if args.dry_run:
        log("dry-run: preflight passed, eval NOT fired")
        return 0

    if not wait_for_lanes(args.timeout_min):
        log("ERROR: lanes never bound within timeout -- abort")
        return 2

    import traceback

    import eval.tbench_v21 as tbench

    out_dir = REPO / "bench" / "results" / "tbench" / "2.0"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"firing execute(manifest, output_dir={out_dir})")
    try:
        rc = tbench.execute(m, out_dir)
        log(f"=== N08 re-baseline complete rc={rc} ===")
        return 0 if rc == 0 else 4
    except Exception:
        tb = traceback.format_exc()
        log("=== N08 re-baseline FAILED ===\n" + tb)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
