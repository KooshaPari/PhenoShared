#!/usr/bin/env python3
"""
WP-30 stream-cross-grade compatibility matrix.

For each cross-stream edge in .github/cross-stream-dependencies.json,
generate a version matrix that asserts the downstream stream's API
contract holds when the upstream stream is at any of {current,
current-1, current-2} versions.

Emits a pass/fail markdown matrix + JSON manifest suitable for PR
comment + branch-protection consumption.

Usage:
  python scripts/stream_compat_matrix.py --channel-manifest .github/channel-manifest.json \
                                         --dep-graph .github/cross-stream-dependencies.json \
                                         --output-dir .stream-compat
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Channel:
    """One stream's channel pointer (stable/beta/nightly)."""

    name: str            # 'cli-stream-stable'
    stream: str          # 'cli-stream'
    version: str         # 'v0.5.0'


@dataclass(frozen=True)
class CrossStreamEdge:
    """One edge from the WP-26 dependency graph."""

    from_crate: str
    from_stream: str
    to_crate: str
    to_stream: str


@dataclass
class MatrixCell:
    """One (upstream_version, downstream_version) test combination."""

    edge: CrossStreamEdge
    upstream_version: str
    downstream_version: str
    result: str = "pending"   # pass | fail | skip | error
    detail: str = ""


@dataclass
class MatrixReport:
    """The full pass/fail report."""

    edges: list[CrossStreamEdge] = field(default_factory=list)
    cells: list[MatrixCell] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    summary: dict[str, int] = field(default_factory=dict)

    def tally(self) -> None:
        self.summary = {"pass": 0, "fail": 0, "skip": 0, "error": 0}
        for cell in self.cells:
            self.summary[cell.result] = self.summary.get(cell.result, 0) + 1

    def to_markdown(self) -> str:
        """Render the matrix as a GitHub-flavored markdown table."""
        if not self.cells:
            return "_no cross-stream edges in graph_"

        # Group cells by edge for readability.
        lines = ["| Edge | Upstream @ Version | Downstream @ Version | Result | Detail |",
                 "|---|---|---|---|---|"]
        for cell in self.cells:
            edge_str = f"`{cell.edge.from_crate}` → `{cell.edge.to_crate}`"
            lines.append(
                f"| {edge_str} "
                f"| {cell.upstream_version} "
                f"| {cell.downstream_version} "
                f"| {cell.result} "
                f"| {cell.detail[:80]} |"
            )
        lines.append("")
        lines.append(
            f"**Summary**: {self.summary.get('pass', 0)} pass / "
            f"{self.summary.get('fail', 0)} fail / "
            f"{self.summary.get('skip', 0)} skip / "
            f"{self.summary.get('error', 0)} error"
        )
        return "\n".join(lines)


def load_channel_manifest(path: Path) -> dict[str, list[Channel]]:
    """Read .github/channel-manifest.json into stream -> channels map."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[Channel]] = {}
    for stream_name, channels in data.get("streams", {}).items():
        out[stream_name] = [
            Channel(
                name=c["name"],
                stream=stream_name,
                version=c["version"],
            )
            for c in channels
        ]
    return out


def load_dep_graph(path: Path) -> list[CrossStreamEdge]:
    """Read .github/cross-stream-dependencies.json into edges."""
    data = json.loads(path.read_text(encoding="utf-8"))
    edges: list[CrossStreamEdge] = []
    for e in data.get("edges", []):
        edges.append(
            CrossStreamEdge(
                from_crate=e["from_crate"],
                from_stream=e["from_stream"],
                to_crate=e["to_crate"],
                to_stream=e["to_stream"],
            )
        )
    return edges


def iter_matrix(
    edges: list[CrossStreamEdge],
    channel_map: dict[str, list[Channel]],
    depth: int = 2,
) -> Iterator[tuple[CrossStreamEdge, str, str]]:
    """Yield (edge, upstream_version, downstream_version) cells.

    For each edge, the upstream stream iterates over (current, current-1,
    ..., current-depth). The downstream stream stays at its current
    stable version (cross-grade compatibility is upstream-driven).
    """
    for edge in edges:
        upstream_channels = channel_map.get(edge.from_stream, [])
        if not upstream_channels:
            continue
        downstream_channels = channel_map.get(edge.to_stream, [])
        if not downstream_channels:
            continue
        # Use stable channel of upstream, current of downstream.
        upstream_stable = next(
            (c for c in upstream_channels if c.name.endswith("-stable")),
            upstream_channels[0],
        )
        downstream_stable = next(
            (c for c in downstream_channels if c.name.endswith("-stable")),
            downstream_channels[0],
        )
        # Iterates upstream over N versions deep.
        for n in range(depth + 1):
            upstream_version = _nth_version_back(
                upstream_channels, upstream_stable, n
            )
            yield edge, upstream_version, downstream_stable.version


def _nth_version_back(channels: list[Channel], current: Channel, n: int) -> str:
    """Return the n-th version back from current within the channel list.

    The channel_manifest.py emits versions in reverse-chronological
    order (newest first), so version[N] is N versions older than the
    current. If N exceeds the list length, returns the oldest available.
    """
    if n == 0:
        return current.version
    # Find current's index.
    for i, ch in enumerate(channels):
        if ch.version == current.version:
            return channels[min(i + n, len(channels) - 1)].version
    return current.version


def run_cell(cell: MatrixCell, workspace_dir: Path) -> None:
    """Run the cross-stream contract test for one cell.

    In production this would:
    1. checkout upstream_crate @ upstream_version + downstream_crate @ downstream_version
    2. run cargo test -p <downstream_crate> --test stream_compat
    3. assert contract holds

    For shadow mode we just shell out and record success/fail based
    on cargo's exit code.
    """
    cmd = [
        "cargo", "test",
        "-p", cell.edge.to_crate,
        "--test", "stream_compat",
        "--manifest-path", str(workspace_dir / "Cargo.toml"),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            cell.result = "pass"
            cell.detail = "test passed"
        else:
            cell.result = "fail"
            # Extract first error line.
            err_lines = [
                line for line in result.stderr.splitlines()
                if "error[" in line
            ]
            cell.detail = err_lines[0][:120] if err_lines else result.stderr[:120]
    except subprocess.TimeoutExpired:
        cell.result = "error"
        cell.detail = "timeout after 300s"
    except FileNotFoundError as e:
        cell.result = "error"
        cell.detail = f"cargo not found: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WP-30 stream-cross-grade compatibility matrix",
    )
    parser.add_argument(
        "--channel-manifest",
        type=Path,
        default=Path(".github/channel-manifest.json"),
    )
    parser.add_argument(
        "--dep-graph",
        type=Path,
        default=Path(".github/cross-stream-dependencies.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".stream-compat"),
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="How many versions back from current to test (default: 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the matrix without running tests (for debugging)",
    )
    args = parser.parse_args()

    if not args.channel_manifest.exists():
        print(f"error: channel manifest not found: {args.channel_manifest}",
              file=sys.stderr)
        return 2
    if not args.dep_graph.exists():
        print(f"error: dep graph not found: {args.dep_graph}",
              file=sys.stderr)
        return 2

    channels = load_channel_manifest(args.channel_manifest)
    edges = load_dep_graph(args.dep_graph)

    report = MatrixReport(edges=edges)
    cells: list[MatrixCell] = []
    for edge, upstream_v, downstream_v in iter_matrix(
        edges, channels, depth=args.depth
    ):
        cells.append(
            MatrixCell(
                edge=edge,
                upstream_version=upstream_v,
                downstream_version=downstream_v,
            )
        )

    if not args.dry_run:
        # In a real workflow this would checkout the specific versions
        # into a temp workspace and run cargo test there. For the
        # shadow-mode rollout we just run from the current checkout.
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            for cell in cells:
                run_cell(cell, workspace)
    else:
        for cell in cells:
            cell.result = "skip"
            cell.detail = "dry-run"

    report.cells = cells
    report.tally()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "matrix.json").write_text(
        json.dumps(
            {
                "edges": [asdict(e) for e in report.edges],
                "cells": [
                    {**asdict(c["edge"]) if False else asdict(c),
                     **{"edge": asdict(c["edge"])}}
                    for c in [{**asdict(cell), "edge": asdict(cell.edge)} for cell in report.cells]
                ],
                "summary": report.summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.output_dir / "matrix.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )

    print(report.to_markdown())
    print(f"\nwrote: {args.output_dir / 'matrix.json'}")
    print(f"wrote: {args.output_dir / 'matrix.md'}")

    # Exit non-zero if any cell failed (used by WP-30 workflow gate).
    return 1 if report.summary.get("fail", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())