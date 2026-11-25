# Audit justification: pheno-context — KEEP_CANONICAL_STANDALONE

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry rows `repo-pheno-context`, `queue-repo-pheno-context`, `queue-repo-pheno-context-stamp`
**Decision**: KEEP_CANONICAL_STANDALONE — DO NOT DELETE

## Why NOT absorb?

1. **Registry commit confirms canonical role**: `bb86721b` "remove wrong
   retroactive stub for pheno-context (source repo is canonical active,
   never deleted)". This commit explicitly retracted any prior absorption
   classification.

2. **Source is the spec-of-truth**: 72 KB Rust crate defining the canonical
   `Context` struct + 32+ header extraction. The struct is the spine of the
   substrate family.

3. **Mirror exists at pheno monorepo**: `pheno/crates/pheno-context/` was
   added via PR `pheno#282` (commit `c3f47016`, 2026-07-17). The mirror is
   a copy, not a replacement.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 72 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-02 |
| archived_at | 2026-08-02 |
| visibility | public |

## Drift fix

The 2026-07-18 registry freeze marked pheno-context with `fsm=deleted`
in some rows, but the source GH repo was never actually deleted. The
`bb86721b` commit explicitly reaffirmed canonical-active. This audit row
corrects the drift: `fsm=active, deleted_at=null` across all 3 affected rows.

## Forward-looking note

**DO NOT DELETE**. The source remains canonical for the `Context` struct
specification. The mirror is a copy. Any gh repo delete would break the
spec surface for downstream consumers.

## References

- commit `bb86721b` — "remove wrong retroactive stub for pheno-context"
- PR `pheno#282` (commit `c3f47016`) — mirror absorb
- target row: `repo-pheno-context` (registry v1.6.83, CORRECTED)
- boundary: `docs/boundary/pheno-context.md`
- prior justification: `pheno-context-2026-06-29.md`
