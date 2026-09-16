# Audit justification: pheno-agents-md — KEEP_CANONICAL_STANDALONE

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `AUTO-IMPORT-pheno-agents-md`
**Decision**: KEEP_CANONICAL_STANDALONE — DO NOT DELETE

## Why NOT absorb?

1. **Registry commit confirms canonical role**: `60d530a3` "remove wrong
   retroactive stub for pheno-agents-md (source repo is canonical active,
   never deleted)". This commit explicitly retracted any prior absorption
   classification.

2. **Functionality survives as workflow templates, not as a crate**: the
   AGENTS.md parsing logic lives in shared workflow templates:
   - `OmniRoute/.github/workflows-templates/pheno-agents-md.yml`
   - `.omni-remediate-20260826/.github/workflows-templates/pheno-agents-md.yml`

3. **Source is the spec-of-truth**: 43 KB Rust crate that parses/validates
   AGENTS.md manifests. The spec format is documented in the source repo
   and is referenced from many downstream consumers.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 43 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-07-29 |
| archived_at | 2026-07-29 |
| visibility | public |

## Forward-looking note

**DO NOT DELETE**. The source remains canonical for AGENTS.md spec
validation. The functionality is mirrored as workflow templates, but the
source code is still the SSOT for the spec format itself.

## References

- commit `60d530a3` — "remove wrong retroactive stub for pheno-agents-md"
- target row: `AUTO-IMPORT-pheno-agents-md` (registry v1.6.83, CORRECTED)
- boundary: `docs/boundary/pheno-agents-md.md`
- workflow mirrors: `OmniRoute/.github/workflows-templates/pheno-agents-md.yml`,
  `.omni-remediate-20260826/.github/workflows-templates/pheno-agents-md.yml`
