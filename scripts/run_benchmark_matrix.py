#!/usr/bin/env python3
"""Dry-run benchmark matrix planner — reads the July 2026 registry and prints an execution plan.

This command has no network, model, or subprocess integration.  It never starts
containers, downloads datasets, or invokes Harbor/Pier.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REGISTRY = ROOT / "config" / "benchmark_registry_2026-07.yaml"
VALID_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})


def load_registry(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    suites = raw.get("suites") or {}
    if not isinstance(suites, dict) or not suites:
        raise ValueError("registry must contain a non-empty suites mapping")
    tiers = raw.get("tiers") or {}
    if not isinstance(tiers, dict):
        raise ValueError("registry tiers must be a mapping")
    return raw


def _suite_tier(suite: dict[str, Any]) -> str:
    return str(suite.get("tier", ""))


def _suite_priority(suite: dict[str, Any]) -> str:
    return str(suite.get("pheno_priority", ""))


def filter_suites(
    registry: dict[str, Any],
    *,
    tier: str | None,
    priority: str | None,
    suite_ids: list[str] | None,
) -> list[tuple[str, dict[str, Any]]]:
    tiers = registry.get("tiers") or {}
    suites = registry.get("suites") or {}
    selected: list[tuple[str, dict[str, Any]]] = []
    for suite_id, suite in suites.items():
        if not isinstance(suite, dict):
            continue
        if tier and _suite_tier(suite) != tier:
            continue
        if priority and _suite_priority(suite) != priority:
            continue
        if suite_ids and suite_id not in suite_ids:
            continue
        if _suite_tier(suite) not in tiers:
            raise ValueError(
                f"suite {suite_id!r} references unknown tier {_suite_tier(suite)!r}"
            )
        if _suite_priority(suite) not in VALID_PRIORITIES:
            raise ValueError(
                f"suite {suite_id!r} has invalid pheno_priority {_suite_priority(suite)!r}"
            )
        selected.append((suite_id, suite))
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    selected.sort(
        key=lambda item: (
            priority_order[_suite_priority(item[1])],
            _suite_tier(item[1]),
            item[0],
        )
    )
    return selected


def _action_for_suite(
    suite_id: str, suite: dict[str, Any], policy: dict[str, Any]
) -> tuple[str, str]:
    if not suite.get("local_runnable", False):
        return "blocked", "not_local_runnable"
    if policy.get("local_only") and not suite.get("local_runnable"):
        return "blocked", "local_only_policy"
    driver = suite.get("driver") or {}
    script = driver.get("script")
    if script is None:
        return "blocked", "driver_not_wired"
    script_path = ROOT / str(script)
    if not script_path.is_file():
        return "blocked", "driver_script_missing"
    if not suite.get("scoreable", False):
        pin_status = str(suite.get("pin_status", "unpinned"))
        if pin_status != "locked":
            return "plan_only", "scoreable_false_or_unpinned"
    return "plan_only", "dry_run_ready"


def _dry_run_command(suite_id: str, suite: dict[str, Any]) -> list[str]:
    driver = suite.get("driver") or {}
    script = driver.get("script")
    if not script:
        return []
    cmd = [sys.executable, str(ROOT / script)]
    if suite_id in {"terminal_bench_2_0", "terminal_bench_2_1"}:
        suite_flag = driver.get("suite_flag")
        if suite_flag:
            cmd.extend(["--suite", str(suite_flag)])
        elif suite_id == "terminal_bench_2_0":
            cmd.extend(["--suite", "terminal-bench@2.0"])
        subset = driver.get("default_subset", "representative-6")
        cmd.extend(["--subset", str(subset)])
    elif suite_id == "deepswe":
        subset = driver.get("default_subset", 16)
        cmd.extend(["--subset", str(subset), "--env", "docker"])
    elif suite_id == "custom_pheno_dual_gpu":
        cmd.extend(
            [
                "--worker",
                "cuda0=http://127.0.0.1:21080",
                "--worker",
                "cuda1=http://127.0.0.1:8081",
                "--output",
                str(
                    ROOT
                    / suite.get("results_dir", "bench/results/perf")
                    / "matrix_dry_run.json"
                ),
                "--requests",
                "1",
            ]
        )
    elif suite_id == "custom_pheno_trace":
        spec_root = driver.get("spec_root", "bench/custom/trace-replay")
        cmd.extend(["--tasks", str(ROOT / spec_root)])
    return cmd


def build_plan(
    registry: dict[str, Any], selected: list[tuple[str, dict[str, Any]]]
) -> dict[str, Any]:
    policy = registry.get("policy") or {}
    tiers = registry.get("tiers") or {}
    rows: list[dict[str, Any]] = []
    for suite_id, suite in selected:
        action, reason = _action_for_suite(suite_id, suite, policy)
        upstream = suite.get("upstream") or {}
        pins = suite.get("pins") or {}
        row = {
            "suite_id": suite_id,
            "label": suite.get("label", suite_id),
            "tier": _suite_tier(suite),
            "tier_description": (tiers.get(_suite_tier(suite)) or {}).get(
                "description"
            ),
            "pheno_priority": _suite_priority(suite),
            "domain": suite.get("domain"),
            "pin_status": suite.get("pin_status"),
            "scoreable": bool(suite.get("scoreable", False)),
            "local_runnable": bool(suite.get("local_runnable", False)),
            "upstream_url": upstream.get("repository_url"),
            "dataset": upstream.get("dataset") or upstream.get("subset"),
            "revision_sha": pins.get("revision_sha"),
            "task_count": pins.get("task_count"),
            "harness": suite.get("harness"),
            "gates": list(suite.get("gates") or []),
            "action": action,
            "reason": reason,
            "results_dir": str(ROOT / str(suite.get("results_dir", "bench/results"))),
            "dry_run_command": _dry_run_command(suite_id, suite),
        }
        rows.append(row)
    actions: dict[str, int] = {}
    for row in rows:
        actions[row["action"]] = actions.get(row["action"], 0) + 1
    return {
        "schema_version": "pheno.benchmark.matrix-plan.v1",
        "registry_id": registry.get("registry_id"),
        "policy": policy,
        "filters_applied": {
            "count": len(rows),
            "actions": actions,
        },
        "plan": rows,
    }


def print_plan(plan: dict[str, Any]) -> None:
    print(f"Registry: {plan.get('registry_id')}  (dry-run only — no execution)")
    print(f"Suites:   {plan['filters_applied']['count']}")
    print(f"Actions:  {plan['filters_applied']['actions']}")
    print()
    for row in plan["plan"]:
        scoreable = "scoreable" if row["scoreable"] else "non-scoreable"
        print(
            f"[{row['pheno_priority']}] {row['suite_id']} "
            f"({row['tier']} / {row['domain']}) — {row['action']} ({scoreable})"
        )
        print(f"  label:   {row['label']}")
        print(
            f"  pin:     {row['pin_status']}  sha={row['revision_sha'] or '—'}  tasks={row['task_count'] or '—'}"
        )
        print(f"  reason:  {row['reason']}")
        if row["gates"]:
            print(f"  gates:   {', '.join(row['gates'])}")
        if row["dry_run_command"]:
            print(f"  command: {' '.join(row['dry_run_command'])}")
        else:
            print("  command: (none — driver not wired)")
        print(f"  results: {row['results_dir']}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a dry-run benchmark execution plan from the July 2026 registry"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to benchmark_registry_2026-07.yaml",
    )
    parser.add_argument(
        "--tier",
        help="Filter by tier id (agent_coding, computer_use, knowledge, kernel_gpu, custom_pheno)",
    )
    parser.add_argument(
        "--priority",
        choices=sorted(VALID_PRIORITIES),
        help="Filter by pheno_priority (P0–P3)",
    )
    parser.add_argument(
        "--suite",
        action="append",
        dest="suites",
        metavar="ID",
        help="Restrict to one or more suite ids (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full plan as JSON instead of human-readable text",
    )
    args = parser.parse_args()
    try:
        registry = load_registry(args.registry)
        selected = filter_suites(
            registry, tier=args.tier, priority=args.priority, suite_ids=args.suites
        )
        if not selected:
            parser.error("no suites matched the requested filters")
        plan = build_plan(registry, selected)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print_plan(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
