# Stock-vs-Ours Matrix — Qwen3.5-0.8B

Generated: 2026-07-25 03:51:19 UTC

Variants: control vs ours

Suites: arc-agi-2, deep-swe, gpqa-diamond, mmlu-pro, terminal-bench


## Variant: `control`

| Suite | n | pass@1 | mean_wall_s | p95_wall_s | mean_tok_s |
| --- | ---:| ---:| ---:| ---:| ---:|
| arc-agi-2 | 5 | 1.00 | 1.50 | 0.38 | 4.6 |
| deep-swe | 5 | 0.00 | 1.11 | 1.10 | 57.9 |
| gpqa-diamond | 5 | 1.00 | 0.33 | 0.33 | 6.0 |
| mmlu-pro | 5 | 1.00 | 0.33 | 0.35 | 3.0 |
| terminal-bench | 5 | 1.00 | 0.39 | 0.44 | 10.3 |

## Variant: `ours`

| Suite | n | pass@1 | mean_wall_s | p95_wall_s | mean_tok_s |
| --- | ---:| ---:| ---:| ---:| ---:|
| arc-agi-2 | 5 | 1.00 | 1.01 | 0.60 | 3.7 |
| deep-swe | 5 | 0.00 | 1.37 | 1.40 | 47.9 |
| gpqa-diamond | 5 | 1.00 | 0.52 | 0.59 | 4.1 |
| mmlu-pro | 5 | 1.00 | 0.47 | 0.59 | 2.3 |
| terminal-bench | 5 | 1.00 | 0.46 | 0.46 | 9.0 |

## Side-by-side

| Suite | Metric | `control` | `ours` |
| --- | --- | ---: | ---: |
| arc-agi-2 | pass@1 | 1.00 | 1.00 |
| arc-agi-2 | mean_wall_s | 1.50 | 1.01 |
| arc-agi-2 | mean_tok_s | 4.6 | 3.7 |
| deep-swe | pass@1 | 0.00 | 0.00 |
| deep-swe | mean_wall_s | 1.11 | 1.37 |
| deep-swe | mean_tok_s | 57.9 | 47.9 |
| gpqa-diamond | pass@1 | 1.00 | 1.00 |
| gpqa-diamond | mean_wall_s | 0.33 | 0.52 |
| gpqa-diamond | mean_tok_s | 6.0 | 4.1 |
| mmlu-pro | pass@1 | 1.00 | 1.00 |
| mmlu-pro | mean_wall_s | 0.33 | 0.47 |
| mmlu-pro | mean_tok_s | 3.0 | 2.3 |
| terminal-bench | pass@1 | 1.00 | 1.00 |
| terminal-bench | mean_wall_s | 0.39 | 0.46 |
| terminal-bench | mean_tok_s | 10.3 | 9.0 |