# Repo Consolidation Summary Index

**Date:** 2026-07-29
**Auditor:** Forge-Code (autonomous consolidation pass)
**Status:** PLANNING — no destructive action has been taken

> **GOVERNING POLICY (2026-07-29 sponsor supersession):** This directory is
> retained as historical audit evidence. Its proposed squash, delete, or
> retirement actions are superseded. Forks remain active parent candidates;
> deletion is permanently forbidden; and a non-fork may be renamed with the
> `zz-archive-` prefix and archived only after independently verified dual-cloud
> preservation and an explicit per-gate sponsor ACK. No docket below authorizes
> a state-changing operation.

---

## Purpose

This is the master index for the <REDACTED> repo consolidation pass dated 2026-07-29. It enumerates each group, the dockets produced, and the per-group approval gate before any squashing.

## Group-Level Dockets

| Group | Docket | Members | Risk |
|---|---|---|---|
| 1. Thegent | [`thegent-family-consolidation.md`](./thegent-family-consolidation.md) | thegent, thegent-workspace, thegent-sharecli, zz-archive-thegent-dispatch, thegent-pr2-v2-...-07-14 | Low |
| 2. vibeproxy | [`vibeproxy-monitoring-unified-consolidation.md`](./vibeproxy-monitoring-unified-consolidation.md) | vibeproxy-monitoring-unified, vibeproxy | Very Low |
| 3. phenotype-omlx | [`phenotype-omlx-upstream-sync.md`](./phenotype-omlx-upstream-sync.md) | phenotype-omlx, zz-archive-phenotype-omlx-{recovered,temp,tmp} | **CRITICAL** |
| 4. forge | [`forge-family-consolidation.md`](./forge-family-consolidation.md) | forgecode, pheno-forge-{smoke,plugins}, forgecode-tmp, phenoForge, PlusForges, MCPForge, Tasken-phenoforge-final, dinoforge-packs-archive-2026-07-14, DINOForge-UnityDoorstop | Medium |
| 5. substrate | [`substrate-family-consolidation.md`](./substrate-family-consolidation.md) | substrate, substrate-adapters-bundle | Low (collision) / High (squash complexity) |
| 6. AgilePlus | [`agileplus-family-consolidation.md`](./agileplus-family-consolidation.md) | AgilePlus, zz-archive-AgilePlus-{recovery-20260714,spec-harmonizer-tool} | Medium |
| 7. PlusForges | [`plusforges-fork-index.md`](./plusforges-fork-index.md) | agentapi-plusplus, cliproxyapi-plusplus, context-mode-plusplus, PlusForges | Low |
| 8. Empty/404 | [`empty-repo-404-receipt.md`](./empty-repo-404-receipt.md) | 17 deleted/empty repos | None (already clear) |

## Audit Artifacts (preserved)

- `/tmp/kp_repos_clean.json` — full non-archived repo list (cleaned of ANSI)
- `/tmp/kp_archived.json` — full archived repo list (cleaned of ANSI)
- `/tmp/kp_audit/audit.json` — per-repo branch+commit+OID inventory for 29 candidates
- `/tmp/kp_audit/audit.py` — reproducible GraphQL driver

## Top 3 Highest-Risk Items

1. **phenotype-omlx** — 330 local ahead, 2,061 upstream behind `jundot/omlx`. **No merge-base** between local fork and upstream — must use cherry-pick or re-fork strategy.
2. **AgilePlus** — 79 branches + 9 `src-*` remotes (8 audit-confirmed fully absorbed). `legacy/forge-AgilePlus-wip-snapshot-2026-07-15-clean` is a snapshot, not separate WIP.
3. **forgecode imports** — `pheno-forge-smoke` and `pheno-forge-plugins` need feature-branch imports (low smoke risk; medium plugins risk).

## Approval Gate — required per group

Before any squash/delete on a group, the user must approve:

| Group | Action | State |
|---|---|---|
| 1 (Thegent) | squash each to 1 commit + retire stubs | ✅ audit complete, awaiting approval |
| 2 (vibeproxy) | squash monitoring-unified to 1 commit | ✅ audit complete, awaiting approval |
| 3 (omlx) | **select option A/B/C** | ✅ critical audit complete, awaiting strategy choice |
| 4 (forge) | import + squash | ✅ audit complete, awaiting approval |
| 5 (substrate) | squash each + branches-manifest export | ✅ audit complete, awaiting approval |
| 6 (AgilePlus) | remove src-* + branches-manifest + squash | ✅ audit complete, awaiting approval |
| 7 (PlusForges) | upstream-sync verify + squash each | ✅ audit complete, awaiting approval |
| 8 (Empty/404) | none — already gone | ✅ cleared |

## What Will NOT Happen Without Explicit Approval

- ❌ Squash any repo to 1 commit
- ❌ Delete any local clone
- ❌ Delete any remote repo
- ❌ Force-push to `main` on any repo
- ❌ Cherry-pick the 330 omlx commits without option-selection
- ❌ Merge `pheno-forge-smoke` / `pheno-forge-plugins` into `forgecode` without sign-off
- ❌ Archive any repo before dual-cloud preservation, provenance parity, and an
  explicit sponsor gate ACK; no deletion is permitted under the current policy

## Next Step

User must respond with explicit per-group approval:

```
Example response:
G1: approved
G2: approved
G3: option A
G4: approved
G5: approved
G6: approved
G7: approved
G8: cleared
```

Or per-line:
```
G1 + G2: approved
G3: option A
G4: hold (need to discuss pheno-forge-plugins conflicts)
G5: approved
G6: hold (need src-* audit verification)
G7: approved
G8: cleared
```

Until receipt of approval, **no mutations have been performed**. All audits, dockets, and branch-manifest exports are non-destructive.
