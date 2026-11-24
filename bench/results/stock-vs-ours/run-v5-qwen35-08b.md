# Qwen/Qwen3.5-0.8B Stock vs Ours — 10 suites × 25 tasks

Model: `Qwen/Qwen3.5-0.8B`  •  Backend: `direct MLX Python API`

## Summary

| Variant | pass@1 | mean wall | mean partial_credit | format_compliance | intent_preservation | ok | n |
|---------|--------|-----------|--------------------|-------------------|--------------------|----|---|
| stock | 1.000 | 35.12s | 1.000 | 1.000 | 1.000 | 1/1 | 1 |
| ours | 1.000 | 32.51s | 1.000 | 1.000 | 1.000 | 1/1 | 1 |

## Quality Contract

| Metric | stock | ours | Δ |
|--------|-------|------|---|
| mean_ttft_ms | 17560.1 ms | 16255.6 ms | -1304.5 |
| mean_verbosity_chars | 912 chars | 912 chars | +0 |
| mean_tokens_read | 38.0 | 38.0 | +0.0 |
| mean_tokens_created | 255.0 | 255.0 | +0.0 |
| total_tokens_in | 38 | 38 | +0 |
| total_tokens_out | 255 | 255 | +0 |
| mean_response_quality_score | 1.0000 | 1.0000 | +0.0000 |
| mean_energy_efficiency | 0.6051 tok/J | 0.6536 tok/J | +0.0486 |
| mean_cache_hit_rate | 0.000 | 0.000 | +0.000 |
| mean_e2e_latency_ms | 35120.2 ms | 32511.1 ms | -2609.1 |
| mean_decode_speed_tps | 48.41 tok/s | 52.29 tok/s | +3.88 |
| mean_cost_efficiency | 7.26 tok/s | 7.84 tok/s | +0.58 |

## Efficiency Metrics

| Metric | stock | ours | Δ |
|--------|-------|------|---|
| mean_joules_per_output_token | 1.6527 J/tok | 1.5299 J/tok | -0.1228 |
| mean_decode_efficiency | 0.1452 | 0.1569 | +0.0117 |
| mean_memory_bandwidth_utilization_pct | 36.3 % | 39.2 % | +2.9 |
| total_energy_joules | 421.44 J | 390.13 J | -31.31 |
| thermal_throttle_count | 0 | 0 | +0 |
| peak_concurrent_session_capacity | 10 | 10 | +0 |

## Per-suite breakdown (variant comparison)

| Suite | stock pass@1 | ours pass@1 | Δ | stock wall | ours wall | Δ | stock pc | ours pc |
|-------|-------------|-------------|---|-----------|-----------|---|---------|---------|
| mmlu-pro | 1.000 | 1.000 | +0.000 | 35.12s | 32.51s | -2.61s | 1.000 | 1.000 |

## Methodology

- Both variants: direct MLX Python API (bypasses mlx_lm.server)
- Both variants use the same model weights (zero confounders)
- 25 tasks per suite (5 easy + 8 medium + 7 hard + 5 ultra)
- temperature=0, enable_thinking=false

## Progress Trace

| Variant | mean quality asymptote | mean completion asymptote | mean waning magnitude | n waning |
|---------|----------------------|--------------------------|----------------------|----------|
| stock | 1.0000 | 1.0000 | 0.0000 | 0 |
| ours | 1.0000 | 1.0000 | 0.0000 | 0 |
