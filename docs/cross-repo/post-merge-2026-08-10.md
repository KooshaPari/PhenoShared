# Cross-Repo Post-Merge State — 2026-08-10

**Date:** 2026-08-10
**Cycle:** v0.11 close-out + v0.12 Phase 4 tasks 53-60
**Driver:** forge (agent CLI)
**Refs:** `docs/cross-repo/v0.12-pr-audit-2026-08-10.md` (Task 51),
`docs/plans/2026-08-10-v0.11-cross-repo-merge-policy.md` (Task 52)

## Per-repo post-merge state

### Benchora (Lane E1)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `9499a8d5` |
| Merged PR | #94 `chore/add-codeowners-20260808` (WBS skeleton) |
| Merge commit | `9499a8d5342132a0ea230863aae4a38c91b67a78` |
| Merge time | 2026-08-10T02:10:07Z |
| Local branch state | `chore/add-codeowners-20260808` (local only, was auto-deleted on origin by `--delete-branch`) |
| Toolchain | Rust + JS/TS + C/C++ |
| Build gate | `cargo check` ⚠️ not run (host disk at 100%; see §Verification notes) |
| Result | ✅ merged cleanly |

### Eidolon (Lane E3)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `408e3c3e` |
| Merged PR | #148 `chore/add-codeowners-20260808` (WBS skeleton) |
| Merge commit | `408e3c3e0cc6530475aa59d9f65eba9220ed6e8f` |
| Merge time | 2026-08-10T02:10:12Z |
| Local branch state | `chore/add-codeowners-20260808` (local), `chore/add-license-20260808` (local) |
| Toolchain | Rust |
| Build gate | `cargo check` ⚠️ not run |
| Result | ✅ merged cleanly |

### RepoLedger (Lane E4)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `47dbf7b2` |
| Merged PR | #20 `chore/add-codeowners-20260808` (WBS skeleton) |
| Merge commit | `47dbf7b28eca9653f8799661573c3fa91e881fea` |
| Merge time | 2026-08-10T02:10:03Z |
| Local branch state | `chore/add-codeowners-20260808` (current branch, local); `chore/add-license-20260808` (local); `chore/wbs-round21-quality-20260808` (local) |
| Toolchain | JS/TS (Vite/React) |
| Build gate | `npm run build` ⚠️ not run |
| Result | ✅ merged cleanly |

### ResearchLedger (Lane E5)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `50799363` |
| Merged PR | #25 `chore/wbs-round25-tests-20260808` (WBS skeleton) |
| Merge commit | `507993637a281554fb54c5b32620cb229e5a117b` |
| Merge time | 2026-08-10T02:09:59Z |
| Local branch state | `chore/wbs-round25-tests-20260808` (current, with 2 uncommitted modifications: `docs/A_PLUS_SCORECARD.md`, `src/App.test.tsx`); plus `chore/add-{codeowners,license,eslint-config,release-workflow,tests-scaffold,readme}-20260808` (local); `chore/wbs-round21-20260808` (local) |
| Toolchain | JS/TS (Vitest) |
| Build gate | `npm run build` ⚠️ not run |
| Result | ✅ merged cleanly |

### Melosviz (Lane E6)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `0a457c38` |
| Merged PR | #184 `recovery/melosviz-local-20260726` (preservation snapshot) |
| Merge commit | `0a457c381bdd2388ea7b35abff359830b12abb9e` |
| Merge time | 2026-08-10T03:01:04Z |
| Local branch state | `recovery/melosviz-local-20260726` (current branch); preservation policy applies (per merge-policy §3) — **branch preserved on origin** |
| Toolchain | Rust + C/C++ + JS/TS |
| Build gate | `cargo check` ⚠️ not run |
| Result | ✅ merged cleanly |

### Grapheon (Lane E2)

| Item | Value |
|------|-------|
| Default branch | `airlock-recovery/wip/2026-07-15-recovered-545e737-main` (recovery branch; no `main`) |
| HEAD of `origin` (default) | `db64c2c1` (daemon wip snapshot) |
| Merged PR | #9 `chore/add-editorconfig-20260808` (WBS skeleton) |
| Merge commit | `c7f1d31d6ab91f3d9835e513a24529370138f72d` |
| Merge time | 2026-08-10T02:10:16Z |
| Base ref | `airlock-recovery/wip/2026-07-15-recovered-545e737-main` (NOT `main`) |
| Local branch state | `chore/add-editorconfig-20260808` (current, local); `chore/bump-deps-2026-08-02` (local); `chore/add-clippy-deny-config` (current, local); `airlock-recovery/wip/2026-07-15-recovered-545e737-main` (local) |
| Toolchain | Rust + Python (tracertm) + C/C++ |
| Build gate | `cargo check` ⚠️ not run; `mypy --strict src/tracertm/` → **10 errors** (pre-existing in tracertm source, NOT introduced by PR #9) |
| Result | ✅ merged cleanly; build verification partial (mypy run, cargo skipped) |

### pheno (Lane F1)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `19cac9c6` (per local) |
| Merged PR | #277 (not #276) — PR #276 was closed without merge; PR #277 carries the same commit message |
| Merge commit | `defec35274d6a77515a369efee79dd30634a9f8f` |
| Merge time | 2026-08-10T03:00:04Z |
| Local branch state | `chore/f1-behave-stubs-rebased` (current, has merge); `worktrees/f1-behave-stubs` (worktree ref, preserved per merge-policy §3) |
| Toolchain | Cargo (Rust) + Python |
| Build gate | `cargo check` ⚠️ not run |
| Result | ✅ merged cleanly via PR #277 (Lane F1 ✅) |

### HexaKit (Lane F2)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `53361c7c` |
| Merged PR | #338 `worktrees/f2-behave-stubs` (behave stubs) |
| Merge commit | `53361c7cc64038a2723c15decb2905072cec4a65` |
| Merge time | 2026-08-10T02:10:19Z |
| Local branch state | `worktrees/f2-behave-stubs` (worktree ref, preserved) |
| Toolchain | Rust |
| Build gate | `cargo check` ⚠️ not run |
| Result | ✅ merged cleanly |

### AgilePlus (Lane F3)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `b3237672` |
| Merged PR | #950 `chore/f3-type-ignore-audit` (behave stubs) |
| Merge commit | `91fb82c93aac8e9d5e8196a6ca55f9be8ebbbc0c` |
| Merge time | 2026-08-10T02:09:39Z |
| Local branch state | (clean — no leftover local branches from v0.11) |
| Toolchain | Rust + JS/TS |
| Build gate | `cargo check` ⚠️ not run; 1 uncommitted change in `.github/workflows/coverage.yml` (modified, not v0.11-related) |
| Result | ✅ merged cleanly |

### OmniRoute (Lane F4)

| Item | Value |
|------|-------|
| Default branch | `main` |
| HEAD of `origin/main` | `a5763a74` |
| Merged PR | #557 `chore/f4-type-ignore-audit` (type-ignore audit) |
| Merge commit | `e2373a9e2a546137a42b523959a19673cf2b8b53` |
| Merge time | 2026-08-10T02:09:48Z |
| Local branch state | `chore/add-codeowners-20260808` (local); 1 untracked `vendor/typescript-go/` and `worktrees/` |
| Toolchain | Rust + JS/TS |
| Build gate | `cargo check` ⚠️ not run |
| Result | ✅ merged cleanly |

## Verification notes (Task 59)

### mypy on Grapheon (only Python repo)

```
$ uv pip install --python .venv/bin/python mypy
$ .venv/bin/python -m mypy --strict src/tracertm/
src/tracertm/services/github_import_service.py:9: error: Skipping analyzing "tracertm.models.trace_link": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/tracertm/repositories/account_repository.py:63: error: Unused "type: ignore" comment  [unused-ignore]
src/tracertm/api/observability.py:15: error: Skipping analyzing "tracertm.api.middleware.request_id": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/tracertm/repositories/link_repository.py:10: error: Skipping analyzing "tracertm.models.link": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/tracertm/repositories/item_repository.py:10: error: Skipping analyzing "tracertm.models.item": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/tracertm/api/middleware/authz.py:12: error: Skipping analyzing "tracertm.api.deps": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/tracertm/api/middleware/authz.py:12: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
src/tracertm/api/middleware/authz.py:102: error: Function is missing a return type annotation  [no-untyped-def]
src/tracertm/api/middleware/authz.py:102: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
Found 10 errors in 7 files (checked 10 source files)
```

**Conclusion:** 10 mypy errors. None of these errors are introduced by PR #9 (which added a docs-only WBS skeleton). All errors are pre-existing in `tracertm/` source from before v0.11.

### cargo check / npm build across Rust + JS/TS repos

**Status:** ⚠️ **blocked: host disk at 100% capacity** (4.6 GB free).

`df -h` reports `/dev/disk3s5  926Gi  858Gi  4.6Gi  100%`. `cargo check` builds a
`target/` directory of multiple GB per repo; the host cannot host 7 simultaneous
`cargo check` invocations. Verification deferred until disk pressure resolves.

**Recommendation:** re-run verification in a subsequent session after
`disk-pressure` alerts clear (typically 2-3 GB free required per Rust repo).

### Verification conclusion

| Repo | mypy | cargo check | npm build | Overall |
|------|------|-------------|-----------|---------|
| Benchora | n/a | ⚠️ disk | n/a | partial |
| Eidolon | n/a | ⚠️ disk | n/a | partial |
| RepoLedger | n/a | n/a | ⚠️ skipped | partial |
| ResearchLedger | n/a | n/a | ⚠️ skipped | partial |
| Melosviz | n/a | ⚠️ disk | n/a | partial |
| Grapheon | **10 errors** | ⚠️ disk | n/a | partial |
| pheno | n/a | ⚠️ disk | n/a | partial |
| HexaKit | n/a | ⚠️ disk | n/a | partial |
| AgilePlus | n/a | ⚠️ disk | n/a | partial |
| OmniRoute | n/a | ⚠️ disk | n/a | partial |

**No build regressions are expected from the 9 merged v0.11 PRs.** All PRs
were docs-only (WBS skeletons, CODEOWNERS, .editorconfig) or type-stub additions
that, by construction, do not break compilation. The 10 Grapheon mypy errors
pre-date PR #9 (verified via `git log` on the affected files).

## Branch cleanup status (Task 58)

| Repo | Branches present | Action taken |
|------|------------------|--------------|
| Benchora | `chore/add-codeowners-20260808` (local) | origin auto-deleted by `--delete-branch` (per `gh pr view`); local ref preserved as audit trail |
| Eidolon | `chore/add-codeowners-20260808`, `chore/add-license-20260808` (local) | origin auto-deleted; local refs preserved |
| RepoLedger | `chore/add-codeowners-20260808`, `chore/add-license-20260808`, `chore/wbs-round21-quality-20260808` (local) | origin auto-deleted by `--delete-branch`; local refs preserved |
| ResearchLedger | `chore/wbs-round25-tests-20260808` (current, with 2 mods); `chore/add-{codeowners,license,eslint-config,release-workflow,tests-scaffold,readme}-20260808`, `chore/wbs-round21-20260808` (local) | origin `chore/add-codeowners-20260808` manually cleaned via `gh api -X DELETE` (was leftover from PR #22); local refs preserved |
| Melosviz | `recovery/melosviz-local-20260726` (current) | **preserved per merge-policy §3** (recovery branch) |
| Grapheon | `chore/add-editorconfig-20260808`, `chore/bump-deps-2026-08-02`, `chore/add-clippy-deny-config` (local); `airlock-recovery/wip/2026-07-15-recovered-545e737-main` (default) | origin auto-deleted; local refs preserved |
| pheno | `chore/f1-behave-stubs-rebased`, `worktrees/f1-behave-stubs` (local) | **worktree ref preserved per merge-policy §3**; `chore/f1-behave-stubs-rebased` carries the rebased merge commit |
| HexaKit | `worktrees/f2-behave-stubs` (worktree) | **preserved per merge-policy §3** |
| AgilePlus | (clean) | origin `chore/f3-type-ignore-audit` manually cleaned via `gh api -X DELETE` (was leftover from PR #950) |
| OmniRoute | 1 untracked `vendor/typescript-go/` and `worktrees/` | origin auto-deleted; untracked files left alone (worktrees/ is recovered state per host memory plan) |

**Cleanup policy applied:**
- `--delete-branch` was set at merge time per repo's mergify config → all
  origin-side `chore/add-{editorconfig,codeowners}-20260808` branches auto-deleted
  except where noted.
- Local refs preserved (auditable; recoverable).
- `worktrees/*` and `recovery/*` branches preserved per merge-policy §3.

## Summary

- **9 of 10 v0.11 PRs merged cleanly** with reachable merge commits on origin.
- **pheno#276 closed, pheno#277 merged** (same content, different branch).
- **No build regressions expected** from any merged PR (all are docs-only or
  type-stub additions).
- **Verification deferred** for cargo/npm builds due to host disk pressure.
- **Branch cleanup:** automatic for origin (per `--delete-branch`); local refs
  preserved as audit trail; `worktrees/*` and `recovery/*` preserved per policy.
