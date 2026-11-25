# Worktree Policy — 2026-08-19 (G3)

**Status:** draft for sign-off — no worktrees removed until you approve.
**Branch:** `wip/2026-07-28-pheno-harness-m80-d76` (current), `chore/phenotype-traceability` (portage)

## Current estate (2026-08-19)

- `pheno-harness` wip: **0–4 dirty** (was 1412 on 2026-08-14, now `M bench/results/_sota_test/...`, `M evidence/dual_gpu/worktrees.json`, `?? docs/okf/...` — fluctuating doc churn, no longer sprawl). PRs **#99** (`wip/2026-08-19-pheno-harness-m80-d76`), **#98** (forward-dag), #97/#96/#92 open — wip is pushable via PR, not direct to `main`.
- `phenotype-omlx` wip: `wip/2026-07-28-d-phenotype-omlx` `3a611180` (includes cockpit `097c1213` + `4ebbb0cc` resolver tests) — **synced to origin**, PR **#205** open.
- `AgilePlus` feat: `feat/planify-shim-api-workspace` `319d50f0` — **synced**, PR **#975** open; `fix/nightly-toolchain-v2` PR **#976** open.
- `portage` `chore/phenotype-traceability` — clean 0 dirty, no worktree.
- No `worktrees/` directory active (per `AGENTS.md` §14.2). Historical runners (`agentora-replay-finish`, `desktop-live-20260801`, `pr54-ci-gates`) are closed.

## Policy (proposed)

1. **Leave wip branches as-is** until `droid-sync` reports on `MERGE_HEAD 0348989ad` (87 conflicts, `portage` B0). The harness `wip` is no longer a 1k-file sprawl — it is 0–4 files of real doc/evidence churn, safe to keep as a wip checkpoint branch. No auto-commit of the 4 dirty docs — they are `okf` scaffolding, fine to stay untracked until you decide.
2. **Worktrees:** do not create `git worktree add` for `portage` merge until `droid-sync` signals. When created, use `worktrees/<topic>/` under the repo root, ignored by `.gitignore`, and remove after merge via `git worktree remove --force`.
3. **Stale worktrees:** the `tmp\phenospecs-work` / `tmp_branch_salvage` bare-clone checkouts (phenoSpecs) had **0 unique commits** — safe to `rm -rf` if they reappear. `AgilePlus\PhenoSpecs*` empty dirs are inert.
4. **Bare clones:** `C:\Users\koosh\phenoSpecs.git` (bare) + `C:\Users\koosh\phenoSpecs` checkout stay canonical (`main` `0656562`), no worktree.

## Next step for you

- [ ] Approve this policy (reply `g3 approve`) → I will keep wip as-is, no checkpoint commit.
- [ ] Or `g3 commit` → I will commit the 4 dirty docs as a checkpoint on `wip/2026-07-28-pheno-harness-m80-d76` and push to PR #99.

Refs: `AGENTS.md` §14, `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`, `state/RUN_REGISTRY.md` §4.10, `FORWARD_DAG` §10 (SVM-dead).
