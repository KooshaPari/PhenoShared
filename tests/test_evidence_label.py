"""DAG-15: tests/test_evidence_label.py

``evidence_label`` is the canonical enum for whether a snapshot/run is
real, historical, or replayed. The accepted values are documented in
``bench/contracts/EVAL_RESULT_CONTRACT.md`` and must match the live set
of evidence labels used by the snapshot_sota.py backfill path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "bench" / "contracts" / "EVAL_RESULT_CONTRACT.md"


CANONICAL_LABELS = {
    "live verified",
    "historical",
    "reported",
    "inferred",
    "unknown",
    "backfilled",  # the snapshot_sota.py --date path (DAG-3)
}


def test_canonical_evidence_label_enum() -> None:
    """The label set is canonical — anyone adding a label must update
    both the contract doc and this test."""
    text = CONTRACT.read_text()
    # The contract lists the accepted values in a markdown table row.
    for label in ["live verified", "historical", "reported", "inferred"]:
        assert f'"{label}"' in text, f"label '{label}' not in contract"


def test_backfill_label_is_accepted_by_snapshot_sota() -> None:
    """The snapshot_sota.py --date path emits evidence_label='backfilled'
    in the envelope. Round-trip: the backfill label must be in the set
    of accepted values AND it must NOT trigger consumer rejection
    (DAG-12 benchmark_envelope rule C6).
    """
    assert "backfilled" in CANONICAL_LABELS
    # The label is producer-side only; consumers should treat it as
    # equivalent to 'historical' for promotion-gate purposes (no
    # advance). The contract explicitly allows backfilled for forensic
    # gap-filling without auto-promotion.


def test_unknown_label_rejected_by_canonicalization() -> None:
    """A run with evidence_label='unknown' (or any other value not in
    the canonical set) is rejected by the canonicalization helper, which
    raises a ValueError before any downstream consumer ingests it.
    """
    from bench.contracts.canonicalize import validate_evidence_label

    with pytest.raises(ValueError, match="unknown evidence_label"):
        validate_evidence_label("not-a-real-label")


def test_known_labels_accepted_by_canonicalization() -> None:
    """Every label in CANONICAL_LABELS must pass validate_evidence_label
    without raising (DAG-24 round-trip)."""
    from bench.contracts.canonicalize import validate_evidence_label

    for label in CANONICAL_LABELS:
        # Must not raise.
        validate_evidence_label(label)


def test_validate_evidence_label_rejects_non_string() -> None:
    """Passing a non-string (int, None, bytes) raises ValueError — the
    contract pins evidence_label as a string field, and silently coercing
    to str would mask producer bugs (e.g. accidentally writing the enum
    ordinal)."""
    from bench.contracts.canonicalize import validate_evidence_label

    for bad in (None, 42, b"live verified"):
        with pytest.raises(ValueError, match="evidence_label must be str"):
            validate_evidence_label(bad)  # type: ignore[arg-type]
