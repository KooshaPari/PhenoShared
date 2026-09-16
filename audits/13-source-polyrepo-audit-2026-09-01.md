# 13-source polyrepo audit — summary (2026-09-01)

**Author**: Forge (wave J)
**Date**: 2026-09-01
**Scope**: GitHub repos under `KooshaPari/*` (13 sources total)
**Contract docs**:
- `~/Downloads/03-forensic-ssot-recovery.md` (operating contract)
- `~/Downloads/04-polyrepo-ecosystem-consolidation.md` (consolidation contract)

## Final result matrix (locked)

| # | Source | GH state | Remote class | Verdict |
|---|---|---|---|---|
| 1 | `heliosBench` | archived 956 KB | ABSORBED_FULL_HISTORY | ✅ DELETE-SAFE (Wave A) |
| 2 | `Benchora` | active 450 KB | CANONICAL_ACTIVE | ❌ DO NOT DELETE (Wave B) |
| 3 | `PhenoSpecs` | active 1.98 MB | CANONICAL_ACTIVE | ❌ DO NOT DELETE (Wave B) |
| 4 | `pheno-agents-md` | archived 43 KB | CANONICAL_ACTIVE | ❌ DO NOT DELETE (Wave B) |
| 5 | `pheno-cdylib-bridge` | archived 72 KB | ABSORBED_FULL_SQUASH | ✅ DELETE-SAFE (Wave A) |
| 6 | `pheno-context` | archived 72 KB | CANONICAL_ACTIVE | ❌ DO NOT DELETE (Wave B) |
| 7 | `pheno-control-plane` | archived 20 KB private | ABSORBED (Wave C, local commit staged) | ✅ DELETE-SAFE pending push (Wave A) |
| 8 | `pheno-forge-plugins` | archived 66 KB | ABSORBED (Wave C, local commit staged) | ✅ DELETE-SAFE pending push (Wave A) |
| 9 | `pheno-forge-smoke` | archived 90 KB | ABSORBED_FULL_SQUASH | ✅ DELETE-SAFE (Wave A) |
| 10 | `pheno-mcp-router` | archived 27 KB | CANONICAL_ACTIVE | ❌ DO NOT DELETE (Wave B) |
| 11 | `pheno-research` | archived 22 KB private | ABSORBED_FULL (commit `be5da947` + earlier) | ✅ DELETE-SAFE (Wave A) |
| 12 | `pheno-runtime-config` | archived 28 KB private | ABSORBED_FULL_SQUASH | ✅ DELETE-SAFE (Wave A) |
| 13 | `phenodag` | archived 282 KB Go | ABSORBED_PHASED_MIGRATION | ✅ DELETE-SAFE (Wave A) |

**Final tally**: 8 DELETE-SAFE + 5 KEEP_CANONICAL. No HOLD repos remain.

## Wave A: 8 repos safe to delete (request user confirmation)

| # | Repo | Absorb PR | Tech |
|---|---|---|---|
| 1 | `KooshaPari/heliosBench` | `phenotype-tooling#78` (`172ab8fd`) | `git-subtree-split: 5f85de67`, history-preserving |
| 2 | `KooshaPari/pheno-cdylib-bridge` | `pheno#282` (`c3f47016`) | squash with provenance |
| 3 | `KooshaPari/pheno-runtime-config` | `pheno#282` (`c3f47016`, 1/4) | squash with provenance |
| 4 | `KooshaPari/pheno-forge-smoke` | `pheno#282` (`c3f47016`, 1/4) | squash with provenance |
| 5 | `KooshaPari/phenodag` | `Tracera#723`+`#725`+`#727`, `AgilePlus#895` | phased migration; 11 queue files + spec doc |
| 6 | `KooshaPari/pheno-research` | `pheno` `be5da947` + earlier commits | full recovery: 13 via be5da947 + 9 via earlier |
| 7 | `KooshaPari/pheno-control-plane` | local commit in `chore/absorb-pheno-control-plane-2026-09-01` (phenotype-fleet-ops worktree, **pending push**) | subtree absorb, 7 files |
| 8 | `KooshaPari/pheno-forge-plugins` | local commit in `chore/absorb-pheno-forge-plugins-2026-09-01` (phenotype-tooling worktree, **pending push**) | subtree absorb, 6 plugins + systemd unit |

Repos #1–#6 have absorbed content **already on remote main**.
Repos #7–#8 have absorb content committed **locally only**; the user must push the
absorb branch and merge before issuing `gh repo delete`.

## Wave B: 5 repos to KEEP (do NOT delete)

1. `Benchora` — active 2026-09-01, has homepage `benchora.phenotype.space`
2. `PhenoSpecs` — active 2026-09-01, 16 open spec issues
3. `pheno-agents-md` — registry commit `60d530a3` confirms canonical active
4. `pheno-context` — registry commit `bb86721b` confirms canonical active
5. `pheno-mcp-router` — registry commit `cc7de1d2` confirms canonical active

Registry rows for all 5 corrected from stale `fsm=deleted` to `fsm=active`.

## Wave C: staged absorbs (now COMPLETE — 3 of 3)

| Source | Local absorb branch | Target path | Status |
|---|---|---|---|
| `pheno-control-plane` | `chore/absorb-pheno-control-plane-2026-09-01` | `phenotype-fleet-ops/agent-devops-setups/tailnet-control-plane/` | ✅ local commit, **pending push** |
| `pheno-forge-plugins` | `chore/absorb-pheno-forge-plugins-2026-09-01` | `phenotype-tooling/.forgecode/plugins/pheno-{cognee,config,letta,mem0,supermemory,tracing}/` | ✅ local commit, **pending push** |
| `pheno-research` | (already merged via `be5da947` + earlier commits on `pheno` main) | `pheno/{audit,devices,docs,experiments,promotion,schemas,sync}/` + 9 root configs | ✅ all 22 files present |

## Registry changes

- **Version bump**: `v1.6.82 → v1.6.83`
- **Rows updated**: 13 existing rows patched (5 ABSORB + 5 KEEP_CANONICAL corrections + 3 Wave-C re-classifications PARTIAL→ABSORB)
- **Rows added**: 4 new rows (pheno-forge-smoke, pheno-control-plane, pheno-research, pheno-mcp-router — last one was a missing-row gap)
- **Drift fixes**: 4 stale `fsm=deleted` rows corrected to `fsm=active` (Benchora, PhenoSpecs, pheno-agents-md, pheno-context)
- **New registry target-path correction**: `pheno-forge-plugins` registry claimed `phenotype-tooling/plugins/pheno-forge/` but that path is absent on remote; corrected to `.forgecode/plugins/` (already contains `elicitate/` crate's plugin)

## Audit artifacts produced (in this worktree)

- `audits/absorption-justifications/heliosBench-2026-09-01.md`
- `audits/absorption-justifications/Benchora-2026-09-01.md`
- `audits/absorption-justifications/PhenoSpecs-2026-09-01.md`
- `audits/absorption-justifications/pheno-agents-md-2026-09-01.md`
- `audits/absorption-justifications/pheno-cdylib-bridge-2026-09-01.md`
- `audits/absorption-justifications/pheno-context-2026-09-01.md`
- `audits/absorption-justifications/pheno-control-plane-2026-09-01.md`
- `audits/absorption-justifications/pheno-forge-plugins-2026-09-01.md`
- `audits/absorption-justifications/pheno-forge-smoke-2026-09-01.md`
- `audits/absorption-justifications/pheno-mcp-router-2026-09-01.md`
- `audits/absorption-justifications/pheno-research-2026-09-01.md`
- `audits/absorption-justifications/pheno-runtime-config-2026-09-01.md`
- `audits/absorption-justifications/phenodag-2026-09-01.md`

## Project JSONs produced

- `projects/heliosBench-2026-09-01.json`
- `projects/pheno-cdylib-bridge-2026-09-01.json`
- `projects/pheno-runtime-config-2026-09-01.json`
- `projects/pheno-forge-smoke-2026-09-01.json`
- `projects/phenodag-2026-09-01.json`
- `projects/pheno-control-plane-2026-09-01.json`
- `projects/pheno-forge-plugins-2026-09-01.json`
- `projects/pheno-research-2026-09-01.json`
- `projects/pheno-mcp-router-2026-09-01.json`

## Local work landed (this session)

1. **Registry worktree**: `worktrees/phenotype-registry-audit-2026-09-01-13sources`
   - Branch: `chore/audit-2026-09-01-13-sources`
   - HEAD: `5cc6d86d`
   - Files changed: `registry/disposition-index.json` (v1.6.83), 13 absorption-justifications + 9 project JSONs + this summary
   - **NOT pushed** to `phenotype-registry` remote (user's call)

2. **fleet-ops absorb worktree**: `worktrees/fleet-ops-absorb-pheno-control-plane-2026-09-01`
   - Branch: `chore/absorb-pheno-control-plane-2026-09-01`
   - Files added: `agent-devops-setups/tailnet-control-plane/{compose,bridge,docs,README.md,ABSORPTION.md}` (7 source files + provenance)
   - **NOT pushed** to `phenotype-fleet-ops` remote (user's call)

3. **tooling absorb worktree**: `worktrees/tooling-absorb-pheno-forge-plugins-2026-09-01`
   - Branch: `chore/absorb-pheno-forge-plugins-2026-09-01`
   - Files added: `.forgecode/plugins/pheno-{cognee,config,letta,mem0,supermemory,tracing}/` (6 plugins, 54 files) + `systemd/pheno-forge-sidecars.target` + 5 metadata/provenance files (61 files total)
   - **NOT pushed** to `phenotype-tooling` remote (user's call)

## gh repo delete — REQUEST (not executed)

Per user standing order ("ASK me to delete … after extensive confirmation"), the 8 Wave A repos are listed below for user-run deletion. **I have not run `gh repo delete` and will not until the user says the exact word.**

For repos #7 and #8 below (`pheno-control-plane`, `pheno-forge-plugins`), the absorb commit exists locally but is **NOT yet on remote**; the user must push and merge the absorb branch first before running `gh repo delete`.

```bash
# After reviewing this worktree, push, and merging absorb branches:
git -C worktrees/phenotype-registry-audit-2026-09-01-13sources push origin chore/audit-2026-09-01-13-sources
# Then open phenotype-registry PR with this branch and merge.

# For pheno-control-plane absorb:
git -C worktrees/fleet-ops-absorb-pheno-control-plane-2026-09-01 push origin chore/absorb-pheno-control-plane-2026-09-01
# Then open phenotype-fleet-ops PR and merge.

# For pheno-forge-plugins absorb:
git -C worktrees/tooling-absorb-pheno-forge-plugins-2026-09-01 push origin chore/absorb-pheno-forge-plugins-2026-09-01
# Then open phenotype-tooling PR and merge.

# After all 3 PRs merge:
gh repo delete KooshaPari/heliosBench            --yes   # PR phenotype-tooling#78
gh repo delete KooshaPari/pheno-cdylib-bridge    --yes   # PR pheno#282
gh repo delete KooshaPari/pheno-runtime-config   --yes   # PR pheno#282
gh repo delete KooshaPari/pheno-forge-smoke      --yes   # PR pheno#282
gh repo delete KooshaPari/phenodag               --yes   # PRs Tracera#723/#725/#727 + AgilePlus#895
gh repo delete KooshaPari/pheno-research         --yes   # be5da947 + earlier
gh repo delete KooshaPari/pheno-control-plane    --yes   # local absorb staged
gh repo delete KooshaPari/pheno-forge-plugins    --yes   # local absorb staged
```

## Outstanding (post-deletion)

1. Rename `phenotype-registry/crates/pheno-dag/` to
   `phenotype-registry/crates/phenotype-dag-core/` to break the
   `phenodag` (Go, deleted) name collision.
2. Update `phenodag.phenotype.space` homepage redirect to
   `tracera.phenotype.space` before GH deletion (if user approves
   Wave A deletion).
3. Audit the ~80 KB delta between `PhenoSpecs` (1.98 MB) source and
   `phenotype-registry/docs/specs/pheno-specs/` (1.9 MB) mirror.

## Method (evidence-based)

Each source was verified by:
1. `gh api repos/KooshaPari/<src>` — confirms existence, archived flag, last push
2. `gh api repos/KooshaPari/<target>/contents/<expected-path>` — confirms the
   absorbed path lives on the target's remote HEAD
3. `gh api search/commits?q=repo:KooshaPari/<target>+<src>` — finds the actual
   absorb commit(s) on each candidate target
4. Read the absorb commit's message + file list — confirms scope, technique
   (squash / subtree / orphan merge), and provenance
5. Checked for "remove wrong retroactive stub" commits — these tell us a
   source is canonical active, never deleted (counter-classification to
   "absorbed")
6. Cross-checked `phenotype-registry/registry/disposition-index.json` on
   remote (1,033 rows)
7. For Wave C repos: read source content directly, verified target remote
   path, staged absorb commits in local worktrees, bytewise-verified
   semantic equivalence where overlap with existing target content