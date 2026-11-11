# Audit log — pheno-substrate-family absorb decision (2026-08-13)

**Session:** audit session for operator question re: pheno-agents-md, pheno-cdylib-bridge, pheno-context, pheno-control-plane, pheno-forge-plugins, pheno-forge-smoke, pheno-mcp-router, pheno-research, phenodag — all need to find a new home for deep proper semantic migrations factoring git histories

**Operator:** kooshapari (AFK; active policy: act-log-continue per AGENTS.md)

**Date:** 2026-08-13

**Files touched:**
- `repos/plans/dockets/N15-pheno-substrate-family.md` — NEW (183 lines, full absorb justification + tier-A soft-tombstone plan + tier-B migration queue)
- `repos/plans/dockets/N15-pheno-substrate-family-DELETION-REQUEST.md` — NEW (142 lines, operator-actionable tier-A soft-tombstone script)

---

## Decision

**Tier A — soft-tombstone-ready (3 repos):**
- `KooshaPari/pheno-cdylib-bridge` → `pheno/crates/pheno-cdylib-bridge/` (DONE 2026-07-17)
- `KooshaPari/pheno-context` → `pheno/crates/context/` (DONE 2026-07-17)
- `KooshaPari/pheno-forge-smoke` → `pheno/crates/pheno-forge-smoke/` (DONE 2026-07-17)

**Tier B — semantic migration queue (6 repos, NOT tombstone-ready):**
- `pheno-agents-md` → `phenotype-org-governance/agents/` (primary) + `pheno/.claude/agents/` (mirror)
- `pheno-control-plane` → `phenotype-infra/control-plane/` (primary)
- `pheno-forge-plugins` → `PhenoPlugins/plugins/pheno-forge-plugins/`
- `pheno-mcp-router` → `phenotype-router/mcp/` (close PR #12)
- `pheno-research` → `phenoResearchEngine/`
- `phenodag` → DEFER (recommend keep standalone + cross-link docs)

**Tier C — cross-reference (1 repo):**
- `KooshaPari/heliosBench` → `portage` (already docketed as N14; deletion request drafted 2026-08-09)

---

## Reasoning chain

### 1. Sources of truth

- `repos/ABSORPTION-LEDGER.md` — pheno (Rust monorepo) absorbed these members per `plans/2026-07-28-repo-ecosystem-absorption-audit-v3.md`: eidolon (5 crates), Logify, **pheno-cdylib-bridge → pheno/crates/pheno-cdylib-bridge/**, **pheno-context → pheno/crates/context/**, **pheno-forge-smoke → pheno/crates/pheno-forge-smoke/**, phenoDesign, phenoEvents, phenoResearchEngine, phenoUtils, Quillr-half (httpora-core).
- `plans/2026-07-28-full-src-target-ledger.md` — KEEP-AS-IS rows for the other 6 pheno-* targets (the operator's current directive reclassifies them as absorb candidates).
- `plans/2026-07-31-estate-execution-ledger.md` — current SHAs and branch counts for Tier B repos.
- `plans/audit-cohort-20260810/audits/AUDIT-pheno-agents-md.md` — per-repo audit status for `pheno-agents-md` (DEFERRED).
- `planes/2026-07-28-repo-ecosystem-full-merge-plan-v2.md:31-34` — explicit absorb mappings for `pheno-forge-plugins` and `pheno-forge-smoke` to `PhenoPlugins`.

### 2. Why the tier split

**Tier A (3 absorbed):** The 3 repos have a verified, completed, and stable (28+ days) absorb into the `pheno` monorepo. The original 2026-07-17 absorb commit is in `pheno` history. No open PRs in the standalone repos. No outstanding worktrees. The standalone repos are pure duplication risk — soft-tombstone is the safe move.

**Tier B (6 pending):** The 6 repos have content with semantic value that needs careful migration:
- `pheno-agents-md` `agents/` directory has prompt templates (HIGH VALUE per existing audit)
- `pheno-control-plane` has the control-plane manifest spec (1 PR, 3 branches)
- `pheno-forge-plugins` has 4 branches with plugin sidecar source
- `pheno-mcp-router` has PR #12 OPEN + merge-blocked (needs disposition)
- `pheno-research` is the research SSOT (per 2026-07-31 ledger)
- `phenodag` is a 330 KB Go DAG substrate — HIGH BLAST-RADIUS primitives (atomic claims + flock + mangled-git scan)

**Tier C (heliosBench):** Already fully docketed at N14. No new work needed in N15 — just cross-reference.

### 3. Why not absorb into the broader "parent" repos (per substrate-family DENY 2026-07-29)

Per `pheno/crates/agile-plus/docs/airlock/substrate-family-consolidation.md`:
- Sponsor DENY 2026-07-29 — G5 NO SQUASH: "NEVER squas parent repos with deep important histories. only a cosnumed REPO AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTOIRY OR OTHER FULL HIST RBANCEHS PRESENT"
- This applies to `substrate` and `substrate-adapters-bundle` (parent repos with 100 and 7 branches) — they are FROZEN.
- It does NOT apply to the 9 pheno-* repos (none have 100 branches; most have 2-4 branches; they are CONSUMED repos, not parent repos).
- Therefore, the 9 pheno-* repos are eligible for the soft-tombstone path after semantic migration.

### 4. What I CANNOT do (per AGENTS.md safety rails)

- I cannot run `gh repo archive` or `gh repo delete` — destructive public ops require operator sign-off.
- I cannot do `git push --force` to any repo.
- I cannot run `rm -rf` on local mirrors.
- I cannot push to operator-controlled sub-agents without explicit permission.

### 5. What the operator needs to do (Tier A only, immediate)

Run the 5-step bundle-archive-ledger-issue-calendar sequence from `plans/dockets/N15-pheno-substrate-family-DELETION-REQUEST.md` for the 3 Tier A repos. Estimated wall time: 15-20 minutes.

### 6. What the operator needs to do (Tier B, queued)

For each of the 6 Tier B repos, write a separate sub-docket (N15-B1..B6) with:
- Per-branch diff (which branches have unique content)
- Per-file-class migration plan (what files map to what target paths)
- PR template (cherry-pick command + commit message)
- Bundle backup before PR
- Tombstone after PR merge

### 7. Counter updates (planned)

| Tracker | Before | After Tier A | After Tier B |
|---|---|---|---|
| `ABSORPTION-LEDGER.md` KEEP count | 217 | 214 | 208 |
| `ABSORPTION-LEDGER.md` Absorbed count | 14 | 17 | 23 |
| Soft-tombstone count | (varies) | +3 | +6 |

---

## Cross-references

- Parent docket: `plans/dockets/N15-pheno-substrate-family.md`
- Deletion request: `plans/dockets/N15-pheno-substrate-family-DELETION-REQUEST.md`
- Sibling: `plans/dockets/N14-heliosBench.md` (heliosBench → portage)
- Source of truth: `ABSORPTION-LEDGER.md`, `plans/2026-07-28-full-src-target-ledger.md`, `plans/2026-07-28-repo-ecosystem-absorption-audit-v3.md`, `plans/2026-07-31-estate-execution-ledger.md`
- Per-repo audit: `plans/audit-cohort-20260810/audits/AUDIT-pheno-agents-md.md`
- Substrate-family DENY policy: `pheno/crates/agile-plus/docs/airlock/substrate-family-consolidation.md` (2026-07-29 G5 sponsor decision)
