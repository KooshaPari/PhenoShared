#!/usr/bin/env python3
"""Diff a fresh criterion run vs the BENCHMARKS.md baseline and fail on regression.

Usage:
    python scripts/bench_diff.py <current.json> [--baseline FILE] [--threshold PCT]

Outputs a markdown regression report on stdout. Exits non-zero if any benchmark's
median regressed more than ``--threshold`` percent. The `current.json` file is
produced by `scripts/bench_parse_criterion.py` from `cargo bench` output.

A *regression* is defined as: current median > baseline median * (1 + threshold / 100).
A *new benchmark* (in current, not in baseline) is reported but does NOT trigger
failure (gracefully absorb as the codebase grows).
A *removed benchmark* (in baseline, not in current) is also reported without
failure (we lose the ability to guard it, but the bench count drops).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BENCHMARK_LINE_RE = re.compile(
    r"^\|\s*`(?P<crate>[^`]+)`\s*\|\s*`(?P<name>[^`]+)`\s*\|\s*(?P<median>[\d.]+)"
)


def parse_baseline_md(path: Path) -> dict[tuple[str, str], float]:
    """Extract `(crate, name) -> median_ns` from a BENCHMARKS-style markdown table."""
    out: dict[tuple[str, str], float] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        match = BENCHMARK_LINE_RE.match(line)
        if not match:
            continue
        out[(match["crate"], match["name"])] = float(match["median"])
    return out


def load_current(path: Path) -> dict[tuple[str, str], float]:
    """Load the `(crate, name) -> median_ns` from the parser-produced JSON-lines file."""
    out: dict[tuple[str, str], float] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        out[(row["crate"], row["bench"])] = float(row["value_ns"])
    return out


def render_report(
    baseline: dict[tuple[str, str], float],
    current: dict[tuple[str, str], float],
    threshold_pct: float,
) -> tuple[str, list[tuple[str, str, float, float, float]]]:
    """Return (markdown_report, list_of_regression_records)."""
    regressions: list[tuple[str, str, float, float, float]] = []
    rows = []
    keys = sorted(set(baseline) | set(current))
    for key in keys:
        base = baseline.get(key)
        cur = current.get(key)
        if base is None and cur is not None:
            rows.append((key[0], key[1], cur, None, 0.0))
            continue
        if cur is None and base is not None:
            rows.append((key[0], key[1], None, base, 0.0))
            continue
        if base is None or cur is None:
            continue
        if base == 0:
            pct = 0.0 if cur == 0 else 100.0 * cur / max(base, 1e-9)
        else:
            pct = 100.0 * (cur - base) / base
        if pct > threshold_pct:
            regressions.append((key[0], key[1], base, cur, pct))
        rows.append((key[0], key[1], cur, base, pct))

    out = [
        "# Bench regression report",
        "",
        f"Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        f"Threshold: {threshold_pct:.2f}% regression allowed before failure",
        "",
        f"Total benchmarks: {len(rows)} | regressions: {len(regressions)}",
        "",
        "| Crate | Bench | Current (ns) | Baseline (ns) | Δ% |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for crate, name, cur, base, pct in rows:
        cur_s = f"{cur:.3f}" if cur is not None else "(removed)"
        base_s = f"{base:.3f}" if base is not None else "(new)"
        flag = " <-- REGRESSION" if pct > threshold_pct else ""
        out.append(
            f"| `{crate}` | `{name}` | {cur_s} | {base_s} | {pct:+.2f}%{flag} |"
        )

    if regressions:
        out.append("")
        out.append("## ❌ Regressions requiring review")
        out.append("")
        for crate, name, base, cur, pct in regressions:
            out.append(
                f"- `{crate}`::`{name}` — baseline {base:.3f}ns → current "
                f"{cur:.3f}ns ({pct:+.2f}%)"
            )
    else:
        out.append("")
        out.append("## ✅ No regressions")

    return "\n".join(out) + "\n", regressions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", type=Path, help="Path to parsed current bench JSONL")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("BENCHMARKS.md"),
        help="Path to the baseline BENCHMARKS.md (default: ./BENCHMARKS.md)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Regression threshold percentage (default: 5.0)",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        help="Optional path to write the report. Defaults to stdout.",
    )
    args = parser.parse_args()

    baseline = parse_baseline_md(args.baseline)
    current = load_current(args.current)

    report, regressions = render_report(baseline, current, args.threshold)

    if args.report_out:
        args.report_out.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
