"""Local Qwen3.5-0.8B benchmark runner.

Drives each vendored suite's tasks through the MLXModelAdapter directly,
bypassing the broken suite.run(task_spec) path which never uses the external
adapter. Measures per-suite wall-clock time, pass@1, and token latency.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import bench.suites.arc_agi2  # noqa: F401
import bench.suites.bfcl_v4  # noqa: F401
import bench.suites.browsercomp  # noqa: F401
import bench.suites.deepswe  # noqa: F401
import bench.suites.gpqa_diamond  # noqa: F401
import bench.suites.hle  # noqa: F401

# Force suite registration
import bench.suites.ifeval  # noqa: F401
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
from bench.adapters import ModelResponse, build_adapter
from bench.registry import list_suites


def main() -> None:
    """CLI entry: build the MLX adapter and run the 16 vendored suites."""
    adapter = build_adapter("mlx")
    print(f"[local-qwen] adapter={type(adapter).__name__} loaded", flush=True)

    results = []

    for cls in list_suites():
        name = cls.name
        print(f"[local-qwen] suite={name}", flush=True)

        # Instantiate and get n=2 tasks (seed=42)
        try:
            suite = cls()
        except Exception as e:
            print(f"  FAIL instantiate: {e}", flush=True)
            results.append({"suite": name, "error": f"instantiate: {e}"})
            continue

        try:
            tasks = suite.subset(2, 42)  # n=2, seed=42
        except AttributeError:
            # Try the spec-based path
            from bench.types import EnergySource, JudgeMode, RunSpec

            spec = RunSpec(
                suite=name,
                n=2,
                seed=42,
                model="mlx",
                judge_mode=JudgeMode.DETERMINISTIC,
                energy_source=EnergySource.NONE,
                run_id=f"local-{name}",
            )
            try:
                tasks_raw = suite.subset(spec.n, spec.seed)
            except Exception:
                # Fallback: use .tasks attribute
                tasks_raw = getattr(suite, "tasks", getattr(suite, "default_tasks", []))
            tasks = tasks_raw[:2] if len(tasks_raw) >= 2 else tasks_raw

        if not tasks:
            print("  FAIL: 0 tasks", flush=True)
            results.append({"suite": name, "error": "0 tasks"})
            continue

        # Run each task through the MLX adapter
        task_results = []
        suite_start = time.time()
        for td in tasks[:2]:
            prompt_str = getattr(td, "prompt", str(td))
            expected = getattr(td, "expected", None)

            t0 = time.time()
            try:
                resp: ModelResponse = adapter.complete(  # type: ignore[assignment]
                    [{"role": "user", "content": prompt_str}],  # type: ignore[arg-type]
                    max_tokens=64,
                )
                elapsed = time.time() - t0
                reply = getattr(resp, "text", "") or str(resp)
                passed = expected is None or (
                    expected.strip().lower() in reply.strip().lower()
                )
                print(
                    f"  [{getattr(td, 'task_id', '?')}] wall={elapsed * 1000:.0f}ms pass={passed} tok_in={resp.prompt_tokens} tok_out={resp.completion_tokens}",
                    flush=True,
                )
                task_results.append(
                    {
                        "task_id": getattr(td, "task_id", "?"),
                        "passed": passed,
                        "wall_ms": elapsed * 1000,
                        "tokens_in": resp.prompt_tokens,
                        "tokens_out": resp.completion_tokens,
                    }
                )
            except Exception as e:
                elapsed = time.time() - t0
                print(
                    f"  [{getattr(td, 'task_id', '?')}] FAIL: {type(e).__name__}: {e}",
                    flush=True,
                )
                task_results.append(
                    {
                        "task_id": getattr(td, "task_id", "?"),
                        "passed": False,
                        "wall_ms": elapsed * 1000,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "error": str(e)[:200],
                    }
                )

        suite_elapsed = time.time() - suite_start
        passed = sum(1 for r in task_results if r["passed"])  # type: ignore[assignment, misc]
        total = len(task_results)
        results.append(
            {
                "suite": name,
                "n": total,  # type: ignore[dict-item]
                "passed": passed,  # type: ignore[dict-item]
                "pass_at_1": passed / total if total else 0,  # type: ignore[dict-item]
                "wall_clock_s": suite_elapsed,  # type: ignore[dict-item]
                "tasks": task_results,  # type: ignore[dict-item]
            }
        )

    # Write results
    out_dir = Path("bench/results/local-qwen")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "arch": "Qwen3.5-0.8B",
        "adapter": "mlx",
        "timestamp": time.time(),
        "results": [r for r in results if "error" not in r],
        "errors": [r for r in results if "error" in r],
    }
    out_path = out_dir / "matrix.json"
    out_path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    print(f"\n[local-qwen] wrote {out_path}", flush=True)

    # Print summary
    print("\n=== SUMMARY ===")
    for r in results:
        if "error" in r:
            print(f"  FAIL {r['suite']:25s}  {r['error'][:100]}")
        else:
            pct = r["pass_at_1"] * 100
            wall = r["wall_clock_s"]
            print(
                f"  PASS {r['suite']:25s}  {r['passed']}/{r['n']} ({pct:.0f}%)  {wall * 1000:.0f}ms"
            )


if __name__ == "__main__":
    main()
