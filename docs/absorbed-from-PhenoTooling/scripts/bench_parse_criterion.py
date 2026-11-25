#!/usr/bin/env python3
"""Parse a Criterion `cargo bench` run into a flat list of records.

Invocation:
    python scripts/bench_parse_criterion.py <bench_output.{json,txt}>

Where the input is one of:

  1. Criterion `--output-format json` JSON document (list of records).
  2. Direct dict: ``{"<crate>::<bench>::<sample>": {"value": <ns>, ...}, ...}``
  3. `cargo bench --output-format bencher` plain text: lines matching
     ``test <benchmark-path> ... bench: <value> ns/iter (+/- <noise>)``
     (the stable Rust bencher formatter). Used by ci-bench.yml today.
  4. Plain-text variant emitted by `cargo bench -- --bench` when binary
     is invoked directly without Criterion. Same line shape as #3.

The output is JSONL on stdout: one record per benchmark, sorted by
(crate, bench), suitable for `bench_diff.py` to consume.

We deliberately avoid `cargo bench --format json-stream` (unstable) and
accept the stable plain-text bencher format as a first-class input so
the WP-08 nightly bench CI doesn't gate on a nightly Cargo feature.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Stable ordering for reproducibility.
OUT_KEYS = ("crate", "bench", "value_ns", "lower_ns", "upper_ns", "unit")

# Lines from `cargo bench --output-format bencher` look like:
#   test diff_lines_apply_dense ... bench:        1,234 ns/iter (+/- 56)
#   test group::name  ... bench:      12,345 ns/iter (+/- 100) = 0 ms
# Capture the bench path and the central value.
_BENCHER_LINE = re.compile(
    r"^test\s+(?P<path>[A-Za-z0-9_:]+)\s+\.\.\.\s+bench:\s+"
    r"(?P<value>[0-9,]+)\s+ns/iter\s+\(\+/-\s*(?P<noise>[0-9,]+)\)",
    re.MULTILINE,
)

# Some benches emit microsecond or picosecond units.
_UNIT_LINE = re.compile(
    r"^test\s+(?P<path>[A-Za-z0-9_:]+)\s+\.\.\.\s+bench:\s+"
    r"(?P<value>[0-9,.]+)\s+(?P<unit>[a-zµμ]+)/iter\s+\(\+/-\s*(?P<noise>[0-9,.]+)\)",
    re.MULTILINE,
)


def _ns_from(value: str, unit: str) -> float:
    """Convert a numeric value in `unit` (ns / µs / us / ms / ps) to nanoseconds."""
    v = float(value.replace(",", ""))
    u = unit.lower().replace("μ", "u").replace("µ", "u")
    if u == "ns":
        return v
    if u == "us" or u == "µs":
        return v * 1_000.0
    if u == "ms":
        return v * 1_000_000.0
    if u == "ps":
        return v / 1_000.0
    return v


def _parse_bencher_text(text: str) -> list[dict]:
    rows: list[dict] = []
    # Prefer the unit-aware regex when present; fall back to ns/iter.
    for match in _UNIT_LINE.finditer(text):
        path = match.group("path")
        value = match.group("value")
        unit = match.group("unit")
        noise = match.group("noise")
        value_ns = _ns_from(value, unit)
        noise_ns = _ns_from(noise, unit)
        parts = path.split("::")
        if len(parts) < 2:
            continue
        rows.append(
            {
                "crate": parts[0],
                "bench": parts[1],
                "value_ns": value_ns,
                "lower_ns": max(value_ns - noise_ns, 0.0),
                "upper_ns": value_ns + noise_ns,
                "unit": "ns",
            }
        )
    if rows:
        return sorted(rows, key=lambda r: (r["crate"], r["bench"]))
    for match in _BENCHER_LINE.finditer(text):
        path = match.group("path")
        value = match.group("value")
        noise = match.group("noise")
        value_ns = float(value.replace(",", ""))
        noise_ns = float(noise.replace(",", ""))
        parts = path.split("::")
        if len(parts) < 2:
            continue
        rows.append(
            {
                "crate": parts[0],
                "bench": parts[1],
                "value_ns": value_ns,
                "lower_ns": max(value_ns - noise_ns, 0.0),
                "upper_ns": value_ns + noise_ns,
                "unit": "ns",
            }
        )
    return sorted(rows, key=lambda r: (r["crate"], r["bench"]))


def parse(path: Path) -> list[dict]:
    """Dispatch to the right parser based on file shape."""
    text = path.read_text(encoding="utf-8")
    # Bencher plain text starts with "test ..." lines.
    if text.lstrip().startswith("test") or _BENCHER_LINE.search(text) or _UNIT_LINE.search(text):
        return _parse_bencher_text(text)
    # Otherwise try JSON.
    raw = json.loads(text)
    rows: list[dict] = []

    # Shape 1: flat dict where key is "<crate>::<bench>::<sample>"
    if isinstance(raw, dict):
        for key, val in raw.items():
            parts = key.split("::")
            if len(parts) < 2:
                continue
            if not isinstance(val, dict):
                continue
            value = val.get("value") or val.get("median") or val.get("point_estimate")
            if value is None:
                continue
            rows.append(
                {
                    "crate": parts[0],
                    "bench": parts[1],
                    "value_ns": float(value),
                    "lower_ns": float(val.get("lower", val.get("lower_bound", value))),
                    "upper_ns": float(val.get("upper", val.get("upper_bound", value))),
                    "unit": str(val.get("unit", "ns")),
                }
            )
        return sorted(rows, key=lambda r: (r["crate"], r["bench"]))

    # Shape 2: criterion's own JSON output. Expect a list of records.
    if isinstance(raw, list):
        for record in raw:
            full_id = record.get("full_id") or record.get("name") or ""
            parts = full_id.split("::")
            if len(parts) < 2:
                continue
            estimate = record.get("estimate") or record.get("median") or {}
            value = estimate.get("value") or estimate.get("median") or record.get("value")
            if value is None:
                continue
            rows.append(
                {
                    "crate": parts[0],
                    "bench": parts[1],
                    "value_ns": float(value),
                    "lower_ns": float(estimate.get("lower", value)),
                    "upper_ns": float(estimate.get("upper", value)),
                    "unit": str(estimate.get("unit", "ns")),
                }
            )
        return sorted(rows, key=lambda r: (r["crate"], r["bench"]))

    raise ValueError(f"Unsupported root shape: {type(raw).__name__}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    rows = parse(Path(sys.argv[1]).resolve())
    for row in rows:
        print(json.dumps({k: row[k] for k in OUT_KEYS}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
