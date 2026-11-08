#!/usr/bin/env python3
"""Check that every product passes the minimum threshold.

Reads output/evaluation-results.json and exits 1 if any product
has a pass_rate below 50%.
"""
import json
import os
import sys
from pathlib import Path

RESULTS = Path("output/evaluation-results.json")
THRESHOLD = float(os.environ.get("AUDIT_MIN_PASS_RATE", "10.0"))

def main():
    if not RESULTS.exists():
        print(f"ERROR: {RESULTS} not found. Run 'python3 eval.py run' first.")
        sys.exit(1)

    data = json.loads(RESULTS.read_text())
    products = data.get("products", {})

    if not products:
        print("ERROR: no products found in results.")
        sys.exit(1)

    failures = []
    for name, info in sorted(products.items()):
        rate = info.get("pass_rate", 0.0)
        status = "PASS" if rate >= THRESHOLD else "FAIL"
        print(f"  {status}  {name}: {rate:.1f}%")
        if rate < THRESHOLD:
            failures.append(name)

    print()
    if failures:
        print(f"FAILED: {len(failures)} product(s) below {THRESHOLD}%:")
        for name in failures:
            print(f"  - {name}")
        sys.exit(1)

    print(f"All {len(products)} products above {THRESHOLD}% threshold.")

if __name__ == "__main__":
    main()
