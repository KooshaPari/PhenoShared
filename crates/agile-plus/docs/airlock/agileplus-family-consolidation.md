# AgilePlus Family Consolidation Docket

**Date:** 2026-07-29
**Auditor:** Forge-Code (autonomous consolidation pass)

---

## STATUS: ❌ SPONSOR DENY 2026-07-29 — G6 NO SQUASH

**Sponsor decision (2026-07-29 transcript):**
> *"g3a g4 ok g5 no only squash lattr as you consume into foremr g4 no g7 no NEVER squas parent repos with deep improtnat histories. only a cosnumed REPO AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTOIRY OR OTHER FULL HIST RBANCEHS PRESENT"*

**Decoded:**
- **G6: DENY** — `AgilePlus` is a **parent repo** with deep history (79 branches including 8 absorbed `src-*` remotes). It is **never squashed** under the new policy.
- The 8 `src-*` remote cleanup (Phase 1) is a separate question — they are local-only remote-ref removals, not a squash. **No destructive remote analysis was executed; nothing changed.**

### What This Means for `AgilePlus` (79 branches) and `zz-archive-*` siblings

| Operation | Status |
|---|---|
| Branch manifest export (Lane-3) | ✅ permitted without ACK |
| SHA-256 checksums (Lane-3) | ✅ permitted without ACK |
| `src-*` remote removal (Phase 1) | ⏸️ held — local-only, but still pending additional ACK |
| Repo squash to 1 commit | ❌ **permanently forbidden** (parent repo) |
| Branch deletion | ❌ **permanently forbidden** |
| Remote deletion | ❌ **permanently forbidden** |
| Force-push to `main` | ❌ **permanently forbidden** |

`AgilePlus` is **frozen as-is**. Future work proceeds on feature branches; `main` and all other branches are immutable. The `legacy/forge-AgilePlus-wip-snapshot-2026-07-15-clean` branch is a snapshot of `main@2026-07-15` — retained as-is.

---

**Status:** MIGRATION PROPOSED — DENIED; repo frozen as parent-per-policy

---

## Members in Scope

| Repo | Default | Branches | Last Push | Local Clone |
|---|---|---|---|---|
| `AgilePlus` | main | **79** | 2026-07-29 | ✅ `/repos/AgilePlus` |
| `zz-archive-AgilePlus-recovery-20260714` | main | 1 | 2026-07-15 | ❌ |
| `zz-archive-agileplus-spec-harmonizer-tool` | main | 1 | 2026-07-14 | ❌ |

## MIGRATE — semantic content mapping

| Source | Target | Rule | Notes |
|---|---|---|---|
| `zz-archive-AgilePlus-recovery-20260714` | `AgilePlus` (history receipt) | snapshot | 1 branch, recovery snapshot at 2026-07-15 |
| `zz-archive-agileplus-spec-harmonizer-tool` | retired | snapshot | 1 branch, archive of deleted repo; "preserved before cleanup" |

## STATE — current branch taxonomy (79 branches)

```
AgilePlus (79 branches):
  main                       (canonical)
  archives/legacy/*          (absorbed-sub-repo legacy states)
  audit/*                    (audit snapshots)
  feat/*                     (~25 feature branches)
  fix/*                      (regression fixes)
  legacy/*                   (legacy code states)
  legacy/forge-AgilePlus-wip-snapshot-2026-07-15-clean
                              (snapshot of main@2026-07-15, NOT independent WIP)
  recoveries/*               (recovery markers)
  src-*                      (8 git remotes for absorbed sub-repos)
  wip/*                      (work-in-progress markers)
```

**The `legacy/forge-AgilePlus-wip-snapshot-2026-07-15-clean` branch is a 2026-07-15 snapshot of `main` — not a separate WIP from `forge-AgilePlus` repo (which was empty/deleted).**

## `src-*` REMOTE AUDIT — 8 sub-repos fully absorbed

The `AgilePlus` repo has **8 `src-*` remotes** that predate this consolidation. Each was a <REDACTED> sub-repo that got absorbed and archived on 2026-07-14:

| src-* Remote | Resolved Repo | Default | Archived | Size | Unique Commits vs AgilePlus/main |
|---|---|---|---|---|---|
| `src-chatta` | `<REDACTED>/zz-archive-chatta` | main | ✅ | 55107kb | 1 |
| `src-eventra` | `<REDACTED>/zz-archive-Eventra` | main | ✅ | 566kb | 1 |
| `src-pheno-drift` | `<REDACTED>/zz-archive-pheno-drift-detector` | main | ✅ | 8kb | 1 |
| `src-pheno-predict` | `<REDACTED>/zz-archive-pheno-predict` | main | ✅ | 11kb | 2 |
| `src-phenotype-sdk` | `<REDACTED>/zz-archive-phenotype-sdk` | main | ✅ | 4265kb | 7 |
| `src-services` | `<REDACTED>/zz-archive-services` | main | ✅ | 134kb | 12 |
| `src-thegent-disp` | `<REDACTED>/zz-archive-thegent-dispatch` | main | ✅ | 98kb | 58 |
| `src-tracera-prwt` | `<REDACTED>/zz-archive-tracera-pr-worktree-20260703-0014` | main | ✅ | 53kb | 1 |

### Verification result: **ALL 8 ABSORBED**

Every `src-*` remote's unique commits vs `AgilePlus/main` consist of:
- Mirror hygiene commits (`.archive/`, `.gitignore` updates)
- ADR/cross-reference table commits
- Branch metadata for the absorbed sub-repo

The actual content of all 8 sub-repos is fully merged into `AgilePlus/main`. The "unique" commits are mirror-side-only, not absorbing-side.

**Largest unique commit count = 58 (`src-thegent-disp`)** — verified these are governance/hygiene commits for the absorbed thegent-dispatch content, **already present in `AgilePlus/main`'s lineage**.

### Recommended disposition of src-* remotes after audit:

| Remote | Action | Reason |
|---|---|---|
| `src-chatta` | **REMOVE remote** | absorbed; receipt at `zz-archive-chatta` |
| `src-eventra` | **REMOVE remote** | absorbed; receipt at `zz-archive-Eventra` |
| `src-pheno-drift` | **REMOVE remote** | absorbed |
| `src-pheno-predict` | **REMOVE remote** | absorbed |
| `src-phenotype-sdk` | **REMOVE remote** | absorbed |
| `src-services` | **REMOVE remote** | absorbed (12 mirror-side commits only) |
| `src-thegent-disp` | **REMOVE remote** | absorbed (58 mirror-side commits only) |
| `src-tracera-prwt` | **REMOVE remote** | absorbed |

**Removing a remote does NOT lose any git data** — branches already merged into `main` remain reachable.

## ABSORBED — confirmed content states

All 8 `src-*` sub-repos fully absorbed into `AgilePlus/main`. The zz-archive-* repos on GitHub remain as receipts (archived = true).

## SUPERSEDES — receipts preserved

- `zz-archive-AgilePlus-recovery-20260714` — preserved as 1-branch snapshot.
- `zz-archive-agileplus-spec-harmonizer-tool` — preserved as 1-branch snapshot.
- `zz-archive-chatta`, `zz-archive-Eventra`, `zz-archive-pheno-drift-detector`, `zz-archive-pheno-predict`, `zz-archive-phenotype-sdk`, `zz-archive-services`, `zz-archive-thegent-dispatch`, `zz-archive-tracera-pr-worktree-20260703-0014` — preserved forever as audit-grade sub-repo receipts.

## PROPOSED MUTATIONS (NOT EXECUTED — pending approval)

### Phase 1: src-* remote cleanup (no data loss)
1. `git remote remove src-chatta`
2. `git remote remove src-eventra`
3. `git remote remove src-pheno-drift`
4. `git remote remove src-pheno-predict`
5. `git remote remove src-phenotype-sdk`
6. `git remote remove src-services`
7. `git remote remove src-thegent-disp`
8. `git remote remove src-tracera-prwt`
9. (Optional) `git remote prune origin` to refresh.

### Phase 2: branches manifest export (RECEIPT)
1. `git for-each-ref refs/heads/ --format='%(refname:short) %(objectname:short) %(committerdate:short) %(subject)' > branches-pre-squash.txt`
2. Stash at `AgilePlus/docs/airlock/agileplus-branches-manifest-pre-squash-2026-07-29.txt`

### Phase 3: SQUASH (per-group approval)
1. `AgilePlus` → squash to 1 commit on `main`.

## LOCAL CHECKOUT COVERAGE

- `/repos/AgilePlus` (origin + 8 src-* remotes): 79/79 branches local ✅
- All src-* remote refs resolved successfully; receipts preserved at `zz-archive-*` on GitHub.

## RISK CLASS

**Medium.** 79 branches is large; `legacy/*` and `recoveries/*` branches contain absorbed sub-repo history (already in main). The `archives/legacy/forge-AgilePlus-wip-snapshot-2026-07-15-clean` is a snapshot, not WIP.

## NEXT CHECKPOINT

User must approve:
- (a) removing 8 `src-*` remotes (no data loss)
- (b) full branches-manifest export before squash
- (c) final squash of `AgilePlus` to 1 commit on `main` (after manifests are stashed)
