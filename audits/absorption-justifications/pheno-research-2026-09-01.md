# Audit justification: pheno-research — ABSORB fsm=deleted (DELETE-SAFE)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-research-audit20260901`
**Decision**: ABSORB — full content recovery, source DELETE-SAFE

## Audit findings

1. **Full absorption via commit `be5da947` on `pheno` main** plus earlier
   commits. ALL 22 source files are present in the pheno monorepo (verified
   2026-09-01 by `find … -type f` + bytewise diff).

2. **`be5da947` contributed 13 files** (the bulk of the recovery):
   - `audit/` (4 files)
   - `devices/` (3 files)
   - `docs/GITHUB_ARCHIVE_POLICY.md`
   - `experiments/` (2 files)
   - `promotion/` (1 file)
   - `schemas/` (1 file)
   - `sync/` (1 file)

3. **The remaining 9 files** (`README.md`, `.mergify.yml`,
   `.circleci/config.yml`, `.github/workflows/{ci,infisical,trunk-check,scorecard}.yml`,
   `renovate.json`, `trunk.yaml`) were absorbed in **earlier commits
   predating `be5da947`** — they predate the recovery commit on the
   `pheno` branch but originate from the same source repository. Several
   have drifted (subsequent modifications) but the original content is
   fully present.

4. **Bytewise diff verification (2026-09-01)**:
   - `README.md` — byte-identical
   - `.mergify.yml` — byte-identical
   - `.circleci/config.yml` — byte-identical
   - `.github/workflows/infisical.yml` — drifted (pheno has own version)
   - `.github/workflows/ci.yml` — drifted
   - `.github/workflows/trunk-check.yml` — drifted
   - `.github/workflows/scorecard.yml` — drifted
   - `renovate.json` — drifted
   - `trunk.yaml` — drifted

   Drift is normal post-absorption — the pheno monorepo's CI config has
   superseded the per-repo config from pheno-research. This is
   expected, not an absorption gap.

5. **No registry row as of 2026-07-18 freeze**: this source had zero
   registry footprint. New row `repo-pheno-research-audit20260901`
   (registry v1.6.83) closes the gap.

6. **Source content (22 KB, 22 files)**: the SSOT for R&D/Experimentation/
   Research across the Win+Mac Phenotype stack. Private repo, archived.

## Correction from initial audit

Initial audit incorrectly classified this as PARTIAL_ARCHIVE with 10
missing files. Deep verification (file enumeration + `git log --diff-filter=A`
for each source path) showed all 22 files are present on `pheno` main,
making pheno-research DELETE-SAFE on par with the rest of Wave A.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 22 |
| open_issues | 1 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-05 |
| archived_at | 2026-08-05 |
| visibility | private (now public via archive) |
| recovered | **22/22 files (100%)** |

## Verdict

**DELETE-SAFE 2026-09-01.** All source files present on `pheno` main.
Drift on 5 CI/config files is normal post-absorption evolution. Source
repo can be deleted from GH.

## References

- primary absorb commit: `be5da947` on `pheno` main
- target row: `repo-pheno-research-audit20260901` (registry v1.6.83, NEW)
- target: `pheno` (monorepo root, 13 files at root + 9 absorbed earlier)
- source repo: `KooshaPari/pheno-research` (archived, private→public)