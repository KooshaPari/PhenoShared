"""TB2 route matrix — pillar scoring (quality / TPS / cost) per route kind."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from eval.tbench import _parse_job_result, score_from_job
from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR, PHENO_ROOT


def load_routes_config() -> dict[str, Any]:
    """Load the route matrix config.

    Returns:
        Parsed YAML dict from ``CONFIG_DIR/harbor_tbench_routes.yaml``.

    """
    data: Any = yaml.safe_load(
        (CONFIG_DIR / "harbor_tbench_routes.yaml").read_text(encoding="utf-8")
    )
    return dict(data) if isinstance(data, dict) else {}


def load_routes_state() -> dict[str, Any]:
    """Load the persisted route matrix state.

    Returns:
        State dict with ``models`` and ``updated_at``.

    """
    cfg: dict[str, Any] = load_routes_config()
    path = PHENO_ROOT / str(cfg.get("state_file", "state/tbench_routes_matrix.json"))
    if path.exists():
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        return (
            dict(data) if isinstance(data, dict) else {"models": {}, "updated_at": None}
        )
    return {"models": {}, "updated_at": None}


def save_routes_state(state: dict[str, Any]) -> Path:
    """Persist the route matrix state.

    Args:
        state: State dict to write.

    Returns:
        Path to the written file.

    """
    cfg: dict[str, Any] = load_routes_config()
    path: Path = PHENO_ROOT / str(
        cfg.get("state_file", "state/tbench_routes_matrix.json")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def _entry_cost_rates(entry: dict[str, Any]) -> tuple[float, float]:
    """Extract per-million cost rates from a route entry.

    Args:
        entry: Route config entry dict.

    Returns:
        Tuple of (cost_in, cost_out) per million tokens.

    """
    return float(entry.get("cost_per_m_in", 0.0)), float(
        entry.get("cost_per_m_out", 0.0)
    )


def estimate_run_cost_usd(
    tokens_in: int | None, tokens_out: int | None, entry: dict[str, Any]
) -> float:
    """Estimate USD cost for a run.

    Args:
        tokens_in: Input tokens if reported.
        tokens_out: Output tokens if reported.
        entry: Route entry with cost rates.

    Returns:
        Cost in USD.

    """
    tin = int(tokens_in or 0)
    tout = int(tokens_out or 0)
    cin, cout = _entry_cost_rates(entry)
    return (tin * cin + tout * cout) / 1_000_000


def estimate_tok_s(tokens_out: int | None, duration_sec: float | None) -> float | None:
    if not tokens_out or not duration_sec or duration_sec <= 0:
        return None
    return round(tokens_out / duration_sec, 2)


def _job_duration_sec(job_dir: Path) -> float | None:
    """Compute job duration from ``result.json`` timestamps.

    Args:
        job_dir: Path to the job directory.

    Returns:
        Duration in seconds or None if timestamps missing.

    """
    parsed = _parse_job_result(job_dir)
    if not parsed:
        return None
    started = parsed.get("started_at")
    finished = parsed.get("finished_at")
    if not started or not finished:
        return None
    try:
        t0 = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
        return max(0.0, (t1 - t0).total_seconds())
    except ValueError:
        return None


def pillar_scores(
    mean: float,
    *,
    tok_s: float | None,
    cost_usd: float,
    entry: dict[str, Any],
    target_mean: float = 0.80,
) -> dict[str, float]:
    """Normalized 0–1 pillar scores for route comparison."""
    qual = min(1.0, mean / target_mean) if target_mean > 0 else mean
    tok_target = float(entry.get("tok_s_target") or 40.0)
    if tok_s is None:
        speed = (
            0.0 if entry.get("route_kind") in ("local_direct", "pheno_serve") else 0.5
        )
    else:
        speed = min(1.0, tok_s / tok_target)
    # Lower cost is better; $5/run ≈ 0, $0 ≈ 1
    cost_score = max(0.0, min(1.0, 1.0 - (cost_usd / 5.0)))
    weights = {"accuracy": 0.40, "speed": 0.30, "cost": 0.30}
    composite = (
        qual * weights["accuracy"]
        + speed * weights["speed"]
        + cost_score * weights["cost"]
    )
    return {
        "accuracy": round(qual, 4),
        "speed": round(speed, 4),
        "cost": round(cost_score, 4),
        "composite": round(composite, 4),
    }


@dataclass
class RouteScore:
    model_id: str
    label: str
    route_kind: str
    routing_policy: str
    mean: float
    n_trials: int
    n_errors: int
    pass_at_1: float
    tokens_in: int | None
    tokens_out: int | None
    tok_s: float | None
    cost_usd: float
    pillars: dict[str, float]
    job_dir: str
    combo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "label": self.label,
            "route_kind": self.route_kind,
            "routing_policy": self.routing_policy,
            "mean": self.mean,
            "n_trials": self.n_trials,
            "n_errors": self.n_errors,
            "pass_at_1": self.pass_at_1,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tok_s": self.tok_s,
            "cost_usd": round(self.cost_usd, 4),
            "pillars": self.pillars,
            "job_dir": self.job_dir,
            "combo": self.combo,
        }


def score_route_from_job(
    job_dir: Path, entry: dict[str, Any], *, target_mean: float = 0.80
) -> RouteScore | None:
    """Score a single route job into ``RouteScore``.

    Args:
        job_dir: Path to the Harbor job directory.
        entry: Route config entry.
        target_mean: Target mean for pillar normalization.

    Returns:
        ``RouteScore`` or None if job is missing.

    """
    ms = score_from_job(
        job_dir,
        entry["id"],
        entry.get("label", entry["id"]),
        combo=bool(entry.get("combo")),
    )
    if not ms:
        return None
    duration = _job_duration_sec(job_dir)
    tok_s = estimate_tok_s(ms.tokens_out, duration)
    cost = estimate_run_cost_usd(ms.tokens_in, ms.tokens_out, entry)
    pillars = pillar_scores(
        ms.mean, tok_s=tok_s, cost_usd=cost, entry=entry, target_mean=target_mean
    )
    return RouteScore(
        model_id=entry["id"],
        label=entry.get("label", entry["id"]),
        route_kind=entry.get("route_kind", "omniroute_cloud"),
        routing_policy=entry.get("routing_policy", "unknown"),
        mean=ms.mean,
        n_trials=ms.n_trials,
        n_errors=ms.n_errors,
        pass_at_1=ms.pass_at_1,
        tokens_in=ms.tokens_in,
        tokens_out=ms.tokens_out,
        tok_s=tok_s,
        cost_usd=cost,
        pillars=pillars,
        job_dir=str(job_dir),
        combo=bool(entry.get("combo")),
    )


def build_route_leaderboard(*, route_kind: str | None = None) -> list[RouteScore]:
    cfg = load_routes_config()
    target = float((cfg.get("eval_protocol") or {}).get("target_mean", 0.80))
    state = load_routes_state()
    entries = list(cfg.get("models", [])) + list(cfg.get("combo_reference", []))
    by_id = {e["id"]: e for e in entries}
    scores: list[RouteScore] = []
    for mid, rec in (state.get("models") or {}).items():
        if rec.get("status") != "complete":
            continue
        entry = by_id.get(mid)
        if not entry:
            continue
        if route_kind and entry.get("route_kind") != route_kind:
            continue
        job_dir = Path(rec.get("job_dir", ""))
        if not job_dir.is_absolute():
            job_dir = PHENO_ROOT / job_dir
        rs = score_route_from_job(job_dir, entry, target_mean=target)
        if rs:
            scores.append(rs)
    scores.sort(key=lambda s: s.pillars["composite"], reverse=True)
    return scores


def export_route_leaderboard(*, route_kind: str | None = None) -> Path:
    """Export the route leaderboard payload to JSON.

    Args:
        route_kind: Optional filter for a single route kind.

    Returns:
        Path to the written JSON payload.

    """
    cfg: dict[str, Any] = load_routes_config()
    scores = build_route_leaderboard(route_kind=route_kind)
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": (cfg.get("eval_protocol") or {}).get("dataset"),
        "router_reference": cfg.get("router_reference"),
        "by_route_kind": {},
        "models": [s.to_dict() for s in scores if not s.combo],
        "combo_reference": [s.to_dict() for s in scores if s.combo],
        "best_composite": scores[0].to_dict() if scores else None,
    }
    by_route_kind: dict[str, Any] = payload["by_route_kind"]
    for kind in ("omniroute_cloud", "pheno_serve", "local_direct", "omniroute_combo"):
        kind_scores = [s for s in scores if s.route_kind == kind]
        if kind_scores:
            by_route_kind[kind] = {
                "best": kind_scores[0].to_dict(),
                "count": len(kind_scores),
            }
    out = EVAL_RESULTS_DIR / "tbench_route_scores.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cfg_path = PHENO_ROOT / cfg.get(
        "results_file", "eval/results/tbench_route_scores.json"
    )
    if cfg_path != out:
        cfg_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def format_route_table(*, route_kind: str | None = None) -> str:
    scores = build_route_leaderboard(route_kind=route_kind)
    lines = [
        "TB2.0 route matrix — composite = 40% accuracy + 30% speed + 30% cost",
        f"{'Route':<14} {'Model':<22} {'Mean':>6} {'Tok/s':>7} {'$/run':>7} {'Comp':>6}",
        "-" * 72,
    ]
    for s in scores:
        tok = f"{s.tok_s:.1f}" if s.tok_s is not None else "—"
        lines.append(
            f"{s.route_kind:<14} {s.label:<22} {s.mean:>6.3f} {tok:>7} {s.cost_usd:>7.3f} "
            f"{s.pillars['composite']:>6.3f}"
        )
    if not scores:
        lines.append("(no completed route runs yet)")
    return "\n".join(lines)
