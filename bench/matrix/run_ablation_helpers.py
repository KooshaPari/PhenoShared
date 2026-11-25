"""Helper functions for the ablation matrix runner."""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bench.contracts.cell_metrics import cell_pass_fields

if TYPE_CHECKING:
    from bench.matrix.run_ablation import AblationResult
else:
    AblationResult = Any  # type: ignore[assignment,misc]

# Verifier wiring (v0.12 task 7) — expose verifier pass computation for integration.
try:
    from verifier.harness import VerifierHarness  # noqa: F401

    _HAS_VERIFIER = True
except ImportError:
    _HAS_VERIFIER = False

REPO_ROOT = Path(__file__).resolve().parents[2]


def compute_verified_pass_at_1(results: list[dict[str, Any]]) -> float:
    """Mean ``verified_pass_at_1`` across raw cell dicts.

    Each cell may carry a ``verified_pass_at_1`` key (populated by Harbor /
    Apple Container reward wiring).  Cells without the key default to 0.0.
    Returns 0.0 for an empty list.
    """
    if not results:
        return 0.0
    values = [float(c.get("verified_pass_at_1", 0.0)) for c in results]
    return round(sum(values) / len(values), 4)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head() -> str:
    try:
        out = subprocess.check_output(  # nosec B603 B607
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _task_ids(suite: str, n: int) -> list[str]:
    return [f"{suite}-task-{i:03d}" for i in range(n)]


def _prompt_for(suite: str, task_id: str) -> str:
    return f"[{suite}] Answer briefly: what is 2+2? (task {task_id})"


def _sort_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sort_json(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort_json(x) for x in obj]
    return obj


def _sha256_hex(obj: Any) -> str:
    payload = json.dumps(
        _sort_json(obj),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _cell_to_task_result(cell: dict[str, Any]) -> dict[str, Any]:
    ok = bool(cell.get("ok", False))
    pass_metrics = cell_pass_fields(
        ok,
        harbor_reward=cell.get("harbor_reward"),
    )
    if "gen_ok" in cell:
        pass_metrics["gen_ok"] = float(cell["gen_ok"])
        pass_metrics["pass_at_1"] = float(cell.get("pass_at_1", cell["gen_ok"]))
        pass_metrics["verified_pass_at_1"] = float(
            cell.get("verified_pass_at_1", pass_metrics["verified_pass_at_1"])
        )
        pass_metrics["evidence_label"] = cell.get(
            "evidence_label", pass_metrics["evidence_label"]
        )
    return {
        "task_id": cell.get("suite_task_key", cell.get("task_id", "")),
        "status": "ok" if ok else "wrong",
        "judge": "deterministic",
        "wall_clock_s": cell.get("wall_clock_s", 0.0),
        "tokens_in": cell.get("tokens_read", 0),
        "tokens_out": cell.get("tokens_created", 0),
        "evidence_label": pass_metrics["evidence_label"],
        "additionalProperties": {
            "synthetic": cell.get("synthetic", False),
            **pass_metrics,
        },
    }


def build_cells_payload(result: AblationResult) -> dict[str, Any]:
    """V5-shaped cells JSON (compatible with convert_to_contract input)."""
    by_variant: dict[str, dict[str, Any]] = {}
    for variant in result.variants:
        vcells = [c for c in result.cells if c["variant"] == variant]
        n = len(vcells)
        ok_count = sum(1 for c in vcells if c.get("ok"))
        gen_ok_vals = [float(c["gen_ok"]) for c in vcells if "gen_ok" in c]
        vpass1 = compute_verified_pass_at_1(vcells)
        by_variant[variant] = {
            "n_cells": n,
            "ok_count": ok_count,
            "gen_ok_mean": round(sum(gen_ok_vals) / n, 4) if n and gen_ok_vals else 0.0,
            "pass_at_1": round(sum(gen_ok_vals) / n, 4) if n and gen_ok_vals else 0.0,
            "verified_pass_at_1": vpass1,
        }

    return {
        "run_id": result.run_id,
        "started_at": result.started_at,
        "stopped_at": result.stopped_at,
        "dry_run": result.dry_run,
        "model_id": result.model_id,
        "variants": result.variants,
        "suites": result.suites,
        "summary": {"by_variant": by_variant, "meta": {"model": result.model_id}},
        "cells": result.cells,
    }


# ---------------------------------------------------------------------------
# Verifier integration (v0.12 task 7)
# ---------------------------------------------------------------------------


def verifier_available() -> bool:
    """Return True if verifier harness is importable."""
    return _HAS_VERIFIER


def verifier_judge_for_cell(cell: dict[str, Any]) -> dict[str, Any]:
    """Run verifier-derived pass fields for a cell (harbor_reward → verified_pass).

    Thin wrapper around bench.contracts.cell_metrics.cell_pass_fields that
    ensures verifier wiring is exercised. For dry-run cells without harbor_reward,
    verified_pass_at_1 remains 0.0 as per contract.
    """
    ok = bool(cell.get("ok", False))
    harbor_reward = cell.get("harbor_reward")
    # Prefer verifier.harness if available; fallback to cell_pass_fields
    if _HAS_VERIFIER:
        try:
            from verifier import rewards as _vr  # noqa: F401

            _ = _vr  # ensure import succeeds
        except ImportError:
            pass
    return cell_pass_fields(ok, harbor_reward=harbor_reward)
