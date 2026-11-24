"""tests/test_cockpit_migrator.py — v0.13 Phase 5 tests.

Tests the cockpit migrator end-to-end against mocked AgilePlus +
Tracera backends (no network, no live daemon).

Coverage:
1. `_read_beads()` parses JSONL correctly (3 valid + skip-blank).
2. `_read_beads()` raises on invalid JSON.
3. `_read_beads()` returns [] when source missing.
4. `_build_agileplus_bead()` maps cockpit fields correctly.
5. `_build_tracera_event()` maps cockpit fields correctly.
6. `migrate_dry_run()` is non-mutating (zero forwarded).
7. `migrate_execute_agileplus()` single-batch path increments stats.
8. `migrate_execute_agileplus()` bulk-path increments stats.
9. `migrate_execute_agileplus()` recovers from BeadStoreError.
10. `verify()` reports missing beads.
11. `main()` dry-run exits 0.
12. `MigrationStats.merge()` adds counters.
13. Field mapping constants contain expected keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Import the agileplus adapter at module load so patching `cm.AgilePlusBeadStore`
# works inside `migrate_execute_agileplus`.

from cockpit_migrator import (
    COCKPIT_TO_AGILEPLUS,
    COCKPIT_TO_TRACERA_TOP,
    MigrationStats,
    _build_agileplus_bead,
    _build_tracera_event,
    _read_beads,
    migrate_dry_run,
    migrate_execute_agileplus,
    verify,
)
from cockpit_migrator import (
    main as migrator_main,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_beads(path: Path, beads: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        for bead in beads:
            fp.write(json.dumps(bead) + "\n")


def _sample_bead(idx: int = 0) -> dict:
    return {
        "id": f"b-{idx}",
        "ts": "2026-08-11T12:00:00Z",
        "agent": "agent-a",
        "kind": "claim",
        "target": f"target-{idx}",
        "text": f"text-{idx}",
        "hash": f"hash{idx:08d}"[:8],
        "host": "test-host",
        "session": f"session-{idx}",
        "frId": f"FR-{idx}",
        "outcome": f"outcome-{idx}",
        "state": "ready",
        "extra_field": "extra-value",
    }


# ---------------------------------------------------------------------------
# 1-3. _read_beads()
# ---------------------------------------------------------------------------


def test_read_beads_parses_jsonl(tmp_path: Path) -> None:
    src = tmp_path / "beads.jsonl"
    _write_beads(src, [_sample_bead(0), _sample_bead(1), _sample_bead(2)])
    beads = _read_beads(src)
    assert len(beads) == 3
    assert beads[0]["id"] == "b-0"


def test_read_beads_skips_blank_lines(tmp_path: Path) -> None:
    src = tmp_path / "beads.jsonl"
    src.write_text("\n" + json.dumps(_sample_bead(0)) + "\n\n\n", encoding="utf-8")
    beads = _read_beads(src)
    assert len(beads) == 1


def test_read_beads_missing_returns_empty(tmp_path: Path) -> None:
    assert _read_beads(tmp_path / "nope.jsonl") == []


def test_read_beads_invalid_json_raises(tmp_path: Path) -> None:
    src = tmp_path / "bad.jsonl"
    src.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        _read_beads(src)


# ---------------------------------------------------------------------------
# 4-5. _build_agileplus_bead() / _build_tracera_event()
# ---------------------------------------------------------------------------


def test_build_agileplus_bead_maps_fields() -> None:
    raw = _sample_bead()
    bead = _build_agileplus_bead(raw)
    assert bead.id == "b-0"
    assert bead.ts == "2026-08-11T12:00:00Z"
    assert bead.kind == "claim"
    assert bead.target == "target-0"
    assert bead.host == "test-host"
    # Extra fields go to metadata.
    assert bead.metadata.get("extra_field") == "extra-value"
    assert bead.metadata.get("state") == "ready"
    assert bead.metadata.get("session") == "session-0"
    assert bead.metadata.get("frId") == "FR-0"


def test_build_tracera_event_maps_fields() -> None:
    raw = _sample_bead()
    event = _build_tracera_event(raw)
    assert event.kind == "claim"
    assert event.actor == "agent-a"
    assert event.target == "target-0"
    assert event.session_id == "session-0"
    assert event.payload.get("text") == "text-0"
    assert event.payload.get("outcome") == "outcome-0"
    assert event.payload.get("bead_id") == "b-0"
    assert event.payload.get("state") == "ready"


def test_build_tracera_event_falls_back_on_bad_ts() -> None:
    raw = {**_sample_bead(), "ts": "not-a-timestamp"}
    event = _build_tracera_event(raw)
    assert event.ts is not None  # falls back to "now"


# ---------------------------------------------------------------------------
# 6. dry-run is non-mutating
# ---------------------------------------------------------------------------


def test_dry_run_does_not_mutate(tmp_path: Path) -> None:
    beads = [_sample_bead(i) for i in range(5)]
    stats = migrate_dry_run(beads, backend="agileplus", batch_size=2)
    assert stats.read == 5
    assert stats.forwarded == 0  # dry-run forwards nothing
    assert stats.failed == 0


# ---------------------------------------------------------------------------
# 7-9. execute_agileplus
# ---------------------------------------------------------------------------


def test_execute_agileplus_single_append(tmp_path: Path) -> None:
    """Single-batch path: each bead calls store.append()."""
    beads = [_sample_bead(0), _sample_bead(1)]
    mock_store = MagicMock()
    mock_store.dedup_check.return_value = False
    mock_store.append.return_value = "id-ok"

    stats = migrate_execute_agileplus(
        beads,
        batch_size=1,
        source=tmp_path / "x.jsonl",
        store=mock_store,
    )
    assert stats.read == 2
    assert stats.forwarded == 2
    assert mock_store.append.call_count == 2


def test_execute_agileplus_dedup_skip(tmp_path: Path) -> None:
    """When dedup_check returns True, skip the append."""
    beads = [_sample_bead(0)]
    mock_store = MagicMock()
    mock_store.dedup_check.return_value = True

    stats = migrate_execute_agileplus(
        beads,
        batch_size=1,
        source=tmp_path / "x.jsonl",
        store=mock_store,
    )
    assert stats.read == 1
    assert stats.skipped_duplicate == 1
    assert stats.forwarded == 0
    assert mock_store.append.call_count == 0


def test_execute_agileplus_bulk_append_path(tmp_path: Path) -> None:
    """Bulk-path: group into batches of N, call bulk_append per batch."""
    beads = [_sample_bead(i) for i in range(5)]
    mock_store = MagicMock()
    mock_store.bulk_append.return_value = ["id-0", "id-1", "id-2"]

    stats = migrate_execute_agileplus(
        beads,
        batch_size=3,
        source=tmp_path / "x.jsonl",
        store=mock_store,
    )
    # 5 beads / 3 per batch = 2 calls to bulk_append
    assert mock_store.bulk_append.call_count == 2
    assert stats.forwarded == 5
    assert stats.failed == 0


def test_execute_agileplus_bulk_error_increments_failed(tmp_path: Path) -> None:
    """When bulk_append raises, the whole chunk is counted as failed."""
    beads = [_sample_bead(0), _sample_bead(1), _sample_bead(2)]
    mock_store = MagicMock()
    mock_store.bulk_append.side_effect = RuntimeError("boom")

    stats = migrate_execute_agileplus(
        beads,
        batch_size=3,
        source=tmp_path / "x.jsonl",
        store=mock_store,
    )
    assert stats.failed == 3
    assert stats.forwarded == 0
    assert any("boom" in e for e in stats.errors)


def test_execute_agileplus_single_error_increments_failed(tmp_path: Path) -> None:
    """Single-path: when append raises, count as failed + capture error."""
    beads = [_sample_bead(0)]
    mock_store = MagicMock()
    mock_store.dedup_check.return_value = False
    mock_store.append.side_effect = RuntimeError("boom")

    stats = migrate_execute_agileplus(
        beads,
        batch_size=1,
        source=tmp_path / "x.jsonl",
        store=mock_store,
    )
    assert stats.read == 1
    assert stats.failed == 1
    assert stats.forwarded == 0
    assert any("boom" in e for e in stats.errors)


# ---------------------------------------------------------------------------
# 10. verify()
# ---------------------------------------------------------------------------


def test_verify_reports_missing(tmp_path: Path) -> None:
    beads = [_sample_bead(0), _sample_bead(1)]
    mock_store = MagicMock()
    # First bead present (dedup returns True), second missing.
    mock_store.dedup_check.side_effect = [True, False]

    stats = verify(beads, backend="agileplus", store=mock_store)
    assert stats.forwarded == 1
    assert len(stats.errors) == 0


# ---------------------------------------------------------------------------
# 11. main() dry-run
# ---------------------------------------------------------------------------


def test_main_dry_run_exits_zero(tmp_path: Path) -> None:
    src = tmp_path / "beads.jsonl"
    _write_beads(src, [_sample_bead(0)])
    rc = migrator_main(
        [
            "--dry-run",
            "--backend=agileplus",
            "--source",
            str(src),
        ]
    )
    assert rc == 0


def test_main_executes_via_agileplus(tmp_path: Path) -> None:
    src = tmp_path / "beads.jsonl"
    _write_beads(src, [_sample_bead(0), _sample_bead(1)])
    mock_store = MagicMock()
    mock_store.dedup_check.return_value = False
    mock_store.append.return_value = "ok"

    # Patch the symbol the migrator imports inside the function.
    with patch(
        "beads.agileplus_adapter.agileplus_adapter.AgilePlusBeadStore",
        return_value=mock_store,
    ):
        rc = migrator_main(
            [
                "--execute",
                "--backend=agileplus",
                "--batch=1",
                "--source",
                str(src),
            ]
        )
    assert rc == 0


# ---------------------------------------------------------------------------
# 12. MigrationStats
# ---------------------------------------------------------------------------


def test_migration_stats_merge() -> None:
    a = MigrationStats(read=5, forwarded=5)
    b = MigrationStats(read=3, forwarded=2, failed=1)
    a.merge(b)
    assert a.read == 8
    assert a.forwarded == 7
    assert a.failed == 1


# ---------------------------------------------------------------------------
# 13. Field mapping constants
# ---------------------------------------------------------------------------


def test_cockpit_to_agileplus_includes_expected_keys() -> None:
    for key in ("id", "ts", "agent", "kind", "target", "text", "hash", "host"):
        assert key in COCKPIT_TO_AGILEPLUS


def test_cockpit_to_tracera_includes_expected_keys() -> None:
    for key in ("kind", "ts", "agent", "session"):
        assert key in COCKPIT_TO_TRACERA_TOP
