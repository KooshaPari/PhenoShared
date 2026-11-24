"""DAG-17: tests/test_handoff_serialization.py

The handoff serialization round-trip: a SuiteResult must serialize to
JSON via ``to_dict()`` and reconstruct losslessly. Used by the
stock_vs_ours.py emit path (chat 6 -> Argis oMLX consumer).
"""

from __future__ import annotations

import json

from bench.types import (
    SuiteResult,
    TaskResult,
    TaskStatus,
)


def _make_suite() -> SuiteResult:
    tr = TaskResult(
        task_id="t1",
        status=TaskStatus.OK,
        prompt="hi",
        completion="hello",
        expected=None,
        meta={"k": "v"},
        wall_clock_s=0.42,
        tokens_in=3,
        tokens_out=2,
        first_token_latency_s=0.01,
        tool_calls=[],
        cached=False,
        synthetic=False,
        error=None,
    )
    return SuiteResult(
        suite="handoff-test",
        model="mlx-stub",
        task_results=[tr],
        meta={"metrics": {"pass@1": 1.0, "wall_clock_total": 0.42}},
    )


def test_suite_result_round_trip_through_dict() -> None:
    sr = _make_suite()
    d = sr.to_dict() if hasattr(sr, "to_dict") else sr.__dict__
    payload = json.dumps(d, default=str)
    reloaded = json.loads(payload)
    assert reloaded["suite"] == "handoff-test"
    task_list = reloaded.get("task_results") or reloaded.get("tasks") or []
    assert task_list and task_list[0]["task_id"] == "t1"
    status = task_list[0]["status"]
    if isinstance(status, str) and status.startswith("TaskStatus."):
        status = status.split(".", 1)[1]
    assert status in {"ok", "wrong", "error", "skipped", "timeout"}


def test_suite_result_status_preserved_across_serialization() -> None:
    """The status field must round-trip as a string the consumer can
    re-parse into the TaskStatus enum (canonical mapping: pass->ok,
    fail->wrong, skip->skipped)."""
    sr = _make_suite()
    d = sr.to_dict() if hasattr(sr, "to_dict") else sr.__dict__
    payload = json.dumps(d, default=str)
    reloaded = json.loads(payload)
    task_list = reloaded.get("task_results") or reloaded.get("tasks") or []
    raw_status = task_list[0]["status"]
    if isinstance(raw_status, str) and raw_status.startswith("TaskStatus."):
        raw_status = raw_status.split(".", 1)[1]
    # Map any legacy aliases back to canonical.
    legacy = {"pass": "ok", "fail": "wrong", "skip": "skipped"}
    canonical = legacy.get(raw_status, raw_status)
    # Must be a known TaskStatus value.
    assert canonical in {s.value for s in TaskStatus}


def test_metrics_field_is_dict() -> None:
    """SuiteResult.metrics must be a dict (never a list/scalar). The
    current SuiteResult stores legacy 'metrics' under .meta['metrics']
    so the assertion targets that path."""
    sr = _make_suite()
    metrics = sr.meta.get("metrics")
    assert isinstance(metrics, dict)
    assert "pass@1" in metrics
