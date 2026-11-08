#!/usr/bin/env python3
"""WP-26: Compute cross-stream dependency edges between release-stream crates.

Reads:
  - workspace.metadata.toml    (group/stream membership)
  - cargo metadata --format-version 1     (per-crate dependency graph)

Emits:
  - .github/cross-stream-dependencies.json
        {
          "edges": [
            {"from_stream": "cli", "from_crate": "phenotype-cli",
             "to_stream": "core", "to_crate": "phenotype-config",
             "kind": "normal"}, ...
          ],
          "summary": {
            "stream_bumps_required": {"core": 0, "cli": 0, "ops": 0},
            "edges_total": 42,
            "cross_stream_edges": 19
          }
        }

Algorithm:
  1. Parse workspace.metadata.toml -> stream_by_crate[crate] = "core"|"cli"|"ops"
  2. Run `cargo metadata --format-version 1 --no-deps` to get the resolved
     workspace member set (skip external deps).
  3. For each workspace crate, read its [dependencies] table. For each
     workspace-internal dependency, record (from_crate, to_crate).
  4. For each edge where from_crate and to_crate are in different streams,
     emit a cross-stream edge. Group edges by (from_stream, to_stream)
     to populate stream_bumps_required when a from_stream gets bumped.

Exit codes:
  0  graph written
  1  cargo metadata failed
  2  workspace.metadata.toml malformed
  3  output write failed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def stream_of(crate: str, group_map: dict[str, str], group_by_stream: dict[str, list[str]]) -> str:
    group = group_map.get(crate)
    if group is None:
        return "unassigned"
    for stream, groups in group_by_stream.items():
        if group in groups:
            return stream
    return "unassigned"


def load_workspace_metadata(path: Path) -> tuple[dict[str, str], dict[str, list[str]], dict[str, str]]:
    """Returns (group_by_crate, streams_by_group, bump_by_group)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = data["workspace"]["metadata"]["release-groups"]
    streams: dict[str, list[str]] = data["workspace"]["metadata"].get("release-streams", {})

    group_by_crate: dict[str, str] = {}
    bump_by_group: dict[str, str] = {}
    for group_name, payload in groups.items():
        bump_by_group[group_name] = payload.get("bump", "minor")
        for crate in payload["members"]:
            group_by_crate[crate] = group_name

    streams_by_group: dict[str, list[str]] = {}
    for stream_name, payload in streams.items():
        streams_by_group[stream_name] = payload["groups"]

    return group_by_crate, streams_by_group, bump_by_group


def cargo_metadata(repo: Path) -> dict:
    """Invoke `cargo metadata` and return parsed JSON."""
    out = subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--no-deps"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        sys.stderr.write(f"cargo metadata failed:\n{out.stderr}\n")
        sys.exit(1)
    return json.loads(out.stdout)


def crate_to_dependencies(meta: dict) -> dict[str, list[str]]:
    """For each workspace member crate, list workspace-internal crate deps."""
    workspace_crates: set[str] = {pkg["name"] for pkg in meta["packages"]}

    deps: dict[str, list[str]] = {}
    for pkg in meta["packages"]:
        name = pkg["name"]
        internal_deps = sorted({
            d["name"]
            for d in pkg.get("dependencies", [])
            if d.get("name") in workspace_crates
        })
        deps[name] = internal_deps
    return deps


def build_edges(
    deps: dict[str, list[str]],
    group_by_crate: dict[str, str],
    streams_by_group: dict[str, list[str]],
) -> list[dict]:
    edges: list[dict] = []
    for src, targets in deps.items():
        src_stream = stream_of(src, group_by_crate, streams_by_group)
        for tgt in targets:
            tgt_stream = stream_of(tgt, group_by_crate, streams_by_group)
            edges.append(
                {
                    "from_crate": src,
                    "from_stream": src_stream,
                    "to_crate": tgt,
                    "to_stream": tgt_stream,
                    "kind": "normal",
                    **(
                        {"cross_stream": True}
                        if src_stream != tgt_stream
                        else {"cross_stream": False}
                    ),
                }
            )
    return edges


def stream_bump_required(edges: list[dict]) -> dict[str, int]:
    """For each from_stream, count distinct target streams it depends on."""
    targets_per_stream: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e["cross_stream"]:
            targets_per_stream[e["from_stream"]].add(e["to_stream"])
    return {stream: len(targets) for stream, targets in targets_per_stream.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        default=".github/cross-stream-dependencies.json",
        type=Path,
        help="Output JSON path (default: .github/cross-stream-dependencies.json)",
    )
    parser.add_argument(
        "--manifest",
        default="workspace.metadata.toml",
        type=Path,
        help="workspace.metadata.toml path (default: workspace.metadata.toml)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 4 if the graph on disk differs from what we compute (CI mode).",
    )
    args = parser.parse_args()

    repo = repo_root()
    metadata_path = repo / args.manifest
    if not metadata_path.is_file():
        sys.stderr.write(f"workspace metadata not found: {metadata_path}\n")
        return 2

    group_by_crate, streams_by_group, _bump_by_group = load_workspace_metadata(metadata_path)
    meta = cargo_metadata(repo)
    deps = crate_to_dependencies(meta)

    edges = build_edges(deps, group_by_crate, streams_by_group)
    cross = sum(1 for e in edges if e["cross_stream"])
    by_stream_targets = stream_bump_required(edges)
    stream_dep_count = Counter(e["from_stream"] for e in edges if e["cross_stream"])

    payload = {
        "schema_version": 1,
        "edges": sorted(edges, key=lambda e: (e["from_stream"], e["from_crate"], e["to_stream"], e["to_crate"])),
        "summary": {
            "edges_total": len(edges),
            "cross_stream_edges": cross,
            "by_from_stream": dict(stream_dep_count),
            "stream_targets_required": by_stream_targets,
        },
    }

    out_path = repo / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2) + "\n"

    if args.check and out_path.is_file():
        existing = out_path.read_text(encoding="utf-8")
        if existing != serialized:
            sys.stderr.write(f"cross-stream graph drift:\n  expected: {out_path}\n  actual:   regenerated\n")
            return 4

    try:
        out_path.write_text(serialized, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"failed to write {out_path}: {exc}\n")
        return 3

    sys.stdout.write(
        f"cross-stream graph: {len(edges)} edges ({cross} cross-stream) -> {out_path}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
