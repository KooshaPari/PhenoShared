# dagctl deletion package

Date: 2026-06-20
Decision: DELETE
Confidence: high

## Executive decision

dagctl can be deleted. The repository is binary-only; both dagctl and the untracked phenodag file are Mach-O arm64 executables. GitHub description states source lives in phenodag. phenodag PR #13 completed dagctl absorption/version bump, and phenodag PR #14 merged provenance docs. The remaining local dagctl commit is a tier-0 hygiene snapshot and is preserved here as a patch.

## Absorption matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|-------------|-----------------|----------|--------------|-------------|-----------------|--------|------------------------|-----------------|-----------------|
| dagctl executable | dagctl/dagctl Mach-O binary | Binary artifact | generated/binary-only | phenodag | phenodag PR #13, repo source files | SUPERSEDED_PARITY | Source repo is phenodag; binary is reproducible artifact | low | none |
| untracked phenodag executable | dagctl/phenodag Mach-O binary | Binary artifact | untracked/generated | phenodag | phenodag main and PR #13 | NO_MERIT | Untracked local binary has no independent source intent; SHA preserved | low | none |
| dagctl version marker/docs | dagctl/README.md, VERSION | Docs/metadata | docs-only | phenodag and phenotype-registry | phenodag PR #13/#14, source-docs here | DONE | Target owns source/version; small docs preserved | low | none |
| dagctl local ahead commit | dagctl chore/security-audit-dagctl ahead main | Historical local work | local-only | phenotype-registry | patches/local-ahead.patch | DONE | Local snapshot preserved before deletion | medium | none |
| dagctl binary hashes | local shasum -a 256 dagctl phenodag | Evidence | generated | phenotype-registry | binary-sha256.txt | DONE | Hashes preserve identification without storing binaries | low | none |

## Gaps and exceptions

No LAST_RESORT_EXCEPTION remains.

## Final deletion recommendation

DELETE dagctl after this registry PR merges. Keep phenodag active as canonical source.
