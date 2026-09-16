---
source_file: ChatGPT-Pairwise Test Case Generation.md
sha256: d1d434d87211847a23eb72123babf5fe19e651e377126dce1dd6e40bd9915a5d
topics: [benchmarks, tbench, test-generation, pairwise, coverage]
related_okf:
  - inference/agent-aware-speculative-decoding.md
  - agents/feature-graph-system-design.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Pairwise Test Case Generation

**Source:** `ChatGPT-Pairwise Test Case Generation.md` (3.3 KB, 2026-06-17) + revs (1)(2)(3) — sha `d1d434d8` (duplicate triplet) — class **L**.

Pairwise (2-way) combinatorial testing covers all value-pairs with `~n log n` tests instead of `n^k`. For `harbor-TB2` (89 tasks × 3 models × 2 routes = 534 combos), pairwise reduces to **~40 representative trials** — exactly the `tbench20_representative_subset.json` (6 trials) and `N08`→`N09` sampling strategy.

## Key insights (stub)

- **Pairwise vs exhaustive:** 89×3×2 = 534; pairwise 2-way ≈ 40 (92% reduction) while keeping defect detection 70–90% (per corpus).
- **Harbor mapping:** each TB2 task is a `trial` with `env` + `verifier`; pairwise picks tasks that cover `model × route × dataset` pairs — `config/tbench20_representative_subset.json` is the 6-trial seed.
- **Pheno-harness link:** Forward DAG `N07` (Portage rep-6) and `N08` (TB2.0 rerun) are pairwise subsets; `bench/custom/deepswe` (N24) should also use pairwise for problem selection.
- **Tool:** `pairwise` Python package or `allpairspy` generates the matrix; verify vs `eval/results/tbench_local_qwen35_final_20260723.json` (0.0 reward, 76% infra) before scaling.

## Next (N10)

- Extract full `[L]` claims with `local://sha256/d1d434d87211...` citations.
- Generate pairwise matrix for `harbor_tbench_routes.yaml` (6 routes × 89 tasks) as `bench/pairwise_tbench_matrix_2026-07-NN.json`.
- Promote to **[P]** after verifying vs primary pairwise literature before `docs/specs/`.

**Evidence:** `local://sha256/d1d434d87211847a23eb72123babf5fe19e651e377126dce1dd6e40bd9915a5d` (class **L**).
