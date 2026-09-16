# pheno-harness / docs / datasets

Per approved repo-realignment decision **D** (2026-09-02):

- Narrative research / docs → `pheno-harness/docs/research/`
- **Dataset metadata index** → this directory (`docs/datasets/`)
- **Raw benchmark assets** live in the consumer's `bench/datasets/` (e.g. `bench/datasets/helios_bench/`)

This index maps dataset assets to their owning benchmark source and the eval
driver configs that consume them. It intentionally keeps *metadata* (what/where/
how) separate from *assets* (the actual task files), which stay in `bench/datasets/`.

## Source of truth for dataset assets

| Dataset | Assets location | Derived benchmark |
|---------|-----------------|-------------------|
| helios_bench | `bench/datasets/helios_bench/` | helios-bench (12 tasks) |

## Eval driver configs

Consumed via `bench/job_configs/`. Each config's `tasks[].path:` resolves the
dataset location above.

| Config | Dataset | Points to |
|--------|---------|-----------|
| `job_config.pheno-harness.qwen.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.oracle.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.oracle-multi.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.oracle-single.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.oracle-remaining5.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.oracle-12.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.1k-parallel.yaml` | helios_bench | `bench/datasets/helios_bench` |
| `job_config.pheno-harness.1k-parallel.adapters.yaml` | helios_bench | `bench/datasets/helios_bench` |

## helios_bench tasks (12)

bayesian_sampler / binary_search / buggy_add / debug_division / fibonacci /
log_parser / matrix_multiply / merge_sort / palindrome / refactor_loop /
word_count / write_tests

## Repo role boundary (from approved B/C/D)

- `pheno-harness` — **experiment home**: benchmark datasets, eval driver configs,
  OKF corpus, research docs, eval orchestration.
- `portage` — **strict fork of `harbor-framework/harbor`**: the eval *runner
  mechanism* (terminus-2, stage2, `src/helios_bench/` bridge, `tests/helios_bench/`)
  plus OCI-runtime gap fixes and pier/podman/wslc/orbstack alternates.
- `Benchora` — **benchmark generics** (runner scaffolding).

Update this index whenever a dataset moves or a config points somewhere new.