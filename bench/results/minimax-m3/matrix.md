# MiniMax-M3 — Stock Qwen3.5 0.8B MLX vs Pheno-Harness Metal (vs MiniMax-M3)

_Generated: 2026-07-17T10:34:26Z_

_Model: `MiniMax-M3` (forge coding-plan, `https://api.minimax.io/anthropic/v1/messages`)_

## Per-suite results (MiniMax-M3)

| suite | n | passed | pass@1 | wall_mean | wall_p95 | wall_total |
|---|---:|---:|---:|---:|---:|---:|
| ifeval | 5 | 4 | 0.80 | 10.8s | 26.0s | 53.8s |
| mmlu-pro | 5 | 5 | 1.00 | 18.0s | 42.2s | 89.8s |
| gpqa-diamond | 5 | 5 | 1.00 | 14.7s | 24.8s | 73.4s |
| hle | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| mt-bench | 5 | 4 | 0.80 | 72.5s | 120.3s | 362.6s |
| terminal-bench | 5 | 0 | 0.00 | 69.5s | 120.4s | 347.4s |
| deep-swe | 5 | 0 | 0.00 | 72.0s | 120.1s | 360.2s |
| swe-bench-verified | 5 | 0 | 0.00 | 90.9s | 120.5s | 454.3s |
| perplexity | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |

## Comparative matrix

| row | stock MLX | pheno-metal | MiniMax-M3 (forge) |
|---|---|---|---|
| suite coverage | n/a | n/a | 9 of 10 (excl. bfcl-v4) |
| per-call wall | ~0.5–25 ms | ~0.7–25 ms | **~3-15 s (forge overhead)** |
| MTTB | n/a | n/a | see per-suite results |
| reasoning visibility | opaque | opaque | **transparent (stdout captures reasoning + reply)** |
| cost | local (free) | local (free) | **forge coding-plan credits** |
| reproducibility | deterministic | deterministic | **stochastic (T=0 reduces but not eliminates)** |

## Notes

- MiniMax-M3 call latency is dominated by `forge -p` agent runtime (~3s reasoning + reply), not raw model inference.
- Pass/fail here is a SMOKE test, not a calibrated benchmark — the judge for ifeval/mmlu/hle/etc. is a placeholder heuristic. For real pass@1, swap in `bench.judge_runner.run_llm_judge(...)` or the appropriate per-suite deterministic verifier.
- Each per-task wall = forge -p total time, including agent initialization, prompt render, MiniMax-M3 inference, and tool-call teardown.
- Wall_p95 is taken over the per-task wall_clock within the suite; for the comparison, what matters is the *suite-level* mean.
