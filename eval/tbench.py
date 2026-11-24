"""Terminal Bench 2.0 score parsing and honest leaderboard.

Parses Harbor ``result.json`` artifacts, computes per-model ``ModelScore``
records, and exports an honest leaderboard with integrity metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR, PHENO_ROOT

# Matrix jobs before the adapter package move remain valid provenance.  New
# jobs must use the collision-free in-repo import path, but both paths are
# accepted here so an exact-head rerun is not silently discarded.
_SAFE_ADAPTER_IMPORT_PATHS = frozenset(
    {
        "harness.harbor.terminus_safe:SafeTerminus2",
        "pheno_agent.terminus_safe:SafeTerminus2",
    }
)


@dataclass
class ModelScore:
    """Per-model Harbor result summary.

    Attributes:
        model_id: Canonical model identifier.
        label: Human-readable label.
        mean: Mean Harbor reward.
        n_trials: Number of trials evaluated.
        n_errors: Number of trial errors.
        pass_at_1: Fraction of tasks with reward >= 1.0.
        job_dir: Path to the job directory on disk.
        combo: Whether this is a combo reference.
        tokens_in: Total input tokens if reported.
        tokens_out: Total output tokens if reported.
        per_task: Mapping of task name to reward.

    """

    model_id: str
    label: str
    mean: float
    n_trials: int
    n_errors: int
    pass_at_1: float
    job_dir: str
    combo: bool = False
    tokens_in: int | None = None
    tokens_out: int | None = None
    per_task: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model score to a JSON-compatible dict.

        Returns:
            Dict with counts and per-task summary.

        """
        return {
            "model_id": self.model_id,
            "label": self.label,
            "mean": self.mean,
            "n_trials": self.n_trials,
            "n_errors": self.n_errors,
            "pass_at_1": self.pass_at_1,
            "job_dir": self.job_dir,
            "combo": self.combo,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "per_task_count": len(self.per_task),
        }


def load_matrix_config() -> dict[str, Any]:
    """Load the TBench matrix config.

    Returns:
        Parsed YAML dict from ``CONFIG_DIR/harbor_tbench_models.yaml``.

    """
    data: Any = yaml.safe_load(
        (CONFIG_DIR / "harbor_tbench_models.yaml").read_text(encoding="utf-8")
    )
    return dict(data) if isinstance(data, dict) else {}


def _safe_slug(model_id: str) -> str:
    """Slugify a model identifier for filesystem use.

    Args:
        model_id: Raw model identifier containing ``/`` or ``:``.

    Returns:
        Filesystem-safe slug.

    """
    return model_id.replace("/", "__").replace(":", "_")


def _parse_job_result(job_dir: Path) -> dict[str, Any] | None:
    """Parse a Harbor job's ``result.json``.

    Args:
        job_dir: Path to the job directory containing ``result.json``.

    Returns:
        Dict with mean, trial counts, per-task rewards, and timestamps, or
        None if ``result.json`` is missing.

    """
    result_path = job_dir / "result.json"
    if not result_path.exists():
        return None
    data: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    stats: dict[str, Any] = data.get("stats") or {}
    evals: dict[str, Any] = stats.get("evals") or {}
    mean: float | None = None
    for ev in evals.values():
        metrics: list[dict[str, Any]] = ev.get("metrics") or []
        if metrics and "mean" in metrics[0]:
            mean = float(metrics[0]["mean"])
            break
    per_task: dict[str, float] = {}
    for trial_dir in job_dir.iterdir():
        if not trial_dir.is_dir():
            continue
        tr = trial_dir / "result.json"
        if not tr.exists():
            continue
        td: dict[str, Any] = json.loads(tr.read_text(encoding="utf-8"))
        task = td.get("task_name") or trial_dir.name
        reward = (td.get("verifier_result") or {}).get("rewards", {}).get("reward")
        if reward is not None:
            per_task[str(task)] = float(reward)
    return {
        "mean": mean,
        "n_trials": int(stats.get("n_trials") or data.get("n_total_trials") or 0),
        "n_errors": int(stats.get("n_errors") or 0),
        "tokens_in": stats.get("n_input_tokens"),
        "tokens_out": stats.get("n_output_tokens"),
        "per_task": per_task,
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
    }


def score_from_job(
    job_dir: Path, model_id: str, label: str, *, combo: bool = False
) -> ModelScore | None:
    """Score a Harbor job directory into a ``ModelScore``.

    Args:
        job_dir: Path to the Harbor job directory.
        model_id: Canonical model identifier.
        label: Human-readable label.
        combo: Whether this is a combo reference entry.

    Returns:
        ``ModelScore`` if ``result.json`` exists and contains a mean, else None.

    """
    parsed = _parse_job_result(job_dir)
    if not parsed or parsed["mean"] is None:
        return None
    per_task: dict[str, float] = parsed["per_task"]
    pass_at_1 = (
        sum(1 for v in per_task.values() if v >= 1.0) / len(per_task)
        if per_task
        else 0.0
    )
    return ModelScore(
        model_id=model_id,
        label=label,
        mean=round(float(parsed["mean"]), 4),
        n_trials=int(parsed["n_trials"]),
        n_errors=int(parsed["n_errors"]),
        pass_at_1=round(pass_at_1, 4),
        job_dir=str(job_dir),
        combo=combo,
        tokens_in=parsed.get("tokens_in"),
        tokens_out=parsed.get("tokens_out"),
        per_task=per_task,
    )


def load_state() -> dict[str, Any]:
    """Load the persisted matrix state.

    Returns:
        State dict with ``models`` and ``updated_at``.

    """
    cfg: dict[str, Any] = load_matrix_config()
    path = PHENO_ROOT / str(cfg.get("state_file", "state/tbench_matrix.json"))
    if path.exists():
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        return (
            dict(data) if isinstance(data, dict) else {"models": {}, "updated_at": None}
        )
    return {"models": {}, "updated_at": None}


def save_state(state: dict[str, Any]) -> Path:
    """Persist the matrix state with an updated timestamp.

    Args:
        state: State dict to write.

    Returns:
        Path to the written state file.

    """
    cfg: dict[str, Any] = load_matrix_config()
    path = PHENO_ROOT / str(cfg.get("state_file", "state/tbench_matrix.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def build_leaderboard(*, include_combo: bool = False) -> list[ModelScore]:
    """Build the leaderboard from the persisted matrix state.

    Args:
        include_combo: Whether to include combo references.

    Returns:
        Sorted list of ``ModelScore`` records, highest mean first.

    """
    cfg: dict[str, Any] = load_matrix_config()
    state = load_state()
    scores: list[ModelScore] = []

    for entry in cfg.get("models", []):
        mid: str = str(entry["id"])
        rec: dict[str, Any] | None = (state.get("models") or {}).get(mid)
        if not rec or rec.get("status") != "complete":
            continue
        job_dir = Path(str(rec.get("job_dir", "")))
        if not job_dir.is_absolute():
            job_dir = PHENO_ROOT / job_dir
        ms = score_from_job(job_dir, mid, str(entry.get("label", mid)))
        if ms:
            scores.append(ms)

    if include_combo:
        for entry in cfg.get("combo_reference", []):
            mid = str(entry["id"])
            rec = (state.get("models") or {}).get(mid)
            if not rec or rec.get("status") != "complete":
                continue
            job_dir = Path(str(rec.get("job_dir", "")))
            if not job_dir.is_absolute():
                job_dir = PHENO_ROOT / job_dir
            ms = score_from_job(job_dir, mid, str(entry.get("label", mid)), combo=True)
            if ms:
                scores.append(ms)

    scores.sort(key=lambda s: s.mean, reverse=True)
    return scores


def _representative_task_names() -> set[str]:
    """Load the representative task lock file.

    Returns:
        Set of task names in the lock, empty if missing.

    """
    manifest = PHENO_ROOT / "config" / "tbench20_representative_subset.json"
    try:
        payload: dict[str, Any] = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    names = payload.get("task_names") or payload.get("task_ids") or []
    return {str(name).strip() for name in names if str(name).strip()}


def _matrix_job_is_representative(job_dir: Path, task_names: set[str]) -> bool:
    """Check if a matrix job matches the representative task lock.

    Require a retained Harbor config to prove membership in the lock.
    Older jobs remain visible as provenance, but missing/empty task filters
    must never make them eligible for matrix_best.

    Args:
        job_dir: Path to the job directory containing ``config.json``.
        task_names: Set of representative task names from the lock.

    Returns:
        True if the job is representative.

    """
    if not task_names:
        return False
    try:
        config: dict[str, Any] = json.loads(
            (job_dir / "config.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return False
    selected = _matrix_job_task_names(config)
    agents: list[dict[str, Any]] = config.get("agents") or []
    import_path = str(agents[0].get("import_path", "")) if agents else ""
    # Accept the current collision-free package path and the legacy path as
    # provenance-compatible evidence. The task lock and exact config still
    # gate representative eligibility.
    return (
        len(selected) == 1
        and selected <= task_names
        and import_path in _SAFE_ADAPTER_IMPORT_PATHS
    )


def _matrix_job_task_names_from_path(job_dir: Path) -> list[str]:
    """Extract task names for a job directory from its config.

    Args:
        job_dir: Path to the job directory.

    Returns:
        Sorted list of task names.

    """
    try:
        config: dict[str, Any] = json.loads(
            (job_dir / "config.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []
    return sorted(_matrix_job_task_names(config))


def _matrix_job_task_names(config: dict[str, Any]) -> set[str]:
    """Extract task names from a Harbor config dict.

    Args:
        config: Parsed Harbor ``config.json`` dict.

    Returns:
        Set of task names.

    """
    return {
        str(name).strip()
        for dataset in (config.get("datasets") or [])
        for name in (dataset.get("task_names") or [])
        if str(name).strip()
    }


def build_matrix_cell_leaderboard(
    *, representative_only: bool = False
) -> list[ModelScore]:
    """Build a leaderboard from retained matrix cell artifacts.

    Args:
        representative_only: If True, restrict to representative jobs.

    Returns:
        Sorted list of ``ModelScore`` records.

    """
    root = PHENO_ROOT / "jobs" / "harbor" / "matrix-cells"
    scores: list[ModelScore] = []
    if not root.is_dir():
        return scores
    task_names = _representative_task_names()
    for cell_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for job_dir in sorted(path for path in cell_dir.iterdir() if path.is_dir()):
            if not (job_dir / "result.json").is_file():
                continue
            if representative_only and not _matrix_job_is_representative(
                job_dir, task_names
            ):
                continue
            score = score_from_job(job_dir, cell_dir.name, cell_dir.name)
            if score is not None:
                scores.append(score)
    scores.sort(key=lambda s: (s.mean, s.n_errors == 0), reverse=True)
    return scores


def export_leaderboard(*, include_combo: bool = False) -> Path:
    """Export the full leaderboard payload to JSON.

    Args:
        include_combo: Whether to include combo references.

    Returns:
        Path to the written JSON payload.

    """
    cfg: dict[str, Any] = load_matrix_config()
    target = float((cfg.get("eval_protocol") or {}).get("target_mean", 0.80))
    scores = build_leaderboard(include_combo=include_combo)
    matrix_scores = build_matrix_cell_leaderboard()
    representative_scores = build_matrix_cell_leaderboard(representative_only=True)
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": (cfg.get("eval_protocol") or {}).get(
            "dataset", "terminal-bench@2.0"
        ),
        "target_mean": target,
        "integrity": (cfg.get("eval_protocol") or {}).get("integrity"),
        "models": [s.to_dict() for s in scores if not s.combo],
        "matrix_cells": [
            {
                **s.to_dict(),
                "scoreable": s.n_errors == 0 and s.n_trials > 0,
                "representative": _matrix_job_is_representative(
                    Path(s.job_dir), _representative_task_names()
                )
                if s.job_dir
                else False,
                "task_names": _matrix_job_task_names_from_path(Path(s.job_dir))
                if s.job_dir
                else sorted(s.per_task),
            }
            for s in matrix_scores
        ],
        "combo_reference": [s.to_dict() for s in scores if s.combo],
        "best_individual": scores[0].to_dict()
        if scores and not scores[0].combo
        else None,
        "meets_target": any(s.mean >= target and not s.combo for s in scores),
        "matrix_best": (
            {
                **representative_scores[0].to_dict(),
                "scoreable": representative_scores[0].n_errors == 0
                and representative_scores[0].n_trials > 0,
                "representative": True,
                "task_names": sorted(representative_scores[0].per_task),
            }
            if representative_scores
            else None
        ),
    }
    out = EVAL_RESULTS_DIR / "tbench_model_scores.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = EVAL_RESULTS_DIR / "tbench_model_scores_latest.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cfg_path = PHENO_ROOT / str(
        cfg.get("results_file", "eval/results/tbench_model_scores.json")
    )
    if cfg_path != out:
        cfg_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def format_leaderboard_table(*, include_combo: bool = True) -> str:
    """Format the leaderboard as a human-readable table.

    Args:
        include_combo: Whether to include combo rows.

    Returns:
        Formatted table string.

    """
    cfg: dict[str, Any] = load_matrix_config()
    target = float((cfg.get("eval_protocol") or {}).get("target_mean", 0.80))
    scores = build_leaderboard(include_combo=include_combo)
    lines = [
        f"Terminal Bench 2.0 — individual models (target >= {target:.0%})",
        f"{'Model':<28} {'Mean':>7} {'Pass@1':>7} {'Trials':>7} {'Err':>4}",
        "-" * 58,
    ]
    for s in scores:
        if s.combo:
            continue
        flag = " *" if s.mean >= target else ""
        lines.append(
            f"{s.label:<28} {s.mean:>7.3f} {s.pass_at_1:>7.3f} {s.n_trials:>7} {s.n_errors:>4}{flag}"
        )
    if include_combo:
        for s in scores:
            if not s.combo:
                continue
            lines.append("-" * 58)
            lines.append(
                f"{s.label + ' (combo)':<28} {s.mean:>7.3f} {s.pass_at_1:>7.3f} {s.n_trials:>7} {s.n_errors:>4}"
            )
    if not any(not s.combo for s in scores):
        lines.append("(no completed individual model runs yet)")
    return "\n".join(lines)


def best_l2_harbor_reward() -> float | None:
    """Return the best individual-model mean for nested RLVR L2 wiring.

    Returns:
        Best mean reward or None if no models are complete.

    """
    scores = build_leaderboard(include_combo=False)
    if not scores:
        return None
    return scores[0].mean
