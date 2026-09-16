# Conft and Settly deletion package

Date: 2026-06-20
Decision: DELETE
Confidence: high

## Executive decision

Conft and Settly can be deleted. Their surviving configuration responsibilities are now owned by Configra. Configra main contains Conft absorption records, config-schema and pheno-config crates, and a full crates/settly copy with source, tests, docs, CI metadata, and governance artifacts. Local-ahead source work from both archived repos is preserved here as patchsets before deletion.

## Absorption matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|-------------|-----------------|----------|--------------|-------------|-----------------|--------|------------------------|-----------------|-----------------|
| Conft config-schema crate | Conft/crates/config-schema | Public Rust crate | implemented | Configra | crates/config-schema | DONE | Crate exists in canonical Configra target | low | none |
| Conft pheno-config crate | Conft/crates/pheno-config | Public Rust crate | implemented | Configra | crates/pheno-config | DONE | Crate exists in canonical Configra target with README/examples/tests | low | none |
| Conft docs and governance | Conft/README.md, SPEC.md, charter.md, docs/* | Docs/spec/governance | docs-only | Configra and phenotype-registry | ABSORBED-FROM/Conft plus source-docs/Conft | DONE | Canonical target records absorption; source docs preserved here | low | none |
| Conft local ahead commit | Conft main ahead origin/main: tier-0 hygiene snapshot | Historical local work | local-only | phenotype-registry | patches/Conft/local-ahead.patch | DONE | Local-only work preserved before deletion | medium; loss of local snapshot | none |
| Settly layered configuration crate | Settly/src/*, Cargo.toml, tests, benches, fuzz | Public Rust crate | implemented | Configra | crates/settly/src, crates/settly/benches, crates/settly/fuzz | DONE | Full Settly crate exists in Configra | low | none |
| Settly docs/spec/ADR/product claims | Settly/README.md, SPEC.md, PRD.md, PLAN.md, ADR.md, docs/* | Docs/spec/ADR | implemented/docs-only | Configra and phenotype-registry | crates/settly docs plus source-docs/Settly | DONE | Runtime docs in target; curated source docs preserved here | low | none |
| Settly deprecation notice | Settly/DEPRECATED.md and remote archived true | Governance | deprecated | Configra and phenotype-registry | Configra absorption records and this package | INTENTIONALLY_DEPRECATED | Source explicitly deprecated in favor of Configra and remote is archived | low | none |
| Settly local ahead branch work | Settly worktrees/orch-v12-s1-002 ahead origin/main | Branch/local history | branch-only/local-only | phenotype-registry | patches/Settly/local-ahead.patch | DONE | Patchset preserves local branch commits before deletion | medium | none |
| Duplicate local checkout name | local Settly and settly both same repo/branch | Local workspace artifact | duplicate checkout | phenotype-registry | this package | NO_MERIT | Duplicate local casing has no distinct source artifact beyond same git repo | low | remove local duplicate |

## Gaps and exceptions

No LAST_RESORT_EXCEPTION remains. Build artifacts under Conft/target and Settly/target were intentionally not preserved because they are generated files with no independent source intent.

## Merit of broken/scaffold work

Generated target directories have no merit. Local snapshot commits do have historical merit and are preserved as patches. Docs-only artifacts have rationale merit and are preserved in Configra and this registry package.

## Final deletion recommendation

DELETE Conft and Settly after this registry PR merges. Remove both local Settly casing checkouts if present.
