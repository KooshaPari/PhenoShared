#!/usr/bin/env python3
"""Snapshot the local pheno-harness SOTA surface once a day.

Captures a JSON envelope describing the current state of:

- `bench/results/` — most recent matrix / ablation runs (top N)
- `kernels/qwen3.5-0.8b/build/` — `kernels.metallib` mtime + size
- `libpheno_qwen.dylib` — mtime + size (if present at repo root)
- `cargo/zig` latest commit hashes (heads only)

Output: ``bench/results/sota/<date>/snapshot.json`` plus a SHA-256
file ``snapshot.sha256`` for tamper-evidence.

This is the **5-day SOTA evolution tracker** mentioned in
``docs/superpowers/specs/``.  Each snapshot is independently verifiable
via the SHA file — diff two snapshots with ``diff -u`` or the
``scripts/cron/diff_snapshots.py`` helper.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_ROOT = REPO_ROOT / "bench" / "results" / "sota"


def _sha256_file(p: Path) -> str:
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _discover_variant_reports(child: Path) -> dict[str, dict[str, Any]]:
    """Find ``evaluation_report{,-<variant>}.json`` files and read them.

    Returns ``{variant_label: {n_cells, source_file}}`` for each variant
    report found (the unstamped ``evaluation_report.json`` is treated as the
    ``primary`` variant — typically the v0.1 smoke path).
    """
    out: dict[str, dict[str, Any]] = {}
    candidates: list[tuple[str, Path]] = []

    primary = child / "evaluation_report.json"
    if primary.is_file():
        candidates.append(("primary", primary))

    for path in sorted(child.glob("evaluation_report-*.json")):
        suffix = path.stem[len("evaluation_report-") :]
        if suffix and path.is_file():
            candidates.append((suffix, path))

    seen: set[str] = set()
    for label, path in candidates:
        if label in seen:
            continue
        seen.add(label)
        try:
            report = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(report, dict):
            continue

        n_cells: int | None = None
        run_variant = (report.get("run") or {}).get("variant")
        totals = report.get("totals") or {}
        if isinstance(totals, dict) and isinstance(totals.get("cells"), (int, float)):
            n_cells = int(totals["cells"])

        key = str(run_variant) if run_variant else label
        out[str(key)] = {
            "n_cells": n_cells,
            "source_file": path.name,
            "report_pass_at_1": (
                (totals or {}).get("pass_at_1") if isinstance(totals, dict) else None
            ),
        }
    return out


def _latest_results(output_root: Path, limit: int) -> list[dict[str, Any]]:
    if not output_root.is_dir():
        return []
    runs: list[dict[str, Any]] = []
    for child in sorted(output_root.iterdir()):
        if not child.is_dir():
            continue
        run_files: list[Path] = []
        for f in (
            "cells.json",
            "evaluation_report.json",
            "per_cell.jsonl",
            "matrix.md",
        ):
            if (child / f).is_file():
                run_files.append(child / f)
        if not run_files:
            continue
        variant_reports = _discover_variant_reports(child)

        # Cells envelope fallback: { summary: { by_variant: { name: { n_cells } } } }
        n_cells: int | None = None
        variants: list[str] = []
        if variant_reports:
            n_cells = sum(v.get("n_cells") or 0 for v in variant_reports.values())
            variants = sorted(variant_reports.keys())
        cells_env = child / "cells.json"
        if cells_env.is_file():
            try:
                env = json.loads(cells_env.read_text())
                summary = env.get("summary") or {}
                byv = summary.get("by_variant") or {}
                if isinstance(byv, dict) and byv:
                    if not variants:
                        variants = list(byv.keys())
                        for v in byv.values():
                            if isinstance(v, dict) and isinstance(
                                v.get("n_cells"), (int, float)
                            ):
                                n_cells = (n_cells or 0) + int(v["n_cells"])
            except Exception:
                pass

        runs.append(
            {
                "run_id": child.name,
                "path": str(child.relative_to(REPO_ROOT)),
                "mtime": datetime.datetime.fromtimestamp(
                    child.stat().st_mtime, tz=datetime.UTC
                ).isoformat(),
                "artifacts": [f.name for f in run_files],
                "variants": variants,
                "n_cells": n_cells,
                "variant_reports": {
                    k: {
                        "n_cells": v.get("n_cells"),
                        "pass_at_1": v.get("report_pass_at_1"),
                        "source_file": v.get("source_file"),
                    }
                    for k, v in sorted(variant_reports.items())
                },
            }
        )
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs[:limit]


def _file_inventory(label: str, p: Path) -> dict[str, Any] | None:
    if not p.is_file():
        return None
    st = p.stat()
    return {
        "label": label,
        "path": str(p.relative_to(REPO_ROOT)) if p.is_absolute() else str(p),
        "size_bytes": st.st_size,
        "mtime": datetime.datetime.fromtimestamp(
            st.st_mtime, tz=datetime.UTC
        ).isoformat(),
        "sha256": _sha256_file(p),
    }


def _same_day_file_inventory(out_dir: Path) -> list[dict[str, str | int]]:
    """Return a stable inventory of non-self snapshot artifacts for ``out_dir``."""
    excluded = {"snapshot.json", "snapshot.sha256"}
    files = [
        path
        for path in out_dir.rglob("*")
        if path.is_file() and path.relative_to(out_dir).as_posix() not in excluded
    ]
    return [
        {
            "path": path.relative_to(out_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in sorted(files, key=lambda path: path.relative_to(out_dir).as_posix())
    ]


def _git_head() -> str | None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def take_snapshot(
    out_root: Path = DEFAULT_OUT_ROOT,
    *,
    bench_results_glob: str = "ablation,comparison,local-qwen,stock-vs-ours",
    recent_runs: int = 5,
    snapshot_date: str | None = None,
    backfill: bool = False,
    backfill_note: str | None = None,
) -> Path:
    if snapshot_date is None:
        today = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d")
    else:
        # Validate the YYYY-MM-DD shape so a typo doesn't silently write to
        # the wrong directory.
        datetime.datetime.strptime(snapshot_date, "%Y-%m-%d")
        today = snapshot_date
    out_dir = out_root / today
    out_dir.mkdir(parents=True, exist_ok=True)

    # Recent runs across multiple bench/results subtrees
    runs: list[dict[str, Any]] = []
    for sub in bench_results_glob.split(","):
        sub = sub.strip()
        if not sub:
            continue
        runs.extend(
            _latest_results(REPO_ROOT / "bench" / "results" / sub, limit=recent_runs)
        )
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    runs = runs[: recent_runs * max(1, len(bench_results_glob.split(",")))]

    metallib = REPO_ROOT / "kernels" / "qwen3.5-0.8b" / "build" / "kernels.metallib"
    # Probe both candidate dylib locations — the historical root path
    # (legacy hand-built artifact) and the canonical kernels/*/build/ path
    # (build_dylib.sh output). Pick whichever exists; record both in the
    # envelope for downstream diff visibility.
    dylib_root = REPO_ROOT / "libpheno_qwen.dylib"
    dylib_build = (
        REPO_ROOT / "kernels" / "qwen3.5-0.8b" / "build" / "libpheno_qwen.dylib"
    )
    dylib = dylib_root if dylib_root.is_file() else dylib_build

    snapshot = {
        "snapshot_date": today,
        "snapshot_taken_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "git_head": _git_head(),
        "evidence_label": "backfilled" if backfill else "live verified",
        "backfill_note": backfill_note,
        "kernels": {
            "metallib": _file_inventory("kernels.metallib", metallib),
            "dylib": _file_inventory("libpheno_qwen.dylib", dylib),
            "dylib_candidates": {
                "root": _file_inventory("libpheno_qwen.dylib", dylib_root),
                "build": _file_inventory("libpheno_qwen.dylib", dylib_build),
            },
        },
        "recent_runs": runs,
        "same_day_files": _same_day_file_inventory(out_dir),
        "schema_version": "0.1.0",
    }

    snap_path = out_dir / "snapshot.json"
    snap_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")

    sha = hashlib.sha256(snap_path.read_bytes()).hexdigest()
    (out_dir / "snapshot.sha256").write_text(f"{sha}  snapshot.json\n")

    return snap_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUT_ROOT,
        help=f"snapshot output root (default: {DEFAULT_OUT_ROOT})",
    )
    parser.add_argument(
        "--recent-runs",
        type=int,
        default=5,
        help="how many runs per bench/results subdir to embed",
    )
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "snapshot date as YYYY-MM-DD; default is today (UTC). "
            "When set, the snapshot is labeled evidence_label='backfilled' "
            "unless --live is also passed."
        ),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Force evidence_label='live verified' even when --date is set. "
            "Use only when the build state truly matches the named date."
        ),
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help=(
            "Explicitly mark the snapshot as backfilled. Requires --date. "
            "When set, evidence_label='backfilled' is forced regardless "
            "of --live. Use this instead of relying on the implicit "
            "backfill behaviour of --date (which is overridden by --live)."
        ),
    )
    parser.add_argument(
        "--backfill-note",
        default=None,
        help=(
            "Optional free-text note recorded in the snapshot envelope, "
            "explaining why this date is being backfilled. Recorded only "
            "when --date is set and --live is not."
        ),
    )
    args = parser.parse_args(argv)

    if args.backfill and not args.date:
        parser.error("--backfill requires --date")
    is_backfill = (bool(args.date) and not args.live) or args.backfill
    snap = take_snapshot(
        args.out_root,
        recent_runs=args.recent_runs,
        snapshot_date=args.date,
        backfill=is_backfill,
        backfill_note=args.backfill_note,
    )
    label = "backfilled" if is_backfill else "live verified"
    try:
        snap_rel = snap.relative_to(REPO_ROOT)
    except ValueError:
        snap_rel = snap
    print(f"wrote {snap_rel} (evidence_label={label})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
