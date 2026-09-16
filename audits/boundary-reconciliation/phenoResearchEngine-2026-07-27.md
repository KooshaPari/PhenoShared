# phenoResearchEngine boundary reconciliation

**Date:** 2026-07-27  
**Disposition:** `REVIEW_TARGET_CONFLICT`  
**Source:** `KooshaPari/phenoResearchEngine` (private, MIT, `main` at `ae736233e612dd1f744b1619e374d22771def3b1`)

## Finding

The registry's 2026-07-17 `ABSORB -> phenoAI` claim is not currently reproducible from remote state:

- GitHub reports the source repository as **unarchived**, private, and updated 2026-07-18.
- The source has post-deprecation commits through 2026-07-02, including retrieval functionality and tests.
- `DEPRECATED.md` says the intended destination is `packages/phenotype-research/` in the monorepo, but no matching path exists in `KooshaPari/phenoAI`.
- `KooshaPari/pheno/main` links `phenotype-research-engine` as a separate submodule at `efb1656e03b02bc2bc76256fb46f709b1f388ca6`, not the private `phenoResearchEngine` repository.

## Decision

Downgrade the source record to `deprecated` with `REVIEW_TARGET_CONFLICT`. Preserve the prior absorption justification as historical evidence. Do not archive, delete, or remove the source. A future `ABSORB` decision requires a verifiable target commit/path and transfer manifest, or an explicit sponsor decision to keep the private source standalone.

## Evidence

- Source metadata: `gh api repos/KooshaPari/phenoResearchEngine`
- Source tree: `gh api 'repos/KooshaPari/phenoResearchEngine/git/trees/main?recursive=1'`
- Source deprecation notice: `DEPRECATED.md`
- Candidate target checks: `gh api 'repos/KooshaPari/phenoAI/git/trees/main?recursive=1'`, `gh api repos/KooshaPari/pheno/contents/phenotype-research-engine`
