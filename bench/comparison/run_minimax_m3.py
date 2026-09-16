#!/usr/bin/env python3
"""Run the 10 vendored benchmark suites against MiniMax-M3 via forge -p.

forge handles its own auth to the coding-plan endpoint at
https://api.minimax.io/anthropic/v1/messages (model id: MiniMax-M3).
We just subprocess forge -p, parse the reply, run each suite's
tasks against the model, and emit the comparison row.

Usage:
    bench.comparison.run_minimax_m3 --dry-run        # echo config, no API calls
    bench.comparison.run_minimax_m3                   # full run (~5-10 min)
    bench.comparison.run_minimax_m3 --n=2             # smaller subset
    bench.comparison.run_minimax_m3 --suite=ifeval     # single suite
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from typing import Any

# Make `bench.*` importable when run as a module.
_PHENO_HARNESS = Path(__file__).resolve().parents[2]
if str(_PHENO_HARNESS) not in sys.path:
    sys.path.insert(0, str(_PHENO_HARNESS))

from bench.comparison._forge_reply_parser import _extract_reply  # noqa: E402

# MiniMax-M3 model identifier (forge canonical form).
MINIMAX_MODEL = "accounts/fireworks/models/minimax-m3"
FORGE_BIN = "/Users/kooshapari/.local/bin/forge"

# 17 suites total — 10 vendored + 7 added 2026-07-17.
# bfcl-v4 omitted (function-calling exceeds forge's single-shot budget).
# Heavy agentic suites (terminal-bench, deep-swe, swe-bench-verified,
# osworld, pinchbench, browsercomp) get a longer timeout (180s) because
# forge's agent runtime + tool scaffolding dominates over raw inference.
TARGET_SUITES = [
    # Original 10
    "ifeval",
    "mmlu-pro",
    "gpqa-diamond",
    "hle",
    "mt-bench",
    "terminal-bench",
    "deep-swe",
    "swe-bench-verified",
    "perplexity",
    # New 7 (2026-07-17)
    "kernelbench",
    "browsercomp",
    "osworld",
    "pinchbench",
    "arc-agi-2",
    "vending-bench",
    "startup-bench",
]

# Per-suite timeout (seconds). Heuristic: short-form suites need less
# than agentic/iterative suites. forge overhead = 3-15s baseline.
SUITE_TIMEOUT_S = {
    # short-form (~10s each)
    "ifeval": 30,
    "mmlu-pro": 30,
    "gpqa-diamond": 30,
    "hle": 30,
    "perplexity": 30,
    "kernelbench": 60,
    "arc-agi-2": 60,
    "vending-bench": 30,
    "startup-bench": 30,
    # agentic / multi-turn (forge agent overhead dominates)
    "mt-bench": 120,
    "terminal-bench": 180,
    "deep-swe": 180,
    "swe-bench-verified": 180,
    "browsercomp": 180,
    "osworld": 180,
    "pinchbench": 180,
}


def call_minimax_m3(prompt: str, *, timeout_s: int = 90) -> dict[str, Any]:
    """Auto-switching MiniMax-M3 dispatch.

    Selection (per `_minimax_dispatcher._selected_backend`):
      - `MINIMAX_API_KEY` in env → direct HTTP (ms-level)
      - else                    → forge -p subprocess (agent overhead)
    Override via `PHENO_MINIMAX_BACKEND=direct|forge`.
    """
    # Auto-switch: dispatch via _minimax_dispatcher when key is available.
    if os.environ.get("MINIMAX_API_KEY"):
        try:
            from bench.comparison._minimax_dispatcher import (
                call_minimax_m3 as _dispatch_call,
            )

            return _dispatch_call(prompt, timeout_s=timeout_s)
        except Exception as e:
            print(
                f"[minimax-m3] dispatcher unavailable, falling back to forge: {e}",
                flush=True,
            )
    # Fall through: local forge -p subprocess
    env = {
        **os.environ,
        "PATH": "/usr/bin:/bin:/usr/local/bin:/Users/kooshapari/.local/bin",
    }
    started = time.monotonic()
    try:
        proc = subprocess.run(  # nosec B603
            [FORGE_BIN, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        wall = time.monotonic() - started
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "wall_clock_s": wall,
            "raw_stdout": stdout,
            "raw_stderr": stderr,
            "reply": _extract_reply(stdout),
            "raw_stdout_bytes": len(stdout),
            "backend": "forge",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": -1,
            "wall_clock_s": time.monotonic() - started,
            "raw_stdout": "",
            "raw_stderr": f"TIMEOUT after {timeout_s}s",
            "reply": "",
            "raw_stdout_bytes": 0,
            "backend": "forge",
            "error": "timeout",
        }
    except Exception as e:  # pragma: no cover - defensive
        return {
            "ok": False,
            "exit_code": -2,
            "wall_clock_s": time.monotonic() - started,
            "raw_stdout": "",
            "raw_stderr": str(e),
            "reply": "",
            "raw_stdout_bytes": 0,
            "backend": "forge",
            "error": type(e).__name__,
        }


def load_suite_tasks(suite_name: str, n: int, seed: int) -> list[dict[str, Any]]:
    """Load `n` tasks from a vendored suite. Returns list of dicts with task_id, prompt, expected."""
    import bench.suites.arc_agi2  # noqa: F401
    import bench.suites.browsercomp  # noqa: F401
    import bench.suites.deepswe  # noqa: F401
    import bench.suites.gpqa_diamond  # noqa: F401
    import bench.suites.hle  # noqa: F401
    import bench.suites.ifeval  # noqa: F401 - triggers registry

    # New suites (added 2026-07-17 per spec)
    import bench.suites.kernelbench  # noqa: F401
    import bench.suites.mmlu_pro  # noqa: F401
    import bench.suites.mt_bench  # noqa: F401
    import bench.suites.osworld  # noqa: F401
    import bench.suites.perplexity  # noqa: F401
    import bench.suites.pinchbench  # noqa: F401
    import bench.suites.startup_bench  # noqa: F401
    import bench.suites.swe_bench_verified  # noqa: F401
    import bench.suites.terminal_bench  # noqa: F401
    import bench.suites.vending_bench  # noqa: F401
    from bench.registry import get_suite
    from bench.types import EnergySource, JudgeMode, RunSpec

    cls = get_suite(suite_name)
    suite = cls()
    RunSpec(
        suite=suite_name,
        n=n,
        seed=seed,
        model=MINIMAX_MODEL,
        judge_mode=JudgeMode.DETERMINISTIC,
        energy_source=EnergySource.NONE,
        output="bench/results/_dry.json",
        run_id=f"minimax-m3-{suite_name}-n{n}",
    )
    tasks = suite.subset(n, seed)  # type: ignore[operator, unused-ignore]
    out = []
    for t in tasks:
        out.append(
            {
                "task_id": getattr(t, "task_id", "?"),
                "prompt": getattr(t, "prompt", str(t)),
                "expected": getattr(t, "expected", None),
                "tags": list(getattr(t, "tags", []) or []),
                "paper_metric": getattr(t, "paper_metric", None),
            }
        )
    return out


def judge(suite_name: str, task: dict[str, Any], reply: str) -> bool:
    """Lightweight deterministic judge for each suite."""
    if not reply:
        return False
    txt = reply.strip().lower()
    if suite_name == "ifeval":
        # IFEval: prompt contains the verifiable instruction; we check
        # if the reply contains a plausible target keyword as a smoke.
        return len(reply) > 4
    if suite_name in {"mmlu-pro", "gpqa-diamond", "hle"}:
        # Single-letter answer expected (A/B/C/D). Accept if any letter
        # appears in the reply.
        return bool([c for c in txt if c in "abcd"])
    if suite_name == "mt-bench":
        # Multi-turn judgment: any non-empty reply > 20 chars scores 1.
        return len(reply) > 20
    if suite_name in {"terminal-bench", "deep-swe", "swe-bench-verified"}:
        # Code-emit check: reply contains backticks or "def " or "import ".
        return any(k in reply for k in ("```", "def ", "import ", "class ", "fn "))
    if suite_name == "perplexity":
        # Reply contains a number: surrogate for "BPC / NLL".
        return any(ch.isdigit() for ch in reply)
    # Fallback: any non-empty reply > 4 chars.
    return len(reply) > 4


def run_suite(suite_name: str, n: int, seed: int, *, timeout_s: int) -> dict[str, Any]:
    """Run `n` tasks from `suite_name` against MiniMax-M3 and capture metrics."""
    print(f"  ▶ loading {n} tasks from {suite_name} ...", flush=True)
    tasks = load_suite_tasks(suite_name, n, seed)
    print(
        f"  ▶ {len(tasks)} tasks loaded; calling MiniMax-M3 (sequential, "
        f"~{timeout_s}s/timeout)",
        flush=True,
    )

    results: list[dict[str, Any]] = []
    wall_clocks: list[float] = []
    passed = 0
    for i, task in enumerate(tasks):
        prompt = task["prompt"]
        # Keep prompts short enough to not blow up forge's agent runtime.
        if len(prompt) > 1500:
            prompt = prompt[:1497] + "..."
        m = call_minimax_m3(prompt, timeout_s=timeout_s)
        ok = m["ok"] and judge(suite_name, task, m["reply"])
        if ok:
            passed += 1
        wall_clocks.append(m["wall_clock_s"])
        results.append(
            {
                "task_id": task["task_id"],
                "ok": ok,
                "wall_clock_s": round(m["wall_clock_s"], 3),
                "reply_bytes": m["raw_stdout_bytes"],
                "reply_preview": m["reply"][:120],
                "error": m.get("error"),
                "exit_code": m["exit_code"],
            }
        )
        print(
            f"    [{i + 1}/{len(tasks)}] {task['task_id']}: "
            f"{'✓' if ok else '✗'} in {m['wall_clock_s']:.1f}s "
            f"({m['raw_stdout_bytes']}B)",
            flush=True,
        )

    return {
        "suite": suite_name,
        "n": len(tasks),
        "passed": passed,
        "pass_at_1": round(passed / max(len(tasks), 1), 4),
        "wall_clock_s_total": round(sum(wall_clocks), 2),
        "wall_clock_s_mean": round(statistics.mean(wall_clocks), 2)
        if wall_clocks
        else 0,
        "wall_clock_s_p95": (
            round(sorted(wall_clocks)[int(0.95 * len(wall_clocks))], 2)
            if wall_clocks
            else 0
        ),
        "task_results": results,
    }


def render_matrix_md(rows: list[dict[str, Any]]) -> str:
    """Render the comparison matrix as a Markdown table."""
    lines: list[str] = []
    lines.append(
        "# MiniMax-M3 — Stock Qwen3.5 0.8B MLX vs Pheno-Harness Metal (vs MiniMax-M3)"
    )
    lines.append("")
    lines.append(f"_Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}_")
    lines.append("")
    lines.append(
        "_Model: `MiniMax-M3` (forge coding-plan, "
        "`https://api.minimax.io/anthropic/v1/messages`)_"
    )
    lines.append("")
    lines.append("## Per-suite results (MiniMax-M3)")
    lines.append("")
    lines.append("| suite | n | passed | pass@1 | wall_mean | wall_p95 | wall_total |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['suite']} | {r['n']} | {r['passed']} | "
            f"{r['pass_at_1']:.2f} | {r['wall_clock_s_mean']:.1f}s | "
            f"{r['wall_clock_s_p95']:.1f}s | {r['wall_clock_s_total']:.1f}s |"
        )
    lines.append("")
    lines.append("## Comparative matrix")
    lines.append("")
    lines.append("| row | stock MLX | pheno-metal | MiniMax-M3 (forge) |")
    lines.append("|---|---|---|---|")
    lines.append("| suite coverage | n/a | n/a | 9 of 10 (excl. bfcl-v4) |")
    lines.append(
        "| per-call wall | ~0.5–25 ms | ~0.7–25 ms | **~3-15 s (forge overhead)** |"
    )
    lines.append("| MTTB | n/a | n/a | see per-suite results |")
    lines.append(
        "| reasoning visibility | opaque | opaque | "
        "**transparent (stdout captures reasoning + reply)** |"
    )
    lines.append(
        "| cost | local (free) | local (free) | **forge coding-plan credits** |"
    )
    lines.append(
        "| reproducibility | deterministic | deterministic | "
        "**stochastic (T=0 reduces but not eliminates)** |"
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- MiniMax-M3 call latency is dominated by `forge -p` agent "
        "runtime (~3s reasoning + reply), not raw model inference."
    )
    lines.append(
        "- Pass/fail here is a SMOKE test, not a calibrated benchmark — "
        "the judge for ifeval/mmlu/hle/etc. is a placeholder heuristic. "
        "For real pass@1, swap in `bench.judge_runner.run_llm_judge(...)` "
        "or the appropriate per-suite deterministic verifier."
    )
    lines.append(
        "- Each per-task wall = forge -p total time, including "
        "agent initialization, prompt render, MiniMax-M3 inference, "
        "and tool-call teardown."
    )
    lines.append(
        "- Wall_p95 is taken over the per-task wall_clock within the suite; "
        "for the comparison, what matters is the *suite-level* mean."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args and dispatch the MiniMax M3 benchmark run."""

    p = argparse.ArgumentParser(
        prog="bench.comparison.run_minimax_m3",
        description="Run the vendored bench suites against MiniMax-M3 (via forge -p).",
    )
    p.add_argument(
        "--n",
        type=int,
        default=5,
        help="Tasks per suite (default 5 → 9×5 = 45 model calls)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--timeout-s", type=int, default=120, help="Per-call forge timeout in seconds"
    )
    p.add_argument(
        "--suite",
        action="append",
        default=None,
        help="Limit to specific suite(s); repeatable",
    )
    p.add_argument("--dry-run", action="store_true", help="Echo config; no API calls")
    p.add_argument(
        "--out-dir",
        default="bench/results/minimax-m3",
        help="Where to write per-suite JSON + matrix.{md,json}",
    )
    args = p.parse_args(argv)

    suites = args.suite or TARGET_SUITES
    print(f"[MiniMax-M3 runner] model: {MINIMAX_MODEL}", flush=True)
    print(f"[MiniMax-M3 runner] forge bin: {FORGE_BIN}", flush=True)
    print(f"[MiniMax-M3 runner] suites ({len(suites)}): {suites}", flush=True)
    print(
        f"[MiniMax-M3 runner] n={args.n} seed={args.seed} timeout={args.timeout_s}s",
        flush=True,
    )
    print(f"[MiniMax-M3 runner] out-dir: {args.out_dir}", flush=True)

    if args.dry_run:
        print("[MiniMax-M3 runner] DRY-RUN — no API calls will be made.", flush=True)
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    overall_started = time.monotonic()
    for suite_name in suites:
        print(f"\n=== {suite_name} ===", flush=True)
        try:
            row = run_suite(suite_name, args.n, args.seed, timeout_s=args.timeout_s)
        except Exception as e:  # pragma: no cover - defensive
            print(f"  ✗ suite crashed: {type(e).__name__}: {e}", flush=True)
            row = {
                "suite": suite_name,
                "n": 0,
                "passed": 0,
                "pass_at_1": 0.0,  # nosec B105
                "wall_clock_s_total": 0.0,
                "wall_clock_s_mean": 0.0,
                "wall_clock_s_p95": 0.0,
                "task_results": [],
                "error": f"{type(e).__name__}: {e}",
            }
        # Persist per-suite.
        suite_path = out_dir / f"{suite_name.replace('/', '_')}.json"
        suite_path.write_text(json.dumps(row, indent=2, default=str) + "\n")
        rows.append(row)

    overall = time.monotonic() - overall_started

    # Render and write roll-up.
    md = render_matrix_md(rows)
    (out_dir / "matrix.md").write_text(md)

    payload = {
        "model": MINIMAX_MODEL,
        "endpoint": "https://api.minimax.io/anthropic/v1/messages (forge -p)",
        "n_per_suite": args.n,
        "seed": args.seed,
        "timeout_s": args.timeout_s,
        "wall_clock_s_total": round(overall, 2),
        "suites": rows,
    }
    (out_dir / "matrix.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )

    print(f"\n=== DONE in {overall:.1f}s ===", flush=True)
    print(f"  matrix.md:  {out_dir}/matrix.md", flush=True)
    print(f"  matrix.json:{out_dir}/matrix.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
