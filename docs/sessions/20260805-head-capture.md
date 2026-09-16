# HEAD capture — 2026-08-05 (end of Phase 0)

Captured at the close of DAG Phase 0 (tasks 1-5). Phase 0 is the
ground-truth + HEAD-alignment phase; this document is the
checkpoint for the next 95 tasks.

## Working tree

```
branch:  main
HEAD:    1c6384fdaf9f0846903b9006293c891ffff7826e
clean:   true (only untracked cron output dirs from today's fires:
         bench/results/branch-lint/, bench/results/gc/)
```

## Phase 0 closeout (DAG tasks 1-5)

| ID | Title | Commit | ac |
|----|-------|--------|----|
| 1 | land this DAG | `ed33e51` | ac_v1 |
| 2 | rewrite AGENTS.md against current phase | `ed33e51` | ac_v1 |
| 3 | backfill missing 2026-07-25..28 SOTA snapshots | `9742256` | ac_v1 |
| 4 | bootstrap + force-fire all 4 launchd cron agents | `1c6384f` | ac_cron |
| 5 | this document + HEAD capture commit | <this commit> | ac_v1 |

## State entering Phase 1

- All 4 launchd agents verified loaded:
  - `com.phenotype.pheno-harness.sota-snapshot` (daily 04:00 UTC)
  - `com.phenotype.pheno-harness.health-repo` (Mon 03:00 UTC)
  - `com.phenotype.pheno-harness.worktree-gc` (Wed 04:00 UTC)
  - `com.phenotype.pheno-harness.lint-branches` (Fri 04:00 UTC)
- SOTA chain: 12 days present (07-25..08-06); no gaps.
- AGENTS.md pinned to current phase (Qwen3.5-0.8B MLX kernels +
  dual-harness + Apple Silicon + WSL2/Fedora 44 LLM host).
- 100-task DAG landed at `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`.

## Critical path forward

```
5 -> 8 -> 25 -> 41 -> 55 -> 70 -> 96 -> 98 -> 99 -> 100
```

Tasks 6-7 require `fix/desktop-vllm-runtime` branch checkout
before the test fixture work can begin.

Refs: DAG-5; WBS-PERT-100.md §Phase 0; AGENTS.md §8.
