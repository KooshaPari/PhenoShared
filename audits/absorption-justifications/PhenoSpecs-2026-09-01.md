# Audit justification: PhenoSpecs — KEEP_CANONICAL_STANDALONE

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry rows `DSPI-14`, `queue-DSPI-14`, `queue-repo-PhenoSpecs`
**Decision**: KEEP_CANONICAL_STANDALONE — DO NOT DELETE

## Why NOT absorb?

1. **Source repo is canonical active**: pushed 2026-09-01, 16 open issues,
   public visibility. The source is the SSOT for the Phenotype spec
   registry.

2. **Mirror exists at registry spine**: `phenotype-registry/docs/specs/pheno-specs/`
   was populated via commit `ea425d8f` ("feat: absorb Benchora + PhenoSpecs —
   registry boundary + absorption records"). The mirror is 1.9 MB
   (492 spec files); the source is 1.98 MB (delta of ~80 KB unaccounted).

3. **Spec body lives at the source**: the source GH repo is the live
   spec-writing surface (issues, PRs, change tracking). Mirroring into the
   registry was a one-way import for offline reference, not a replacement.

## What was absorbed

- `phenotype-registry/docs/specs/pheno-specs/` (1.9 MB) — mirror copy
- 492 spec files imported

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 1980 |
| open_issues | 16 (active spec issues) |
| stars/forks | ? / ? |
| last_push | 2026-09-01 |
| archived_at | — (not archived) |
| visibility | public |

## Drift fix

The 2026-07-18 registry freeze marked PhenoSpecs with `fsm=deleted`,
but the source GH repo was never actually deleted (it remains active
2026-09-01). This audit row corrects the drift: `fsm=active, deleted_at=null`.

## Forward-looking note

**DO NOT DELETE**. The source remains the canonical home for live spec
writing. Mirror is reference-only. Any gh repo delete would break the
spec-writing surface.

The ~80 KB delta between source (1.98 MB) and mirror (1.9 MB) should be
audited in a follow-up to ensure no spec files were dropped during the
2026-07 import.

## References

- commit `ea425d8f` — registry absorb of PhenoSpecs + Benchora
- target row: `DSPI-14` (registry v1.6.83, CORRECTED)
- boundary: `docs/boundary/PhenoSpecs.md`
