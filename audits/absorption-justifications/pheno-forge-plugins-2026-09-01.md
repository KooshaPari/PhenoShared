# Audit justification: pheno-forge-plugins — PARTIAL_ARCHIVE (in-progress, target path corrected)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-forge-plugins`
**Decision**: PARTIAL_ARCHIVE — staged for absorb into phenotype-tooling/.forgecode/plugins/

## Audit findings

1. **Never absorbed on remote**: zero commit/PR/branch references across all
   candidate target repos (phenotype-hub, phenotype-tooling, pheno,
   phenotype-fleet-ops). The source repo was archived but no absorb PR was
   ever opened.

2. **Registry target path was wrong**: the 2026-07-18 freeze marked target
   as `phenotype-tooling (plugins/pheno-forge/)`. That path does NOT exist
   on the remote HEAD (`phenotype-tooling` has no `plugins/` directory).
   The actual matching path on remote is
   `phenotype-tooling/.forgecode/plugins/` (currently contains only
   `elicitate/`).

3. **Source content (66 KB, 6 plugins)**:
   - `pheno-supermemory/` — long-term memory sidecar (systemd unit +
     spawn/teardown/healthcheck scripts)
   - `pheno-tracing/` — distributed tracing sidecar
   - `pheno-letta/` — letta agent sidecar
   - `pheno-mem0/` — mem0 short-term memory sidecar
   - `pheno-config/` — runtime config sidecar
   - `pheno-cognee/` — cognee knowledge-graph sidecar
   - plus SCOPE.md, README, LICENSE, .gitignore

## Corrected planned absorb target

**`phenotype-tooling/.forgecode/plugins/pheno-{supermemory,tracing,letta,mem0,config,cognee}/`**

Rationale:
- `phenotype-tooling/.forgecode/plugins/` already houses plugins with the
  same per-plugin layout pattern (currently `elicitate/`).
- Per-plugin subdirectory matches existing convention.
- Each plugin will retain its systemd unit + spawn/teardown/healthcheck
  scripts.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 66 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-02 |
| archived_at | 2026-08-02 |
| visibility | public |

## Forward-looking note

**HOLD — not DELETE-SAFE**. The source has never been absorbed. The
registry's claimed target path is wrong. A new PR is required to land the
6 plugins into `phenotype-tooling/.forgecode/plugins/pheno-*/` before the
GH source can be deleted.

PR scope (planned):
- Move 6 plugin directories into
  `phenotype-tooling/.forgecode/plugins/pheno-{supermemory,tracing,letta,mem0,config,cognee}/`
- Update `phenotype-tooling/.forgecode/plugins/README.md` with new plugin list
- Update registry row with corrected target + pr fields
- Update `phenotype-tooling/ABSORPTION.md` (if exists) with new absorb record

Estimated effort: 3 hours (6 plugins × ~30 min each for layout adaptation).

## References

- target row: `repo-pheno-forge-plugins` (registry v1.6.83, target CORRECTED)
- planned target: `phenotype-tooling/.forgecode/plugins/pheno-{supermemory,tracing,letta,mem0,config,cognee}/`
- existing sibling: `phenotype-tooling/.forgecode/plugins/elicitate/`
- source repo: `KooshaPari/pheno-forge-plugins` (archived)
