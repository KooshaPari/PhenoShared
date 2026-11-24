# Profila deletion package

Date: 2026-06-20
Decision: DELETE
Confidence: high

## Executive decision

Profila can be deleted. Its surviving profiling scripts and public intent are represented by pheno-profiling, whose README and SPEC explicitly state that it replaces Profila per ADR-021. The pheno-profiling target is archived, so this pass does not mutate it; registry preserves the local-ahead patchset and source specs/docs before deleting the source repo.

## Absorption matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|-------------|-----------------|----------|--------------|-------------|-----------------|--------|------------------------|-----------------|-----------------|
| System metrics profiler | Profila/bin/system_metrics.py | Public Python script | implemented | pheno-profiling | src/pheno_profiling/profilers/system_metrics.py | DONE | Equivalent profiler exists in target package | low | none |
| Complexity analyzer | Profila/bin/complexity_analyzer.py | Public Python script | implemented | pheno-profiling | src/pheno_profiling/profilers/complexity_analyzer.py | DONE | Equivalent analyzer exists in target package | low | none |
| Continuous profiler | Profila/bin/continuous_profiler.py | Public Python script | implemented | pheno-profiling | src/pheno_profiling/profilers/continuous_profiler.py | DONE | Equivalent profiler exists in target package | low | none |
| Chart generator | Profila/bin/generate_charts.py | Public Python script | implemented | pheno-profiling | src/pheno_profiling/profilers/generate_charts.py | DONE | Equivalent chart generator exists in target package | low | none |
| Shell profiler suite claim | Profila README/docs, pheno-profiling README migration table | CLI/scripts | implemented/claimed | pheno-profiling | README migration table and docs/SPEC.md sections 3.1-3.3 | SUPERSEDED_PARITY | Target documents all 11 Profila scripts as migrated | low-medium; shell-script behavior drift if target archive incomplete | none |
| Profila docs/specs | Profila/PRD.md, ADR.md, BOUNDARY.md, docs/specs/*, kitty-specs/* | Docs/spec/ADR | docs-only | pheno-profiling and phenotype-registry | pheno-profiling/docs/SPEC.md plus source-docs/source-specs here | DONE | Canonical target spec plus original docs preserved in registry | low | none |
| Profila explicit deprecation | Profila/DEPRECATED.md, MOVED_TO_OBSERVABILITYKIT.md, remote archived true | Governance | deprecated | pheno-profiling/phenotype-registry | pheno-profiling README/SPEC and this package | INTENTIONALLY_DEPRECATED | Source explicitly superseded by profiling/observability substrate | low | none |
| Profila local ahead commit | Profila chore/spec-docs ahead origin/chore/spec-docs | Historical local work | local-only | phenotype-registry | patches/local-ahead.patch | DONE | Local snapshot preserved before deletion | medium | none |
| Spec-kitty command scaffolds | Profila/.claude, .codex, .cursor, .github/prompts, .kilocode | Tooling scaffold | scaffold | phenotype-registry | source-specs and final package note | NO_MERIT | Generic command scaffolds are not profiling domain artifacts; specs are preserved | low | none |

## Gaps and exceptions

No LAST_RESORT_EXCEPTION remains. The target pheno-profiling repo is archived, so future improvements should happen only if that target is intentionally reactivated or moved into a broader observability substrate.

## Final deletion recommendation

DELETE Profila after this registry PR merges. Preserve pheno-profiling as the archived canonical replacement; do not delete it in this pass.
