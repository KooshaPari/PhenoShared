#!/usr/bin/env python3
"""Run TB2.0 eval across route kinds: OmniRoute cloud, local llama, Main router combo."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from eval.route_matrix import (
    export_route_leaderboard,
    load_routes_config,
    load_routes_state,
    save_routes_state,
    score_route_from_job,
)
from harness.intent_graph import IntentGraphRecorder
from pheno.harbor_util import harbor_exe, route_env
from pheno.paths import EVAL_RESULTS_DIR, PHENO_ROOT


def _entries(
    cfg: dict[str, Any], *, model: str | None, route_kind: str | None, include_combo: bool
) -> list[dict]:
    entries = list(cfg.get("models", []))
    if (cfg.get("policy") or {}).get("local_only"):
        entries = [
            e for e in entries if e.get("route_kind") in ("local_direct", "pheno_serve")
        ]
    if include_combo:
        entries.extend(cfg.get("combo_reference", []))
    if route_kind:
        entries = [e for e in entries if e.get("route_kind") == route_kind]
    if model:
        entries = [e for e in entries if e["id"] == model or e.get("label") == model]
    return entries


def _assert_local_only(entries: list[dict]) -> None:
    cloud = [
        e.get("id", "")
        for e in entries
        if e.get("route_kind") not in ("local_direct", "pheno_serve")
    ]
    if cloud:
        raise SystemExit(
            "Cloud TBench execution is disabled by policy; select route-kind local_direct or pheno_serve. "
            f"Rejected entries: {cloud}"
        )


def _run_entry(
    entry: dict[str, Any],
    *,
    n_tasks: int,
    n_concurrent: int,
    dry_run: bool,
    jobs_root: Path,
    cfg: dict[str, Any],
) -> int:
    model_id = entry["id"]
    label = entry.get("label", model_id)
    slug = model_id.replace("/", "__").replace(":", "_")
    job_out = jobs_root / slug
    job_out.mkdir(parents=True, exist_ok=True)
    run_id = (
        datetime.now(UTC).strftime("tb20_route_%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8]
    )
    graph_path = job_out / f"{run_id}.graph.json"
    recorder = IntentGraphRecorder(
        run_id, "terminal-bench@2.0", metadata={"route_kind": entry.get("route_kind")}
    )
    root_node = recorder.start_node(
        "run",
        "tbench_route_cell",
        attributes={"model_id": model_id, "n_tasks": n_tasks},
    )

    route_kind, harbor_model, run_env = route_env(entry, cfg)
    cmd = [
        harbor_exe(),
        "run",
        "-c",
        str(PHENO_ROOT / "config" / "harbor_tbench_agent.yaml"),
        "--dataset",
        cfg["eval_protocol"]["dataset"],
        "-a",
        cfg["eval_protocol"]["agent"],
        "-m",
        harbor_model,
        "--env",  # Portage compatibility token for the Podman runtime.
        "docker",
        "--n-concurrent",
        str(n_concurrent),
        "-l",
        str(n_tasks),
        "-o",
        str(job_out),
        "-y",
    ]
    # Observability: attach the Langfuse job plugin when LANGFUSE_* env vars
    # are present (job->session, trial->trace, reward->score). No-op otherwise.
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        cmd += ["--plugin", "harbor_langfuse:LangfusePlugin"]

    state = load_routes_state()
    state.setdefault("models", {})[model_id] = {
        "status": "running",
        "label": label,
        "route_kind": route_kind,
        "routing_policy": entry.get("routing_policy"),
        "started_at": datetime.now(UTC).isoformat(),
        "n_tasks_requested": n_tasks,
        "harbor_model": harbor_model,
        "job_dir": str(job_out),
        "graph_path": str(graph_path),
    }
    save_routes_state(state)

    print(
        f"\n=== {label} ({model_id}) kind={route_kind} policy={entry.get('routing_policy')} ==="
    )
    print("Command:", " ".join(cmd))
    model_node = recorder.start_node(
        "model_call",
        "harbor_agent_session",
        parent=root_node,
        attributes={"model": harbor_model, "route_kind": route_kind, "command": cmd},
    )
    if dry_run:
        state["models"][model_id]["status"] = "planned"
        save_routes_state(state)
        recorder.finish_node(model_node, status="planned")
        recorder.finish_node(root_node, status="planned")
        recorder.write(graph_path)
        return 0

    if route_kind not in ("local_direct", "pheno_serve") and not run_env.get(
        "OPENAI_API_KEY"
    ):
        state["models"][model_id]["status"] = "failed"
        state["models"][model_id]["error"] = "missing OPENAI_API_KEY"
        save_routes_state(state)
        print("ERROR: OPENAI_API_KEY missing for OmniRoute route")
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
    job_dirs = sorted(
        [p for p in job_out.iterdir() if p.is_dir() and (p / "result.json").exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    job_dir = job_dirs[0] if job_dirs else job_out
    target = float(cfg["eval_protocol"]["target_mean"])
    rs = score_route_from_job(job_dir, entry, target_mean=target)
    verifier_node = recorder.start_node(
        "verifier",
        "harbor_result",
        parent=root_node,
        attributes={"job_dir": str(job_dir)},
    )
    recorder.finish_node(
        verifier_node,
        status="passed" if rs and rc == 0 else "failed" if rc else "incomplete",
        attributes={
            "mean": rs.mean if rs else None,
            "pass_at_1": rs.pass_at_1 if rs else None,
        },
    )
    recorder.add_edge(verifier_node, model_node, "verifies")

    rec = state["models"][model_id]
    rec["finished_at"] = datetime.now(UTC).isoformat()
    rec["returncode"] = rc
    rec["job_dir"] = str(job_dir)
    if rs:
        rec.update(rs.to_dict())
        rec["status"] = "complete" if rc == 0 else "failed"
    else:
        rec["status"] = "failed" if rc != 0 else "incomplete"
    save_routes_state(state)
    if rs:
        print(
            f"  mean={rs.mean:.3f} tok/s={rs.tok_s} cost=${rs.cost_usd:.3f} "
            f"composite={rs.pillars['composite']:.3f}"
        )
    recorder.finish_node(root_node, status=rec["status"])
    recorder.write(graph_path)
    return rc


def main() -> int:
    p = argparse.ArgumentParser(
        description="TB2.0 route matrix (non-firepass + local + router)"
    )
    p.add_argument("--model", help="Single model id or label")
    p.add_argument(
        "--route-kind",
        help="omniroute_cloud | pheno_serve | local_direct | omniroute_combo",
    )
    p.add_argument("--all", action="store_true")
    p.add_argument(
        "--include-combo", action="store_true", help="Include Main combo router"
    )
    p.add_argument("--n-tasks", type=int, default=None)
    p.add_argument(
        "--n-concurrent",
        type=int,
        default=None,
        help="Concurrent Harbor trials for scaled local runs",
    )
    p.add_argument("--pilot", action="store_true", help="Use pilot_n_tasks from config")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--export-only", action="store_true")
    args = p.parse_args()

    cfg = load_routes_config()
    proto = cfg.get("eval_protocol") or {}
    n_tasks = args.n_tasks
    if n_tasks is None:
        n_tasks = int(
            proto.get("pilot_n_tasks", 3)
            if args.pilot
            else proto.get("n_tasks_total", 89)
        )
    n_concurrent = args.n_concurrent or int(proto.get("n_concurrent_trials", 1))
    if n_concurrent < 1:
        raise SystemExit("--n-concurrent must be positive")

    if args.export_only:
        out = export_route_leaderboard(route_kind=args.route_kind)
        print(f"Exported {out}")
        return 0

    if not args.dry_run:
        probe_cmd = [
            sys.executable,
            str(PHENO_ROOT / "scripts" / "probe_tbench_routes.py"),
            "--force",
        ]
        if args.route_kind:
            probe_cmd.extend(["--route-kind", args.route_kind])
        subprocess.run(probe_cmd, cwd=PHENO_ROOT)
        probe_path = EVAL_RESULTS_DIR / "tbench_route_probe.json"
        ok_models: set[str] = set()
        if probe_path.exists():
            ok_models = {
                mid
                for mid, r in json.loads(probe_path.read_text(encoding="utf-8"))
                .get("models", {})
                .items()
                if r.get("route")
            }
        if not ok_models and not args.force:
            print(
                "ERROR: No routes passed probe. Start OmniRoute/local swarm, then re-run with --force."
            )
            return 1

    state = load_routes_state()
    for mid, rec in list(state.get("models", {}).items()):
        if rec.get("status") == "running":
            rec["status"] = "failed"
            rec["error"] = "interrupted — resume will retry"
    save_routes_state(state)

    entries = _entries(
        cfg,
        model=args.model,
        route_kind=args.route_kind,
        include_combo=args.include_combo,
    )
    if args.all or args.resume:
        entries = _entries(
            cfg,
            model=None,
            route_kind=args.route_kind,
            include_combo=args.include_combo,
        )

    if args.resume:
        probe_path = EVAL_RESULTS_DIR / "tbench_route_probe.json"
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
            if state.get("models", {}).get(e["id"], {}).get("status") != "complete"
            and (not ok_models or e["id"] in ok_models or args.force)
        ]

    if not entries:
        print("No route entries to run.")
        export_route_leaderboard(route_kind=args.route_kind)
        return 0

    if not args.dry_run:
        _assert_local_only(entries)

    jobs_root = PHENO_ROOT / cfg.get("jobs_subdir", "jobs/harbor/tbench-routes")
    print(f"Route matrix: {len(entries)} entry(ies), {n_tasks} tasks each")
    worst = 0
    for entry in entries:
        worst = max(
            worst,
            _run_entry(
                entry,
                n_tasks=n_tasks,
                n_concurrent=n_concurrent,
                dry_run=args.dry_run,
                jobs_root=jobs_root,
                cfg=cfg,
            ),
        )
    out = export_route_leaderboard(route_kind=args.route_kind)
    print(f"\nRoute leaderboard: {out}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
