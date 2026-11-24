# Stock-vs-Ours Matrix — `full-dry-2026-07-23` (Qwen/Qwen3.5-0.8B)

- generated_at: 2026-07-24T00:28:42Z
- run_id: `full-dry-2026-07-23`
- model: `Qwen/Qwen3.5-0.8B`
- variants: ['baseline_mlx', 'candidate_stack']
- suites: ['mmlu-pro', 'gpqa-diamond', 'aime', 'arc-agi-2', 'livecodebench']
- tasks_per_suite: 25
- total_cells: 250
- started_at: 2026-07-23T23:58:11Z
- stopped_at: 2026-07-23T23:58:22Z
- mode: **dry-run** (live MLX inference unavailable — `mlx_lm` not installed)

| Suite | n (per variant) | baseline_mlx pass@1 | candidate_stack pass@1 | Δ |
|---|---|---|---|---|
| mmlu-pro | 25/25 | 1.0000 | 1.0000 | +0.0000 |
| gpqa-diamond | 25/25 | 1.0000 | 1.0000 | +0.0000 |
| aime | 25/25 | 1.0000 | 1.0000 | +0.0000 |
| arc-agi-2 | 25/25 | 1.0000 | 1.0000 | +0.0000 |
| livecodebench | 25/25 | 1.0000 | 1.0000 | +0.0000 |

## Aggregate pass@1 (from summary.by_variant)

- **baseline_mlx**: n_cells=125, ok=125, pass@1=1.0000, verified_pass@1=0.0000, gen_ok_mean=1.0000
- **candidate_stack**: n_cells=125, ok=125, pass@1=1.0000, verified_pass@1=0.0000, gen_ok_mean=1.0000

> Note: under `--dry-run` `verified_pass_at_1` is hardwired to 0.0 because there
> is no real verifier call — the synthetic generator round-trip produces `ok`
> (parse/format only) but the verified axis is explicitly suppressed until live
> MLX inference is available.

## Variant mapping

- `baseline_mlx` → **stock** (`mlx-lm` baseline, no Pheno-Metal)
- `candidate_stack` → **ours** (`libpheno_qwen.dylib` + embedded metallib)

## Artifacts

- `cells.json` — flat cell list (V5 shape with v0.2 pass-1 and v0.3 assignment/transcript fields)
- `evaluation_report.json` — primary contract report
- `evaluation_report-stock.json` — stock variant report
- `evaluation_report-ours.json` — ours variant report
- `per_cell.jsonl` — append-only cell stream (one JSON line per cell)

## Live re-run instructions

```bash
pip install mlx-lm
python3 -m bench.matrix.run_ablation \
  --run-id live-$(date +%Y-%m-%d) \
  --suites mmlu-pro,gpqa-diamond,aime,arc-agi-2,livecodebench \
  --tasks-per-suite 25 \
  --variants baseline_mlx,candidate_stack \
  --output-root bench/results/ablation
```
