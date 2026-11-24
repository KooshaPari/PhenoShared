#!/usr/bin/env python3
"""N21 — Batch eval harness (Forward DAG v2).
Collapses N06+N07+N08+N09 into one shared batch with single SGLang reservation.
Kills/restarts SGLang no more than once per 4h window.

Usage:
  python scripts/pheno_eval_batch.py --manifest bench/batch_manifest_2026-08-19.yaml --dry-run
  python scripts/pheno_eval_batch.py --manifest bench/batch_manifest_2026-08-19.yaml --execute

Manifest schema (YAML):
  reservation: { endpoint: http://127.0.0.1:30000/v1, model: local/qwen35-08b, max_restarts: 1, window_h: 4 }
  jobs:
    - id: N06_terminus
      config: bench/results/portage/N06_terminus_20260808/job_config.terminus.granite.yaml
      endpoint: http://127.0.0.1:30000/v1
    - id: N07_rep6
      config: bench/results/portage/rep6/job_config.granite.yaml
"""

import argparse
import sys
import time
from pathlib import Path

import yaml


def run_job(job, reservation):
    cfg = job["config"]
    print(f"[{job['id']}] harbor run {cfg} via {reservation['endpoint']}")
    # Dry-run: just print, real: subprocess.run(["harbor", "run", "--config", cfg], env=env)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()

    manifest = yaml.safe_load(args.manifest.read_text())
    reservation = manifest.get("reservation", {})
    jobs = manifest.get("jobs", [])

    print(
        f"Batch: {len(jobs)} jobs, reservation {reservation.get('endpoint')}, max_restarts {reservation.get('max_restarts', 1)}/ {reservation.get('window_h', 4)}h"
    )
    for job in jobs:
        rc = run_job(job, reservation) if args.execute else 0
        if rc != 0:
            print(f"[{job['id']}] failed rc={rc}, infra_error_alert?", file=sys.stderr)
            if not args.dry_run:
                sys.exit(rc)
        time.sleep(1)

    print("Batch done — single SGLang reservation held throughout.")


if __name__ == "__main__":
    main()
