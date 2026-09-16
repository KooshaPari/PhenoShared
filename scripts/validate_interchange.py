#!/usr/bin/env python3
"""
validate_interchange.py -- Validate a V5 interchange contract JSON file.

Checks required fields and verifies the hash chain SHA256.

Usage:
    python scripts/validate_interchange.py <path-to-contract.json>

Exit codes:
    0 -- all checks pass
    1 -- one or more checks fail
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_PRODUCER_FIELDS = {"name", "version"}
REQUIRED_RUN_FIELDS = {"run_id", "model", "variant"}
REQUIRED_SUITE_FIELDS = {"suite", "n", "passed", "pass_at_1"}
REQUIRED_TOTALS_FIELDS = {"cells", "passed", "pass_at_1"}
REQUIRED_HASH_CHAIN_FIELDS = {"top_level_sha256"}


class Check:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.detail = ""

    def ok(self, detail: str = "") -> None:
        self.passed = True
        self.detail = detail

    def fail(self, detail: str) -> None:
        self.passed = False
        self.detail = detail

    def __str__(self) -> str:
        tag = "PASS" if self.passed else "FAIL"
        suffix = f" -- {self.detail}" if self.detail else ""
        return f"  [{tag}] {self.name}{suffix}"


def canonical_json_bytes(doc: dict[str, Any]) -> bytes:
    return json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def validate(path: str) -> list[Check]:
    checks: list[Check] = []

    c = Check("file readable")
    try:
        raw = Path(path).read_text()
        c.ok(f"{len(raw)} bytes")
    except Exception as exc:
        c.fail(str(exc))
        checks.append(c)
        return checks
    checks.append(c)

    c = Check("valid JSON")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        c.fail(str(exc))
        checks.append(c)
        return checks
    c.ok()
    checks.append(c)

    # 1. contract_version
    c = Check("contract_version present and == '0.1'")
    cv = doc.get("contract_version")
    if cv is None:
        c.fail("missing")
    elif cv != "0.1":
        c.fail(f"got {cv!r}")
    else:
        c.ok()
    checks.append(c)

    # 2. producer (object with name/version)
    c = Check("producer is object with name/version")
    producer = doc.get("producer")
    if not isinstance(producer, dict):
        c.fail(f"not a dict (got {type(producer).__name__})")
    else:
        missing = REQUIRED_PRODUCER_FIELDS - set(producer.keys())
        if missing:
            c.fail(f"missing fields: {sorted(missing)}")
        else:
            c.ok(f"name={producer['name']!r}, version={producer['version']!r}")
    checks.append(c)

    # 3. run (object with run_id, model, variant)
    c = Check("run is object with run_id/model/variant")
    run = doc.get("run")
    if not isinstance(run, dict):
        c.fail(f"not a dict (got {type(run).__name__})")
    else:
        missing = REQUIRED_RUN_FIELDS - set(run.keys())
        if missing:
            c.fail(f"missing fields: {sorted(missing)}")
        else:
            c.ok(
                f"run_id={run['run_id']!r}, model={run['model']!r}, variant={run['variant']!r}"
            )
    checks.append(c)

    # 4. suites (array of objects with suite, n, passed, pass_at_1)
    c = Check("suites is array with required fields per entry")
    suites = doc.get("suites")
    if not isinstance(suites, list) or len(suites) == 0:
        c.fail(
            f"not a non-empty array (got {type(suites).__name__}, len={len(suites) if isinstance(suites, list) else 'N/A'})"
        )
    else:
        bad_indices = []
        for i, s in enumerate(suites):
            if not isinstance(s, dict):
                bad_indices.append((i, "not a dict"))
            else:
                missing = REQUIRED_SUITE_FIELDS - set(s.keys())
                if missing:
                    bad_indices.append((i, f"missing {sorted(missing)}"))
        if bad_indices:
            details = "; ".join(f"suites[{i}]: {msg}" for i, msg in bad_indices[:5])
            c.fail(details)
        else:
            c.ok(f"{len(suites)} suites, all have required fields")
    checks.append(c)

    # 5. totals (object with cells, passed, pass_at_1)
    c = Check("totals is object with cells/passed/pass_at_1")
    totals = doc.get("totals")
    if not isinstance(totals, dict):
        c.fail(f"not a dict (got {type(totals).__name__})")
    else:
        missing = REQUIRED_TOTALS_FIELDS - set(totals.keys())
        if missing:
            c.fail(f"missing fields: {sorted(missing)}")
        else:
            c.ok(
                f"cells={totals['cells']}, passed={totals['passed']}, pass_at_1={totals['pass_at_1']}"
            )
    checks.append(c)

    # 6. hash_chain (object with top_level_sha256)
    c = Check("hash_chain is object with top_level_sha256")
    hc = doc.get("hash_chain")
    if not isinstance(hc, dict):
        c.fail(f"not a dict (got {type(hc).__name__})")
    elif "top_level_sha256" not in hc:
        c.fail("missing top_level_sha256")
    else:
        c.ok(f"top_level_sha256={hc['top_level_sha256'][:16]}...")
    checks.append(c)

    # 7. hash chain SHA256 verification
    c = Check("hash_chain.top_level_sha256 matches content")
    if isinstance(hc, dict) and "top_level_sha256" in hc:
        content_without_hash = {k: v for k, v in doc.items() if k != "hash_chain"}
        computed = hashlib.sha256(
            canonical_json_bytes(content_without_hash)
        ).hexdigest()
        stored = hc["top_level_sha256"]
        if computed == stored:
            c.ok(f"verified: {computed[:16]}...")
        else:
            c.fail(f"expected {computed[:16]}..., got {stored[:16]}...")
    else:
        c.fail("hash_chain not present or incomplete")
    checks.append(c)

    return checks


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-contract.json>")
        return 2

    path = sys.argv[1]
    print(f"Validating: {path}")
    print("=" * 60)

    checks = validate(path)

    for chk in checks:
        print(str(chk))

    all_pass = all(chk.passed for chk in checks)
    failures = sum(1 for chk in checks if not chk.passed)

    print("=" * 60)
    if all_pass:
        print(f"RESULT: ALL {len(checks)} CHECKS PASSED")
    else:
        print(f"RESULT: {failures} OF {len(checks)} CHECKS FAILED")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
