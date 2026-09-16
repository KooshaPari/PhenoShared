# Audit justification: pheno-mcp-router — KEEP_CANONICAL_STANDALONE

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-mcp-router-audit20260901` (NEW)
**Decision**: KEEP_CANONICAL_STANDALONE — DO NOT DELETE

## Why NOT absorb?

1. **Registry commit confirms canonical role**: `cc7de1d2` "remove wrong
   retroactive stub for pheno-mcp-router (source repo is canonical active,
   never deleted)". This commit explicitly retracted any prior absorption
   classification.

2. **Source is the spec-of-truth**: 27 KB Python package — FastMCP router
   substrate with tier allowlist and payload sanitization. The routing
   spec is referenced from many downstream consumers.

3. **Mirror exists at phenotype-tooling/docs/absorbed-from-pheno-mcp-router/**:
   the source code was imported as a reference copy into
   `phenotype-tooling/docs/absorbed-from-pheno-mcp-router/`. The mirror is
   documentation, not a replacement.

## Gap fix

This source had NO registry disposition row as of 2026-07-18 freeze.
The new row `repo-pheno-mcp-router-audit20260901` (registry v1.6.83) closes
the gap.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 27 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-02 |
| archived_at | 2026-08-02 |
| visibility | public |

## Forward-looking note

**DO NOT DELETE**. The source remains canonical for the MCP routing spec.
The mirror at `phenotype-tooling/docs/absorbed-from-pheno-mcp-router/` is
documentation-only. Any gh repo delete would break the spec surface.

## References

- commit `cc7de1d2` — "remove wrong retroactive stub for pheno-mcp-router"
- target row: `repo-pheno-mcp-router-audit20260901` (registry v1.6.83, NEW)
- boundary: `docs/boundary/pheno-mcp-router.md`
- mirror: `phenotype-tooling/docs/absorbed-from-pheno-mcp-router/`
