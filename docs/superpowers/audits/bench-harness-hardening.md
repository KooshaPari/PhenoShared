# Bench Harness Hardening — Audit + SOTA-isms (2026-07-24)

## Status: 17 suites, 22 files, all compile clean. 3 known bug classes.

### P0 — Field-Name Mismatches (blocking)
| Bug | Severity | Location | Files Affected |
|---|---|---|---|
| `metrics=` passed to `TaskResult()` | P0 | 7 suites use `metrics=` but actual field is `meta=` | hle.py, perplexity.py, swe_bench_verified.py, terminal_bench.py, mt_bench.py, deepswe.py, ifeval.py |
| `reward=` passed to `TaskResult()` | P0 | 5 suites pass non-existent `reward` kwarg | ifeval.py, mt_bench.py, hle.py, deepswe.py, terminal_bench.py |
| `tool_calls=int` passed to `TaskResult()` | P0 | 2 suites pass int, field is `tool_calls=list` | terminal_bench.py, swe_bench_verified.py |
| `message=` passed to `TaskResult()` | P0 | 4 suites pass non-existent `message` kwarg | ifeval.py, mt_bench.py, terminal_bench.py, deepswe.py |

### P1 — Tests Missing
- No CI pipeline; no GitHub Actions workflow in `bench/`
- No `pytest` tests for the suite runner or adapter dispatch
- RLVR-AF tournament has 0 unit tests
- Only smoke test is `python3 -m bench.comparison.run_5min_benchmark`

### P2 — Exception Handling
- `adapter.aclose()` call is not idempotent-safe
- `Adapter.generate()` in MockModel returns dummy text with zero timings — callers that divide by `latency_ms` will crash

### P3 — Stale Code
- `bench/comparison/stock_vs_ours_analysis.py` — 169 LoC, imports non-existent modules
- `bench/comparison/stock_vs_ours_adapters.py` — imports `mlx_direct` which exists but may drift
- 5 empty audit directories (created but nothing written)
