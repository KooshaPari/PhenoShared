# Ablation matrix runner

Scaffold for replacing `bench/comparison/stock_vs_ours.py` with an honest
generation-vs-verification metric split (contract v0.2).

## Variants

| Name | Role |
|------|------|
| `baseline_mlx` | Direct MLX inference via `bench.comparison.mlx_direct` |
| `candidate_stack` | Candidate kernel stack (scaffold: same MLX path until PR3+) |

## Quick start (CI / smoke)

```bash
python -m bench.matrix.run_ablation --dry-run --run-id smoke
```

Artifacts land under `bench/results/ablation/<run_id>/`:

- `cells.json` — V5 cell list + per-variant summary
- `evaluation_report.json` — contract-shaped `EvaluationReport`

## Live MLX (when `mlx-lm` is installed)

```bash
python -m bench.matrix.run_ablation \
  --suites mmlu-pro,ifeval \
  --tasks-per-suite 1 \
  --run-id live-smoke
```

## Harbor verification (future)

`verified_pass_at_1` is always `0.0` in this scaffold. Harbor / Apple Container
reward wiring is tracked in `run_ablation.py`.

To install Harbor for verification:

```sh
# Harbor ≥ 0.6.0 (PEP 668 override; pyproject.toml [project.optional-dependencies] harbor)
uv pip install -e ".[harbor]"
# Or via the helper installer:
bash scripts/install_harbor_for_tests.sh
```

Verify the consumer boundary: `python3 scripts/harbor_consumer_dry_run.py`
should print `PASS (consumer boundary; no framework fork)`.

## Deprecation

`bench/comparison/stock_vs_ours.py` remains for full 10-suite parity until this
runner reaches feature parity. New work should target `bench.matrix.run_ablation`.
