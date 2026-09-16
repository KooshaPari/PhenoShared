"""DAG-18: tests/test_contamination_guard.py

The contamination guard prevents trace-derived evalsets from leaking
into training. The check is: any dataset_revision used as an eval task
must NOT appear as a training-set path. The current implementation
relies on file-system separation + a manifest diff at suite load time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAINING = REPO_ROOT / "training"
DATASETS = REPO_ROOT / "datasets"


def test_training_and_datasets_dirs_are_distinct() -> None:
    """training/ and datasets/ must be separate top-level dirs so the
    contamination guard can rely on a path-based check."""
    assert TRAINING.exists(), "training/ must exist for the guard to be meaningful"
    assert DATASETS.exists(), "datasets/ must exist"
    # Resolved paths must not be the same.
    assert TRAINING.resolve() != DATASETS.resolve()


def test_training_dir_does_not_contain_dataset_subdir() -> None:
    """A nested datasets/ inside training/ would be a contamination risk
    (training could silently read eval data from a relative path)."""
    if not TRAINING.exists():
        pytest.skip("training/ not present")
    nested = TRAINING / "datasets"
    assert not nested.exists(), f"contamination risk: {nested} exists inside training/"


def test_no_eval_result_in_training_path() -> None:
    """Any file under training/ matching bench/results/*.json would be a
    contamination flag — eval results must not be co-located with
    training data."""
    if not TRAINING.exists():
        pytest.skip("training/ not present")
    offenders = list(TRAINING.rglob("*.json"))
    # Filter to files that look like eval artifacts (top-level
    # evaluation_report or cells.json).
    eval_offenders = [
        p
        for p in offenders
        if p.name in {"evaluation_report.json", "cells.json", "per_cell.jsonl"}
    ]
    assert not eval_offenders, f"eval artifacts in training/: {eval_offenders}"
