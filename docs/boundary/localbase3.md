# localbase3 boundary / disposition

**Status**: AFFIRMED (canonical, NOT absorbed)
**Source**: `KooshaPari/localbase3`
**Air-record**: 2026-07-17, registry v1.6.30
**Disposition**: AFFIRM (canonical full-stack project)

## Why AFFIRM and not ABSORB?

localbase3 is a multi-service full-stack project with **its own
production identity**:

| Subsystem        | bytes | Role |
| ---------------- | ----- | ---- |
| localbase/       |  ~7K  | core domain |
| localbase-api/   | ~14K  | Express/Node.js backend |
| localbase-chain/ |  ~1K  | blockchain adapter |
| localbase-docs/  |  ~2K  | project docs |
| localbase-frontend/ | ~4K | UI |
| localbase-provider/ | ~2K | external provider adapters |
| localbase-tests/ |  ~3K  | integration tests |
| src/services/    |  ~2K  | shared services |
| amp/             |  ~3K  | agent orchestration |
| ~87000 LOC       | total | TS/JS/HTML/CSS/Python/shell |

Absorbing this into the registry or any other monorepo would lose its
product identity, break deployment topologies, and create cross-tenant
churn. localbase3 IS a Phenotype-org adjacent project — it works on
Phenotype runtime hooks (the `mcp_server_browser_use.log` and
`fix_localbase_tests.*` scripts show Phenotype-style interaction) — but
its primary identity is its own product.

## What changed on 2026-07-17

1. **Verified alive**: 32 remote branches, last push 2026-06-08,
   size 256KB.
2. **Verified read-only safe**: main branch has a 3011bde commit that
   rewrites HEAD to an empty tree (the repo was deliberately emptied
   during the wave-7 reorganization). Real source-of-truth lives on
   `airlock-recovery/main` and the various `chore/*` branches.
3. **Marked AFFIRM** in registry v1.6.30 row `repo-localbase3` —
   disposition remains AFFIRM, fsm transitioned active → verified.

## If you are reading this from localbase3 itself

- The headline disposition is unchanged: AFFIRMED.
- The position in the registry is row `repo-localbase3`.
- Any future relocations (e.g. into PhenoApps as `apps/localbase3`)
  must come with a fresh ADR (proposed: ADR-122) before the row is
  flipped from AFFIRM to ABSORB.
