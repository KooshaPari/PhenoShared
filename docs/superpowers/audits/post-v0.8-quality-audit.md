# Audit: post-v0.8 quality inventory (DAG-100 close-out sweep)

> **Date:** 2026-08-07.
> **Scope:** post-`v0.8-pheno-harness-summit` tag. The 100-task DAG shipped; this
> audit inventories residual quality gaps across the repo so future
> "proc all" sweeps have a clear backlog.

## Summary

| Audit area | Tool | Total findings | HIGH | LOW | Notes |
|---|---|---|---|---|---|
| Unused Python imports | ruff 0.x (F401) | 189 | 189 | 0 | All HIGH — easy to fix mechanically |
| TODO/FIXME/HACK/XXX | ripgrep | 8 matches | 3 real | 5 false-positives | Most are doc-only or `mktemp -t XXXXXX` patterns |
| SOTA snapshot chain | sha256sum + manual | 14 snapshots | 3 missing sidecars | 0 chain breaks | Sidecar content is correctly hashed |
| Doc broken links | ripgrep + `test -e` | 1 missing | 1 expected | 0 unexpected | `agileplus-specs/index/spec.md` is the submodule, may be uninitialized locally |

## Unused imports (HIGH = 189, all fixable)

Ruff F401 across `bench/`, `eval/`, `pheno/`, `scripts/`, `kernels/qwen3.5-0.8b/python/`, `verifier/`.

**By directory:**
- `bench/`: 128 (mostly in `bench/comparison/*.py` and `bench/suites/*.py`)
- `scripts/`: 43 (cron wrappers + dual-GPU scripts)
- `kernels/`: 10 (codegen + reference impl)
- `eval/`: 6 (pillars + nested_rlvr)
- `pheno/`: 2 (paths + model manager)

**Reproduce:**

```sh
ruff check --select F401 bench/ eval/ pheno/ scripts/ kernels/qwen3.5-0.8b/python/ verifier/
```

**Representative HIGH findings:**

| File:line | Import |
|---|---|
| `bench/adapters.py:166` | `import json` (function-local) |
| `bench/cli.py:17` | `from typing import Any` |
| `bench/comparison/mlx_direct.py:9` | `import time` |
| `bench/comparison/run_5min_benchmark.py:14` | `import dataclasses` |
| `bench/suites/kernelbench.py:22-32` | `field`, `Path`, `RunSpec`, `SuiteResult`, `TaskResult`, `TaskStatus`, `synthetic_prompt`, `synthetic_response`, `DatasetSource`, `synth_instruction_prompt`, `load_suite_dataset` |
| `bench/suites/ifeval.py:15` | `import time` |
| `bench/suites/hle.py:14` | `import time` |
| `scripts/deploy_kv_winner.ps1:24` | TODO comment (not Python — see below) |

**Recommended fix batch (atomic commits):**

1. `bench/cli.py` + `bench/comparison/mlx_direct.py` (3 imports) → one commit
2. `bench/comparison/run_5min_*.py` + `stock_vs_ours*.py` (~25 imports) → one commit
3. `bench/suites/*.py` (~40 imports) → one commit
4. `scripts/cron/*.sh` + dual-GPU wrappers (~43 imports) → one commit
5. `kernels/qwen3.5-0.8b/python/*.py` (~10 imports) → one commit
6. `eval/pillars.py` + `eval/nested_rlvr.py` (~6 imports) → one commit

Each commit subject: `chore(lint): drop N unused imports in <dir> (ruff F401)`.

## TODO / FIXME inventory (3 real, 5 false-positive)

Ripgrep across `bench/`, `eval/`, `pheno/`, `scripts/`, `kernels/`, `verifier/`, `tests/`, `docs/`.

**Real findings:**

| File:line | Text | Disposition |
|---|---|---|
| `bench/matrix/README.md:36` | `reward wiring is tracked in run_ablation.py (TODO(harbor)).` | DAG-claimed. Future follow-up; no action. |
| `scripts/deploy_kv_winner.ps1:24` | `# TODO: merge winner ctk/ctv flags into models.yaml or env template` | Real. Out of scope for this audit. |
| `kernels/qwen3.5-0.8b/docs/CONTRIBUTING.md:168` | `dispatch table at python/bench.py:<TODO>.` | Doc-only. Update or remove. |
| `kernels/qwen3.5-0.8b/docs/README.md:195` | `## 5. Performance notes / TODO gaps` | Doc-only section header. OK. |
| `kernels/qwen3.5-0.8b/docs/PERFORMANCE.md:241` | `← TODO: revise against actual measured numbers in bench/results/` | Doc-only. Update when measurements land. |

**False-positives** (regex matched but not real TODOs): `mktemp -t XXXXXX.XXXXXX` patterns in shell scripts (`bench_harness_smoke.sh`, `test_mojo.sh`, `install_nim.sh`).

## SOTA snapshot chain (3 missing sidecars)

The SOTA chain is unbroken (each snapshot references the previous day's SHA). However, 3 dates are missing their `.sha256` sidecar:

| Date | json | sha256 | Disposition |
|---|---|---|---|
| `2026-07-30` | yes | **no** | regenerate sidecar |
| `2026-07-31` | yes | **no** | regenerate sidecar |
| `2026-08-01` | yes | **no** | regenerate sidecar |

All 11 other dates (07-25..29, 08-02..07) have matching sidecars (sha256sum confirms).

**Recommended fix:** regenerate the 3 missing sidecars with `shasum -a 256 -b snapshot.json | tr -d '\n' > snapshot.sha256`, then force-commit them per the §6.4 backfill procedure.

## Doc broken links (1 expected missing)

Verified local markdown link targets across `AGENTS.md`, `README.md`, `docs/guides/`, `docs/CRON_OPS.md`, `docs/SETUP_VERSIONS.md`, `docs/ARCHITECTURE_LAYERS.md`.

**All referenced files exist except:**

| Target | Context | Status |
|---|---|---|
| `agileplus-specs/index/spec.md` | `README.md:40` — "Specs: agileplus-specs/index/spec.md (submodule → pheno-specs)" | Expected missing — `agileplus-specs/` is a git submodule (AGENTS.md §5) that may be uninitialized locally. Not a defect. |

**All other local links resolve:** `docs/guides/INSTALL.md`, `docs/guides/PORTAGE_AND_HARBOR.md`, `eval/HARBOR.md`, `docs/PHENOLM_MIGRATION.md`, `docs/GARDEN_LOOP.md`, `docs/PUBLISHING.md`, `docs/ARCHITECTURE_LAYERS.md`, `kernels/qwen3.5-0.8b/arch.yaml`, `kernels/qwen3.5-0.8b/python/codegen.py`, `kernels/qwen3.5-0.8b/docs/README.md`, `AGENTS.md`.

## Recommended fix batches (priority order)

1. **SOTA missing sidecars** (3 dates) — small bash fix, ~5 min total
2. **bench/cli.py unused imports** (3 imports) — mechanical, ~2 min
3. **bench/comparison/run_5min_*.py unused imports** (~25 imports) — mechanical, ~5 min
4. **bench/suites/*.py unused imports** (~40 imports) — mechanical, ~10 min
5. **scripts/ + kernels/ unused imports** (~53 imports) — mechanical, ~15 min
6. **eval/ + pheno/ unused imports** (~8 imports) — mechanical, ~2 min
7. **scripts/deploy_kv_winner.ps1 TODO** — defer until kv-winner promotion is decided
8. **Doc-only TODOs** — defer until relevant docs get content updates

## References

- AGENTS.md §5 (repo layout)
- AGENTS.md §6.4 (SOTA snapshot chain — backfill procedure)
- `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md` (DAG plan)
- ruff docs: <https://docs.astral.sh/ruff/rules/unused-import/>
