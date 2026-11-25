#!/usr/bin/env python3
"""scripts/cockpit_migrator.py — migrate beads.jsonl to AgilePlus + Tracera.

v0.13 WBS-PERT-100 Phase 5 task 68 — cockpit-migrator script.

Reads append-only beads from `phenotype-dag/beads.jsonl` and forwards
each to the configured backend:

- `--backend=agileplus` (default): posts each bead via
  `AgilePlusBeadStore.append()` (idempotent on hash dedup).
- `--backend=tracera`: posts each event via
  `TraceraAdapter.append_event()` (used for trace ingestion).
- `--backend=dual`: writes to both backends (mirrors the cockpit
  dual-write semantics into the production stack).

Modes:
- `--dry-run` (default): read beads.jsonl, print migration plan, do
  not mutate any backend. Exit code 0 if plan looks healthy.
- `--execute`: actually post beads to the backend(s).
- `--verify`: check that the configured backend has every bead ID
  present in beads.jsonl.

Batch:
- `--batch=N`: send N beads per request (default 50). Used with
  `--backend=agileplus --execute` to call `bulk_append()` instead of
  `append()`. Pass `--batch=1` to disable batching.

Source path:
- `--source=PATH`: read from a custom JSONL path. Default is
  `~/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl`. Set to
  `/dev/null` for testing.

Refs:
- beads/agileplus_adapter/agileplus_adapter.py (AgilePlusBeadStore).
- pheno/trace_store/tracera.py (TraceraAdapter).
- docs/cockpit/deprecation-ladder.md (design + mapping).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Imported lazily inside functions; module-level imports kept here only
# for type-checkers.


# Default source path (matches the cockpit renderer's input).
DEFAULT_SOURCE = (
    Path.home()
    / "CodeProjects"
    / "Phenotype"
    / "repos"
    / "phenotype-dag"
    / "beads.jsonl"
)


def _bootstrap_path() -> None:
    """Add repo root (parent of scripts/) to sys.path so `beads` and
    `pheno` packages resolve when the script is run directly.

    No-op when imports already succeed (e.g. when PYTHONPATH is set).
    """
    if "beads" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parent.parent
    candidate = str(repo_root)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


# Field mapping: cockpit → AgilePlus Bead (subset of fields).
# Bead dataclass: id, ts, agent, kind, target, text, hash, host, metadata.
# All other cockpit fields (session, frId, outcome, state, ...)
# route through `metadata`.
COCKPIT_TO_AGILEPLUS = (
    "id",
    "ts",
    "agent",
    "kind",
    "target",
    "text",
    "hash",
    "host",
)

# Field mapping: cockpit → Tracera event payload.
# TraceEvent has top-level fields id, kind, ts, actor, target, session_id,
# payload. Everything else (text, hash, host, frId, outcome, state, ...) lands
# in `payload`.
COCKPIT_TO_TRACERA_TOP = (
    "kind",
    "ts",
    "agent",
    "session",
)


@dataclass
class MigrationStats:
    """Counters for one migration run."""

    read: int = 0
    forwarded: int = 0
    skipped_duplicate: int = 0
    failed: int = 0
    duration_s: float = 0.0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: MigrationStats) -> None:
        self.read += other.read
        self.forwarded += other.forwarded
        self.skipped_duplicate += other.skipped_duplicate
        self.failed += other.failed
        self.duration_s += other.duration_s
        self.errors.extend(other.errors)


def _read_beads(source: Path) -> list[dict[str, Any]]:
    """Read every bead from the JSONL source."""
    _bootstrap_path()
    if not source.exists():
        return []
    beads: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as fp:
        for line_no, raw in enumerate(fp, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                bead = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {source}:{line_no}: {exc}") from exc
            if not isinstance(bead, dict):
                raise ValueError(
                    f"non-dict bead at {source}:{line_no}: {type(bead).__name__}"
                )
            if "id" not in bead:
                raise ValueError(f"bead at {source}:{line_no} missing 'id'")
            beads.append(bead)
    return beads


def _build_agileplus_bead(raw: dict[str, Any]) -> Any:
    """Construct an AgilePlus Bead from a cockpit raw bead."""
    _bootstrap_path()
    from beads.agileplus_adapter.agileplus_adapter import Bead

    metadata: dict[str, Any] = {}
    # Anything not in the explicit field list lands in metadata.
    for key, value in raw.items():
        if key in COCKPIT_TO_AGILEPLUS:
            continue
        metadata[key] = value

    return Bead(
        id=str(raw["id"]),
        ts=raw["ts"],
        agent=raw.get("agent", "unknown"),
        kind=raw.get("kind", "unknown"),
        target=raw.get("target", ""),
        text=raw.get("text", ""),
        hash=raw.get("hash", "")[:8],
        host=raw.get("host", ""),
        metadata=metadata,
    )


def _build_tracera_event(raw: dict[str, Any]) -> Any:
    """Construct a Tracera TraceEvent from a cockpit raw bead."""
    _bootstrap_path()
    from datetime import datetime
    from uuid import uuid4

    from pheno.trace_store import TraceEvent

    # Try to parse ts; fall back to "now" if invalid.
    ts_raw = raw.get("ts", "")
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except ValueError:
        ts = datetime.now().astimezone()

    payload: dict[str, Any] = {
        "bead_id": str(raw.get("id", "")),
        "bead_hash": raw.get("hash", "")[:8],
    }
    for key, value in raw.items():
        if key in COCKPIT_TO_TRACERA_TOP:
            continue
        payload[key] = value

    return TraceEvent(
        id=uuid4(),
        kind=str(raw.get("kind", "unknown")),
        ts=ts,
        actor=str(raw.get("agent", "unknown")),
        target=raw.get("target"),
        session_id=raw.get("session"),
        payload=payload,
    )


def migrate_dry_run(
    beads: list[dict[str, Any]],
    *,
    backend: str,
    batch_size: int,
) -> MigrationStats:
    """Print the migration plan without mutating any backend."""
    stats = MigrationStats()
    stats.read = len(beads)
    batch_count = (len(beads) + batch_size - 1) // batch_size if beads else 0
    print(
        f"[dry-run] backend={backend} beads={len(beads)} batch_size={batch_size} "
        f"batches={batch_count}",
        file=sys.stderr,
    )
    stats.forwarded = 0  # dry-run forwards nothing
    return stats


def migrate_execute_agileplus(
    beads: list[dict[str, Any]],
    *,
    batch_size: int,
    source: Path,
    store: Any | None = None,
) -> MigrationStats:
    """Execute migration to AgilePlus. Idempotent via dedup_check().

    If ``store`` is supplied (test path), use it directly; otherwise
    construct a real AgilePlusBeadStore from env vars.
    """
    from beads.agileplus_adapter.agileplus_adapter import AgilePlusBeadStore as _AP

    stats = MigrationStats()
    stats.read = len(beads)
    if not beads:
        return stats

    started = time.monotonic()
    if store is None:
        store = _AP(
            base_url=os.environ.get("AGILEPLUS_BASE_URL", "http://127.0.0.1:8080"),
            token=os.environ.get("AGILEPLUS_API_TOKEN"),
        )

    # Decide batch strategy.
    if batch_size <= 1:
        # Single appends; honor dedup.
        for raw in beads:
            try:
                ap_bead = _build_agileplus_bead(raw)
                if store.dedup_check(ap_bead):
                    stats.skipped_duplicate += 1
                    continue
                store.append(ap_bead)
                stats.forwarded += 1
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                stats.errors.append(
                    f"id={raw.get('id', '?')} failed: {type(exc).__name__}: {exc}"
                )
    else:
        # Bulk appends; dedup is left to the server (idempotent on hash).
        for i in range(0, len(beads), batch_size):
            chunk = beads[i : i + batch_size]
            try:
                ap_beads = [_build_agileplus_bead(raw) for raw in chunk]
                store.bulk_append(ap_beads)
                stats.forwarded += len(ap_beads)
            except Exception as exc:  # noqa: BLE001
                stats.failed += len(chunk)
                stats.errors.append(
                    f"batch {i // batch_size + 1} (size={len(chunk)}) failed: "
                    f"{type(exc).__name__}: {exc}"
                )

    stats.duration_s = time.monotonic() - started
    return stats


def migrate_execute_tracera(
    beads: list[dict[str, Any]],
    *,
    adapter: Any | None = None,
) -> MigrationStats:
    """Execute migration to Tracera. Best-effort, never raises.

    If ``adapter`` is supplied (test path), use it directly.
    """
    from pheno.trace_store import TraceraAdapter as _TA

    stats = MigrationStats()
    stats.read = len(beads)
    if not beads:
        return stats

    started = time.monotonic()
    if adapter is None:
        adapter = _TA(
            host=os.environ.get("TRACERA_HOST", "127.0.0.1"),
            port=int(os.environ.get("TRACERA_PORT", "8080")),
            base_url=os.environ.get("TRACERA_BASE_URL"),
            token=os.environ.get("TRACERA_API_TOKEN"),
        )

    for raw in beads:
        try:
            event = _build_tracera_event(raw)
            adapter.append_event(event)
            stats.forwarded += 1
        except Exception as exc:  # noqa: BLE001
            stats.failed += 1
            stats.errors.append(
                f"id={raw.get('id', '?')} failed: {type(exc).__name__}: {exc}"
            )
    stats.duration_s = time.monotonic() - started
    return stats


def migrate_execute_dual(
    beads: list[dict[str, Any]],
    *,
    batch_size: int,
    source: Path,
) -> MigrationStats:
    """Execute migration to both AgilePlus + Tracera."""
    a = migrate_execute_agileplus(beads, batch_size=batch_size, source=source)
    t = migrate_execute_tracera(beads)
    combined = MigrationStats()
    combined.merge(a)
    combined.merge(t)
    return combined


def verify(
    beads: list[dict[str, Any]],
    *,
    backend: str,
    store: Any | None = None,
) -> MigrationStats:
    """Verify the backend has every bead id from beads.jsonl."""
    from beads.agileplus_adapter.agileplus_adapter import AgilePlusBeadStore as _AP

    stats = MigrationStats()
    stats.read = len(beads)
    if not beads:
        return stats

    if backend not in ("agileplus",):
        print(f"[verify] backend={backend} not supported yet", file=sys.stderr)
        stats.failed = len(beads)
        return stats

    if store is None:
        store = _AP(
            base_url=os.environ.get("AGILEPLUS_BASE_URL", "http://127.0.0.1:8080"),
            token=os.environ.get("AGILEPLUS_API_TOKEN"),
        )
    missing: list[str] = []
    for raw in beads:
        try:
            ap_bead = _build_agileplus_bead(raw)
            if store.dedup_check(ap_bead):
                stats.forwarded += 1
            else:
                missing.append(str(raw.get("id", "?")))
        except Exception as exc:  # noqa: BLE001
            stats.failed += 1
            stats.errors.append(
                f"id={raw.get('id', '?')} verify failed: {type(exc).__name__}: {exc}"
            )
    if missing:
        print(
            f"[verify] {len(missing)} missing: {missing[:10]}{'...' if len(missing) > 10 else ''}",
            file=sys.stderr,
        )
    return stats


def _print_summary(stats: MigrationStats, *, mode: str) -> None:
    print(
        f"[{mode}] read={stats.read} forwarded={stats.forwarded} "
        f"skipped_dup={stats.skipped_duplicate} failed={stats.failed} "
        f"duration_s={stats.duration_s:.3f}",
        file=sys.stderr,
    )
    for err in stats.errors[:10]:
        print(f"  err: {err}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    _bootstrap_path()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"path to beads.jsonl (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--backend",
        choices=["agileplus", "tracera", "dual"],
        default="agileplus",
        help="destination backend (default: agileplus)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=50,
        help="batch size for bulk_append (default: 50; 1 = single appends)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="read beads.jsonl, print plan, do not mutate (default)",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="actually post beads to the backend(s)",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="check that the backend has every bead id present",
    )
    args = parser.parse_args(argv)

    beads = _read_beads(args.source)

    if args.verify:
        stats = verify(beads, backend=args.backend)
        _print_summary(stats, mode="verify")
        return 0 if stats.failed == 0 else 1

    if args.execute:
        if args.backend == "agileplus":
            stats = migrate_execute_agileplus(
                beads,
                batch_size=args.batch,
                source=args.source,
            )
        elif args.backend == "tracera":
            stats = migrate_execute_tracera(beads)
        else:
            stats = migrate_execute_dual(
                beads,
                batch_size=args.batch,
                source=args.source,
            )
        _print_summary(stats, mode="execute")
        return 0 if stats.failed == 0 else 2

    # default: dry-run
    stats = migrate_dry_run(
        beads,
        backend=args.backend,
        batch_size=args.batch,
    )
    _print_summary(stats, mode="dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
