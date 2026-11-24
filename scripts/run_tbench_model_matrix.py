#!/usr/bin/env python3
"""Run terminal-bench@2.0 terminus-2 eval for each individual OmniRoute model."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from eval.tbench import (
    export_leaderboard,
    load_matrix_config,
    load_state,
    save_state,
    score_from_job,
)
from harness.intent_graph import IntentGraphRecorder
from pheno.harbor_util import (
    fireworks_env,
    harbor_exe,
    litellm_model,
    local_env,
    omniroute_env,
)
from pheno.paths import EVAL_RESULTS_DIR, PHENO_ROOT


def _resolve_route(
    model_id: str, entry: dict[str, Any], cfg: dict[str, Any]
) -> tuple[str, str, dict[str, str]]:
    """Return (route, harbor_model, env). Default: OmniRoute Main combo."""
    prov = cfg.get("provider") or {}
    primary = prov.get("primary", "omniroute_main")

    if primary == "pheno_serve":
        base = str(prov.get("pheno_serve_base", "http://127.0.0.1:21080/v1"))
        return (
            "pheno_serve",
            f"openai/{model_id}",
            local_env(base, api_key=prov.get("local_api_key", "local-no-key")),
        )

    if primary == "omniroute_main" or entry.get("combo"):
        return ("omniroute_main", "openai/Main", omniroute_env())

    cred = prov.get("credential_id", "fireworks-ai-firepass")
    direct_model = entry.get("direct_model") or model_id.replace(
        "fireworks/", "accounts/fireworks/models/"
    )

    if primary == "direct_fireworks":
        return (
            "direct",
            litellm_model(model_id, direct=True, direct_model=direct_model),
            fireworks_env(cred),
        )

    probe_path = EVAL_RESULTS_DIR / "tbench_model_probe.json"
    route = "omniroute"
    harbor_model = litellm_model(model_id)
    env = omniroute_env()
    if probe_path.exists():
        rec = (
            json.loads(probe_path.read_text(encoding="utf-8"))
            .get("models", {})
            .get(model_id, {})
        )
        route = rec.get("route") or route
        if route == "direct":
            harbor_model = rec.get("harbor_model_direct") or litellm_model(
                model_id, direct=True, direct_model=direct_model
            )
            env = fireworks_env(cred)
        else:
            harbor_model = rec.get("harbor_model_omniroute") or harbor_model
            env = omniroute_env()
    return route, harbor_model, env


def _model_entries(cfg: dict[str, Any], model_filter: str | None) -> list[dict]:
    entries = list(cfg.get("models", []))
    if model_filter:
        entries = [
            e
            for e in entries
            if e["id"] == model_filter or e.get("label") == model_filter
        ]
    if cfg.get("include_combo"):
        entries.extend(cfg.get("combo_reference", []))
    return entries


def _assert_local_only(entries: list[dict], cfg: dict[str, Any]) -> None:
    primary = (cfg.get("provider") or {}).get("primary", "")
    if primary not in ("local_direct", "pheno_serve"):
        raise SystemExit(
            "Cloud TBench execution is disabled by policy; configure provider.primary as local_direct or pheno_serve."
        )
    if any(
        e.get("route_kind") not in (None, "local_direct", "pheno_serve")
        for e in entries
    ):
        raise SystemExit(
            "TBench model matrix contains a non-local route; refusing execution"
        )


def _run_model(
    entry: dict[str, Any],
    *,
    n_tasks: int,
    n_concurrent: int,
    dry_run: bool,
    jobs_root: Path,
) -> int:
    cfg = load_matrix_config()
    model_id = entry["id"]
    label = entry.get("label", model_id)
    slug = model_id.replace("/", "__").replace(":", "_")
    job_out = jobs_root / slug
    job_out.mkdir(parents=True, exist_ok=True)
    run_id = (
        datetime.now(UTC).strftime("tb20_model_%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8]
    )
    graph_path = job_out / f"{run_id}.graph.json"
    recorder = IntentGraphRecorder(
        run_id, "terminal-bench@2.0", metadata={"matrix": "model"}
    )
    root_node = recorder.start_node(
        "run",
        "tbench_model_cell",
        attributes={"model_id": model_id, "n_tasks": n_tasks},
    )

    harbor = harbor_exe()
    route, harbor_model, run_env = _resolve_route(model_id, entry, cfg)
    cmd = [
        harbor,
        "run",
        "-c",
        str(PHENO_ROOT / "config" / "harbor_tbench_agent.yaml"),
        "--dataset",
        cfg["eval_protocol"]["dataset"],
        "-a",
        cfg["eval_protocol"]["agent"],
        "-m",
        harbor_model,
        "--env",
        "docker",
        "--n-concurrent",
        str(n_concurrent),
        "-l",
        str(n_tasks),
        "-o",
        str(job_out),
        "-y",
    ]

    state = load_state()
    state.setdefault("models", {})[model_id] = {
        "status": "running",
        "label": label,
        "started_at": datetime.now(UTC).isoformat(),
        "n_tasks_requested": n_tasks,
        "harbor_model": harbor_model,
        "route": route,
        "job_dir": str(job_out),
        "graph_path": str(graph_path),
    }
    save_state(state)

    print(f"\n=== {label} ({model_id}) route={route} ===")
    print("Command:", " ".join(cmd))
    model_node = recorder.start_node(
        "model_call",
        "harbor_agent_session",
        parent=root_node,
        attributes={"model": harbor_model, "route": route, "command": cmd},
    )
    if dry_run:
        state["models"][model_id]["status"] = "planned"
        save_state(state)
        recorder.finish_node(model_node, status="planned")
        recorder.finish_node(root_node, status="planned")
        recorder.write(graph_path)
        return 0

    if route == "direct" and not run_env.get("FIREWORKS_AI_API_KEY"):
        print(
            "ERROR: FIREWORKS_AI_API_KEY missing — check ~/forge/.credentials.json fireworks-ai-firepass"
        )
        state["models"][model_id]["status"] = "failed"
        state["models"][model_id]["error"] = "missing FIREWORKS_AI_API_KEY"
        save_state(state)
        recorder.finish_node(
            model_node,
            status="blocked",
            attributes={"reason": "missing_fireworks_api_key"},
        )
        recorder.finish_node(root_node, status="blocked")
        recorder.write(graph_path)
        return 1
    if route != "direct" and not run_env.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing")
        state["models"][model_id]["status"] = "failed"
        state["models"][model_id]["error"] = "missing OPENAI_API_KEY"
        save_state(state)
        recorder.finish_node(
            model_node,
            status="blocked",
            attributes={"reason": "missing_openai_api_key"},
        )
        recorder.finish_node(root_node, status="blocked")
        recorder.write(graph_path)
        return 1

    rc = subprocess.run(cmd, cwd=PHENO_ROOT, env=run_env).returncode
    recorder.finish_node(
        model_node,
        status="completed" if rc == 0 else "failed",
        attributes={"returncode": rc},
    )

    # Harbor writes timestamped subdir under job_out
    job_dirs = sorted(
        [p for p in job_out.iterdir() if p.is_dir() and (p / "result.json").exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    job_dir = job_dirs[0] if job_dirs else job_out
    ms = score_from_job(job_dir, model_id, label, combo=bool(entry.get("combo")))
    verifier_node = recorder.start_node(
        "verifier",
        "harbor_result",
        parent=root_node,
        attributes={"job_dir": str(job_dir)},
    )
    recorder.finish_node(
        verifier_node,
        status="passed" if ms and rc == 0 else "failed" if rc else "incomplete",
        attributes={
            "mean": ms.mean if ms else None,
            "pass_at_1": ms.pass_at_1 if ms else None,
        },
    )
    recorder.add_edge(verifier_node, model_node, "verifies")

    rec = state["models"][model_id]
    rec["finished_at"] = datetime.now(UTC).isoformat()
    rec["returncode"] = rc
    rec["job_dir"] = str(job_dir)
    if ms:
        rec.update(ms.to_dict())
        rec["status"] = "complete" if rc == 0 and ms.n_errors == 0 else "failed"
    else:
        rec["status"] = "failed" if rc != 0 else "incomplete"
    save_state(state)
    if ms:
        print(
            f"  mean={ms.mean:.3f} pass@1={ms.pass_at_1:.3f} trials={ms.n_trials} errors={ms.n_errors}"
        )
    recorder.finish_node(root_node, status=rec["status"])
    recorder.write(graph_path)
    return rc


def main() -> int:
    p = argparse.ArgumentParser(description="Terminal Bench 2.0 per-model matrix")
    p.add_argument("--model", help="Single model id or label (default: all pending)")
    p.add_argument("--all", action="store_true", help="Run all models in config")
    p.add_argument(
        "--include-combo", action="store_true", help="Also run Main combo reference"
    )
    p.add_argument(
        "--n-tasks", type=int, default=89, help="Tasks per model (89=full TB2.0)"
    )
    p.add_argument(
        "--n-concurrent",
        type=int,
        default=None,
        help="Concurrent Harbor trials for scaled local runs",
    )
    p.add_argument("--resume", action="store_true", help="Skip models already complete")
    p.add_argument(
        "--force", action="store_true", help="Run even if probe finds no routes"
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--export-only", action="store_true", help="Rebuild leaderboard JSON only"
    )
    args = p.parse_args()

    cfg = load_matrix_config()
    n_concurrent = args.n_concurrent or int(
        (cfg.get("eval_protocol") or {}).get("n_concurrent_trials", 1)
    )
    if n_concurrent < 1:
        raise SystemExit("--n-concurrent must be positive")
    if args.include_combo:
        cfg = dict(cfg)
        cfg["include_combo"] = True

    if args.export_only:
        out = export_leaderboard(include_combo=args.include_combo)
        print(f"Exported {out}")
        return 0

    if not args.dry_run:
        prov = cfg.get("provider") or {}
        primary = prov.get("primary", "omniroute_main")
        if primary == "pheno_serve":
            print("Local-only Pheno route: skipping OmniRoute/Fireworks probes.")
        else:
            # Cloud probing is retained only for historical configurations; the
            # execution gate below rejects those providers in the active matrix.
            pass
        omni_key = omniroute_env().get("OPENAI_API_KEY")
        probe = subprocess.CompletedProcess([], 0)
        if primary != "pheno_serve":
            probe = subprocess.run(
                [
                    sys.executable,
                    str(PHENO_ROOT / "scripts" / "probe_omniroute_models.py"),
                    "--force",
                ],
                cwd=PHENO_ROOT,
            )
        probe_path = EVAL_RESULTS_DIR / "tbench_model_probe.json"
        ok_models: set[str] = set()
        if probe_path.exists():
            ok_models = {
                mid
                for mid, r in json.loads(probe_path.read_text(encoding="utf-8"))
                .get("models", {})
                .items()
                if r.get("route") and not r.get("sunset")
            }
        if primary == "omniroute_main" and omni_key and not ok_models:
            ok_models = {e["id"] for e in cfg.get("models", [])}
            print(
                "OmniRoute Main: probe failed but API key present — continuing (--force implied)."
            )
        if primary == "direct_fireworks":
            fw_key = fireworks_env(
                prov.get("credential_id", "fireworks-ai-firepass")
            ).get("FIREWORKS_AI_API_KEY")
            if fw_key and not ok_models:
                ok_models = {e["id"] for e in cfg.get("models", [])}
                print(
                    "Direct FW: probe failed but fpk present — continuing (--force implied for direct API)."
                )
        if primary == "pheno_serve":
            ok_models = {e["id"] for e in cfg.get("models", [])}
        if not ok_models and not args.force:
            print("ERROR: No routes passed probe. Fix OmniRoute Main, then re-run.")
            print("  python scripts/probe_omniroute_models.py --force")
            print("  python scripts/run_tbench_model_matrix.py --all --resume --force")
            return 1
        if probe.returncode != 0:
            print(
                f"Warning: only {len(ok_models)} route(s) OK — continuing with those."
            )

    jobs_root = PHENO_ROOT / cfg.get("jobs_subdir", "jobs/harbor/tbench")
    state = load_state()
    # Clear stale "running" from interrupted jobs
    for mid, rec in list(state.get("models", {}).items()):
        if rec.get("status") == "running":
            rec["status"] = "failed"
            rec["error"] = "interrupted — resume will retry"
    save_state(state)

    entries = _model_entries(cfg, args.model)
    if not entries and not args.all and not args.model:
        entries = list(cfg.get("models", []))

    if args.all or args.resume:
        entries = list(cfg.get("models", []))
        if args.include_combo:
            entries.extend(cfg.get("combo_reference", []))

    if args.resume:
        probe_path = EVAL_RESULTS_DIR / "tbench_model_probe.json"
        ok_models = set()
        if probe_path.exists():
            ok_models = {
                mid
                for mid, r in json.loads(probe_path.read_text(encoding="utf-8"))
                .get("models", {})
                .items()
                if r.get("route")
            }
        entries = [
            e
            for e in entries
            if (state.get("models", {}).get(e["id"], {}).get("status") != "complete")
            and (not ok_models or e["id"] in ok_models)
        ]

    if not entries:
        print("No models to run.")
        export_leaderboard(include_combo=args.include_combo)
        return 0

    if not args.dry_run:
        _assert_local_only(entries, cfg)

    target = float(cfg["eval_protocol"]["target_mean"])
    print(
        f"TB2.0 matrix: {len(entries)} model(s), {args.n_tasks} tasks each, target>={target:.0%}"
    )
    print(
        "Integrity: terminus-2 only, n_attempts=1, holdout — no DPO/distill on these tasks."
    )

    worst_rc = 0
    for entry in entries:
        rc = _run_model(
            entry,
            n_tasks=args.n_tasks,
            n_concurrent=n_concurrent,
            dry_run=args.dry_run,
            jobs_root=jobs_root,
        )
        worst_rc = max(worst_rc, rc)

    out = export_leaderboard(include_combo=args.include_combo)
    print(f"\nLeaderboard: {out}")
    return worst_rc


if __name__ == "__main__":
    raise SystemExit(main())
