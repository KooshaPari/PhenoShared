from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from bench.contracts.cell_metrics import EVIDENCE_REPORTED, EVIDENCE_VERIFIED
from scripts import run_desktop_lane_eval
from scripts.run_desktop_lane_eval import (
    _is_qwen35_model,
    apply_evidence_label_to_perf_output,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_desktop_lane_eval.py"

# Canonical evidence_label enum per AGENTS.md §12.3 / §12.4. The desktop
# lane only ever emits one of these two — Harbor paths emit "verified";
# direct-generate / MLX ablation paths emit "reported".
CANONICAL_DESKTOP_LANE_LABELS = {EVIDENCE_REPORTED, EVIDENCE_VERIFIED}


def _iter_perf_cells(perf_result: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield every per-cell dict inside a ``pheno.perf.v1`` envelope.

    Cells live in ``levels[].results`` (per-level request results) and in
    ``warmup.results`` (warmup request results). The wrapper annotates both
    containers with v0.5 cell fields including ``evidence_label``.
    """
    levels = perf_result.get("levels") or []
    if isinstance(levels, list):
        for level in levels:
            if not isinstance(level, dict):
                continue
            results = level.get("results") or []
            if isinstance(results, list):
                for cell in results:
                    if isinstance(cell, dict):
                        yield cell
    warmup = perf_result.get("warmup")
    if isinstance(warmup, dict):
        results = warmup.get("results") or []
        if isinstance(results, list):
            for cell in results:
                if isinstance(cell, dict):
                    yield cell


def _synthetic_perf_output() -> dict[str, Any]:
    """Build a minimal ``pheno.perf.v1`` payload with mix of ok + error cells."""
    return {
        "schema_version": "pheno.perf.v1",
        "engine": "desktop-vllm-3090ti",
        "model": "local/qwen35-08b",
        "request_model": "local/qwen35-08b",
        "warmup": {
            "requested": 1,
            "results": [
                {
                    "elapsed_ms": 12.0,
                    "ttft_ms": 6.0,
                    "completion_tokens": 16,
                    "decode_tok_s": 1333.3,
                    "measurement_quality": "synthetic",
                },
            ],
            "error_count": 0,
        },
        "levels": [
            {
                "concurrency": 1,
                "request_count": 2,
                "success_count": 1,
                "error_count": 1,
                "wall_ms": 42.0,
                "aggregate_tokens": 16,
                "aggregate_tokens_per_s": 380.95,
                "latency_ms_p50": 12.0,
                "latency_ms_p95": 12.0,
                "results": [
                    {
                        "elapsed_ms": 12.0,
                        "ttft_ms": 6.0,
                        "completion_tokens": 16,
                        "decode_tok_s": 1333.3,
                        "measurement_quality": "synthetic",
                    },
                    {"error": "caller exception: ConnectionError: refused"},
                ],
            },
            {
                "concurrency": 2,
                "request_count": 1,
                "success_count": 1,
                "error_count": 0,
                "wall_ms": 18.0,
                "aggregate_tokens": 24,
                "aggregate_tokens_per_s": 1333.3,
                "latency_ms_p50": 18.0,
                "latency_ms_p95": 18.0,
                "results": [
                    {
                        "elapsed_ms": 18.0,
                        "ttft_ms": 9.0,
                        "completion_tokens": 24,
                        "decode_tok_s": 1333.3,
                        "measurement_quality": "synthetic",
                    },
                ],
            },
        ],
    }


def test_desktop_lane_eval_is_dry_run_by_default(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "primary",
            "--window-id",
            "desktop-test-window",
            "--output",
            str(tmp_path / "perf.json"),
            "--manifest-output",
            str(tmp_path / "manifest.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(result.stdout)
    assert plan["execute"] is False
    assert plan["model"] == "local/qwen35-08b"
    assert plan["request_model"] == "local/qwen35-08b"
    assert plan["base_url"] == "http://127.0.0.1:8000"
    assert not (tmp_path / "perf.json").exists()


def test_desktop_lane_eval_accepts_canonical_qwen35_model_id() -> None:
    assert _is_qwen35_model("Qwen/Qwen3.5-0.8B") is True
    assert _is_qwen35_model("Qwen/Qwen2.5-0.5B") is False


def test_desktop_lane_eval_helper_defaults_to_isolated_endpoint(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "helper",
            "--window-id",
            "desktop-test-window",
            "--output",
            str(tmp_path / "perf.json"),
            "--manifest-output",
            str(tmp_path / "manifest.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["base_url"] == "http://127.0.0.1:8082"


def test_lane_eval_contract_digest_normalizes_windows_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows line endings must not change the plan contract binding."""
    unix = tmp_path / "lane-unix.yaml"
    windows = tmp_path / "lane-windows.yaml"
    unix.write_bytes(
        b"status: planning_only\nexecution_policy:\n  allow_model_inference: false\n"
    )
    windows.write_bytes(
        b"status: planning_only\r\nexecution_policy:\r\n  allow_model_inference: false\r\n"
    )

    monkeypatch.setattr(run_desktop_lane_eval, "CONTRACT", unix)
    unix_digest = run_desktop_lane_eval._contract_sha256()
    monkeypatch.setattr(run_desktop_lane_eval, "CONTRACT", windows)

    assert unix_digest == run_desktop_lane_eval._contract_sha256()


# DAG-30: per-cell evidence_label wiring. The desktop lane is a
# direct-generate path (not Harbor), so by default every cell carries
# ``evidence_label = "reported"``. These tests pin both the enum
# membership and the AGENTS.md §12.4 invariant that ``verified`` implies
# a positive verifier score while ``reported`` allows ``verified_pass_at_1 == 0.0``.


def test_per_cell_evidence_label_is_reported_or_verified() -> None:
    """Each per-cell result carries an evidence_label from the canonical enum.

    Per AGENTS.md §12.3 the canonical enum for v0.5 cells is
    ``{"reported", "verified"}``. The desktop lane default path is
    direct-generate so we assert every cell ends up as one of the two
    accepted values — never ``None``, never a legacy alias, never a
    dropped label that downstream consumers must reject.
    """
    perf = _synthetic_perf_output()
    apply_evidence_label_to_perf_output(perf)

    cells = list(_iter_perf_cells(perf))
    assert cells, "synthetic perf output must contain at least one cell"
    for cell in cells:
        assert "evidence_label" in cell, f"cell missing evidence_label: {cell}"
        assert cell["evidence_label"] in CANONICAL_DESKTOP_LANE_LABELS, (
            f"unexpected evidence_label value: {cell['evidence_label']!r}"
        )
    assert perf["evidence_label"] == EVIDENCE_REPORTED


def test_per_cell_evidence_label_consistent_with_verified_pass_at_1() -> None:
    """verified ⇔ positive reward; reported ⇔ zero reward (AGENTS.md §12.4).

    Producer rule #2 (Harbor path): when a Harbor reward is supplied,
    ``evidence_label = "verified"`` AND ``verified_pass_at_1`` carries
    the score. Producer rule #1 (direct-generate / MLX ablation):
    ``verified_pass_at_1 = 0.0`` AND ``evidence_label = "reported"``.

    The desktop lane default is direct-generate, so the synthetic payload
    must end up fully reported with zero rewards. To exercise the
    verified branch too, we run the helper again with an explicit
    ``harbor_reward`` and assert the invariant flips.
    """
    # Default direct-generate path: every cell is reported with reward=0.0
    perf_reported = _synthetic_perf_output()
    apply_evidence_label_to_perf_output(perf_reported)
    for cell in _iter_perf_cells(perf_reported):
        assert cell["evidence_label"] == EVIDENCE_REPORTED
        assert cell["verified_pass_at_1"] == 0.0

    # Harbor reward path: every cell becomes verified with the reward.
    perf_verified = _synthetic_perf_output()
    apply_evidence_label_to_perf_output(perf_verified, harbor_reward=0.85)
    for cell in _iter_perf_cells(perf_verified):
        assert cell["evidence_label"] == EVIDENCE_VERIFIED
        assert cell["verified_pass_at_1"] > 0.0


def test_per_cell_evidence_label_writes_back_into_perf_output(tmp_path: Path) -> None:
    """The wrapper writes the augmented perf output back to disk (DAG-30 wiring).

    Round-trips the helper through a JSON file: load → augment → write →
    reload → assert the cells still carry evidence_label. Mirrors what
    ``main()`` does after ``subprocess.run`` so a regression in either
    path surfaces here.
    """
    perf = _synthetic_perf_output()
    out_path = tmp_path / "perf.json"
    out_path.write_text(json.dumps(perf, indent=2), encoding="utf-8")

    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    apply_evidence_label_to_perf_output(loaded)
    out_path.write_text(json.dumps(loaded, indent=2), encoding="utf-8")

    reloaded = json.loads(out_path.read_text(encoding="utf-8"))
    cells = list(_iter_perf_cells(reloaded))
    assert cells
    for cell in cells:
        assert cell["evidence_label"] in CANONICAL_DESKTOP_LANE_LABELS
        assert cell["evidence_label"] == EVIDENCE_REPORTED


def test_perf_output_root_label_is_verified_only_when_all_cells_are_verified() -> None:
    """A root verified label is an aggregate fact, not a caller preference."""
    perf = _synthetic_perf_output()

    apply_evidence_label_to_perf_output(perf, harbor_reward=0.85)

    assert perf["evidence_label"] == EVIDENCE_VERIFIED
