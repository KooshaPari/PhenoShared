# 5-min Benchmark Matrix — pheno-harness stock Qwen3.5-0.8B

version: bench 0.1.0  |  model: mock  |  n=5 tasks/suite  |  wall: 0.2s

| Suite | Domain | n | pass@1 | wall (s) | avg task (s) | tok/s | passed/failed |
|---|---|---:|---:|---:|---:|---:|---|

## Per-suite paper-metric targets
| Suite | paper metric (target) | achieved |
|---|---|---|

## Notes
- Mock-model: deterministic stub that flips pass/fail per task.
- Wall + per-task durations measured on M1 Pro.
- Token counts are whitespace-split word counts (stub adapter).
- Per-suite `paper_metrics` come from the vendored source suites.
