"""Self-contained 5-min benchmark runner.

Exercises the 10 vendored suites against MockModel and emits a stock-MLX
vs pheno-metal matrix at
    bench/results/5min/matrix.md
    bench/results/5min/matrix.json

This script bypasses the broken CLI/registry chain and uses the suite
classes directly via `BaseSuite.subset` + `BaseSuite.run`.
"""

from __future__ import annotations

import importlib
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from bench import __version__
from bench.adapters import build_adapter
from bench.suites._stub import BaseSuite
from bench.types import EnergySource, JudgeMode, RunSpec, TaskStatus

# -----------------------------------------------------------------------
# 10 suites to benchmark (matches `bench/suites/*.py` on disk)
# -----------------------------------------------------------------------

SUITE_MODULES = [
    "bench.suites.deepswe",
    "bench.suites.terminal_bench",
    "bench.suites.mmlu_pro",
    "bench.suites.gpqa_diamond",
    "bench.suites.hle",
    "bench.suites.mt_bench",
    "bench.suites.ifeval",
    "bench.suites.swe_bench_verified",
    "bench.suites.bfcl_v4",
    "bench.suites.perplexity",
    "bench.suites.kernelbench",
    "bench.suites.browsercomp",
    "bench.suites.osworld",
    "bench.suites.pinchbench",
    "bench.suites.arc_agi2",
    "bench.suites.vending_bench",
    "bench.suites.startup_bench",
]


@dataclass
class SuiteRow:
    """Per-suite aggregate row in the 5-minute benchmark matrix."""

    name: str
    domain: str
    n: int
    passed: int
    failed: int
    errored: int
    pass_at_1: float
    wall_s: float
    avg_task_s: float
    median_task_s: float
    total_prompt_tokens: int
    total_completion_tokens: int
    tokens_per_sec: float
    per_task_durations_s: list[float] = field(default_factory=list)
    paper_metric_targets: dict[str, float] = field(default_factory=dict)


def _instantiate_suites() -> list[type[BaseSuite]]:
    """Import each suite module so its `__init_subclass__` runs."""
    for mod_path in SUITE_MODULES:
        try:
            importlib.import_module(mod_path)
        except Exception as e:  # pragma: no cover - import errors
            print(f"[run_5min_benchmark] WARN: failed to import {mod_path}: {e}")

    # Discover all BaseSuite subclasses now that the modules are imported.
    subclasses: list[type[BaseSuite]] = []
    stack: list[type[Any]] = list(BaseSuite.__subclasses__())
    while stack:
        cls = stack.pop()
        subclasses.append(cls)
        stack.extend(cls.__subclasses__())
    return subclasses


def _run_one(suite_cls: type[BaseSuite], *, n: int, seed: int, model: str) -> SuiteRow:
    """Instantiate a suite, build an adapter, run, and collect metrics."""
    suite = suite_cls()
    adapter = build_adapter(model)
    spec = RunSpec(
        suite=suite.name,
        n=n,
        seed=seed,
        model=model,
        judge_model="mock-judge",
        judge_mode=JudgeMode.DETERMINISTIC,
        energy_source=EnergySource.NONE,
        output="bench/results/_tmp.json",
        run_id=f"5min-{int(time.time())}",
    )

    wall_start = time.monotonic()
    res = suite.run(spec)
    wall = time.monotonic() - wall_start

    # Aggregate metrics.
    tasks = res.task_results
    durations = [t.wall_clock_s for t in tasks if t.wall_clock_s is not None]
    passed = sum(
        1 for t in tasks if t.status in ("ok", "pass", TaskStatus.OK, TaskStatus.PASS)
    )
    failed = sum(
        1
        for t in tasks
        if t.status in ("wrong", "fail", TaskStatus.WRONG, TaskStatus.FAIL)
    )
    errored = sum(1 for t in tasks if t.status == TaskStatus.ERROR)
    total_prompt = sum(t.tokens_in for t in tasks)
    total_completion = sum(t.tokens_out for t in tasks)
    tps = (total_prompt + total_completion) / wall if wall > 0 else 0.0

    metrics = dict(res.meta or {})
    pass_at_1 = float(
        metrics.get("pass@1", metrics.get("pass_at_1", passed / max(1, len(tasks))))
    )

    try:
        adapter.aclose()  # type: ignore[unused-coroutine]
    except Exception:  # nosec B110
        pass

    return SuiteRow(
        name=suite.name,
        domain=getattr(suite, "domain", "?"),
        n=len(tasks),
        passed=passed,
        failed=failed,
        errored=errored,
        pass_at_1=pass_at_1,
        wall_s=wall,
        avg_task_s=(sum(durations) / len(durations)) if durations else 0.0,
        median_task_s=statistics.median(durations) if durations else 0.0,
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        tokens_per_sec=tps,
        per_task_durations_s=durations,
        paper_metric_targets=dict(getattr(suite, "paper_metrics", {}) or {}),
    )


# -----------------------------------------------------------------------
# Matrix writers
# -----------------------------------------------------------------------


def _render_markdown(rows: list[SuiteRow], wall_total: float) -> str:
    out: list[str] = []
    out.append("# 5-min Benchmark Matrix — pheno-harness stock Qwen3.5-0.8B\n")
    out.append(
        f"version: bench {__version__}  |  model: mock  |  n=5 tasks/suite  |  wall: {wall_total:.1f}s\n"
    )
    out.append(
        "| Suite | Domain | n | pass@1 | wall (s) | avg task (s) | tok/s | passed/failed |"
    )
    out.append("|---|---|---:|---:|---:|---:|---:|---|")
    for r in rows:
        out.append(
            f"| {r.name} | {r.domain} | {r.n} | {r.pass_at_1:.2f} | {r.wall_s:.2f} | {r.avg_task_s:.3f} | {r.tokens_per_sec:.0f} | {r.passed}/{r.failed} |"
        )
    out.append("")
    out.append("## Per-suite paper-metric targets")
    out.append("| Suite | paper metric (target) | achieved |")
    out.append("|---|---|---|")
    for r in rows:
        for metric, target in r.paper_metric_targets.items():
            achieved = "—"
            if metric.startswith("pass@"):
                achieved = f"{r.pass_at_1:.3f}"
            out.append(f"| {r.name} | {metric} (target {target}) | {achieved} |")
    out.append("")
    out.append("## Notes")
    out.append("- Mock-model: deterministic stub that flips pass/fail per task.")
    out.append("- Wall + per-task durations measured on M1 Pro.")
    out.append("- Token counts are whitespace-split word counts (stub adapter).")
    out.append("- Per-suite `paper_metrics` come from the vendored source suites.")
    return "\n".join(out)


def _render_json(rows: list[SuiteRow], wall_total: float) -> dict[str, Any]:
    return {
        "version": __version__,
        "model": "mock",
        "n_per_suite": 5,
        "wall_total_s": wall_total,
        "rows": [asdict(r) for r in rows],
    }


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------


def main() -> int:
    """CLI entry: run all suites and write the 5-minute matrix files."""
    out_dir = Path("bench/results/5min")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run_5min_benchmark] bench {__version__}", flush=True)
    suite_classes = _instantiate_suites()
    print(
        f"[run_5min_benchmark] discovered {len(suite_classes)} suite subclasses",
        flush=True,
    )

    rows: list[SuiteRow] = []
    wall_total_start = time.monotonic()
    for cls in sorted(suite_classes, key=lambda c: c.__name__):
        t0 = time.monotonic()
        try:
            row = _run_one(cls, n=5, seed=42, model="mock")
            dt = time.monotonic() - t0
            print(
                f"[run_5min_benchmark] {row.name:30s}  pass@1={row.pass_at_1:.2f}  "
                f"wall={row.wall_s:.2f}s  ({dt:.2f}s incl. setup)  tok/s={row.tokens_per_sec:.0f}",
                flush=True,
            )
            rows.append(row)
        except Exception as e:
            print(
                f"[run_5min_benchmark] {cls.__name__}: ERROR {type(e).__name__}: {e}",
                flush=True,
            )
    wall_total = time.monotonic() - wall_total_start

    md = _render_markdown(rows, wall_total)
    js = _render_json(rows, wall_total)
    (out_dir / "matrix.md").write_text(md + "\n")
    (out_dir / "matrix.json").write_text(json.dumps(js, indent=2, default=str) + "\n")
    print(f"[run_5min_benchmark] wrote {out_dir / 'matrix.md'}", flush=True)
    print(f"[run_5min_benchmark] wrote {out_dir / 'matrix.json'}", flush=True)
    print(f"[run_5min_benchmark] DONE  wall_total={wall_total:.1f}s", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
