# Successor-target discrepancy

This repository's deprecation notices claim a successor target that does
not currently exist. This document records the discrepancy and the
implications.

## What the package claims

| Source | Claim |
|---|---|
| `README.md` (line 21) | "**Archived**: Functionality has been consolidated into the main Phenotype monorepo structure under `packages/phenotype-research/`" |
| `DEPRECATED.md` | "migration to `@phenotype/research`" |
| `ADR.md` (governance) | "Records the rationale for the reorganisation" |

The intended successor target is `KooshaPari/phenoAI/python/phenotype-research/`
(or the monorepo equivalent at `packages/phenotype-research/`).

## What actually exists (verified 2026-09-09)

`KooshaPari/phenoAI` does not contain a `phenotype-research` directory at
any path. Direct GitHub tree query:

```
$ gh api '/repos/KooshaPari/phenoAI/git/trees/HEAD?recursive=1'
→ 0 paths matching 'phenotype-research' or 'phenotype_research'
```

`KooshaPari/pheno/main` links `phenotype-research-engine` as a separate
git **submodule** pinned at `efb1656e03b02bc2bc76256fb46f709b1f388ca6`,
not as a directory in the monorepo.

`phenotype-registry/audits/boundary-reconciliation/phenoResearchEngine-2026-07-27.md`
already downgraded the 2026-07-17 `ABSORBED` claim because the destination
path does not match the source. Disposition is now:

```
deprecated + REVIEW_TARGET_CONFLICT
```

## Implications

1. **No live successor.** Consumers of `phenotype-research-engine` cannot
   migrate to the claimed target because it does not exist.
2. **The `KooshaPari/pheno` submodule pointer** is the actual de-facto
   successor: it pins this repo at commit `efb1656e03b02bc2bc76256fb46f709b1f388ca6`.
3. **Manifest contradiction (resolved in PR #66).** The `pyproject.toml`
   classifier was previously `3 - Alpha`, contradicting the README's
   `DEPRECATED` status. PR #66 (`7a5f308`) flipped it to `7 - Inactive`
   to align with reality. This is the lower-cost half of the
   contradiction.
4. **GitHub archive flag** is not yet toggled (per the README, scheduled
   2026-09-18). Until the archive flag is set, the repo remains a live
   public/private remote that `pip install` may resolve to.

## What is required to close the gap

| Action | Owner | Effort |
|---|---|---|
| Decide whether `KooshaPari/phenoAI/packages/phenotype-research/` will be created | Operator | Decision |
| If yes: create it, copy `src/research_engine/*` from the airlock commit, deprecate this remote | Operator + registry owner | ~2 hours |
| If no: update README.md and DEPRECATED.md to point to the actual successor (`pheno` submodule pointer or a different target) | Operator | ~30 min |
| Confirm the GitHub archive flag toggle (currently scheduled 2026-09-18) | Operator | ~5 min |
| Update `phenotype-registry/audits/boundary-reconciliation/phenoResearchEngine-*.md` to note the disposition outcome | Registry owner | ~15 min |

## In-repo status (this branch)

This branch (which contains PR #66's classifier fix merged into
`origin/main = babe73ce`) does NOT attempt to close the gap. Closing
the gap is an operator + absorbed-consumers decision that requires
consent from the `KooshaPari/phenoAI` and `phenotype-registry` owners.

## Maintenance status (per PR #66's classifier flip)

```
classifiers = [
    "Development Status :: 7 - Inactive",  # was "3 - Alpha"
    ...
]
```

This is the truthful signal: the package is no longer actively
developed. `pip install phenoResearchEngine==0.1.0` now reports
`Inactive` instead of `Alpha`, which matches the README's
`DEPRECATED` status and the git history's post-2026-07-02 silence.

## References

- PR #66 (`7a5f308`): manifest-contradiction repair
- PR #67 (`1aa8632`): Ruff I001 + quality-gate.yml cargo→pytest
- PR #68 (`babe73ce`): workflow action-pin resolution
- `phenotype-registry/audits/boundary-reconciliation/phenoResearchEngine-2026-07-27.md`
- `phenotype-registry/audits/absorption-justifications/phenoResearchEngine-2026-07-17.md`
- DEPRECATED.md (README claim line 11)
- GitHub submodule `KooshaPari/pheno/main` → `phenotype-research-engine` @ `efb1656e03b02bc2bc76256fb46f709b1f388ca6`
