# MiniMax-M3 — Stock Qwen3.5 0.8B MLX vs Pheno-Harness Metal (vs MiniMax-M3)

_Generated: 2026-07-17T22:34:19Z_

_Model: `MiniMax-M3` (forge coding-plan, `https://api.minimax.io/anthropic/v1/messages`)_

## Per-suite results (MiniMax-M3)

| suite | n | passed | pass@1 | wall_mean | wall_p95 | wall_total |
|---|---:|---:|---:|---:|---:|---:|
| ifeval | 3 | 2 | 0.67 | 6.2s | 9.0s | 18.6s |
| mmlu-pro | 3 | 3 | 1.00 | 8.3s | 12.7s | 24.9s |
| gpqa-diamond | 3 | 3 | 1.00 | 4.7s | 7.0s | 13.9s |
| hle | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| mt-bench | 3 | 3 | 1.00 | 33.2s | 78.9s | 99.7s |
| terminal-bench | 3 | 0 | 0.00 | 15.6s | 30.9s | 46.9s |
| deep-swe | 3 | 0 | 0.00 | 81.0s | 120.0s | 243.1s |
| swe-bench-verified | 3 | 0 | 0.00 | 120.0s | 120.0s | 360.1s |
| perplexity | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| kernelbench | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| browsercomp | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| osworld | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| pinchbench | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| arc-agi-2 | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| vending-bench | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |
| startup-bench | 0 | 0 | 0.00 | 0.0s | 0.0s | 0.0s |

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
