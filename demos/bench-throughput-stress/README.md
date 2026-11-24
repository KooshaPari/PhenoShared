# bench-throughput-stress

GUI/visual stress-test demo for pheno-harness's bench CLI. Spawns N
concurrent bash workers invoking `bench/cli.py info <suite>` against
the registered suites and serves a live HTML dashboard on http://127.0.0.1:9003/.

## Run

```bash
cd pheno-harness
# terminal 1: stress driver (N=8, duration_s=15)
N=8 duration_s=15 bash demos/bench-throughput-stress/scripts/stress.sh

# terminal 2: aggregator + dashboard
PYTHONPATH=. python3 demos/bench-throughput-stress/scripts/aggregate.py --watch --port 9003
```

Open http://127.0.0.1:9003/ while the demo runs.

## What it stresses

| Dimension | How |
|---|---|
| Concurrent bench CLI invocations | N parallel bash workers |
| Suite introspection | `bench/cli.py info` per suite per worker |
| Per-suite latency | wall-clock per call, p50/p99 captured |
| Exit-code distribution | OK vs fail ratio |

## Files

- `scripts/stress.sh` — N workers × duration_s against all suites
- `scripts/aggregate.py` — reads `artifacts/runs.jsonl`, writes `metrics.json`, serves dashboard
- `assets/dashboard/index.html` — GUI (served at runtime)
- `artifacts/runs.jsonl` — per-invocation telemetry
