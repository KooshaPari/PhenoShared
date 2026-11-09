#!/usr/bin/env python3
"""Regression tracker for audit evaluation scores.

Reads output/evaluation-results.json, appends a run to history/scores.jsonl,
compares with the previous run, and prints a diff report highlighting
regressions and improvements.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_FILE = SCRIPT_DIR / "output" / "evaluation-results.json"
HISTORY_FILE = SCRIPT_DIR / "history" / "scores.jsonl"


def load_results() -> dict:
    if not RESULTS_FILE.exists():
        print(f"ERROR: {RESULTS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(RESULTS_FILE) as f:
        return json.load(f)


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    entries = []
    with open(HISTORY_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_history(entry: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def extract_scores(results: dict) -> dict[str, float]:
    """Return {product_name: pass_rate} from evaluation results."""
    products = results.get("products", {})
    return {name: data["pass_rate"] for name, data in products.items()}


def diff_reports(prev_scores: dict[str, float], curr_scores: dict[str, float]) -> None:
    regressions = []
    improvements = []
    unchanged = []

    all_products = sorted(set(prev_scores) | set(curr_scores))

    for product in all_products:
        prev = prev_scores.get(product)
        curr = curr_scores.get(product)

        if prev is None:
            improvements.append((product, None, curr, "NEW"))
        elif curr is None:
            regressions.append((product, prev, None, "REMOVED"))
        elif curr > prev:
            improvements.append((product, prev, curr, ""))
        elif curr < prev:
            regressions.append((product, prev, curr, ""))
        else:
            unchanged.append((product, curr))

    # --- Report ---
    print("=" * 64)
    print("  REGRESSION TRACKER DIFF REPORT")
    print("=" * 64)

    if regressions:
        print(f"\n  REGRESSIONS ({len(regressions)}):")
        print("  " + "-" * 40)
        for product, prev, curr, note in regressions:
            if curr is None:
                print(f"    !! {product}: {prev}% -> REMOVED {note}")
            else:
                delta = curr - prev
                print(f"    !! {product}: {prev}% -> {curr}%  ({delta:+.1f}%) {note}")
    else:
        print("\n  No regressions detected.")

    if improvements:
        print(f"\n  IMPROVEMENTS ({len(improvements)}):")
        print("  " + "-" * 40)
        for product, prev, curr, note in improvements:
            if prev is None:
                print(f"    ++ {product}: NEW -> {curr}% {note}")
            else:
                delta = curr - prev
                print(f"    ++ {product}: {prev}% -> {curr}%  ({delta:+.1f}%) {note}")
    else:
        print("\n  No improvements detected.")

    print(f"\n  UNCHANGED ({len(unchanged)}):", end="")
    if unchanged:
        names = [f"{n} ({v}%)" for n, v in unchanged]
        print()
        for name in names:
            print(f"    -- {name}")
    else:
        print(" none")

    print("\n" + "=" * 64)

    # Exit code: 1 if regressions found (useful for CI gating)
    if regressions:
        print(f"  RESULT: {len(regressions)} regression(s) detected")
        print("=" * 64)
        return True
    else:
        print("  RESULT: No regressions")
        print("=" * 64)
        return False


def main() -> None:
    results = load_results()
    curr_scores = extract_scores(results)
    now = datetime.now(timezone.utc).isoformat()

    history = load_history()

    if history:
        prev_entry = history[-1]
        prev_scores = prev_entry["scores"]
        print(f"Comparing against previous run: {prev_entry['timestamp']}")
        print(f"Products in previous run: {len(prev_scores)}")
        print(f"Products in current run:  {len(curr_scores)}")
        print()
        had_regressions = diff_reports(prev_scores, curr_scores)
    else:
        print("No previous runs found. This is the baseline.")
        print(f"Products: {len(curr_scores)}")
        had_regressions = False

    # Append current run to history
    entry = {
        "timestamp": now,
        "evaluated_at": results.get("evaluated_at"),
        "rubric_criteria_count": results.get("rubric_criteria_count"),
        "product_count": len(curr_scores),
        "scores": curr_scores,
    }
    append_history(entry)
    print(f"\nRun saved to {HISTORY_FILE}")

    if had_regressions:
        sys.exit(1)


if __name__ == "__main__":
    main()
