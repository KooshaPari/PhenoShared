#!/usr/bin/env python3
"""Read-only live API contract probe. Never promotes discovered jobs to verified."""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from incident_policy import evaluate as evaluate_incident

BASE = "https://job-collector.worker.example.com"
def load(path):
    last = None
    for attempt in range(3):
        try:
            req = Request(BASE + path, headers={"Accept": "application/json", "Cache-Control": "no-cache", "User-Agent": "job-cockpit-health-probe/1"})
            with urlopen(req, timeout=18) as response:
                if response.status != 200:
                    raise ValueError("HTTP status " + str(response.status))
                if "json" not in response.headers.get("Content-Type", ""):
                    raise ValueError("Expected application/json")
                return json.load(response)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            last = str(exc)
            if attempt != 2:
                time.sleep(1 + 2 * attempt)
    raise RuntimeError(path + ": " + last)

def evaluate(health, review):
    problems = []
    if health.get("service") != "job-collector":
        problems.append("health service identifier mismatch")
    if health.get("health") not in ("ok", "degraded", "stale"):
        problems.append("health state absent or invalid")
    if health.get("health") != "ok":
        problems.append("collector " + str(health.get("health")))
    age = health.get("age_hours")
    if type(age) not in (int, float) or not math.isfinite(age) or age < 0 or age > 36:
        problems.append("collector last completed run is stale or unknown")
    boards = health.get("boards") or {}
    if type(boards.get("total")) is not int or boards["total"] <= 0:
        problems.append("board count missing or no active employer boards")
    if boards.get("last_failure", 0):
        problems.append(str(boards["last_failure"]) + " failing employer board(s)")
    if boards.get("never_checked", 0):
        problems.append(str(boards["never_checked"]) + " unchecked employer board(s)")
    if health.get("strict_verified_la") is not None:
        problems.append("strict verified count requires separate evidence contract")
    if review.get("kind") != "unverified_la_review_queue":
        problems.append("review endpoint contract mismatch")
    candidates = review.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 200:
        problems.append("review candidates missing or oversized")
    else:
        if any(x.get("verification_status") != "unverified" or x.get("graduation_eligible") is not None for x in candidates):
            problems.append("unsafe candidate verification status")
    if review.get("truncated") is not True and review.get("count") == 200:
        problems.append("review pagination/truncation signal inconsistent")
    return problems

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="collector/data/live_health.json")
    p.add_argument("--previous-report", help="Previous main monitor artifact; missing file means first observation")
    args = p.parse_args(argv)
    previous = None
    if args.previous_report and Path(args.previous_report).exists():
        previous = json.loads(Path(args.previous_report).read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ValueError("previous health report must be an object")
    errors = []
    health, review = {}, {}
    try:
        health = load("/health")
        if not isinstance(health, dict):
            health = {}
            raise ValueError("health response must be an object")
        review = load("/review")
        if not isinstance(review, dict):
            review = {}
            raise ValueError("review response must be an object")
        errors = evaluate(health, review)
    except (RuntimeError, KeyError, TypeError, ValueError, AttributeError) as exc:
        errors = ["probe failed: " + str(exc)[:350]]
    now = datetime.now(timezone.utc)
    incident, checkpoint = evaluate_incident(health, previous, now, target=BASE)
    errors.extend(incident["data_issues"])
    if incident["finalized_age_hours"] is not None and incident["finalized_age_hours"] > 36:
        errors.append("collector latest finalized run is stale")
    result = {
        "checked_at": now.isoformat(timespec="seconds"),
        "status": "healthy" if not errors else "degraded",
        "problems": errors,
        "source_health": health.get("health"),
        "source_age_hours": health.get("age_hours"),
        "boards": health.get("boards"),
        "counts": health.get("counts"),
        "strict_verified_la": None,
        "review_count": review.get("count"),
        "latest_run": health.get("latest_run"),
        "finalized_runs": health.get("finalized_runs"),
        "incident": incident,
        "incident_checkpoint": checkpoint,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0  # Persist evidence and allow incident updater even on degraded health.

if __name__ == "__main__":
    sys.exit(main())
