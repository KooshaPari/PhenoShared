#!/usr/bin/env bash
# Smoke test for the pheno-harness bench/runner.
#
# Runs a tiny end-to-end pass:
#   - 3 tasks sampled deterministically (--seed=42)
#   - MLX stub adapter (no GPU, no network)
#   - Verifies both JSON + md outputs are produced and under 50KB
#
# Exit codes:
#   0  success
#   1  report.md or report.json missing
#   2  output file exceeded 50KB limit
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${OUTPUT:-/tmp/bench-smoke}"
SIZE_LIMIT_BYTES=$((50 * 1024))

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"

cd "$REPO_ROOT"

# The skeleton does not ship a real Suite yet, so the smoke test registers
# a tiny StubSuite in-process and runs it through the executor end-to-end.
BENCH_DISABLE_METAL_PROBE=1 OUTPUT="$OUTPUT" python - <<'PY'
import asyncio, os, sys, time
from pathlib import Path

from bench.registry import Suite
from bench.types import (
    EnergySource, JudgeMode, RunSpec, TaskResult, SuiteResult,
)
from bench.metric import Metric
from bench.runner.executor import Executor, ExecutorConfig
from bench.runner.report import RunReportAggregator, write_report

OUTPUT = os.environ["OUTPUT"]

class StubSuite(Suite):
    name = "deep-swe-smoke"
    source_url = "smoke://stub"
    format = "deterministic"
    subset = "n=3"
    rationale = "in-process smoke test"
    default_judge_mode = "deterministic"

    def run(self, run_spec):
        tasks = []
        for i in range(3):
            tasks.append(TaskResult(
                task_id=f"deep-swe-smoke-{i:04d}",
                suite=self.name,
                status="PASS",
                score=1.0,
                metrics={
                    "tokens_in": 12 + i,
                    "tokens_out": 24 + i,
                    "wall_clock_s": 0.5 + i * 0.1,
                    "joules": 1.2 + i,
                    "peak_rss_mb": 200.0,
                    "tokens_per_s": 48.0 + i,
                },
            ))
        return SuiteResult(
            suite=self.name, model="mlx-stub", tasks=tasks,
            metrics={
                "pass@1": Metric("pass@1", 1.0, "smoke", "frac", True),
                "wall_clock_total": Metric("wall_clock_total", 1.8, "smoke", "s", False),
                "joules_total": Metric("joules_total", 5.4, "smoke", "J", False),
                "joules_per_passed_task": Metric("joules_per_passed_task", 1.8, "smoke", "J", False),
                "tokens_in_total": Metric("tokens_in_total", 39, "smoke", "tok", True),
                "tokens_out_total": Metric("tokens_out_total", 75, "smoke", "tok", True),
            },
        )

spec = RunSpec(
    suite="deep-swe-smoke",
    n=3, seed=42,
    model="mlx-stub",
    judge_model="claude-sonnet-5",
    judge_mode=JudgeMode.DETERMINISTIC,
    energy_source=EnergySource.NONE,
    output=OUTPUT,
    run_id=f"smoke-{int(time.time())}",
)
config = ExecutorConfig(
    spec=spec, workers=2, per_task_timeout_s=10.0,
    cache_path=None, no_cache=True, stability_metric=False,
)
executor = Executor(config)
result = asyncio.run(executor.run())

out_path = Path(OUTPUT)
out_path.mkdir(parents=True, exist_ok=True)
agg = RunReportAggregator(
    run_id=spec.run_id,
    judge_mode=spec.judge_mode,
    energy_source=spec.energy_source,
)
agg.set_extra("runner_version", "smoke")
agg.set_extra("model", "mlx-stub")
agg.add(result)
files = write_report(agg.to_run_report(), out_path, aggregator=agg, filename_base="report")
print("[smoke] wrote", files["json"], "and", files["md"])
PY

report_json="$OUTPUT/report.json"
report_md="$OUTPUT/report.md"

if [[ ! -s "$report_json" ]]; then
    echo "FAIL: $report_json not produced or empty" >&2
    exit 1
fi
if [[ ! -s "$report_md" ]]; then
    echo "FAIL: $report_md not produced or empty" >&2
    exit 1
fi

for f in "$report_json" "$report_md"; do
    size=$(wc -c < "$f" | tr -d ' ')
    if [[ "$size" -gt "$SIZE_LIMIT_BYTES" ]]; then
        echo "FAIL: $f is ${size}B, exceeds ${SIZE_LIMIT_BYTES}B limit" >&2
        exit 2
    fi
    echo "OK: $f (${size}B)"
done

echo
echo "--- report.md (head) ---"
head -20 "$report_md"
echo "--- report.json (head) ---"
head -c 400 "$report_json"
echo
echo "SMOKE TEST PASSED"
